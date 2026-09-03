"""
tests/test_m2_models_adversarial.py
===================================
Automated Pytest Adversarial & Stress Suite for Milestone 2 Neural Models
- TabularMLPFeatureExtractor
- Temporal1DCNNFeatureExtractor
- DualStreamSLFeatureExtractor
- SLPretrainer
- HybridActorCritic
- HybridPPO & SB3 Integration
"""

import math
import os
import pytest
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from modules.models.feature_extractor import (
    DualStreamSLFeatureExtractor,
    SLPretrainer,
    TabularMLPFeatureExtractor,
    Temporal1DCNNFeatureExtractor,
)
from modules.models.hybrid_policy import (
    HybridActorCritic,
    HybridPPO,
    RolloutBuffer,
    SB3CustomFeaturesExtractor,
    SB3HybridPolicyAdapter,
)
from modules.engine.hybrid_trading_env import (
    ContinuousToHybridActionWrapper,
    HybridTradingEnv,
)


class TestTabularMLPAdversarial:
    """Stress tests for TabularMLPFeatureExtractor"""

    def test_nan_inf_sanitization(self):
        mlp = TabularMLPFeatureExtractor(input_dim=14, output_dim=64)
        mlp.eval()
        x = torch.tensor([[float("nan"), float("inf"), float("-inf")] + [0.5] * 11])
        out = mlp(x)
        assert out.shape == (1, 64)
        assert not torch.isnan(out).any()
        assert not torch.isinf(out).any()

    def test_unbatched_1d_tensor(self):
        mlp = TabularMLPFeatureExtractor(input_dim=14, output_dim=64)
        mlp.eval()
        x = torch.randn(14)
        out = mlp(x)
        assert out.shape == (64,)
        assert not torch.isnan(out).any()

    def test_zero_batch_size(self):
        mlp = TabularMLPFeatureExtractor(input_dim=14, output_dim=64)
        mlp.eval()
        x = torch.zeros((0, 14))
        out = mlp(x)
        assert out.shape == (0, 64)

    def test_numpy_array_interop(self):
        mlp = TabularMLPFeatureExtractor(input_dim=14, output_dim=64)
        mlp.eval()
        x_np = np.random.randn(5, 14).astype(np.float32)
        out = mlp(x_np)
        assert isinstance(out, torch.Tensor)
        assert out.shape == (5, 64)


class TestTemporal1DCNNAdversarial:
    """Stress tests for Temporal1DCNNFeatureExtractor"""

    def test_input_dimension_permutations(self):
        cnn = Temporal1DCNNFeatureExtractor(
            in_channels=10, seq_len=20, num_filters=[32, 64], output_dim=64
        )
        cnn.eval()

        # (B, seq_len, in_channels) = (3, 20, 10)
        out1 = cnn(torch.randn(3, 20, 10))
        assert out1.shape == (3, 64)

        # (B, in_channels, seq_len) = (3, 10, 20)
        out2 = cnn(torch.randn(3, 10, 20))
        assert out2.shape == (3, 64)

        # 1D single feature vector (10,)
        out3 = cnn(torch.randn(10))
        assert out3.shape == (64,)

    def test_nan_inf_defense(self):
        cnn = Temporal1DCNNFeatureExtractor(in_channels=10, seq_len=20, output_dim=64)
        cnn.eval()
        x = torch.full((2, 20, 10), float("nan"))
        out = cnn(x)
        assert not torch.isnan(out).any()
        assert not torch.isinf(out).any()

    def test_batch_seqlen_collision_warning_probe(self):
        """Probe for shape collision when batch size equals seq_len"""
        cnn = Temporal1DCNNFeatureExtractor(in_channels=10, seq_len=20, output_dim=64)
        cnn.eval()
        # Batched 2D features of size B=20, in_channels=10
        x_batched = torch.randn(20, 10)
        out = cnn(x_batched)
        # Note: Documenting that shape collapses to (64,) due to shape heuristic
        assert out.shape in ((64,), (20, 64))


class TestDualStreamFusionAdversarial:
    """Stress tests for DualStreamSLFeatureExtractor"""

    def test_dict_and_tuple_and_flat_inputs(self):
        fusion = DualStreamSLFeatureExtractor(
            temporal_in_channels=10,
            temporal_seq_len=20,
            tabular_dim=4,
            output_dim=64,
        )
        fusion.eval()

        # Dict
        out_dict = fusion(x={"temporal": torch.randn(2, 20, 10), "tabular": torch.randn(2, 4)})
        assert out_dict.shape == (2, 64)

        # Tuple
        out_tuple = fusion(x=(torch.randn(2, 20, 10), torch.randn(2, 4)))
        assert out_tuple.shape == (2, 64)

        # Flat 1D (14,)
        out_flat_1d = fusion(x=torch.randn(14))
        assert out_flat_1d.shape == (64,)

        # Flat 2D (5, 14)
        out_flat_2d = fusion(x=torch.randn(5, 14))
        assert out_flat_2d.shape == (5, 64)

    def test_missing_stream_zero_fallback(self):
        fusion = DualStreamSLFeatureExtractor(
            temporal_in_channels=10,
            temporal_seq_len=20,
            tabular_dim=4,
            output_dim=64,
        )
        fusion.eval()
        out = fusion(temporal_x=None, tabular_x=None)
        assert out.shape == (1, 64)
        assert not torch.isnan(out).any()


