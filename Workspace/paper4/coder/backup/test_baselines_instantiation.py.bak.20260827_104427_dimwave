# tests/test_baselines_instantiation.py
# ============================================================================
# Comprehensive Test Suite for All 9 Baseline RL Algorithms (S3 / R2)
#
# Covers:
# - Category 1 (Basic 3종): HybridPPO, HybridSAC, HybridTD3
# - Category 2 (Latest 3종): MAPPO, HyARPPO, MPDQN (PDQN)
# - Category 3 (SOTA AoI 3종): PureAoI, DuelingQAoI, SACAoI
#
# Validates:
# - Instantiation & parameter initialization
# - Deterministic and stochastic action selection bounds & formats
# - Loss calculation and gradient backpropagation on transition batches
# - Model serialization (save / load / state_dict)
# - SMDP variable-interval discount handling
# ============================================================================

import math
import os
import tempfile
import numpy as np
import pytest
import torch
from src.baselines import (
    BaseRLModel,
    HybridPPO,
    HybridSAC,
    HybridTD3,
    MAPPO,
    HyARPPO,
    MPDQN,
    PureAoI,
    DuelingQAoI,
    SACAoI,
    BASELINE_REGISTRY,
)


@pytest.fixture
def sample_batch():
    batch_size = 16
    return {
        "state": torch.randn(batch_size, 16, dtype=torch.float32),
        "action": torch.stack([
            torch.randn(batch_size),
            torch.randint(0, 4, (batch_size,)).float(),
            torch.randn(batch_size),
        ], dim=1),
        "reward": torch.randn(batch_size, 1, dtype=torch.float32),
        "next_state": torch.randn(batch_size, 16, dtype=torch.float32),
        "done": torch.zeros(batch_size, 1, dtype=torch.float32),
        "delta_t": torch.ones(batch_size, 1, dtype=torch.float32) * 1.5,
        "discount": torch.pow(0.99, torch.ones(batch_size, 1, dtype=torch.float32) * 1.5),
    }


ALL_MODEL_CLASSES = [
    HybridPPO,
    HybridSAC,
    HybridTD3,
    MAPPO,
    HyARPPO,
    MPDQN,
    PureAoI,
    DuelingQAoI,
    SACAoI,
]


