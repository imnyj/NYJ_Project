# tests/test_tier2_boundaries.py
# ============================================================================
# Tier 2: Boundary & Corner Cases Test Suite
# Stresses extreme values, edge conditions, contention limits, and safety guards.
# ============================================================================

import math
import numpy as np
import pytest
import torch
import src.Communications as comm
from tests.contract_adapters import (
    extract_tls_features,
    predict_dynamics,
    HeuristicScheduler,
    StateVectorizer,
    ActionDecoder,
    RetrospectiveReplayBuffer,
    DummyPolicy,
    DualModelHotSwapManager,
)
from tests.conftest import DummyNode


class TestTier2BoundaryCornerCases:
    """Tier 2: Boundary & Corner Case Verification."""

    def test_01_speed_extremes(self, synthetic_rsu_node):
        """Verify handling of extreme stationary (v=0) and super-speed (v=40m/s)."""
        vectorizer = StateVectorizer(rsu_range=300.0, v_max=30.0)

        # 1. Stationary vehicle
        node_still = DummyNode("veh_still", pos=(100.0, 100.0), vel=(0.0, 0.0), comm_range=300.0)
        vec_still = vectorizer.vectorize(node_still, synthetic_rsu_node, current_time=10.0)
        assert vec_still[1] == 0.0 and vec_still[2] == 0.0 and vec_still[3] == 0.0

        # 2. Extreme overspeed (v=40m/s > v_max=30m/s) -> must clip cleanly to 1.0 without crashing
        node_fast = DummyNode("veh_fast", pos=(100.0, 100.0), vel=(40.0, 0.0), comm_range=300.0)
        vec_fast = vectorizer.vectorize(node_fast, synthetic_rsu_node, current_time=10.0)
        assert vec_fast[1] == 1.0, f"Expected clipped vx to 1.0, got {vec_fast[1]}"
        assert vec_fast[3] == 1.0, f"Expected clipped speed to 1.0, got {vec_fast[3]}"

    def test_02_distance_extremes_and_out_of_coverage(self, synthetic_rsu_node):
        """Verify handling of d=0m (RSU center) and d=2000m (far out-of-cell)."""
        vectorizer = StateVectorizer(rsu_range=300.0)

        # 1. Zero distance (at RSU center)
        node_center = DummyNode("veh_center", pos=(0.0, 0.0), comm_range=300.0)
        vec_center = vectorizer.vectorize(node_center, synthetic_rsu_node, current_time=10.0)
        assert vec_center[5] == 0.0 and vec_center[6] == 0.0 and vec_center[7] == 0.0

        # 2. Extreme distance (d=2000m > rsu_range=300m)
        node_far = DummyNode("veh_far", pos=(1600.0, 1200.0), comm_range=300.0)  # dist = 2000m
        vec_far = vectorizer.vectorize(node_far, synthetic_rsu_node, current_time=10.0)
        assert vec_far[7] == 1.0, f"Expected clipped dist norm to 1.0, got {vec_far[7]}"

        # Check uplink success at extreme distance. Shadowing is disabled here on
        # purpose: this asserts the *distance* boundary of the link budget, and a
        # 4 dB log-normal draw clears the 0.1 bound about 21% of the time, which
        # would make the assertion a coin flip rather than a boundary check.
        group_far = [("veh_far", 20.0, 2000.0)]
        probs = comm.judge_uplink(group_far, shadowing_sigma_db=0.0)
        assert 0.0 <= probs["veh_far"] < 0.1, "Expected very low success probability at 2000m"

    def test_03_signal_phase_boundaries(self):
        """Verify edge conditions in TLS: exact switch instant (time_to_switch=0), yellow phase, missing TLS."""
        # 1. Exact 0.0 switch instant
        tls_zero = {"state": "r", "dist_to_stopline": 10.0, "time_to_switch": 0.0}
        stop_imm, start_imm = predict_dynamics(tls_zero, current_speed=0.0)
        assert start_imm == 1.0

        # 2. Yellow phase
        tls_yellow = {"state": "y", "dist_to_stopline": 25.0, "time_to_switch": 3.0}
        stop_imm, start_imm = predict_dynamics(tls_yellow, current_speed=12.0)
        assert stop_imm == 1.0

        # 3. Missing TLS features (empty dict or None)
        tls_empty = {}
        stop_imm, start_imm = predict_dynamics(tls_empty, current_speed=10.0)
        assert stop_imm == 0.0 and start_imm == 0.0

    def test_04_subchannel_contention_extremes(self):
        """Verify Rayleigh SINR judge_uplink at zero contention vs massive contention."""
        # 1. Zero contention (Single transmitter at good distance)
        single_group = [("v_solo", 23.0, 100.0)]
        probs_solo = comm.judge_uplink(single_group)
        assert probs_solo["v_solo"] > 0.95, f"Expected solo success > 0.95, got {probs_solo['v_solo']}"

        # 2. Massive contention (50 simultaneous vehicles on 1 subchannel)
        crowded_group = [(f"v_{i}", 23.0, 200.0 + (i % 50)) for i in range(50)]
        probs_crowded = comm.judge_uplink(crowded_group)
        assert len(probs_crowded) == 50
        for vid, p in probs_crowded.items():
            assert 0.0 <= p <= 1.0
            assert not math.isnan(p) and not math.isinf(p)
            assert p < 0.15, f"Expected heavy interference drop < 0.15, got {p}"

    def test_05_replay_buffer_edge_cases(self):
        """Verify replay buffer behavior with empty sample, sampling > size, and ring overwrites."""
        buffer = RetrospectiveReplayBuffer(capacity=5)

        # 1. Sampling from empty buffer raises ValueError
        with pytest.raises(ValueError, match="Cannot sample from an empty buffer"):
            buffer.sample(batch_size=2)

        # 2. Push 3 items and sample 5 -> should gracefully sample min(len, batch_size) = 3
        for i in range(3):
            s = np.zeros(18, dtype=np.float32)
            buffer.push(s, [0, 0, 0], 0.0, s, False, 1.0)
        batch = buffer.sample(batch_size=5)
        assert batch["state"].shape[0] == 3

        # 3. Push 4 more items to trigger ring buffer overwrite
        for i in range(4):
            s = np.full(18, float(i + 10), dtype=np.float32)
            buffer.push(s, [0, 0, 0], 0.0, s, False, 1.0)
        assert len(buffer) == 5, f"Buffer capacity exceeded: {len(buffer)}"

    def test_06_hot_swap_nan_inf_guard(self):
        """Verify Hot-Swap rejects contaminated models containing NaN or Inf values."""
        act_model = DummyPolicy(state_dim=18, num_channels=4, hidden_dim=32)
        rest_model = DummyPolicy(state_dim=18, num_channels=4, hidden_dim=32)
        manager = DualModelHotSwapManager(act_model, rest_model)

        # 1. Clean swap works
        assert manager.hot_swap() is True

        # 2. Inject NaN into Rest model
        with torch.no_grad():
            list(rest_model.parameters())[0][0, 0] = float("nan")
        assert manager.hot_swap() is False, "Hot-swap should reject NaN parameters"

        # 3. Inject Inf into Rest model
        with torch.no_grad():
            list(rest_model.parameters())[0][0, 0] = float("inf")
        assert manager.hot_swap() is False, "Hot-swap should reject Inf parameters"

        # 4. Verify Act model parameters were not corrupted
        for p in act_model.parameters():
            assert not torch.isnan(p).any()
            assert not torch.isinf(p).any()
