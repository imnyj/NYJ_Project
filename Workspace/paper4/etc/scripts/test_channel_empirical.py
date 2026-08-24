#!/usr/bin/env python3
"""
test_channel_empirical.py
=========================
Comprehensive Empirical Verification & Adversarial Stress Harness for M1:
1. 802.11p Nakagami-m Channel Model & Path Loss Physics
2. CBR Collision Factor & Local CBR Sensing Computation
3. Real SUMO Simulation Sweep (Multi-density, Multi-method)
4. Distance vs PDR & Distance vs AoI Cross-Validation
5. CBR Time-Series Continuity & Range [0.0, 1.0]
6. Adversarial Stress Scenarios (Sudden departures, Extreme congestion, Single-vehicle)

Author: challenger_m1_2
Date: 2026-08-24
"""

import os
import sys
import math
import json
import time
import random
import numpy as np
from scipy import stats

_code_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "code")
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from sim_engine import (
    reception_probability,
    reception_probability_vec,
    compute_local_n_est,
    compute_local_cbr,
    simulate_receptions,
    SimulationRunner,
    COMM_RANGE_M,
    CHANNEL_BW_HZ,
    DATA_RATE_BPS,
    PATH_LOSS_EXP,
    NAKAGAMI_M_PARAM,
    TX_DURATION_S,
)
from aoi_tracker import AoITracker
from etsi_cam_layer import ETSICAMLayer, T_GENCAM_MIN, T_GENCAM_MAX


def run_math_channel_verification():
    print("\n========================================================")
    print("TEST SUITE 1: 802.11p Nakagami-m & Path Loss Physics")
    print("========================================================")
    results = {}

    # 1.1 Vectorized vs Scalar implementation consistency across 10,000 points
    distances = np.random.uniform(0.5, 600.0, size=10000)
    powers = np.random.choice([-10.0, -5.0, 0.0, 5.0, 10.0, 15.0, 20.0, 25.0], size=10000)

    vec_probs = reception_probability_vec(distances, powers)
    scalar_probs = np.array([reception_probability(float(d), float(p)) for d, p in zip(distances, powers)])

    max_diff = float(np.max(np.abs(vec_probs - scalar_probs)))
    print(f"[1.1] Vectorized vs Scalar Max Diff: {max_diff:.2e}")
    assert max_diff < 1e-6, f"Mismatch between scalar and vectorized calculation: {max_diff}"
    results["vec_scalar_max_diff"] = max_diff

    # 1.2 Monotonicity over distance (p_tx = 20 dBm)
    d_grid = np.linspace(1.0, 500.0, 500)
    p_grid = reception_probability_vec(d_grid, 20.0)

    is_monotonic_decay = np.all(np.diff(p_grid) <= 1e-9)
    print(f"[1.2] Distance Monotonic Decay: {'PASS' if is_monotonic_decay else 'FAIL'}")
    assert is_monotonic_decay, "reception_probability_vec is not monotonically non-increasing over distance!"

    sample_dists = [10.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0, 400.0, 500.0]
    sample_probs = reception_probability_vec(np.array(sample_dists), 20.0).tolist()
    print("      Distance P(rx) @ +20 dBm:")
    for d, pr in zip(sample_dists, sample_probs):
        print(f"        d = {d:5.1f}m -> P(rx) = {pr*100:6.2f}%")
    results["sample_distance_probs_20dbm"] = dict(zip(sample_dists, sample_probs))

    # 1.3 Power scaling at d=150m
    powers_test = [-5.0, 0.0, 5.0, 10.0, 15.0, 20.0]
    d_fixed = 150.0
    p_at_powers = [float(reception_probability(d_fixed, p)) for p in powers_test]
    is_power_monotonic = np.all(np.diff(p_at_powers) >= -1e-9)
    print(f"[1.3] Power Scaling Monotonicity @ d=150m: {'PASS' if is_power_monotonic else 'FAIL'}")
    for p, pr in zip(powers_test, p_at_powers):
        print(f"        P_tx = {p:+5.1f}dBm -> P(rx) = {pr*100:6.2f}%")
    assert is_power_monotonic, "P(rx) does not increase monotonically with Tx power!"
    results["power_scaling_150m"] = dict(zip(powers_test, p_at_powers))

    # 1.4 Controlled Power Grid vs Distance Grid (Monte Carlo & Closed Form)
    grid_powers = [0.0, 5.0, 10.0, 20.0]
    grid_dists = [25.0, 75.0, 125.0, 175.0, 225.0, 275.0]
    p_matrix = {}
    print("\n[1.4] Distance vs PDR across Transmit Powers (6 Distance Bins):")
    print("      Dist (m) |  P_tx=0dBm | P_tx=5dBm | P_tx=10dBm | P_tx=20dBm")
    print("      " + "-" * 55)
    for d in grid_dists:
        row = []
        for p in grid_powers:
            val = float(reception_probability(d, p))
            row.append(val)
        p_matrix[d] = row
        print(f"       {d:5.1f}m  |  {row[0]*100:8.2f}% | {row[1]*100:8.2f}% | {row[2]*100:9.2f}% | {row[3]*100:9.2f}%")
    results["power_distance_matrix"] = p_matrix

    # Verify that at lower power (e.g. 0 dBm or 5 dBm), PDR strictly and sharply drops with distance
    p_0dbm = [p_matrix[d][0] for d in grid_dists]
    assert p_0dbm[0] > 0.99 and p_0dbm[-1] < 1e-4, f"0 dBm curve should drop from 100% to 0%, got {p_0dbm}"
    corr_0dbm, _ = stats.spearmanr(grid_dists, p_0dbm)
    assert corr_0dbm < -0.99, f"0 dBm curve correlation with distance must be strongly negative, got {corr_0dbm}"

    # 1.5 CBR Collision Attenuation Factor
    cbr_grid = np.linspace(0.0, 1.0, 11)
    col_factors = np.maximum(0.1, 1.0 - cbr_grid * 0.8)
    print(f"\n[1.5] CBR Collision Factor: cbr=0.0 -> {col_factors[0]:.2f}, cbr=0.5 -> {col_factors[5]:.2f}, cbr=1.0 -> {col_factors[10]:.2f}")
    assert abs(col_factors[0] - 1.0) < 1e-6
    assert abs(col_factors[5] - 0.6) < 1e-6
    assert abs(col_factors[10] - 0.2) < 1e-6
    results["cbr_factors"] = dict(zip([round(c, 2) for c in cbr_grid], col_factors.tolist()))

    # 1.6 Edge case robustness
    edge_dists = np.array([0.0, -10.0, 1e-5, 1.0, 1000.0, 10000.0])
    edge_probs = reception_probability_vec(edge_dists, 20.0)
    print(f"[1.6] Edge Cases P(rx): d=0 -> {edge_probs[0]}, d=-10 -> {edge_probs[1]}, d=10000 -> {edge_probs[5]:.2e}")
    assert edge_probs[0] == 1.0
    assert edge_probs[1] == 1.0
    assert edge_probs[5] < 1e-20
    assert np.all(edge_probs >= 0.0) and np.all(edge_probs <= 1.0)

    print(">>> TEST SUITE 1 PASSED SUCCESSFULLY.\n")
    return results