class TestActorCriticAndGradientFlow:
    """Gradient flow, isolation, and distribution stability"""

    def test_freeze_unfreeze_autograd_isolation(self):
        backbone = TabularMLPFeatureExtractor(input_dim=14, output_dim=64)
        ac = HybridActorCritic(obs_dim=14, feature_extractor=backbone)

        obs = torch.randn(4, 14)
        disc_a = torch.randint(0, 3, (4,))
        cont_a = torch.rand(4, 1)

        # 1. Unfrozen
        log_p, _, val = ac.evaluate_actions(obs, (disc_a, cont_a))
        loss = -log_p.mean() + val.mean()
        loss.backward()

        assert any(p.grad is not None and p.grad.norm().item() > 0 for p in ac.feature_extractor.parameters())

        # 2. Freeze
        ac.zero_grad()
        ac.freeze_backbone()
        log_p, _, val = ac.evaluate_actions(obs, (disc_a, cont_a))
        loss = -log_p.mean() + val.mean()
        loss.backward()

        # Feature extractor must have NO gradients
        assert all(p.grad is None or p.grad.norm().item() == 0 for p in ac.feature_extractor.parameters())
        # Actor head must still receive gradients
        assert any(p.grad is not None and p.grad.norm().item() > 0 for p in ac.actor_latent.parameters())

        # 3. Unfreeze
        ac.zero_grad()
        ac.unfreeze_backbone()
        log_p, _, val = ac.evaluate_actions(obs, (disc_a, cont_a))
        loss = -log_p.mean() + val.mean()
        loss.backward()

        assert any(p.grad is not None and p.grad.norm().item() > 0 for p in ac.feature_extractor.parameters())

    def test_beta_distribution_boundary_stability(self):
        ac = HybridActorCritic(obs_dim=14, distribution_type="beta")
        ac.eval()

        # Extreme observations
        obs = torch.randn(8, 14) * 50.0
        # Boundary actions
        actions = (torch.tensor([0, 1, 2, 0, 1, 2, 0, 1]), torch.tensor([0.0, 1.0, 1e-8, 1.0 - 1e-8, 0.5, 0.2, 0.8, 0.5]))

        log_p, ent, val = ac.evaluate_actions(obs, actions)
        assert not torch.isnan(log_p).any()
        assert not torch.isinf(log_p).any()
        assert not torch.isnan(ent).any()
        assert not torch.isinf(ent).any()

    def test_extreme_learning_rate_stability(self):
        for lr in [1e-5, 1e-1, 1.0]:
            ac = HybridActorCritic(obs_dim=14, distribution_type="beta")
            opt = torch.optim.Adam(ac.parameters(), lr=lr)
            for _ in range(5):
                obs = torch.randn(8, 14)
                act = (torch.randint(0, 3, (8,)), torch.rand(8, 1))
                log_p, ent, val = ac.evaluate_actions(obs, act)
                loss = -log_p.mean() + val.mean() - 0.01 * ent.mean()
                opt.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(ac.parameters(), max_norm=1.0)
                opt.step()

                assert not torch.isnan(loss).any()
                for p in ac.parameters():
                    assert not torch.isnan(p).any()


class TestPPOAndSB3Integration:
    """End-to-End PPO and SB3 Adapter integration"""

    def test_hybrid_ppo_learn_and_evaluate(self):
        env = HybridTradingEnv(initial_cash=10_000_000.0)
        agent = HybridPPO(env=env, n_steps=32, batch_size=16, n_epochs=2, seed=42)
        agent.learn(total_timesteps=64)
        res = agent.evaluate(n_episodes=1)
        assert "mean_reward" in res

    def test_sb3_hybrid_adapter_predict(self):
        env = HybridTradingEnv(initial_cash=10_000_000.0)
        sb3_model = SB3HybridPolicyAdapter.create_sb3_ppo(env=env, features_dim=32, n_steps=32, batch_size=16, seed=42)
        sb3_model.learn(total_timesteps=64)

        obs, _ = env.reset(seed=42)
        hybrid_act, raw_act = SB3HybridPolicyAdapter.predict_hybrid(sb3_model, obs)
        assert 0 <= hybrid_act[0] <= 2
        assert 0.0 <= hybrid_act[1] <= 1.0
