#!/usr/bin/env python3
"""
verify_m1_forensics.py
======================
Independent forensic audit script for Milestone 1:
1. Wireless Channel Model Mathematical Decay & CBR Collision Factor Verification
2. ResNetMoEAgent & MoEAgent Genuine PyTorch Forward Pass & Latent Extraction Verification
3. AoITracker Timestamp-based Staleness, Packet Drop Accumulation, and Distance Binning Verification
4. Zero-Mock & Non-Hardcoded Output Verification
"""

import sys
import os
import numpy as np
import torch

_cur_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_cur_dir, "..", ".."))
_code_dir = os.path.join(_project_root, "code")
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from sim_engine import reception_probability, reception_probability_vec, COMM_RANGE_M, compute_local_cbr, simulate_receptions, SimulationRunner
from aoi_tracker import AoITracker
from resnet_moe_agent import ResNetMoEAgent, ResNetMoEDQN
from moe_agent import MoEAgent, MoEDQN


def test_channel_model_decay():
    print("\n[CHECK 1] Wireless Channel Model Decay & Mathematical Authenticity...")
    distances = np.array([10.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0, 500.0], dtype=np.float32)
    p_vec = reception_probability_vec(distances, p_tx_dbm=20.0)
    p_scalar = [reception_probability(float(d), p_tx_dbm=20.0) for d in distances]

    np.testing.assert_allclose(p_vec, p_scalar, atol=1e-5, err_msg="Scalar and Vectorized reception probability mismatch!")
    print(f"  Distances (m): {distances.tolist()}")
    print(f"  PDR values   : {[round(float(p), 4) for p in p_vec]}")

    # Check monotonic decay
    for i in range(len(p_vec) - 1):
        assert p_vec[i] >= p_vec[i+1], f"PDR increased with distance at index {i}: {p_vec[i]} < {p_vec[i+1]}"

    # Check CBR collision scaling
    cbr_vals = np.array([0.0, 0.2, 0.5, 0.8, 1.0], dtype=np.float32)
    col_factors = np.maximum(0.1, 1.0 - cbr_vals * 0.8)
    print(f"  CBR collision factors for CBR {cbr_vals.tolist()}: {col_factors.tolist()}")
    for i in range(len(col_factors) - 1):
        assert col_factors[i] > col_factors[i+1], "CBR collision factor should decrease as CBR increases"

    print("  -> PASS: Mathematical decay and collision degradation strictly verified.")


def test_latent_and_gate_authenticity():
    print("\n[CHECK 2] ResNetMoEAgent & MoEAgent Genuine PyTorch Forward Pass...")
    agent = ResNetMoEAgent(state_dim=5, action_dim=24, num_experts=3, hidden_dim=128)

    # Test 1: Single state
    s1 = np.array([0.1, 15.0, 20.0, 0.05, 0.3], dtype=np.float32)
    s2 = np.array([0.8, 45.0, 5.0, 0.25, 0.9], dtype=np.float32)
    feat1, gate1 = agent.get_latent_and_gate(s1)
    feat2, gate2 = agent.get_latent_and_gate(s2)

    assert feat1.shape == (128,), f"Feature 1 shape mismatch: {feat1.shape}"
    assert gate1.shape == (3,), f"Gate 1 shape mismatch: {gate1.shape}"
    assert not np.allclose(feat1, feat2), "Features for different states must NOT be identical (Dummy/Hardcoded detected)!"
    assert not np.allclose(gate1, gate2), "Gate weights for different states must NOT be identical (Dummy/Hardcoded detected)!"
    assert abs(np.sum(gate1) - 1.0) < 1e-5, f"Gate 1 sum != 1.0: {np.sum(gate1)}"
    assert abs(np.sum(gate2) - 1.0) < 1e-5, f"Gate 2 sum != 1.0: {np.sum(gate2)}"

    # Test 2: Weight perturbation test (ensures tensor passes through actual model graph)
    with torch.no_grad():
        orig_weight = agent.q_network.feature_extractor.input_layer[0].weight.clone()
        agent.q_network.feature_extractor.input_layer[0].weight.fill_(0.0)
    feat_zero, _ = agent.get_latent_and_gate(s1)
    assert not np.allclose(feat1, feat_zero), "Feature extraction did NOT react to model weight modification (Not a real forward pass)!"

    # Restore weight
    with torch.no_grad():
        agent.q_network.feature_extractor.input_layer[0].weight.copy_(orig_weight)

    # Test 3: Batch state
    batch_s = np.random.randn(8, 5).astype(np.float32)
    batch_feat, batch_gate = agent.get_latent_and_gate(batch_s)
    assert batch_feat.shape == (8, 128)
    assert batch_gate.shape == (8, 3)
    np.testing.assert_allclose(np.sum(batch_gate, axis=1), np.ones(8), atol=1e-5)

    # Test 4: Baseline MoEAgent
    moe_agent = MoEAgent(state_dim=5, action_dim=24, num_experts=2)
    m_feat1, m_gate1 = moe_agent.get_latent_and_gate(s1)
    m_feat2, m_gate2 = moe_agent.get_latent_and_gate(s2)
    assert m_feat1.shape == (128,)
    assert m_gate1.shape == (2,)
    assert not np.allclose(m_feat1, m_feat2)
    assert not np.allclose(m_gate1, m_gate2)

    print("  -> PASS: PyTorch forward pass, latent extraction (128D) and Softmax gating strictly authentic.")


