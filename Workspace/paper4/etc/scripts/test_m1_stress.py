#!/usr/bin/env python3
"""
test_m1_stress.py
=================
Comprehensive Adversarial and Empirical Stress Test Suite for Milestone 1:
1. AoITracker boundary and extreme density tests (0, 1, 500+ vehicles, churn, timestamps)
2. ResNetMoEAgent get_latent_and_gate adversarial input tests (shapes, softmax invariants, extreme values)
3. Channel model & PDR mathematical monotonicity tests (distance 0~3000m, CBR 0~1)
4. Sim engine helper functions edge case resilience (compute_local_n_est, compute_local_cbr, simulate_receptions)
5. SimulationRunner end-to-end integration and metric stability

Author: challenger_m1_1 (Critic / Specialist)
"""

import os
import sys
import math
import random
import pytest
import numpy as np
import torch

_cur_dir = os.path.dirname(os.path.abspath(__file__))
_paper4_root = os.path.abspath(os.path.join(_cur_dir, "..", ".."))
_code_dir = os.path.join(_paper4_root, "code")
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from aoi_tracker import AoITracker
from resnet_moe_agent import ResNetMoEAgent
from sim_engine import (
    reception_probability,
    reception_probability_vec,
    compute_local_n_est,
    compute_local_cbr,
    simulate_receptions,
    SimulationRunner,
    COMM_RANGE_M,
)


