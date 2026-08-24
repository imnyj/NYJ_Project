#!/usr/bin/env python3
"""
test_m1_audit.py
================
Comprehensive verification and unit/integration test suite for Milestone 1:
1. AoITracker 6-bin distance AoI tracking & get_distance_aoi()
2. SimulationRunner distance_aoi, distance_pdr, and cbr_history integration
3. ResNetMoEAgent & MoEAgent get_latent_and_gate() latent vector and softmax gating extraction
"""

import os
import sys
import pytest
import numpy as np

_cur_dir = os.path.dirname(os.path.abspath(__file__))
if _cur_dir not in sys.path:
    sys.path.insert(0, _cur_dir)

from aoi_tracker import AoITracker
from resnet_moe_agent import ResNetMoEAgent
from moe_agent import MoEAgent
from sim_engine import SimulationRunner


# =============================================================================
# 1. AoITracker Unit Tests
# =============================================================================
class TestAoITrackerDistance:
    def test_distance_bins_accumulation(self):
        """Verify AoI is correctly accumulated into the 6 distance bins."""
        tracker = AoITracker(comm_range_m=300.0, eval_start_time=0.0)

        # Place sender at (0, 0)
        # Place receivers at distances: 25m, 75m, 125m, 175m, 225m, 275m
        positions = {
            "v_sender": (0.0, 0.0),
            "v_bin0": (25.0, 0.0),    # bin 0: 0~50m
            "v_bin1": (75.0, 0.0),    # bin 1: 50~100m
            "v_bin2": (125.0, 0.0),   # bin 2: 100~150m
            "v_bin3": (175.0, 0.0),   # bin 3: 150~200m
            "v_bin4": (225.0, 0.0),   # bin 4: 200~250m
            "v_bin5": (275.0, 0.0),   # bin 5: 250~300m
        }

        # Sender sent CAM at t = 1.0s
        tracker.on_cam_sent("v_sender", 1.0, 0.0, 0.0, in_range_count=6)

        # All receivers received CAM at t = 1.0s (delay ~0)
        for vid in ["v_bin0", "v_bin1", "v_bin2", "v_bin3", "v_bin4", "v_bin5"]:
            tracker.on_cam_received("v_sender", vid, t_rx=1.0, t_gen=1.0, dist_m=positions[vid][0])

        # Step at t = 1.2s -> age = 0.2s = 200ms
        mean_aoi = tracker.step(1.2, positions)
        assert mean_aoi > 0, "Mean AoI should be positive"

        # Check distance AoI
        dist_aoi = tracker.get_distance_aoi()
        assert len(dist_aoi) == 6, f"Expected 6 bins, got {len(dist_aoi)}"
        for b in range(6):
            assert abs(dist_aoi[b] - 200.0) < 1e-2, f"Bin {b} expected ~200.0 ms, got {dist_aoi[b]}"

        # Check dict format
        dist_dict = tracker.get_distance_aoi(as_dict=True)
        assert "distances" in dist_dict
        assert dist_dict["distances"] == [25, 75, 125, 175, 225, 275]
        assert "aoi_mean" in dist_dict
        assert "aoi_std" in dist_dict
        assert len(dist_dict["aoi_mean"]) == 6
        assert len(dist_dict["aoi_std"]) == 6

    def test_empty_bins_and_reset(self):
        """Verify empty bins return 0.0 and reset clears distance accumulators."""
        tracker = AoITracker(comm_range_m=300.0, eval_start_time=0.0)
        positions = {
            "v0": (0.0, 0.0),
            "v1": (25.0, 0.0), # bin 0 only
        }
        tracker.on_cam_sent("v0", 0.0, 0.0, 0.0, in_range_count=1)
        tracker.on_cam_received("v0", "v1", t_rx=0.0, t_gen=0.0, dist_m=25.0)
        tracker.step(0.1, positions)

        dist_aoi = tracker.get_distance_aoi()
        assert dist_aoi[0] > 0
        for b in range(1, 6):
            assert dist_aoi[b] == 0.0, f"Unused bin {b} should be 0.0"

        # Reset
        tracker.reset()
        dist_aoi_reset = tracker.get_distance_aoi()
        assert dist_aoi_reset == [0.0] * 6
        assert tracker.dist_aoi_count == [0] * 6
        assert tracker.dist_aoi_sum == [0.0] * 6


