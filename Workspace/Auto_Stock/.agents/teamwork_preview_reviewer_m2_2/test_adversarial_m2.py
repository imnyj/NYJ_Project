"""
.agents/teamwork_preview_reviewer_m2_2/test_adversarial_m2.py
Reviewer 2 독립 적대적(Adversarial) 및 수치 안정성 심층 검증 스크립트.
"""

import sys
import os
import math
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# Add project root to path
sys.path.insert(0, "/home/imnyj/Workspace/Auto_Stock")

from modules.engine.hybrid_trading_env import (
    HybridTradingEnv,
    ContinuousToHybridActionWrapper,
)
from modules.models.feature_extractor import (
    TabularMLPFeatureExtractor,
    Temporal1DCNNFeatureExtractor,
    DualStreamSLFeatureExtractor,
    SLPretrainer,
    get_activation_fn,
)
from modules.models.hybrid_policy import (
    HybridActorCritic,
    HybridPPO,
    RolloutBuffer,
    SB3CustomFeaturesExtractor,
    SB3HybridPolicyAdapter,
)

def test_numerical_stability_extreme_inputs():
    print("[1] Testing Numerical Stability with Extreme Inputs...")
    
    # MLP Extreme Input
    mlp = TabularMLPFeatureExtractor(input_dim=14, output_dim=64, use_residual=True)
    extreme_x = torch.tensor([
        [float('nan'), float('inf'), -float('inf'), 1e12, -1e12] + [0.0] * 9,
        [0.0] * 14,
        [1e-15] * 14,
        [-1e10] * 14,
    ])
    out_mlp = mlp(extreme_x)
    assert not torch.isnan(out_mlp).any(), "MLP produced NaN on extreme inputs"
    assert not torch.isinf(out_mlp).any(), "MLP produced Inf on extreme inputs"
    assert out_mlp.shape == (4, 64)

    # 1D-CNN Extreme Input (B=1, B=4)
    cnn = Temporal1DCNNFeatureExtractor(in_channels=10, seq_len=20, output_dim=64, norm_type="group_norm")
    extreme_cnn_x = torch.full((4, 20, 10), float('nan'))
    extreme_cnn_x[0, 0, 0] = float('inf')
    extreme_cnn_x[1, 5, 2] = -float('inf')
    out_cnn = cnn(extreme_cnn_x)
    assert not torch.isnan(out_cnn).any(), "CNN produced NaN on extreme inputs"
    assert not torch.isinf(out_cnn).any(), "CNN produced Inf on extreme inputs"
    assert out_cnn.shape == (4, 64)
    print(" -> MLP & CNN Extreme Input Pass!")


def test_beta_and_gaussian_boundary_conditions():
    print("[2] Testing Beta & Gaussian Distribution Boundary Conditions...")
    
    # Beta Policy
    policy_beta = HybridActorCritic(obs_dim=14, feature_dim=64, distribution_type="beta")
    
    # Test boundary actions [0.0, 1.0, 1e-10, 1.0 - 1e-10]
    obs = torch.randn(8, 14)
    act_disc = torch.tensor([0, 1, 2, 0, 1, 2, 1, 0])
    act_cont_boundaries = torch.tensor([[0.0], [1.0], [1e-12], [1.0 - 1e-12], [-0.5], [1.5], [0.5], [0.3]])
    
    log_prob, entropy, val = policy_beta.evaluate_actions(obs, (act_disc, act_cont_boundaries))
    assert not torch.isnan(log_prob).any(), "Beta evaluate_actions produced NaN for boundary actions"
    assert not torch.isinf(log_prob).any(), "Beta evaluate_actions produced Inf for boundary actions"
    assert not torch.isnan(entropy).any(), "Beta entropy is NaN"
    assert not torch.isnan(val).any(), "Beta value is NaN"

    # Deterministic vs Stochastic Beta Sampling
    for _ in range(20):
        obs_single = np.random.randn(14).astype(np.float32)
        act_stoch, lp_s, val_s = policy_beta.sample_action(obs_single, deterministic=False)
        act_det, lp_d, val_d = policy_beta.sample_action(obs_single, deterministic=True)
        assert act_stoch[0] in (0, 1, 2)
        assert 0.0 <= act_stoch[1] <= 1.0
        assert act_det[0] in (0, 1, 2)
        assert 0.0 <= act_det[1] <= 1.0
        assert not np.isnan(act_stoch[1])
        assert not np.isnan(act_det[1])

    # Gaussian Policy
    policy_gauss = HybridActorCritic(obs_dim=14, feature_dim=64, distribution_type="gaussian")
    log_prob_g, ent_g, val_g = policy_gauss.evaluate_actions(obs, (act_disc, act_cont_boundaries))
    assert not torch.isnan(log_prob_g).any(), "Gaussian evaluate_actions produced NaN"
    assert not torch.isinf(log_prob_g).any(), "Gaussian evaluate_actions produced Inf"
    print(" -> Beta & Gaussian Boundary Handling Pass!")


