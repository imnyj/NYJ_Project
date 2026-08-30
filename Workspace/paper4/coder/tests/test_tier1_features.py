# tests/test_tier1_features.py
# ============================================================================
# Tier 1: Feature Coverage Test Suite
# Tests individual components against their exact requirement specifications.
# ============================================================================

import math
import numpy as np
import pytest
import torch
from tests.contract_adapters import (
    extract_tls_features,
    predict_dynamics,
    HeuristicScheduler,
    StateVectorizer,
    ActionDecoder,
    RetrospectiveReplayBuffer,
    DummyPolicy,
    run_hpo_study,
    DualModelHotSwapManager,
    calculate_metrics,
)
from src.rl_interface import STATE_DIM


class TestTier1FeatureCoverage:
    """Tier 1: Feature Coverage Verification."""

    def test_01_signal_extraction_contract(self):
        """Verify TraCI TLS feature extraction contract returns required keys with correct types."""
        tls_info = extract_tls_features(sumo=None, vid="veh_0")
        required_keys = {"tls_id", "dist_to_stopline", "state", "time_to_switch", "stop_imminent", "start_imminent"}
        assert required_keys.issubset(tls_info.keys()), f"Missing keys in extract_tls_features: {required_keys - set(tls_info.keys())}"
        assert isinstance(tls_info["dist_to_stopline"], (int, float))
        assert isinstance(tls_info["state"], str)
        assert isinstance(tls_info["time_to_switch"], (int, float))
        assert tls_info["stop_imminent"] in [0.0, 1.0]
        assert tls_info["start_imminent"] in [0.0, 1.0]

    def test_02_stop_start_prediction_logic(self):
        """Verify dynamics predictor correctly identifies stop and start transitions."""
        # 1. High speed approaching red light -> stop_imminent must be 1.0
        tls_red = {"state": "r", "dist_to_stopline": 20.0, "time_to_switch": 15.0}
        stop_imm, start_imm = predict_dynamics(tls_red, current_speed=10.0, current_accel=-2.0)
        assert stop_imm == 1.0, "Expected stop_imminent=1.0 when approaching red light"
        assert start_imm == 0.0, "Expected start_imminent=0.0 while in motion"

        # 2. Stopped vehicle at red light with 2.0s left to switch -> start_imminent must be 1.0
        tls_red_switch = {"state": "r", "dist_to_stopline": 5.0, "time_to_switch": 2.0}
        stop_imm, start_imm = predict_dynamics(tls_red_switch, current_speed=0.0, current_accel=0.0)
        assert start_imm == 1.0, "Expected start_imminent=1.0 when red phase is ending soon"
        assert stop_imm == 0.0

        # 3. Stopped vehicle seeing green light at front of queue -> start_imminent must be 1.0
        tls_green_queue = {"state": "g", "dist_to_stopline": 5.0, "time_to_switch": 25.0}
        stop_imm, start_imm = predict_dynamics(tls_green_queue, current_speed=0.0, current_accel=0.0)
        assert start_imm == 1.0, "Expected start_imminent=1.0 on green switch"

        # 4. Cruising vehicle on open green road -> neither imminent
        tls_cruise = {"state": "g", "dist_to_stopline": 400.0, "time_to_switch": 25.0}
        stop_imm, start_imm = predict_dynamics(tls_cruise, current_speed=15.0, current_accel=0.0)
        assert stop_imm == 0.0 and start_imm == 0.0, "Expected no transitions during steady cruise"

    def test_03_heuristic_scheduler_grants(self):
        """Verify S2.5 Heuristic Scheduler assigns urgent grants on transitions and backoff on red."""
        scheduler = HeuristicScheduler(num_channels=4)

        # Urgent stop grant
        grant_urgent = scheduler.decide_grant("v1", {"speed": 12.0, "stop_imminent": 1.0, "start_imminent": 0.0})
        delta, ch, p = grant_urgent
        assert 0.1 <= delta <= 1.0, f"Expected urgent interval, got {delta}"
        assert 0 <= ch < 4, f"Invalid channel: {ch}"
        assert 10.0 <= p <= 23.0, f"Invalid power: {p}"

        # Stopped at red backoff grant
        grant_backoff = scheduler.decide_grant("v2", {"speed": 0.0, "stop_imminent": 0.0, "start_imminent": 0.0, "time_to_switch": 10.0})
        delta_b, ch_b, p_b = grant_backoff
        assert delta_b >= 3.0, f"Expected backoff interval >= 3.0s, got {delta_b}"
        assert p_b == 10.0 or p_b == 20.0, "Expected low power level on backoff"

    def test_04_state_vectorizer_normalization_and_no_leakage(self, synthetic_vehicle_node, synthetic_rsu_node):
        """Verify STATE_DIM-wide state vectorizer produces bounded values and contains no ground truth leakage."""
        vectorizer = StateVectorizer(rsu_range=300.0, v_max=30.0, a_max=5.0)
        tls_info = {"state": "r", "dist_to_stopline": 120.0, "time_to_switch": 14.0, "stop_imminent": 1.0, "start_imminent": 0.0}
        
        vec = vectorizer.vectorize(synthetic_vehicle_node, synthetic_rsu_node, current_time=15.0,
                                   tls_info=tls_info, cbr=0.35, n_active=12)
        
        assert vec.shape == (STATE_DIM,), f"Expected shape (18,), got {vec.shape}"
        assert vec.dtype == np.float32
        assert np.all(vec >= -1.0) and np.all(vec <= 1.0), f"State vector values outside [-1, 1]: {vec}"
        
        # Verify specific feature components
        assert vec[8] == 1.0  # is_red
        assert vec[9] == 0.0  # is_yellow
        assert vec[10] == 0.0 # is_green
        assert 0.0 <= vec[0] <= 1.0  # Age norm
        assert 0.0 <= vec[3] <= 1.0  # Speed norm
        assert 0.0 <= vec[7] <= 1.0  # Distance norm

    def test_05_hybrid_action_decoder_bounds(self):
        """Verify hybrid action decoder produces bounded 3-tuple (Delta, ch, power)."""
        decoder = ActionDecoder(num_channels=4, delta_min=0.1, delta_max=45.0, p_min=10.0, p_max=23.0)

        # Test extreme raw logits
        test_inputs = [
            [-100.0, 0, -100.0],
            [100.0, 3, 100.0],
            [0.0, 2, 0.0],
            torch.tensor([1.5, 2.0, -0.8]),
            {"delta": 2.0, "ch": 1, "power": -1.0},
        ]
        for raw in test_inputs:
            delta, ch, power = decoder.decode_action(raw)
            assert 0.1 <= delta <= 45.0, f"Delta out of bounds: {delta}"
            assert ch in [0, 1, 2, 3], f"Channel out of bounds: {ch}"
            assert 10.0 <= power <= 23.0, f"Power out of bounds: {power}"

    def test_06_retrospective_replay_buffer(self):
        """Verify SMDP Retrospective Replay Buffer pushes and samples batches with delta_t."""
        buffer = RetrospectiveReplayBuffer(capacity=100)
        assert len(buffer) == 0

        # Push 10 transitions
        for i in range(10):
            s = np.full(STATE_DIM, i * 0.1, dtype=np.float32)
            a = np.array([1.0, 2.0, 20.0], dtype=np.float32)
            r = -float(i) * 0.5
            s_prime = np.full(STATE_DIM, (i + 1) * 0.1, dtype=np.float32)
            buffer.push(s, a, r, s_prime, done=False, delta_t=1.5)

        assert len(buffer) == 10
        batch = buffer.sample(batch_size=4)
        assert batch["state"].shape == (4, STATE_DIM)
        assert batch["action"].shape == (4, 3)
        assert batch["reward"].shape == (4, 1)
        assert batch["next_state"].shape == (4, STATE_DIM)
        assert batch["done"].shape == (4, 1)
        assert batch["delta_t"].shape == (4, 1)

    def test_07_policy_instantiation_and_forward(self, sample_state_vector, sample_batch):
        """Verify policy instantiates correctly, selects actions, and updates."""
        model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)

        # 1. Action selection
        grant, raw_action, info = model.select_action(sample_state_vector, deterministic=True)
        delta, ch, power = grant
        assert 0.1 <= delta <= 45.0, f"Delta out of bounds {delta}"
        assert ch in [0, 1, 2, 3], f"Channel out of bounds {ch}"
        assert 10.0 <= power <= 23.0, f"Power out of bounds {power}"

        # 2. Update step
        loss_dict = model.update(sample_batch)
        assert isinstance(loss_dict, dict)
        assert "loss" in loss_dict
        assert not math.isnan(loss_dict["loss"]) and not math.isinf(loss_dict["loss"])

    def test_08_optuna_study_execution(self):
        """Verify Optuna HPO study runs trials and outputs best parameters."""
        study = run_hpo_study("DummyPolicy", model_cls=DummyPolicy, n_trials=3)
        assert len(study.trials) == 3
        assert study.best_value is not None
        assert "lr" in study.best_params
        assert "hidden_dim" in study.best_params

    def test_09_hot_swap_synchronization(self):
        """Verify Dual-Model Hot-Swap copies parameters atomically."""
        act_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        rest_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)

        # Make rest_model weights distinct
        with torch.no_grad():
            for p in rest_model.parameters():
                p.fill_(0.777)

        manager = DualModelHotSwapManager(act_model, rest_model)
        success = manager.hot_swap()
        assert success is True
        assert manager.swap_count == 1

        # Check act_model weights match rest_model exactly
        for p_act, p_rest in zip(act_model.parameters(), rest_model.parameters()):
            assert torch.equal(p_act, p_rest), "Act model weights did not update to Rest model weights"

    def test_10_benchmark_metrics_calculation(self):
        """Verify IEEE TWC 6 metrics calculation produces bounded and correct values."""
        records = [
            {"aoi": 2.0, "peak_aoi": 3.0, "error": 1.2, "tx_attempts": 2, "tx_fails": 0, "power_dbm": 15.0},
            {"aoi": 4.0, "peak_aoi": 5.0, "error": 2.8, "tx_attempts": 3, "tx_fails": 1, "power_dbm": 23.0},
            {"aoi": 1.5, "peak_aoi": 2.0, "error": 0.5, "tx_attempts": 1, "tx_fails": 0, "power_dbm": 10.0},
        ]
        metrics = calculate_metrics(records)
        assert 0.0 < metrics["mean_aoi"] < 10.0
        assert metrics["peak_aoi"] >= metrics["mean_aoi"]
        assert 0.0 <= metrics["packet_loss_rate"] <= 1.0
        assert metrics["mean_error"] >= 0.0
        assert 10.0 <= metrics["avg_tx_power_dbm"] <= 23.0
        assert 0.0 < metrics["jains_fairness_aoi"] <= 1.0