# =============================================================================
# 2. ResNetMoEAgent & MoEAgent Latent / Gating Tests
# =============================================================================
class TestMoEActivationExtraction:
    def test_resnet_moe_single_state(self):
        """Test ResNetMoEAgent.get_latent_and_gate for 1D single state vector."""
        agent = ResNetMoEAgent(state_dim=5, action_dim=24, num_experts=3, hidden_dim=128)
        state = np.array([0.5, 30.0, 15.0, 0.1, 0.48], dtype=np.float32)

        feat, gate = agent.get_latent_and_gate(state)

        assert isinstance(feat, np.ndarray), "Feature must be a numpy ndarray"
        assert isinstance(gate, np.ndarray), "Gate must be a numpy ndarray"
        assert feat.shape == (128,), f"Expected feature shape (128,), got {feat.shape}"
        assert gate.shape == (3,), f"Expected gate shape (3,), got {gate.shape}"

        # Softmax properties
        assert np.all(gate >= 0.0), "Gating probabilities must be >= 0"
        assert np.all(gate <= 1.0), "Gating probabilities must be <= 1"
        assert abs(np.sum(gate) - 1.0) < 1e-5, f"Gating probabilities must sum to 1.0, got {np.sum(gate)}"

    def test_resnet_moe_batch_state(self):
        """Test ResNetMoEAgent.get_latent_and_gate for 2D batch of states."""
        agent = ResNetMoEAgent(state_dim=5, action_dim=24, num_experts=3, hidden_dim=128)
        batch_size = 16
        batch_states = np.random.randn(batch_size, 5).astype(np.float32)

        feats, gates = agent.get_latent_and_gate(batch_states)

        assert feats.shape == (batch_size, 128), f"Expected (16, 128), got {feats.shape}"
        assert gates.shape == (batch_size, 3), f"Expected (16, 3), got {gates.shape}"

        sums = np.sum(gates, axis=1)
        np.testing.assert_allclose(sums, np.ones(batch_size), atol=1e-5)

    def test_moe_agent_latent_and_gate(self):
        """Test baseline MoEAgent.get_latent_and_gate."""
        agent = MoEAgent(state_dim=5, action_dim=24, num_experts=2)
        state = np.array([0.2, 10.0, 20.0, 0.05, 0.22], dtype=np.float32)

        feat, gate = agent.get_latent_and_gate(state)
        assert feat.shape == (128,)
        assert gate.shape == (2,)
        assert abs(np.sum(gate) - 1.0) < 1e-5


# =============================================================================
# 3. Simulation Engine End-to-End Metrics Integration Test
# =============================================================================
class TestSimEngineMetrics:
    def test_simulation_metrics_export(self):
        """Run short simulation and verify distance_aoi, distance_pdr, and cbr_history."""
        runner = SimulationRunner(
            scenario="urban_grid",
            n_vehicles=20,
            seed=42,
            method="ReactDCC",
            duration_steps=60
        )
        runner.warmup_s = 2.0  # short warmup for fast testing

        metrics = runner.run()

        # 1. Essential metric keys existence
        assert "AoI_mean" in metrics, "AoI_mean missing from result"
        assert "CBR_mean" in metrics, "CBR_mean missing from result"
        assert "PDR_mean" in metrics, "PDR_mean missing from result"
        assert "distance_pdr" in metrics, "distance_pdr missing from result"
        assert "distance_aoi" in metrics, "distance_aoi missing from result"
        assert "cbr_history" in metrics, "cbr_history missing from result"

        # 2. distance_pdr verification (6 bins)
        dist_pdr = metrics["distance_pdr"]
        assert isinstance(dist_pdr, list), "distance_pdr must be a list"
        assert len(dist_pdr) == 6, f"distance_pdr must have 6 bins, got {len(dist_pdr)}"
        for b, val in enumerate(dist_pdr):
            assert isinstance(val, (int, float)), f"distance_pdr[{b}] not a number"
            assert 0.0 <= val <= 100.0, f"distance_pdr[{b}] = {val} out of [0, 100]"

        # 3. distance_aoi verification (6 bins)
        dist_aoi = metrics["distance_aoi"]
        assert isinstance(dist_aoi, list), "distance_aoi must be a list"
        assert len(dist_aoi) == 6, f"distance_aoi must have 6 bins, got {len(dist_aoi)}"
        for b, val in enumerate(dist_aoi):
            assert isinstance(val, (int, float)), f"distance_aoi[{b}] not a number"
            assert 0.0 <= val <= 2000.0, f"distance_aoi[{b}] = {val} out of [0, 2000] ms"

        # 4. cbr_history verification
        cbr_hist = metrics["cbr_history"]
        assert isinstance(cbr_hist, list), "cbr_history must be a list"
        assert len(cbr_hist) > 0, "cbr_history must not be empty"
        for val in cbr_hist:
            assert isinstance(val, (int, float)), f"cbr_history element {val} not a number"
            assert 0.0 <= val <= 1.0, f"cbr_history element {val} out of [0.0, 1.0]"

        print("\n--- Milestone 1 Simulation Metrics Verification Summary ---")
        print(f"AoI_mean: {metrics['AoI_mean']} ms")
        print(f"CBR_mean: {metrics['CBR_mean']}")
        print(f"PDR_mean: {metrics['PDR_mean']}%")
        print(f"distance_pdr: {metrics['distance_pdr']}")
        print(f"distance_aoi: {metrics['distance_aoi']}")
        print(f"cbr_history length: {len(metrics['cbr_history'])}")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
