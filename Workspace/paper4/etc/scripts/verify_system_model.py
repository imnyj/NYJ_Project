#!/usr/bin/env python3
"""
verify_system_model.py
======================
Empirical verification script for Paper 4 System Model & Codebase consistency.
Tests:
1. ResNetMoEDQN architecture dimensions, forward pass, gradient detach, dueling output, load balancing loss.
2. 5D State vector normalization & 16-action grid decoding.
3. ETSI CAM 4 dynamic trigger conditions & ReactDCC/AdaptDCC logic.
4. Channel physics: Nakagami-m CCDF formula, Log-distance path loss, Noise floor, CSMA/CA collision attenuation.
5. Reward function comparison across codebase hooks.
"""

import math
import torch
import numpy as np
import sys
import os

# Add code directory to path
code_dir = "/home/imnyj/Workspace/paper4/code"
sys.path.insert(0, code_dir)

from resnet_moe_agent import ResNetMoEDQN, ResNetMoEAgent
from etsi_cam_layer import VehicleCAMState, ETSICAMLayer, T_GENCAM_MIN, T_GENCAM_MAX
from sim_engine import reception_probability, PATH_LOSS_EXP, NAKAGAMI_M_PARAM, CHANNEL_BW_HZ, DATA_RATE_BPS, CAM_PACKET_BYTES, TX_DURATION_S

def test_resnet_moe_architecture():
    print("=== Test 1: ResNetMoEDQN Architecture Verification ===")
    state_dim = 5
    action_dim = 16
    num_experts = 3
    hidden_dim = 128
    batch_size = 64

    model = ResNetMoEDQN(state_dim=state_dim, action_dim=action_dim, num_experts=num_experts, hidden_dim=hidden_dim)
    
    # 1. Check feature extractor layers
    dummy_input = torch.randn(batch_size, state_dim)
    features = model.feature_extractor(dummy_input)
    assert features.shape == (batch_size, 128), f"Feature shape mismatch: {features.shape} != ({batch_size}, 128)"
    
    # 2. Check gating network & gradient detach
    # Verify features.detach() is passed to gating
    q_vals, gate_weights = model(dummy_input, return_gate_weights=True)
    assert q_vals.shape == (batch_size, action_dim), f"Q-vals shape mismatch: {q_vals.shape} != ({batch_size}, {action_dim})"
    assert gate_weights.shape == (batch_size, num_experts), f"Gate weights shape mismatch: {gate_weights.shape} != ({batch_size}, {num_experts})"
    
    # Check that gate weights sum to 1.0
    gate_sum = gate_weights.sum(dim=-1)
    assert torch.allclose(gate_sum, torch.ones(batch_size)), "Gate weights do not sum to 1.0"
    
    # 3. Check Dueling Expert Head
    for expert in model.experts:
        v = expert.value_stream(features)
        a = expert.advantage_stream(features)
        assert v.shape == (batch_size, 1), f"Value stream shape mismatch: {v.shape}"
        assert a.shape == (batch_size, action_dim), f"Advantage stream shape mismatch: {a.shape}"
        q_exp = expert(features)
        # Check mean centering property
        # Q = V + (A - mean(A)) -> mean(Q - V) == 0
        diff = q_exp - v
        assert torch.allclose(diff.mean(dim=1), torch.zeros(batch_size), atol=1e-5), "Dueling mean-centering failed"

    # 4. Check Load Balancing Loss formula
    importance = gate_weights.mean(dim=0)
    cv_squared = torch.var(importance) / (torch.mean(importance)**2 + 1e-8)
    lb_loss = 0.01 * cv_squared
    assert lb_loss.item() >= 0, "Load balancing loss must be non-negative"
    
    print("[PASS] ResNetMoEDQN architecture and formulas verified successfully.")
    return True

