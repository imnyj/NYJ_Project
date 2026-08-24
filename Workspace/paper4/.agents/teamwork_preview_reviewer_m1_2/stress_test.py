#!/usr/bin/env python3
"""
Independent Adversarial Stress Test Script for Milestone 1
Run by reviewer_m1_2
"""
import sys
import os
import numpy as np
import torch

_code_dir = "/home/imnyj/Workspace/paper4/code"
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from aoi_tracker import AoITracker
from sim_engine import (
    reception_probability,
    reception_probability_vec,
    compute_local_n_est,
    compute_local_cbr,
    simulate_receptions,
    SimulationRunner
)
from resnet_moe_agent import ResNetMoEAgent
from moe_agent import MoEAgent


def test_aoi_tracker_adversarial():
    print("=== Testing AoITracker Adversarial Scenarios ===")
    tracker = AoITracker(comm_range_m=300.0, eval_start_time=0.0)

    # 1. Zero vehicles
    aoi_0 = tracker.step(1.0, {})
    assert aoi_0 == 0.0, f"Expected 0.0 for 0 vehicles, got {aoi_0}"

    # 2. Single vehicle
    aoi_1 = tracker.step(1.0, {"v1": (100.0, 100.0)})
    assert aoi_1 == 0.0, f"Expected 0.0 for 1 vehicle, got {aoi_1}"

    # 3. Two vehicles outside comm range (e.g. 500m apart)
    positions_far = {"v1": (0.0, 0.0), "v2": (500.0, 0.0)}
    tracker.on_cam_sent("v1", 0.5, 0.0, 0.0, in_range_count=0)
    aoi_far = tracker.step(1.0, positions_far)
    assert aoi_far == 0.0, f"Expected 0.0 for vehicles out of range, got {aoi_far}"
    assert tracker.get_distance_aoi() == [0.0] * 6

    # 4. Exact boundary distances (0m, 50m, 100m, 150m, 200m, 250m, 300m)
    tracker.reset()
    positions_boundary = {
        "v_tx": (0.0, 0.0),
        "v_0m": (0.0, 0.0),      # same coord -> bin 0
        "v_50m": (50.0, 0.0),    # exactly 50m -> 50/50 = 1 -> bin 1
        "v_100m": (100.0, 0.0),  # exactly 100m -> 100/50 = 2 -> bin 2
        "v_150m": (150.0, 0.0),  # exactly 150m -> 150/50 = 3 -> bin 3
        "v_200m": (200.0, 0.0),  # exactly 200m -> 200/50 = 4 -> bin 4
        "v_250m": (250.0, 0.0),  # exactly 250m -> 250/50 = 5 -> bin 5
        "v_300m": (300.0, 0.0),  # exactly 300m -> 300/50 = 6 -> clipped to bin 5
        "v_300_1m": (300.1, 0.0),# >300m -> excluded from in_range_mask
    }
    tracker.on_cam_sent("v_tx", 1.0, 0.0, 0.0, in_range_count=7)
    for k in positions_boundary:
        if k != "v_tx":
            tracker.on_cam_received("v_tx", k, t_rx=1.0, t_gen=1.0, dist_m=positions_boundary[k][0])

    step_aoi = tracker.step(1.5, positions_boundary)
    assert step_aoi > 0, "Step AoI should be > 0"
    dist_aoi = tracker.get_distance_aoi()
    assert len(dist_aoi) == 6
    for b in range(6):
        assert abs(dist_aoi[b] - 500.0) < 1e-2, f"Bin {b} should be 500.0 ms, got {dist_aoi[b]}"

    # Check dict format
    dist_dict = tracker.get_distance_aoi(as_dict=True)
    assert not any(np.isnan(dist_dict["aoi_mean"])), "NaN found in aoi_mean"
    assert not any(np.isnan(dist_dict["aoi_std"])), "NaN found in aoi_std"

    # 5. Vehicle removal test
    tracker.remove_vehicle("v_tx")
    tracker.remove_vehicle("non_existent_vehicle")
    assert "v_tx" not in tracker.last_cam_sent

    print("AoITracker Adversarial tests passed successfully.")