# =============================================================================
# 1. AoITracker Adversarial & Edge Case Tests
# =============================================================================
class TestAoITrackerStress:
    def test_zero_vehicles_no_crash_or_nan(self):
        """AoITracker should handle 0 vehicles gracefully at all lifecycle stages."""
        tracker = AoITracker(comm_range_m=300.0, eval_start_time=10.0)

        # Before warmup
        aoi_pre = tracker.step(sim_time=5.0, vehicle_positions={})
        assert aoi_pre == 0.0

        # After warmup
        aoi_post = tracker.step(sim_time=15.0, vehicle_positions={})
        assert aoi_post == 0.0

        # Query all getters
        assert tracker.get_mean_aoi() == 0.0
        assert tracker.get_pdr() == 100.0
        dist_aoi = tracker.get_distance_aoi()
        assert dist_aoi == [0.0] * 6
        assert not any(math.isnan(x) for x in dist_aoi)

        dist_dict = tracker.get_distance_aoi_dict()
        assert dist_dict["distances"] == [25, 75, 125, 175, 225, 275]
        assert dist_dict["aoi_mean"] == [0.0] * 6
        assert dist_dict["aoi_std"] == [0.0] * 6
        assert not any(math.isnan(x) for x in dist_dict["aoi_mean"])
        assert not any(math.isnan(x) for x in dist_dict["aoi_std"])

    def test_single_vehicle_no_crash_or_nan(self):
        """AoITracker should handle a lone vehicle without division by zero or NaN."""
        tracker = AoITracker(comm_range_m=300.0, eval_start_time=10.0)
        positions = {"v_lone": (100.0, 200.0)}

        # Lone vehicle transmits
        tracker.step(sim_time=10.0, vehicle_positions=positions)
        tracker.on_cam_sent("v_lone", t_gen=11.0, x=100.0, y=200.0, in_range_count=0)
        aoi = tracker.step(sim_time=11.1, vehicle_positions=positions)
        assert aoi == 0.0

        # Check metrics
        assert tracker.get_mean_aoi() == 0.0
        assert tracker.get_pdr() == 100.0
        dist_aoi = tracker.get_distance_aoi()
        assert dist_aoi == [0.0] * 6
        assert not any(math.isnan(x) for x in dist_aoi)

    def test_disconnected_pairs_out_of_range(self):
        """Two vehicles separated beyond comm_range_m should produce no in-range pairs."""
        tracker = AoITracker(comm_range_m=300.0, eval_start_time=0.0)
        positions = {
            "v_west": (0.0, 0.0),
            "v_east": (1000.0, 0.0), # distance = 1000m > 300m
        }
        tracker.step(sim_time=0.0, vehicle_positions=positions)
        tracker.on_cam_sent("v_west", t_gen=1.0, x=0.0, y=0.0, in_range_count=0)
        tracker.on_cam_sent("v_east", t_gen=1.0, x=1000.0, y=0.0, in_range_count=0)

        aoi = tracker.step(sim_time=1.1, vehicle_positions=positions)
        assert aoi == 0.0
        dist_aoi = tracker.get_distance_aoi()
        assert dist_aoi == [0.0] * 6
        assert not any(math.isnan(x) for x in dist_aoi)

    def test_massive_density_stress_500_vehicles(self):
        """Stress-test 500 vehicles packed in high density (pairwise N=250,000)."""
        tracker = AoITracker(comm_range_m=300.0, eval_start_time=0.0)
        rng = np.random.RandomState(42)

        n_vehs = 500
        # Pack into 200m x 200m area
        coords = rng.uniform(0.0, 200.0, size=(n_vehs, 2))
        vids = [f"v_{i}" for i in range(n_vehs)]
        positions = {vids[i]: (float(coords[i, 0]), float(coords[i, 1])) for i in range(n_vehs)}

        # Initialize warmup
        tracker.step(sim_time=0.0, vehicle_positions=positions)

        # 50 vehicles send CAMs
        tx_vids = vids[:50]
        for vid in tx_vids:
            tracker.on_cam_sent(vid, t_gen=1.0, x=positions[vid][0], y=positions[vid][1], in_range_count=n_vehs - 1)

        # Receptions for subset of pairs
        for sid in tx_vids:
            sx, sy = positions[sid]
            for rid in vids[50:150]:
                rx, ry = positions[rid]
                dist = math.hypot(rx - sx, ry - sy)
                if dist <= 300.0:
                    tracker.on_cam_received(sid, rid, t_rx=1.001, t_gen=1.0, dist_m=dist)

        # Run 5 consecutive steps
        for step_idx in range(1, 6):
            sim_time = 1.0 + step_idx * 0.1
            mean_aoi = tracker.step(sim_time, positions)
            assert 0.0 <= mean_aoi <= 2000.0, f"AoI {mean_aoi} out of bounds"
            assert not math.isnan(mean_aoi)

        dist_aoi = tracker.get_distance_aoi()
        assert len(dist_aoi) == 6
        for b in range(6):
            assert not math.isnan(dist_aoi[b]), f"Bin {b} is NaN"
            assert 0.0 <= dist_aoi[b] <= 2000.0, f"Bin {b} out of range: {dist_aoi[b]}"

        dist_dict = tracker.get_distance_aoi(as_dict=True)
        for b in range(6):
            assert not math.isnan(dist_dict["aoi_mean"][b])
            assert not math.isnan(dist_dict["aoi_std"][b])

    def test_churn_and_vehicle_removal(self):
        """Verify dynamic departure of vehicles does not leave orphaned state or crash."""
        tracker = AoITracker(comm_range_m=300.0, eval_start_time=0.0)
        positions = {f"v_{i}": (i * 20.0, 0.0) for i in range(10)}

        tracker.step(sim_time=0.0, vehicle_positions=positions)

        for vid in positions:
            tracker.on_cam_sent(vid, t_gen=1.0, x=positions[vid][0], y=positions[vid][1], in_range_count=9)

        # Cross-receptions
        for sid in positions:
            for rid in positions:
                if sid != rid:
                    dist = abs(positions[sid][0] - positions[rid][0])
                    if dist <= 300.0:
                        tracker.on_cam_received(sid, rid, t_rx=1.01, t_gen=1.0, dist_m=dist)

        tracker.step(1.1, positions)

        # Depart 5 vehicles
        departed = [f"v_{i}" for i in range(5)]
        for vid in departed:
            tracker.remove_vehicle(vid)
            del positions[vid]

        # Step after removal
        mean_aoi = tracker.step(1.2, positions)
        assert not math.isnan(mean_aoi)
        assert mean_aoi > 0.0

        # Ensure departed vehicles are cleaned from dictionaries
        for vid in departed:
            assert vid not in tracker.last_cam_sent
            assert vid not in tracker.first_tx_time
            assert not any(k[0] == vid or k[1] == vid for k in tracker.last_received_gen_time)
            assert not any(k[0] == vid or k[1] == vid for k in tracker.current_aoi)

    def test_abnormal_timestamps_and_clipping(self):
        """AoITracker must clip negative AoI to 0.0 and excessively high AoI to 2000.0 ms."""
        tracker = AoITracker(comm_range_m=300.0, eval_start_time=0.0)
        positions = {"v0": (0.0, 0.0), "v1": (10.0, 0.0)}

        tracker.step(sim_time=0.0, vehicle_positions=positions)

        # t_rx < t_gen (e.g. clock jitter)
        tracker.on_cam_received("v0", "v1", t_rx=1.0, t_gen=1.05, dist_m=10.0)
        assert tracker.current_aoi[("v0", "v1")] == 0.0, "Negative AoI should be clamped to 0.0"

        # Step far in future (1000s later)
        tracker.on_cam_sent("v0", t_gen=1.0, x=0.0, y=0.0, in_range_count=1)
        aoi = tracker.step(1000.0, positions)
        assert aoi <= 2000.0, f"AoI {aoi} must be clamped to 2000.0 ms max"


