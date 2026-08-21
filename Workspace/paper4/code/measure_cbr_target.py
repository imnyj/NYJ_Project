#!/usr/bin/env python3
"""
measure_cbr_target.py
=====================
Measures empirical CBR (Channel Busy Ratio) ranges across various vehicle densities
under the existing 802.11p channel model (sim_engine.py) with Fixed10Hz transmission,
and computes the calibrated CBR_TARGET for DRL congestion control.

Outputs:
  - Prints statistical summary per density
  - Saves detailed results to data/cbr_target_measurement.csv
  - Exports CBR_TARGET constant
"""

import os
import sys
import csv
import numpy as np

# Ensure code directory is in sys.path
_code_dir = os.path.dirname(os.path.abspath(__file__))
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from sim_engine import SimulationRunner

# Default calibrated CBR target based on channel model measurements
# (approx 80% of peak density CBR or saturation knee point)
DEFAULT_CBR_TARGET = 0.035


def run_cbr_measurement(densities=None, seeds=None, duration_steps=300, warmup_s=5.0, out_csv=None):
    if densities is None:
        densities = [10, 20, 30, 40, 50, 60, 80, 100]
    if seeds is None:
        seeds = [42, 123]
    if out_csv is None:
        data_dir = os.path.join(_code_dir, "..", "data")
        os.makedirs(data_dir, exist_ok=True)
        out_csv = os.path.join(data_dir, "cbr_target_measurement.csv")

    results = []
    all_cbr_peaks = []
    
    print("=" * 70)
    print("  Empirical CBR_TARGET Measurement Suite (Fixed10Hz Benchmark)")
    print("=" * 70)
    print(f"{'Density':>8} | {'Seed':>6} | {'Mean CBR':>10} | {'Std CBR':>10} | {'P95 CBR':>10} | {'Max CBR':>10}")
    print("-" * 70)

    for d in densities:
        for s in seeds:
            runner = SimulationRunner(
                scenario='urban_grid',
                n_vehicles=d,
                seed=s,
                method='Fixed10Hz',
                method_params={'n_vehicles_sweep': d},
                duration_steps=duration_steps,
                warmup_s=warmup_s
            )
            metrics = runner.run()
            cbr_hist = metrics.get('cbr_history', [])
            if cbr_hist:
                mean_c = float(np.mean(cbr_hist))
                std_c = float(np.std(cbr_hist))
                p95_c = float(np.percentile(cbr_hist, 95))
                max_c = float(np.max(cbr_hist))
            else:
                mean_c = std_c = p95_c = max_c = 0.0

            results.append({
                "density": d,
                "seed": s,
                "mean_cbr": mean_c,
                "std_cbr": std_c,
                "p95_cbr": p95_c,
                "max_cbr": max_c
            })
            all_cbr_peaks.append(max_c)
            print(f"{d:8d} | {s:6d} | {mean_c:10.4f} | {std_c:10.4f} | {p95_c:10.4f} | {max_c:10.4f}")

    # Write results to CSV
    with open(out_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["density", "seed", "mean_cbr", "std_cbr", "p95_cbr", "max_cbr"])
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    global_max_cbr = max(all_cbr_peaks) if all_cbr_peaks else 0.06
    # Target set to 70%~80% of max CBR under high density to penalize channel saturation
    recommended_target = round(global_max_cbr * 0.75, 4)

    print("=" * 70)
    print(f"Global Maximum CBR (100% 10Hz): {global_max_cbr:.4f}")
    print(f"Recommended CBR_TARGET (75% of Max): {recommended_target:.4f}")
    print(f"Results successfully saved to: {out_csv}")
    print("=" * 70)

    return recommended_target, results


if __name__ == "__main__":
    target, _ = run_cbr_measurement()
    print(f"Determined CBR_TARGET = {target}")