def run_cbr_sensing_verification():
    print("========================================================")
    print("TEST SUITE 2: Local CBR Sensing & Neighbor Density")
    print("========================================================")
    results = {}

    # 2.1 Synthetic topology: Center vehicle v0, 10 neighbors within 100m, 5 outside (400m)
    positions = {"v0": (0.0, 0.0)}
    for i in range(1, 11):
        positions[f"v_near_{i}"] = (float(i * 10.0), 0.0)
    for i in range(1, 6):
        positions[f"v_far_{i}"] = (float(350.0 + i * 20.0), 0.0)

    n_est = compute_local_n_est(positions, COMM_RANGE_M)
    print(f"[2.1] n_est for v0 (expected 10): {n_est['v0']}")
    assert n_est["v0"] == 10, f"Expected 10 neighbors, got {n_est['v0']}"

    # 2.2 Exact CAM packet CBR calculation
    tx_events = [{"vid": "v0", "x": 0.0, "y": 0.0}]
    for i in range(1, 6):
        tx_events.append({"vid": f"v_near_{i}", "x": float(i * 10.0), "y": 0.0})

    cbr_dict, cbr_mean = compute_local_cbr(positions, tx_events, window_duration_s=0.1)
    expected_cbr = 6 * TX_DURATION_S / 0.1
    print(f"[2.2] Measured CBR for v0: {cbr_dict['v0']:.6f}, Expected: {expected_cbr:.6f}")
    assert abs(cbr_dict["v0"] - expected_cbr) < 1e-5, f"CBR calculation error: {cbr_dict['v0']} vs {expected_cbr}"

    # 2.3 Saturation test: 200 packets in 100ms window
    tx_events_heavy = [{"vid": "v0", "x": 0.0, "y": 0.0} for _ in range(200)]
    cbr_dict_sat, _ = compute_local_cbr(positions, tx_events_heavy, window_duration_s=0.1)
    print(f"[2.3] Saturated CBR for v0 (expected 1.0): {cbr_dict_sat['v0']}")
    assert cbr_dict_sat["v0"] == 1.0, f"Saturated CBR must be 1.0, got {cbr_dict_sat['v0']}"

    print(">>> TEST SUITE 2 PASSED SUCCESSFULLY.\n")
    return results