# =============================================================================
# 2. ResNetMoEAgent Latent & Gating Adversarial Tests
# =============================================================================
class TestResNetMoEStress:
    @pytest.fixture
    def agent(self):
        return ResNetMoEAgent(state_dim=5, action_dim=24, num_experts=3, hidden_dim=128)

    def test_various_input_types_and_shapes(self, agent):
        """Test get_latent_and_gate across 1D list, 1D ndarray, 1D Tensor, 2D ndarray, 2D Tensor."""
        # 1D python list
        s_list = [0.1, 10.0, 5.0, 0.05, 0.2]
        feat, gate = agent.get_latent_and_gate(s_list)
        assert feat.shape == (128,)
        assert gate.shape == (3,)
        assert np.isclose(np.sum(gate), 1.0, atol=1e-5)

        # 1D numpy array
        s_np = np.array([0.2, 20.0, 10.0, 0.1, 0.4], dtype=np.float32)
        feat, gate = agent.get_latent_and_gate(s_np)
        assert feat.shape == (128,)
        assert gate.shape == (3,)
        assert np.isclose(np.sum(gate), 1.0, atol=1e-5)

        # 1D torch Tensor
        s_torch = torch.tensor([0.3, 15.0, 8.0, 0.08, 0.35], dtype=torch.float32)
        feat, gate = agent.get_latent_and_gate(s_torch)
        assert feat.shape == (128,)
        assert gate.shape == (3,)
        assert np.isclose(np.sum(gate), 1.0, atol=1e-5)

        # 2D batch numpy arrays of varying sizes
        for B in [1, 7, 32, 128, 512]:
            batch_np = np.random.randn(B, 5).astype(np.float32)
            feat, gate = agent.get_latent_and_gate(batch_np)
            assert feat.shape == (B, 128), f"Batch {B} feature shape mismatch: {feat.shape}"
            assert gate.shape == (B, 3), f"Batch {B} gate shape mismatch: {gate.shape}"
            sums = np.sum(gate, axis=-1)
            assert np.allclose(sums, np.ones(B), atol=1e-5), f"Batch {B} softmax sum != 1.0"
            assert np.all(gate >= 0.0) and np.all(gate <= 1.0)

        # 2D batch torch tensor
        batch_torch = torch.randn(64, 5, dtype=torch.float32)
        feat, gate = agent.get_latent_and_gate(batch_torch)
        assert feat.shape == (64, 128)
        assert gate.shape == (64, 3)
        assert np.allclose(np.sum(gate, axis=1), np.ones(64), atol=1e-5)

    def test_extreme_and_adversarial_values(self, agent):
        """Adversarial stress: large values, negative values, zeros, noise."""
        adversarial_inputs = [
            np.zeros(5, dtype=np.float32),                        # all zeros
            np.ones(5, dtype=np.float32) * 1e4,                   # massive positive
            np.ones(5, dtype=np.float32) * -1e4,                  # massive negative
            np.array([1e4, -1e4, 0.0, 1e2, -1e2], dtype=np.float32), # mixed extreme
            np.random.standard_cauchy(size=(100, 5)).astype(np.float32), # heavy-tailed Cauchy noise
        ]

        for s in adversarial_inputs:
            feat, gate = agent.get_latent_and_gate(s)
            assert np.isfinite(feat).all(), "Latent features contain NaN or Inf"
            assert np.isfinite(gate).all(), "Gating weights contain NaN or Inf"
            if gate.ndim == 1:
                assert np.isclose(np.sum(gate), 1.0, atol=1e-5)
                assert np.all(gate >= 0.0) and np.all(gate <= 1.0)
            else:
                assert np.allclose(np.sum(gate, axis=-1), np.ones(len(gate)), atol=1e-5)
                assert np.all(gate >= 0.0) and np.all(gate <= 1.0)

    def test_training_mode_preservation(self, agent):
        """Calling get_latent_and_gate should restore original train/eval mode."""
        agent.q_network.train()
        assert agent.q_network.training is True
        agent.get_latent_and_gate(np.zeros(5))
        assert agent.q_network.training is True, "Training mode was not restored"

        agent.q_network.eval()
        assert agent.q_network.training is False
        agent.get_latent_and_gate(np.zeros(5))
        assert agent.q_network.training is False, "Eval mode was not preserved"