def test_single_obs_and_unbatched_groupnorm():
    print("[3] Testing Single Observation & Unbatched GroupNorm Handling...")
    
    cnn = Temporal1DCNNFeatureExtractor(in_channels=10, seq_len=20, output_dim=32, norm_type="group_norm")
    
    # 1D single flat vector (10,)
    x_1d = torch.randn(10)
    out_1d = cnn(x_1d)
    assert out_1d.shape == (32,), f"Expected shape (32,), got {out_1d.shape}"
    
    # 2D unbatched sequence (20, 10)
    x_2d_seq = torch.randn(20, 10)
    out_2d_seq = cnn(x_2d_seq)
    assert out_2d_seq.shape == (32,), f"Expected shape (32,), got {out_2d_seq.shape}"
    
    # 2D unbatched transposed sequence (10, 20)
    x_2d_trans = torch.randn(10, 20)
    out_2d_trans = cnn(x_2d_trans)
    assert out_2d_trans.shape == (32,), f"Expected shape (32,), got {out_2d_trans.shape}"
    
    # DualStream with 1D numpy array
    dual = DualStreamSLFeatureExtractor(
        temporal_in_channels=10, temporal_seq_len=20, tabular_dim=4, output_dim=48
    )
    obs_1d_flat = np.random.randn(14).astype(np.float32)
    out_dual_1d = dual(x=torch.as_tensor(obs_1d_flat))
    assert out_dual_1d.shape == (48,), f"Expected shape (48,), got {out_dual_1d.shape}"
    
    print(" -> Single Obs & Unbatched GroupNorm Pass!")


def test_gae_and_advantage_zero_variance():
    print("[4] Testing GAE & Advantage Zero-Variance Edge Case...")
    
    buf = RolloutBuffer(buffer_size=10, obs_dim=14, device=torch.device("cpu"))
    # Add identical transitions (zero reward, identical values)
    for _ in range(10):
        buf.add(
            obs=np.zeros(14, dtype=np.float32),
            action=(0, 0.5),
            reward=0.0,
            value=1.0,
            log_prob=-0.5,
            done=False,
        )
    
    buf.compute_returns_and_advantages(last_value=1.0, last_done=False, gamma=0.99, gae_lambda=0.95)
    assert not np.isnan(buf.advantages).any(), "GAE advantages contains NaN"
    assert not np.isnan(buf.returns).any(), "GAE returns contains NaN"
    
    # Simulate PPO advantage normalization with 0 std
    adv = buf.advantages[:buf.ptr]
    adv_mean, adv_std = adv.mean(), adv.std() + 1e-8
    norm_adv = (adv - adv_mean) / adv_std
    assert not np.isnan(norm_adv).any(), "Zero-variance advantage normalization produced NaN"
    assert not np.isinf(norm_adv).any(), "Zero-variance advantage normalization produced Inf"
    print(" -> GAE & Zero-Variance Advantage Pass!")


