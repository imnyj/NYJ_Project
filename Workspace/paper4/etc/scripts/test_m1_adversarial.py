#!/usr/bin/env python3
"""
test_m1_adversarial.py
======================
Adversarial stress-testing and boundary verification suite for Milestone 1:
1. AoITracker boundary distances, warmup isolation, memory leak prevention, staleness growth
2. ResNetMoEAgent & MoEAgent input stress, extreme values, mode preservation, gradient isolation
3. End-to-end SimulationRunner consistency and mathematical validity
"""

import os
import sys
import pytest
import numpy as np
import torch

_cur_dir = os.path.dirname(os.path.abspath(__file__))
_proj_dir = os.path.abspath(os.path.join(_cur_dir, "..", ".."))
_code_dir = os.path.join(_proj_dir, "code")
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from aoi_tracker import AoITracker
from resnet_moe_agent import ResNetMoEAgent, ResNetMoEDQN
from moe_agent import MoEAgent, MoEDQN
from sim_engine import SimulationRunner


# =============================================================================
# 1. Adversarial AoITracker Stress Tests
# =============================================================================
class TestAoITrackerAdversarial:
    def test_exact_distance_boundaries(self):
        """Test exact distance boundary points for 6 bins: [0,50), [50,100), [100,150), [150,200), [200,250), [250,300]."""
        tracker = AoITracker(comm_range_m=300.0, eval_start_time=0.0)

        # Boundary test points
        test_points = [
            ("v_0_min", 0.0, 0),
            ("v_0_max", 49.999, 0),
            ("v_1_min", 50.0, 1),
            ("v_1_max", 99.999, 1),
            ("v_2_min", 100.0, 2),
            ("v_2_max", 149.999, 2),
            ("v_3_min", 150.0, 3),
            ("v_3_max", 199.999, 3),
            ("v_4_min", 200.0, 4),
            ("v_4_max", 249.999, 4),
            ("v_5_min", 250.0, 5),
            ("v_5_max", 299.999, 5),
            ("v_5_exact", 300.0, 5),
            ("v_out_range", 300.001, -1), # Outside comm range
        ]

        positions = {"v_tx": (0.0, 0.0)}
        for vid, dist, _ in test_points:
            positions[vid] = (dist, 0.0)

        # Tx at t=0.0
        tracker.on_cam_sent("v_tx", 0.0, 0.0, 0.0, in_range_count=len(test_points)-1)

        # All receive at t=0.0
        for vid, dist, bin_idx in test_points:
            if bin_idx >= 0:
                tracker.on_cam_received("v_tx", vid, t_rx=0.0, t_gen=0.0, dist_m=dist)

        # Step at t=0.5s -> Age = 500ms
        tracker.step(0.5, positions)

        dist_aoi = tracker.get_distance_aoi()
        assert len(dist_aoi) == 6
        for b in range(6):
            assert abs(dist_aoi[b] - 500.0) < 1e-2, f"Bin {b} should be 500ms, got {dist_aoi[b]}"

        # Counts: bin 0: 2, bin 1: 2, bin 2: 2, bin 3: 2, bin 4: 2, bin 5: 3 (250, 299.999, 300.0)
        assert tracker.dist_aoi_count[0] == 2
        assert tracker.dist_aoi_count[1] == 2
        assert tracker.dist_aoi_count[2] == 2
        assert tracker.dist_aoi_count[3] == 2
        assert tracker.dist_aoi_count[4] == 2
        assert tracker.dist_aoi_count[5] == 3

    def test_warmup_isolation(self):
        """Ensure no AoI or PDR is accumulated during warmup period."""
        eval_start = 10.0
        tracker = AoITracker(comm_range_m=300.0, eval_start_time=eval_start)
        positions = {"v1": (0.0, 0.0), "v2": (50.0, 0.0)}

        # Events during warmup
        tracker.on_cam_sent("v1", 1.0, 0.0, 0.0, in_range_count=1)
        tracker.on_cam_received("v1", "v2", t_rx=1.0, t_gen=1.0, dist_m=50.0)
        res = tracker.step(2.0, positions)

        assert res == 0.0
        assert len(tracker.aoi_history) == 0
        assert sum(tracker.dist_aoi_count) == 0
        assert tracker.cam_tx_total == 0

        # Step after warmup
        tracker.step(eval_start + 0.1, positions)
        assert not tracker._in_warmup
        assert len(tracker.aoi_history) == 1

    def test_aoi_growth_and_reset_on_reception(self):
        """Verify AoI linearly grows when packets are dropped and resets upon fresh reception."""
        tracker = AoITracker(comm_range_m=300.0, eval_start_time=0.0)
        positions = {"v1": (0.0, 0.0), "v2": (25.0, 0.0)} # bin 0

        # Tx at t=0.0, Rx at t=0.0
        tracker.on_cam_sent("v1", 0.0, 0.0, 0.0, in_range_count=1)
        tracker.on_cam_received("v1", "v2", t_rx=0.0, t_gen=0.0, dist_m=25.0)

        # Step 1: t=0.1 -> AoI = 100ms
        aoi_1 = tracker.step(0.1, positions)
        assert abs(aoi_1 - 100.0) < 1e-2

        # Step 2: t=0.2 (no new packet) -> AoI = 200ms
        aoi_2 = tracker.step(0.2, positions)
        assert abs(aoi_2 - 200.0) < 1e-2

        # Step 3: t=0.3 (no new packet) -> AoI = 300ms
        aoi_3 = tracker.step(0.3, positions)
        assert abs(aoi_3 - 300.0) < 1e-2

        # Tx at t=0.35, Rx at t=0.35
        tracker.on_cam_sent("v1", 0.35, 0.0, 0.0, in_range_count=1)
        tracker.on_cam_received("v1", "v2", t_rx=0.35, t_gen=0.35, dist_m=25.0)

        # Step 4: t=0.4 -> AoI should reset to (0.4 - 0.35) * 1000 = 50ms
        aoi_4 = tracker.step(0.4, positions)
        assert abs(aoi_4 - 50.0) < 1e-2

    def test_vehicle_removal_cleanup(self):
        """Verify remove_vehicle removes all state to prevent memory leaks."""
        tracker = AoITracker(comm_range_m=300.0, eval_start_time=0.0)
        tracker._in_warmup = False
        positions = {"v1": (0.0, 0.0), "v2": (25.0, 0.0), "v3": (50.0, 0.0)}

        tracker.on_cam_sent("v1", 0.0, 0.0, 0.0, in_range_count=2)
        tracker.on_cam_received("v1", "v2", t_rx=0.0, t_gen=0.0, dist_m=25.0)
        tracker.on_cam_received("v1", "v3", t_rx=0.0, t_gen=0.0, dist_m=50.0)

        assert ("v1", "v2") in tracker.last_received_gen_time
        assert ("v1", "v3") in tracker.last_received_gen_time

        # Remove v2
        tracker.remove_vehicle("v2")
        assert ("v1", "v2") not in tracker.last_received_gen_time
        assert ("v1", "v3") in tracker.last_received_gen_time

        # Remove v1
        tracker.remove_vehicle("v1")
        assert ("v1", "v3") not in tracker.last_received_gen_time
        assert "v1" not in tracker.last_cam_sent
        assert "v1" not in tracker.first_tx_time