# =============================================================================
# 3. Channel Model & Mathematical Monotonicity Tests
# =============================================================================
class TestChannelModelAndMonotonicity:
    def test_scalar_vs_vectorized_channel_equivalence(self):
        """Vectorized reception probability must match scalar function across [0, 500m]."""
        dists = np.linspace(0.0, 500.0, 1000)
        p_vec = reception_probability_vec(dists, p_tx_dbm=20.0)
        p_scalar = np.array([reception_probability(d, p_tx_dbm=20.0) for d in dists])

        np.testing.assert_allclose(p_vec, p_scalar, atol=1e-6, err_msg="Scalar and vector reception prob mismatch")

    def test_reception_probability_distance_monotonic_decrease(self):
        """
        Reception probability P(d) must be mathematically monotonically non-increasing
        as distance d increases from 0m to 3000m.
        """
        dists = np.linspace(0.5, 3000.0, 1000)
        p_vals = reception_probability_vec(dists, p_tx_dbm=20.0)

        # Check monotonic non-increasing
        diffs = np.diff(p_vals)
        violating = np.where(diffs > 1e-12)[0]
        assert len(violating) == 0, f"PDR increases with distance at indices {violating}: {dists[violating]} -> {dists[violating+1]}"

        # Boundary checks
        assert reception_probability(0.0) == 1.0
        assert reception_probability(0.5) == 1.0
        assert reception_probability(100.0) >= reception_probability(300.0)
        assert reception_probability(300.0) >= reception_probability(1000.0)
        assert reception_probability(1000.0) >= reception_probability(2000.0)
        assert reception_probability(3000.0) < 1e-5

    def test_cbr_collision_factor_monotonic_decrease(self):
        """Collision factor max(0.1, 1.0 - 0.8 * CBR) must decrease monotonically as CBR increases."""
        cbr_grid = np.linspace(0.0, 1.0, 100)
        col_factors = np.maximum(0.1, 1.0 - cbr_grid * 0.8)

        diffs = np.diff(col_factors)
        assert np.all(diffs <= 1e-12), "Collision factor is not monotonically decreasing with CBR"
        assert col_factors[0] == 1.0
        assert np.isclose(col_factors[-1], 0.2)

    def test_reception_probability_scaling_with_tx_power_and_distance(self):
        """
        Under lower transmit power (e.g. p_tx=0 dBm), reception probability decreases
        sharply over the 0~300m range, validating that the distance decay mechanism functions properly.
        """
        dists = np.array([25.0, 75.0, 125.0, 175.0, 225.0, 275.0])
        p_low_power = reception_probability_vec(dists, p_tx_dbm=0.0) # 0 dBm (1 mW)

        # Check strictly decreasing across distance bins
        for b in range(len(dists) - 1):
            assert p_low_power[b] > p_low_power[b + 1], (
                f"P(d) at {dists[b]}m ({p_low_power[b]:.4f}) not > P(d) at {dists[b+1]}m ({p_low_power[b+1]:.4f})"
            )

    def test_simulated_pdr_cbr_monotonicity(self):
        """
        Empirically simulate receptions across varying CBR levels [0.0, 0.2, 0.4, 0.6, 0.8, 1.0].
        PDR must decrease monotonically as channel load (CBR) increases.
        """
        rng = random.Random(123)
        cbr_levels = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        measured_pdrs = []

        positions = {
            "v_sender": (0.0, 0.0),
            "v_rcv1": (50.0, 0.0),
            "v_rcv2": (100.0, 0.0),
            "v_rcv3": (150.0, 0.0),
        }

        for cbr in cbr_levels:
            cbr_dict = {vid: cbr for vid in positions}
            dist_tx = [0] * 6
            dist_rx = [0] * 6

            for t_step in range(3000):
                cam_events = [{
                    "vid": "v_sender",
                    "x": 0.0,
                    "y": 0.0,
                    "t_gen": float(t_step) * 0.1,
                    "p_tx": 20.0
                }]
                simulate_receptions(
                    cam_events=cam_events,
                    vehicle_positions=positions,
                    cbr_dict=cbr_dict,
                    rng=rng,
                    dist_tx_counts=dist_tx,
                    dist_rx_counts=dist_rx,
                    is_warmup=False
                )

            total_tx = sum(dist_tx)
            total_rx = sum(dist_rx)
            pdr = 100.0 * total_rx / total_tx if total_tx > 0 else 0.0
            measured_pdrs.append(pdr)

        print(f"\nEmpirical PDR vs CBR levels: {list(zip(cbr_levels, [round(p, 2) for p in measured_pdrs]))}")

        # Check monotonic decrease with CBR
        for i in range(len(cbr_levels) - 1):
            assert measured_pdrs[i] >= measured_pdrs[i + 1] - 0.5, (
                f"PDR at CBR={cbr_levels[i]} ({measured_pdrs[i]:.2f}%) < PDR at CBR={cbr_levels[i+1]} ({measured_pdrs[i+1]:.2f}%)"
            )