def test_sl_to_rl_weight_transfer_and_gradients():
    print("[5] Testing SL -> RL Transfer Exact Weight Matching & Freezing...")
    
    dual = DualStreamSLFeatureExtractor(output_dim=64)
    pretrainer = SLPretrainer(backbone=dual, feature_dim=64)
    
    # Train 2 steps
    batch = (torch.randn(8, 20, 10), torch.randn(8, 4), torch.randn(8, 1), torch.randint(0, 3, (8,)))
    pretrainer.train_step(batch)
    
    # Transfer to HybridActorCritic with freeze=True
    policy = HybridActorCritic(obs_dim=14, feature_dim=64, feature_extractor=dual)
    policy.load_from_sl_pretrainer(pretrainer, freeze=True)
    
    # Test feature extraction with explicit args and dict/tuple
    pretrainer.eval()
    policy.eval()
    t_x = torch.randn(4, 20, 10)
    tab_x = torch.randn(4, 4)
    with torch.no_grad():
        feat_pretrainer = pretrainer.extract_features(temporal_x=t_x, tabular_x=tab_x)
        # Using dict input or explicit args
        feat_policy_dict = policy.extract_features({"temporal": t_x, "tabular": tab_x})
    
    torch.testing.assert_close(feat_pretrainer, feat_policy_dict, rtol=1e-5, atol=1e-6)
    
    # Check frozen gradients
    policy.train()
    obs_b = torch.randn(4, 14)
    log_p, ent, val = policy.evaluate_actions(obs_b, (torch.tensor([0, 1, 2, 0]), torch.tensor([[0.1], [0.5], [0.9], [0.2]])))
    loss = -log_p.mean() + val.mean()
    loss.backward()
    
    for name, p in policy.feature_extractor.named_parameters():
        assert p.grad is None, f"Parameter {name} in frozen backbone received gradient!"
        
    for name, p in policy.actor_latent.named_parameters():
        assert p.grad is not None, f"Parameter {name} in actor_latent missed gradient!"
        
    # Unfreeze and check gradient propagation
    policy.unfreeze_backbone()
    policy.zero_grad()
    log_p2, _, val2 = policy.evaluate_actions(obs_b, (torch.tensor([0, 1, 2, 0]), torch.tensor([[0.1], [0.5], [0.9], [0.2]])))
    loss2 = -log_p2.mean() + val2.mean()
    loss2.backward()
    
    backbone_has_grad = False
    for name, p in policy.feature_extractor.named_parameters():
        if p.grad is not None:
            backbone_has_grad = True
            break
    assert backbone_has_grad, "Unfrozen backbone failed to receive gradients!"
    print(" -> SL to RL Transfer & Gradient Control Pass!")


def test_sb3_adapter_e2e_resilience():
    print("[6] Testing SB3 Adapter E2E Resilience...")
    
    raw_env = HybridTradingEnv()
    wrapped_env = ContinuousToHybridActionWrapper(raw_env)
    
    # Test all action spaces and wrappers
    assert wrapped_env.action_space.shape == (2,)
    
    sb3_model = SB3HybridPolicyAdapter.create_sb3_ppo(
        env=raw_env,
        features_dim=32,
        n_steps=16,
        batch_size=8,
    )
    
    # Train 32 steps
    SB3HybridPolicyAdapter.train_sb3_agent(sb3_model, total_timesteps=32)
    
    # Predict and test boundary signals
    test_signals = [
        np.array([0.5, 0.8], dtype=np.float32),   # BUY, 0.8
        np.array([-0.5, 0.3], dtype=np.float32),  # SELL, 0.3
        np.array([0.0, 0.0], dtype=np.float32),   # HOLD, 0.0
        np.array([0.334, 1.5], dtype=np.float32), # BUY, clamped to 1.0
        np.array([-0.334, -0.5], dtype=np.float32), # SELL, clamped to 0.0
    ]
    
    for sig in test_signals:
        h_act, _ = wrapped_env.action(sig)
        assert h_act in (0, 1, 2)
        
    print(" -> SB3 Adapter E2E Resilience Pass!")


if __name__ == "__main__":
    print("==================================================")
    print("  RUNNING REVIEWER 2 ADVERSARIAL & STRESS SUITE   ")
    print("==================================================")
    test_numerical_stability_extreme_inputs()
    test_beta_and_gaussian_boundary_conditions()
    test_single_obs_and_unbatched_groupnorm()
    test_gae_and_advantage_zero_variance()
    test_sl_to_rl_weight_transfer_and_gradients()
    test_sb3_adapter_e2e_resilience()
    print("==================================================")
    print("  ALL 6 ADVERSARIAL STRESS SUITES PASSED (100%)!  ")
    print("==================================================")