def run_controlled_distance_aoi_pdr_monte_carlo():
    print("========================================================")
    print("TEST SUITE 3: Controlled Distance vs AoI & PDR Monte Carlo")
    print("========================================================")
    results = {}
    
    # Simulate a controlled 6-distance topology with realistic packet reception & AoI tracking
    # 6 pairs at distances 25m, 75m, 125m, 175m, 225m, 275m
    # Sender transmits at 10 Hz with transmit power p_tx = 5 dBm and background CBR = 0.3
    # Duration: 50 seconds (500 steps)
    tracker = AoITracker(comm_range_m=300.0, eval_start_time=0.0)
    rng = random.Random(12345)
    
    distances = [25.0, 75.0, 125.0, 175.0, 225.0, 275.0]
    p_tx_dbm = 5.0
    cbr = 0.30
    col_factor = max(0.1, 1.0 - cbr * 0.8) # 0.76
    
    positions = {"v_tx": (0.0, 0.0)}
    for idx, d in enumerate(distances):
        positions[f"v_rx_{idx}"] = (d, 0.0)
        
    p_rx_theoretical = [float(reception_probability(d, p_tx_dbm)) * col_factor for d in distances]
    
    tx_counts = [0] * 6
    rx_counts = [0] * 6
    
    steps = 5000
    for s in range(steps):
        t_sim = s * 0.1
        # Transmit CAM every 0.1s
        tracker.on_cam_sent("v_tx", t_sim, 0.0, 0.0, in_range_count=6)
        
        for idx, d in enumerate(distances):
            tx_counts[idx] += 1
            p_succ = p_rx_theoretical[idx]
            if rng.random() < p_succ:
                rx_counts[idx] += 1
                tracker.on_cam_received("v_tx", f"v_rx_{idx}", t_rx=t_sim, t_gen=t_sim, dist_m=d)
                
        tracker.step(t_sim, positions)
        
    emp_pdrs = [rx / tx * 100.0 for rx, tx in zip(rx_counts, tx_counts)]
    emp_aois = tracker.get_distance_aoi()
    
    print("Controlled Topology Results (P_tx = +5 dBm, CBR = 0.30, 50s run):")
    print("  Distance Bin | P(succ) Th. | Emp PDR (%) | Emp AoI (ms)")
    print("  " + "-" * 55)
    for idx, d in enumerate(distances):
        print(f"    {d:5.1f}m     |   {p_rx_theoretical[idx]*100:6.2f}%   |   {emp_pdrs[idx]:6.2f}%  |  {emp_aois[idx]:7.2f} ms")
        
    # Cross-validation assertions:
    # 1. PDR must strictly decrease with distance
    pdr_monotonic = all(emp_pdrs[i] >= emp_pdrs[i+1] for i in range(len(emp_pdrs)-1))
    print(f"\n  [3.1] Controlled Distance-PDR Monotonic Decay: {'PASS' if pdr_monotonic else 'FAIL'}")
    assert pdr_monotonic, f"Empirical PDR is not monotonically decreasing: {emp_pdrs}"
    
    # 2. AoI must strictly increase with distance
    aoi_monotonic = all(emp_aois[i] <= emp_aois[i+1] for i in range(len(emp_aois)-1))
    print(f"  [3.2] Controlled Distance-AoI Monotonic Growth: {'PASS' if aoi_monotonic else 'FAIL'}")
    assert aoi_monotonic, f"Empirical AoI is not monotonically increasing: {emp_aois}"
    
    # 3. Correlation metrics
    corr_pdr, _ = stats.spearmanr(distances, emp_pdrs)
    corr_aoi, _ = stats.spearmanr(distances, emp_aois)
    print(f"  [3.3] Distance vs PDR Spearman Correlation: {corr_pdr:.4f} (target < -0.95)")
    print(f"  [3.4] Distance vs AoI Spearman Correlation: {corr_aoi:.4f} (target > +0.95)")
    assert corr_pdr < -0.95, f"PDR correlation should be strongly negative: {corr_pdr}"
    assert corr_aoi > 0.95, f"AoI correlation should be strongly positive: {corr_aoi}"
    
    results["distances"] = distances
    results["emp_pdrs"] = emp_pdrs
    results["emp_aois"] = emp_aois
    results["corr_pdr"] = corr_pdr
    results["corr_aoi"] = corr_aoi
    
    print(">>> TEST SUITE 3 PASSED SUCCESSFULLY.\n")
    return results