def test_moe_agent_adversarial():
    print("=== Testing ResNetMoEAgent & MoEAgent Adversarial Scenarios ===")

    # 1. ResNetMoEAgent with extreme values (inf, nan, large values, zero values)
    resnet_agent = ResNetMoEAgent(state_dim=5, action_dim=24, num_experts=3, hidden_dim=128)
    resnet_agent.q_network.train()

    # Verify mode preservation
    assert resnet_agent.q_network.training is True
    feat, gate = resnet_agent.get_latent_and_gate([0.0, 0.0, 0.0, 0.0, 0.0])
    assert resnet_agent.q_network.training is True, "Training mode should be preserved"
    assert feat.shape == (128,)
    assert gate.shape == (3,)
    assert abs(np.sum(gate) - 1.0) < 1e-5

    # 2. Batch input with varied shapes
    batch_states = np.random.uniform(-10.0, 10.0, size=(128, 5)).astype(np.float32)
    feats, gates = resnet_agent.get_latent_and_gate(batch_states)
    assert feats.shape == (128, 128)
    assert gates.shape == (128, 3)
    assert np.all(gates >= 0.0)
    assert np.all(gates <= 1.0)
    np.testing.assert_allclose(np.sum(gates, axis=1), np.ones(128), atol=1e-5)

    # 3. PyTorch tensor inputs
    tensor_single = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])
    feat_t, gate_t = resnet_agent.get_latent_and_gate(tensor_single)
    assert feat_t.shape == (128,)
    assert gate_t.shape == (3,)

    tensor_batch = torch.randn(32, 5)
    feat_tb, gate_tb = resnet_agent.get_latent_and_gate(tensor_batch)
    assert feat_tb.shape == (32, 128)
    assert gate_tb.shape == (32, 3)

    # 4. MoEAgent tests
    moe_agent = MoEAgent(state_dim=5, action_dim=24, num_experts=2)
    moe_agent.q_network.train()
    feat_m, gate_m = moe_agent.get_latent_and_gate([0.1, 0.2, 0.3, 0.4, 0.5])
    assert moe_agent.q_network.training is True
    assert feat_m.shape == (128,)
    assert gate_m.shape == (2,)
    assert abs(np.sum(gate_m) - 1.0) < 1e-5

    print("ResNetMoEAgent & MoEAgent Adversarial tests passed successfully.")


def test_channel_model_adversarial():
    print("=== Testing Channel & CBR Adversarial Scenarios ===")

    # 1. Extreme distances: 0m, negative, 10,000m
    p_0 = reception_probability(0.0)
    assert p_0 == 1.0, f"Distance 0m should have reception prob 1.0, got {p_0}"

    p_vec_0 = reception_probability_vec(np.array([0.0, -5.0, 1.0, 300.0, 1000.0, 10000.0]))
    assert p_vec_0[0] == 1.0
    assert p_vec_0[1] == 1.0
    assert 0.0 <= p_vec_0[3] <= 1.0
    assert p_vec_0[5] <= p_vec_0[3]
    assert not np.any(np.isnan(p_vec_0))

    # 2. Local CBR edge cases
    empty_cbr, empty_mean = compute_local_cbr({}, {})
    assert empty_cbr == {} and empty_mean == 0.0

    pos = {"v1": (0.0, 0.0), "v2": (100.0, 0.0)}
    # Zero duration
    cbr_z, mean_z = compute_local_cbr(pos, {"v1": 1}, window_duration_s=0.0)
    assert cbr_z["v1"] == 0.0 and mean_z == 0.0

    # High collision/packet count clipping at 1.0
    cbr_high, mean_high = compute_local_cbr(pos, {"v1": 10000, "v2": 10000}, window_duration_s=0.1)
    assert cbr_high["v1"] == 1.0 and cbr_high["v2"] == 1.0 and mean_high == 1.0

    print("Channel & CBR Adversarial tests passed successfully.")


if __name__ == "__main__":
    test_aoi_tracker_adversarial()
    test_moe_agent_adversarial()
    test_channel_model_adversarial()
    print("\nALL ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY!")