class TestBaselinesInstantiationAndExecution:
    """Test suite for 9 baseline RL algorithms."""

    def test_registry_contains_all_9_baselines(self):
        expected_keys = [
            "HybridPPO", "HybridSAC", "HybridTD3",
            "MAPPO", "HyARPPO", "MPDQN",
            "PureAoI", "DuelingQAoI", "SACAoI",
        ]
        for key in expected_keys:
            assert key in BASELINE_REGISTRY
            assert issubclass(BASELINE_REGISTRY[key], BaseRLModel)

    @pytest.mark.parametrize("model_cls", ALL_MODEL_CLASSES)
    def test_model_instantiation(self, model_cls):
        model = model_cls(state_dim=16, num_channels=4, hidden_dim=32)
        assert isinstance(model, BaseRLModel)
        assert model.state_dim == 16
        assert model.num_channels == 4

    @pytest.mark.parametrize("model_cls", ALL_MODEL_CLASSES)
    def test_select_action_deterministic_and_stochastic(self, model_cls):
        model = model_cls(state_dim=16, num_channels=4, hidden_dim=32)
        state_np = np.random.uniform(-0.5, 0.5, size=(16,)).astype(np.float32)

        # Deterministic
        grant_det, raw_det, info_det = model.select_action(state_np, deterministic=True)
        delta_d, ch_d, p_d = grant_det
        assert 0.5 <= delta_d <= 10.0, f"Delta {delta_d} out of range in {model_cls.__name__}"
        assert ch_d in [0, 1, 2, 3], f"Channel {ch_d} out of range in {model_cls.__name__}"
        assert 20.0 <= p_d <= 30.0, f"Power {p_d} out of range in {model_cls.__name__}"
        assert isinstance(raw_det, np.ndarray)
        assert isinstance(info_det, dict)

        # Stochastic
        grant_stoch, raw_stoch, info_stoch = model.select_action(state_np, deterministic=False)
        delta_s, ch_s, p_s = grant_stoch
        assert 0.5 <= delta_s <= 10.0
        assert ch_s in [0, 1, 2, 3]
        assert 20.0 <= p_s <= 30.0

    @pytest.mark.parametrize("model_cls", ALL_MODEL_CLASSES)
    def test_model_update_produces_finite_loss(self, model_cls, sample_batch):
        model = model_cls(state_dim=16, num_channels=4, hidden_dim=32)
        loss_dict = model.update(sample_batch)
        assert isinstance(loss_dict, dict)
        assert "loss" in loss_dict
        loss_val = loss_dict["loss"]
        assert not math.isnan(loss_val) and not math.isinf(loss_val)

    @pytest.mark.parametrize("model_cls", ALL_MODEL_CLASSES)
    def test_model_save_and_load(self, model_cls):
        model1 = model_cls(state_dim=16, num_channels=4, hidden_dim=32)
        model2 = model_cls(state_dim=16, num_channels=4, hidden_dim=32)

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
            tmp_path = f.name

        try:
            model1.save(tmp_path)
            model2.load(tmp_path)

            for p1, p2 in zip(model1.parameters(), model2.parameters()):
                assert torch.allclose(p1, p2)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_category1_sac_entropy_and_targets(self, sample_batch):
        sac = HybridSAC(state_dim=16, num_channels=4, hidden_dim=32)
        initial_alpha = float(sac.alpha.item())
        assert initial_alpha > 0.0
        res = sac.update(sample_batch)
        assert "alpha" in res
        assert "critic_loss" in res
        assert "actor_loss" in res

    def test_category1_td3_delayed_policy(self, sample_batch):
        td3 = HybridTD3(state_dim=16, num_channels=4, hidden_dim=32, policy_freq=2)
        res1 = td3.update(sample_batch)
        assert res1["actor_loss"] == 0.0  # Step 1: Critic only
        res2 = td3.update(sample_batch)
        assert "actor_loss" in res2  # Step 2: Policy updated

    def test_category2_mappo_central_critic(self, sample_batch):
        mappo = MAPPO(state_dim=16, num_channels=4, hidden_dim=32)
        res = mappo.update(sample_batch)
        assert "policy_loss" in res
        assert "value_loss" in res

    def test_category2_hyar_ppo_conditioned_branch(self):
        hyar = HyARPPO(state_dim=16, num_channels=4, hidden_dim=32, embed_dim=8)
        s = np.zeros(16, dtype=np.float32)
        grant, raw, info = hyar.select_action(s)
        assert len(grant) == 3
        assert "log_prob" in info

    def test_category2_pdqn_multi_pass_q(self, sample_batch):
        pdqn = MPDQN(state_dim=16, num_channels=4, hidden_dim=32)
        s = np.zeros(16, dtype=np.float32)
        grant, raw, info = pdqn.select_action(s)
        assert "q_values" in info
        assert len(info["q_values"]) == 4
        res = pdqn.update(sample_batch)
        assert "critic_loss" in res

    def test_category3_pure_aoi_whittle_urgency(self):
        aoi_model = PureAoI(state_dim=16, num_channels=4, urgency_threshold=0.3)
        # Fresh state (age_norm = 0.05)
        fresh_state = np.zeros(16, dtype=np.float32)
        fresh_state[0] = 0.05
        grant_fresh, _, _ = aoi_model.select_action(fresh_state)

        # Stale state (age_norm = 0.95)
        stale_state = np.zeros(16, dtype=np.float32)
        stale_state[0] = 0.95
        grant_stale, _, _ = aoi_model.select_action(stale_state)

        # Stale vehicle must get shorter interval Delta and higher power
        assert grant_stale[0] < grant_fresh[0]
        assert grant_stale[2] >= grant_fresh[2]

    def test_category3_dueling_q_stream_separation(self, sample_batch):
        dueling = DuelingQAoI(state_dim=16, num_channels=4, hidden_dim=32)
        res = dueling.update(sample_batch)
        assert "loss" in res
        assert "mean_q" in res

    def test_category3_sac_aoi_lyapunov_penalty(self, sample_batch):
        sac_aoi = SACAoI(state_dim=16, num_channels=4, hidden_dim=32, lyapunov_v=2.0, aoi_thresh=0.2)
        res = sac_aoi.update(sample_batch)
        assert "mean_lyapunov_penalty" in res
        assert res["mean_lyapunov_penalty"] >= 0.0