def run_sumo_empirical_simulation_sweep():
    print("========================================================")
    print("TEST SUITE 4: Full SUMO Simulation Sweep & Metrics Audit")
    print("========================================================")
    densities = [10, 25, 40]
    methods = ["Fixed10Hz", "ReactDCC", "AdaptDCC"]
    sweep_records = []

    for n_veh in densities:
        for method in methods:
            print(f"\n--- Running SUMO Simulation: Density={n_veh} veh, Method={method} ---")
            t0 = time.time()
            runner = SimulationRunner(
                scenario="urban_grid",
                n_vehicles=n_veh,
                seed=42 + n_veh,
                method=method,
                method_params={"n_vehicles_sweep": n_veh},
                duration_steps=250, # 25s simulation
                warmup_s=5.0        # 5s warmup (50 steps)
            )
            metrics = runner.run()
            elapsed = time.time() - t0

            # Inspect metrics
            cbr_hist = metrics["cbr_history"]
            dist_pdr = metrics["distance_pdr"]
            dist_aoi = metrics["distance_aoi"]

            print(f"  Completed in {elapsed:.2f}s (sim runtime: {metrics['runtime_sec']}s)")
            print(f"  AoI_mean: {metrics['AoI_mean']} ms, CBR_mean: {metrics['CBR_mean']}, PDR_mean: {metrics['PDR_mean']}%")
            print(f"  Distance PDR (6 bins: 25, 75, 125, 175, 225, 275m): {[round(x, 2) for x in dist_pdr]}")
            print(f"  Distance AoI (6 bins: 25, 75, 125, 175, 225, 275m): {dist_aoi}")
            print(f"  CBR History: len={len(cbr_hist)}, min={min(cbr_hist) if cbr_hist else 0:.4f}, max={max(cbr_hist) if cbr_hist else 0:.4f}")

            # Verification 4.1: CBR history continuity and range
            expected_steps = 250 - int(5.0 / 0.1) # 200 steps
            assert len(cbr_hist) == expected_steps, f"CBR history length mismatch: {len(cbr_hist)} vs {expected_steps}"
            assert all(0.0 <= c <= 1.0 for c in cbr_hist), "CBR values out of range [0.0, 1.0]!"
            assert not any(math.isnan(c) or math.isinf(c) for c in cbr_hist), "NaN or Inf in cbr_history!"

            # Step-to-step delta check
            cbr_deltas = [abs(cbr_hist[i] - cbr_hist[i-1]) for i in range(1, len(cbr_hist))]
            max_delta = max(cbr_deltas) if cbr_deltas else 0.0
            mean_delta = np.mean(cbr_deltas) if cbr_deltas else 0.0
            print(f"  CBR Step Deltas: max={max_delta:.4f}, mean={mean_delta:.4f}")
            assert max_delta < 0.20, f"Unreasonably abrupt CBR discontinuity: max delta = {max_delta}"

            sweep_records.append({
                "n_vehicles": n_veh,
                "method": method,
                "AoI_mean": metrics["AoI_mean"],
                "CBR_mean": metrics["CBR_mean"],
                "PDR_mean": metrics["PDR_mean"],
                "distance_pdr": dist_pdr,
                "distance_aoi": dist_aoi,
                "cbr_history_len": len(cbr_hist),
                "cbr_min": float(min(cbr_hist)),
                "cbr_max": float(max(cbr_hist)),
                "cbr_max_step_delta": float(max_delta),
                "cbr_mean_step_delta": float(mean_delta),
            })

    # Verification 4.2: Density Scaling across methods
    print("\n[4.2] Density Scaling Analysis:")
    for method in methods:
        sub_records = [r for r in sweep_records if r["method"] == method]
        cbr_vals = [r["CBR_mean"] for r in sub_records]
        print(f"      {method:10s} -> Densities {[r['n_vehicles'] for r in sub_records]} : CBRs {cbr_vals}")
        # CBR must increase with density
        assert cbr_vals[0] < cbr_vals[1] < cbr_vals[2], f"CBR must strictly increase with vehicle density for {method}: {cbr_vals}"

    print(">>> TEST SUITE 4 PASSED EMPIRICALLY.\n")
    return sweep_records