# =============================================================================
# 4. Simulation Engine Helper Functions Edge Cases
# =============================================================================
class TestSimEngineHelpersStress:
    def test_compute_local_n_est_edge_cases(self):
        """compute_local_n_est for 0, 1, 2, and 500 vehicles."""
        # 0 vehicles
        assert compute_local_n_est({}) == {}

        # 1 vehicle
        assert compute_local_n_est({"v0": (0.0, 0.0)}) == {"v0": 0}

        # 2 vehicles close (in range)
        assert compute_local_n_est({"v0": (0.0, 0.0), "v1": (100.0, 0.0)}) == {"v0": 1, "v1": 1}

        # 2 vehicles far (out of range)
        assert compute_local_n_est({"v0": (0.0, 0.0), "v1": (400.0, 0.0)}) == {"v0": 0, "v1": 0}

        # 500 vehicles
        pos = {f"v_{i}": (float(i % 10), float(i // 10)) for i in range(500)}
        n_est = compute_local_n_est(pos, comm_range_m=300.0)
        assert len(n_est) == 500
        for vid, count in n_est.items():
            assert count == 499 # all within ~50m < 300m

    def test_compute_local_cbr_edge_cases(self):
        """compute_local_cbr with empty positions, empty events, dict/list formats, zero window."""
        # Empty
        cbr_dict, cbr_mean = compute_local_cbr({}, [])
        assert cbr_dict == {} and cbr_mean == 0.0

        # Zero window duration
        pos = {"v0": (0.0, 0.0)}
        cbr_dict, cbr_mean = compute_local_cbr(pos, [], window_duration_s=0.0)
        assert cbr_dict == {"v0": 0.0} and cbr_mean == 0.0

        # Dict format tx counts
        cbr_dict, cbr_mean = compute_local_cbr(
            {"v0": (0.0, 0.0), "v1": (50.0, 0.0)},
            {"v0": 1, "v1": 0},
            window_duration_s=0.1
        )
        assert 0.0 < cbr_dict["v0"] <= 1.0
        assert 0.0 < cbr_dict["v1"] <= 1.0
        assert cbr_mean > 0.0

        # List format events
        events = [{"vid": "v0", "x": 0.0, "y": 0.0}]
        cbr_dict, cbr_mean = compute_local_cbr(
            {"v0": (0.0, 0.0), "v1": (50.0, 0.0)},
            events,
            window_duration_s=0.1
        )
        assert cbr_dict["v0"] > 0.0
        assert cbr_dict["v1"] > 0.0

    def test_simulate_receptions_empty(self):
        """simulate_receptions should return empty list on empty inputs without error."""
        rng = random.Random(42)
        dist_tx = [0] * 6
        dist_rx = [0] * 6

        assert simulate_receptions([], {}, {}, rng, dist_tx, dist_rx) == []
        assert simulate_receptions([{"vid": "v0", "x": 0, "y": 0, "t_gen": 1.0, "p_tx": 20}], {}, {}, rng, dist_tx, dist_rx) == []
        assert simulate_receptions([], {"v0": (0, 0)}, {}, rng, dist_tx, dist_rx) == []


# =============================================================================
# 5. SimulationRunner End-to-End Metric Integrity
# =============================================================================
class TestSimulationRunnerEndToEnd:
    def test_full_runner_metrics_consistency(self):
        """Run SimulationRunner for 80 steps and ensure all exported metrics are non-empty and finite."""
        runner = SimulationRunner(
            scenario="urban_grid",
            n_vehicles=20,
            seed=42,
            method="ReactDCC",
            duration_steps=80,
            warmup_s=2.0
        )
        metrics = runner.run()

        # Check required fields
        for k in ["AoI_mean", "CBR_mean", "PDR_mean", "distance_pdr", "distance_aoi", "cbr_history"]:
            assert k in metrics, f"Missing key {k}"

        # distance_pdr length & bounds
        assert len(metrics["distance_pdr"]) == 6
        assert all(0.0 <= p <= 100.0 for p in metrics["distance_pdr"])

        # distance_aoi length & bounds
        assert len(metrics["distance_aoi"]) == 6
        assert all(0.0 <= a <= 2000.0 for a in metrics["distance_aoi"])

        # cbr_history length & bounds
        assert len(metrics["cbr_history"]) > 0
        assert all(0.0 <= c <= 1.0 for c in metrics["cbr_history"])


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