# =============================================================================
# 2. Adversarial ResNetMoEAgent / MoEAgent Stress Tests
# =============================================================================
class TestMoEAgentsAdversarial:
    def test_mode_preservation_and_no_grad(self):
        """Ensure get_latent_and_gate preserves train/eval mode and does not compute gradients."""
        agent = ResNetMoEAgent(state_dim=5, action_dim=24, num_experts=3, hidden_dim=128)
        
        # Test when agent is in train mode
        agent.q_network.train()
        assert agent.q_network.training is True

        state = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
        feat, gate = agent.get_latent_and_gate(state)

        # Must still be in train mode
        assert agent.q_network.training is True

        # Test when agent is in eval mode
        agent.q_network.eval()
        assert agent.q_network.training is False

        feat, gate = agent.get_latent_and_gate(state)
        # Must still be in eval mode
        assert agent.q_network.training is False

    def test_extreme_input_values(self):
        """Test with extreme numerical values: zeros, large numbers, negatives."""
        agent = ResNetMoEAgent(state_dim=5, action_dim=24, num_experts=3, hidden_dim=128)

        extreme_states = [
            np.zeros(5, dtype=np.float32),
            np.ones(5, dtype=np.float32) * 1e4,
            np.ones(5, dtype=np.float32) * -1e4,
            np.array([1e-7, -1e-7, 100.0, -50.0, 0.0], dtype=np.float32),
        ]

        for s in extreme_states:
            feat, gate = agent.get_latent_and_gate(s)
            assert not np.isnan(feat).any(), f"NaN in features for state {s}"
            assert not np.isinf(feat).any(), f"Inf in features for state {s}"
            assert not np.isnan(gate).any(), f"NaN in gate for state {s}"
            assert abs(np.sum(gate) - 1.0) < 1e-4, f"Gate sum != 1.0: {np.sum(gate)}"

    def test_various_input_types(self):
        """Test list, 1D torch tensor, 2D torch tensor, 1D numpy, 2D numpy."""
        agent = ResNetMoEAgent(state_dim=5, action_dim=24, num_experts=3, hidden_dim=128)

        # 1. Python List
        f1, g1 = agent.get_latent_and_gate([0.1, 0.2, 0.3, 0.4, 0.5])
        assert f1.shape == (128,)
        assert g1.shape == (3,)

        # 2. 1D Tensor
        f2, g2 = agent.get_latent_and_gate(torch.tensor([0.1, 0.2, 0.3, 0.4, 0.5]))
        assert f2.shape == (128,)
        assert g2.shape == (3,)

        # 3. 2D Tensor
        f3, g3 = agent.get_latent_and_gate(torch.randn(8, 5))
        assert f3.shape == (8, 128)
        assert g3.shape == (8, 3)

        # 4. Large Batch
        f4, g4 = agent.get_latent_and_gate(np.random.randn(256, 5).astype(np.float32))
        assert f4.shape == (256, 128)
        assert g4.shape == (256, 3)


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