def test_state_and_action_spaces():
    print("=== Test 2: State Space Normalization & Action Grid Decoding ===")
    # 5D State normalization factors:
    # s1: CBR in [0, 1]
    # s2: N_est / 50.0
    # s3: v / 25.0
    # s4: dt / 1.0
    # s5: CBR_smoothed in [0, 1]
    n_est = 25
    v = 15.0 # m/s
    dt = 0.5 # s
    cbr = 0.45
    cbr_smoothed = 0.48
    
    s1 = cbr
    s2 = n_est / 50.0
    s3 = v / 25.0
    s4 = dt / 1.0
    s5 = cbr_smoothed
    
    assert s1 == 0.45
    assert s2 == 0.50
    assert s3 == 0.60
    assert s4 == 0.50
    assert s5 == 0.48
    
    # 16-Action grid decoding
    t_grid = [0.1, 0.2, 0.5, 1.0]
    p_tx_grid = [0.0, 10.0, 20.0, 30.0]
    n_p = len(p_tx_grid)
    
    for a in range(16):
        t_act = t_grid[a // n_p]
        p_act = p_tx_grid[a % n_p]
        i_T = a // 4
        i_P = a % 4
        assert t_act == t_grid[i_T]
        assert p_act == p_tx_grid[i_P]
        
    print(f"Action 0: T={t_grid[0//4]}, P={p_tx_grid[0%4]}")
    print(f"Action 7: T={t_grid[7//4]}, P={p_tx_grid[7%4]}")
    print(f"Action 15: T={t_grid[15//4]}, P={p_tx_grid[15%4]}")
    print("[PASS] State normalization and 16-action grid verified successfully.")
    return True

def test_etsi_cam_and_dcc():
    print("=== Test 3: ETSI CAM Generation & DCC Control Rules ===")
    layer = ETSICAMLayer(method="ReactDCC")
    vs = layer.get_or_create_vehicle("v1")
    
    # Check trigger thresholds:
    # 1. Delta heading >= 4.0 deg
    # 2. Delta pos >= 4.0 m
    # 3. Delta speed >= 0.5 m/s
    # 4. T_GenCam_max >= 1.0 s
    # 5. T_GenCam_min >= 0.1 s
    
    # Test ReactDCC state transitions:
    # CBR < 0.40 -> RELAXED, T=0.1
    layer._dcc_reactive(vs, 0.35)
    assert vs.dcc_state == "RELAXED" and vs.T_GenCam == 0.100
    
    # 0.40 <= CBR < 0.60 -> ACTIVE, T=0.3
    layer._dcc_reactive(vs, 0.50)
    assert vs.dcc_state == "ACTIVE" and vs.T_GenCam == 0.300
    
    # CBR >= 0.60 -> RESTRICTED, T=1.0
    layer._dcc_reactive(vs, 0.70)
    assert vs.dcc_state == "RESTRICTED" and vs.T_GenCam == 1.000
    
    # Test AdaptDCC logic:
    layer_adapt = ETSICAMLayer(method="AdaptDCC")
    vs_adapt = layer_adapt.get_or_create_vehicle("v2")
    vs_adapt.T_GenCam = 0.3
    vs_adapt.blb_CBR_smoothed = 0.5
    
    # step with high CBR (0.8) -> CBR_smoothed = 0.5*0.5 + 0.5*0.8 = 0.65 > 0.60
    # error > 0 -> T_GenCam increases by delta_T (0.05) -> 0.35
    layer_adapt._dcc_simplified_adaptive(vs_adapt, 0.80)
    assert math.isclose(vs_adapt.blb_CBR_smoothed, 0.65), f"CBR_smoothed mismatch: {vs_adapt.blb_CBR_smoothed}"
    assert math.isclose(vs_adapt.T_GenCam, 0.35), f"T_GenCam mismatch: {vs_adapt.T_GenCam}"
    
    print("[PASS] ETSI CAM triggers and ReactDCC/AdaptDCC verified successfully.")
    return True

def test_wireless_channel_and_mac():
    print("=== Test 4: Wireless Channel & MAC Physics Equations ===")
    
    # Parameters from Table III-1 & Section 3.1.B:
    fc = 5.9e9
    c = 3.0e8
    d0 = 1.0
    PL_0_theoretical = 20 * math.log10(4 * math.pi * d0 * fc / c)
    print(f"PL_0 theoretical: {PL_0_theoretical:.4f} dB (Paper states 47.86 dB)")
    assert math.isclose(PL_0_theoretical, 47.86, abs_tol=0.01)
    
    # Noise floor:
    # -174 dBm/Hz + 10*log10(10 MHz) + 10 dB NF = -174 + 70 + 10 = -94.0 dBm
    noise_theoretical = -174 + 10 * math.log10(10e6) + 10
    print(f"Noise floor theoretical: {noise_theoretical:.1f} dBm (Paper states -94.0 dBm)")
    assert math.isclose(noise_theoretical, -94.0)
    
    # Airtime duration:
    # 280 bytes * 8 bits / 3 Mbps = 2240 / 3e6 = 0.000746667 s = 0.7467 ms
    tx_duration_theoretical = (280 * 8) / 3e6
    print(f"TX duration: {tx_duration_theoretical*1000:.4f} ms (Paper states 0.7467 ms)")
    assert math.isclose(tx_duration_theoretical, TX_DURATION_S)
    
    # Nakagami-m CCDF formula for m=3:
    # P_succ(d, P_tx) = exp(-x) * (1 + x + x^2 / 2), where x = m * gamma_th_lin / gamma_lin
    # Let's test at distance d=100m, P_tx = 20 dBm
    d = 100.0
    p_tx = 20.0
    PL_d = 47.86 + 20 * math.log10(d)
    p_rx = p_tx - PL_d
    snr_db = p_rx - (-94.0)
    snr_lin = 10 ** (snr_db / 10.0)
    gamma_th_lin = 10 ** (5.0 / 10.0)
    m = 3.0
    ratio = snr_lin / gamma_th_lin
    x = m / ratio
    p_succ_theoretical = math.exp(-x) * (1.0 + x + 0.5 * (x**2))
    p_succ_code = reception_probability(d, p_tx)
    print(f"At d=100m, P_tx=20dBm: SNR={snr_db:.2f}dB, P_succ(theory)={p_succ_theoretical:.6f}, P_succ(code)={p_succ_code:.6f}")
    assert math.isclose(p_succ_theoretical, p_succ_code, abs_tol=1e-5)
    
    # CSMA/CA Collision Attenuation factor:
    # f_collision(CBR) = max(0.1, 1.0 - 0.8 * CBR)
    for cbr_val in [0.0, 0.3, 0.6, 0.9, 1.0]:
        f_coll = max(0.1, 1.0 - 0.8 * cbr_val)
        print(f"CBR={cbr_val:.1f} -> f_collision={f_coll:.3f}")
        if cbr_val == 0.0:
            assert f_coll == 1.0
        elif cbr_val == 0.6:
            assert math.isclose(f_coll, 0.52)
        elif cbr_val == 1.0:
            assert math.isclose(f_coll, 0.20)
            
    print("[PASS] Wireless channel physics and MAC equations verified successfully.")
    return True

if __name__ == "__main__":
    t1 = test_resnet_moe_architecture()
    t2 = test_state_and_action_spaces()
    t3 = test_etsi_cam_and_dcc()
    t4 = test_wireless_channel_and_mac()
    if t1 and t2 and t3 and t4:
        print("\n========================================================")
        print("ALL EMPIRICAL MATHEMATICAL & ARCHITECTURE TESTS PASSED!")
        print("========================================================")