def run_adversarial_stress_tests():
    print("========================================================")
    print("TEST SUITE 5: Adversarial Stress & Corner Cases")
    print("========================================================")
    results = {}

    # 5.1 Vehicle departure cleanup & stale state test
    tracker = AoITracker(comm_range_m=300.0, eval_start_time=0.0)
    pos = {
        "v_stable": (0.0, 0.0),
        "v_departing": (50.0, 0.0),
    }
    tracker.on_cam_sent("v_departing", 1.0, 50.0, 0.0, in_range_count=1)
    tracker.on_cam_received("v_departing", "v_stable", t_rx=1.0, t_gen=1.0, dist_m=50.0)
    aoi_before = tracker.step(1.5, pos)
    assert aoi_before > 0

    # Simulate departure
    tracker.remove_vehicle("v_departing")
    pos_after = {"v_stable": (0.0, 0.0)}
    aoi_after = tracker.step(2.0, pos_after)
    print(f"[5.1] AoI after vehicle departure: {aoi_after} (expected 0.0)")
    assert aoi_after == 0.0, f"AoI should be 0.0 after other vehicle departs, got {aoi_after}"
    assert "v_departing" not in tracker.last_cam_sent
    assert ("v_departing", "v_stable") not in tracker.last_received_gen_time

    # 5.2 Massive congestion stress test: 200 co-located vehicles
    print("[5.2] Testing massive congestion cluster (200 vehicles)...")
    dense_pos = {f"v_{i}": (float(i % 10), float(i // 10)) for i in range(200)}
    dense_tx_events = [{"vid": f"v_{i}", "x": float(i % 10), "y": float(i // 10), "p_tx": 20.0, "t_gen": 1.0} for i in range(200)]
    cbr_dict_dense, cbr_mean_dense = compute_local_cbr(dense_pos, dense_tx_events, window_duration_s=0.1)
    assert 0.0 <= cbr_mean_dense <= 1.0
    assert not math.isnan(cbr_mean_dense)

    # Reception simulation under massive congestion
    dist_tx = [0]*6
    dist_rx = [0]*6
    receptions = simulate_receptions(
        dense_tx_events, dense_pos, cbr_dict_dense, random.Random(42),
        dist_tx, dist_rx, is_warmup=False
    )
    print(f"      Dense simulation: 200 vehicles -> Total Tx events: {len(dense_tx_events)}, Receptions: {len(receptions)}")
    print(f"      dist_tx: {dist_tx}, dist_rx: {dist_rx}")
    assert sum(dist_tx) > 0
    pdr_dense = sum(dist_rx) / sum(dist_tx) * 100.0
    print(f"      Congested Cluster PDR: {pdr_dense:.2f}%")
    assert pdr_dense < 90.0, f"Dense cluster PDR should be degraded, got {pdr_dense}%"

    # 5.3 Zero vehicles / isolated vehicle test
    single_pos = {"v_lone": (100.0, 100.0)}
    n_lone = compute_local_n_est(single_pos, 300.0)
    assert n_lone["v_lone"] == 0
    cbr_lone, mean_lone = compute_local_cbr(single_pos, [{"vid": "v_lone", "x": 100.0, "y": 100.0}], 0.1)
    assert 0.0 <= cbr_lone["v_lone"] <= 1.0

    print(">>> TEST SUITE 5 PASSED SUCCESSFULLY.\n")
    return results


def main():
    print("================================================================================")
    print("  EMPIRICAL CHALLENGER M1 VERIFICATION (challenger_m1_2)  ")
    print("================================================================================")

    math_res = run_math_channel_verification()
    cbr_res = run_cbr_sensing_verification()
    mc_res = run_controlled_distance_aoi_pdr_monte_carlo()
    sweep_res = run_sumo_empirical_simulation_sweep()
    stress_res = run_adversarial_stress_tests()

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "ALL_TESTS_PASSED",
        "math_channel_verification": math_res,
        "cbr_sensing_verification": cbr_res,
        "controlled_monte_carlo": mc_res,
        "sumo_empirical_sweep": sweep_res,
        "adversarial_stress_tests": "PASSED"
    }

    out_json_path = "/home/imnyj/Workspace/paper4/etc/scripts/test_channel_empirical_results.json"
    with open(out_json_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nAll empirical verification tests completed successfully.")
    print(f"Summary saved to: {out_json_path}")


if __name__ == "__main__":
    main()