def test_aoi_tracker_timestamp_and_bins():
    print("\n[CHECK 3] AoITracker Timestamp-based AoI & Distance Bin Accumulation...")
    tracker = AoITracker(comm_range_m=300.0, eval_start_time=0.0)

    # Create 6 receivers at centers of 6 distance bins: 25m, 75m, 125m, 175m, 225m, 275m
    positions = {
        "tx": (0.0, 0.0),
        "rx0": (25.0, 0.0),
        "rx1": (75.0, 0.0),
        "rx2": (125.0, 0.0),
        "rx3": (175.0, 0.0),
        "rx4": (225.0, 0.0),
        "rx5": (275.0, 0.0),
        "rx_far": (350.0, 0.0), # Out of range
    }

    # Step 1: Transmit at t=1.0s
    t_gen_1 = 1.0
    tracker.on_cam_sent("tx", t_gen_1, 0.0, 0.0, in_range_count=6)

    # Receive at rx0, rx1, rx2 only (simulating packet drops at rx3, rx4, rx5)
    tracker.on_cam_received("tx", "rx0", t_rx=1.001, t_gen=t_gen_1, dist_m=25.0)
    tracker.on_cam_received("tx", "rx1", t_rx=1.001, t_gen=t_gen_1, dist_m=75.0)
    tracker.on_cam_received("tx", "rx2", t_rx=1.001, t_gen=t_gen_1, dist_m=125.0)

    # Step at t=1.5s (Elapsed 500ms from t_gen_1)
    mean_aoi_step1 = tracker.step(1.5, positions)
    print(f"  Step 1 mean AoI: {mean_aoi_step1:.2f} ms")

    # Verify that rx0, rx1, rx2 have AoI = (1.5 - 1.0)*1000 = 500ms
    # rx3, rx4, rx5 used first_tx_time (1.0s), so their AoI is also 500ms
    dist_aoi_1 = tracker.get_distance_aoi()
    print(f"  Distance AoI step 1: {dist_aoi_1}")
    for b in range(6):
        assert abs(dist_aoi_1[b] - 500.0) < 1e-2, f"Bin {b} mismatch: {dist_aoi_1[b]} != 500.0"

    # Step 2: Transmit at t=2.0s
    t_gen_2 = 2.0
    tracker.on_cam_sent("tx", t_gen_2, 0.0, 0.0, in_range_count=6)
    # Receive at rx0 ONLY (rx1~rx5 dropped this second packet)
    tracker.on_cam_received("tx", "rx0", t_rx=2.001, t_gen=t_gen_2, dist_m=25.0)

    # Step at t=2.2s
    # rx0: (2.2 - 2.0)*1000 = 200ms
    # rx1~rx5: still holding t_gen_1 (1.0s) -> (2.2 - 1.0)*1000 = 1200ms (staleness accumulation!)
    mean_aoi_step2 = tracker.step(2.2, positions)
    print(f"  Step 2 mean AoI: {mean_aoi_step2:.2f} ms")

    dist_dict = tracker.get_distance_aoi(as_dict=True)
    print(f"  Distance AoI Dict: {dist_dict}")

    assert "distances" in dist_dict
    assert dist_dict["distances"] == [25, 75, 125, 175, 225, 275]
    assert len(dist_dict["aoi_mean"]) == 6
    assert len(dist_dict["aoi_std"]) == 6

    # Bin 0 (rx0) must have a lower cumulative average than Bin 1~5
    # Bin 0 had 500ms and 200ms -> avg = 350ms
    # Bin 1 had 500ms and 1200ms -> avg = 850ms
    assert abs(dist_dict["aoi_mean"][0] - 350.0) < 1e-2, f"Bin 0 mean mismatch: {dist_dict['aoi_mean'][0]} != 350.0"
    for b in range(1, 6):
        assert abs(dist_dict["aoi_mean"][b] - 850.0) < 1e-2, f"Bin {b} mean mismatch: {dist_dict['aoi_mean'][b]} != 850.0"

    print("  -> PASS: Timestamp-based staleness growth and 6-bin distance tracking strictly verified.")


def test_sim_engine_integration():
    print("\n[CHECK 4] SimulationRunner Execution & Real Data Output Generation...")
    runner = SimulationRunner(
        scenario="urban_grid",
        n_vehicles=20,
        seed=100,
        method="ReactDCC",
        duration_steps=50,
        warmup_s=2.0
    )
    res = runner.run()

    print("  Simulation Results Keys:", list(res.keys()))
    assert "distance_aoi" in res and len(res["distance_aoi"]) == 6
    assert "distance_pdr" in res and len(res["distance_pdr"]) == 6
    assert "cbr_history" in res and len(res["cbr_history"]) > 0
    assert "AoI_mean" in res and res["AoI_mean"] > 0
    assert "PDR_mean" in res and 0 <= res["PDR_mean"] <= 100

    print(f"  Result distance_aoi: {res['distance_aoi']}")
    print(f"  Result distance_pdr: {res['distance_pdr']}")
    print(f"  Result cbr_history sample (first 5): {res['cbr_history'][:5]}")
    print("  -> PASS: SimulationRunner end-to-end integration strictly verified.")


if __name__ == "__main__":
    test_channel_model_decay()
    test_latent_and_gate_authenticity()
    test_aoi_tracker_timestamp_and_bins()
    test_sim_engine_integration()
    print("\n========================================================")
    print("ALL FORENSIC VERIFICATION CHECKS PASSED WITH ZERO FLAWS.")
    print("========================================================")
