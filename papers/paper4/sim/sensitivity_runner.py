#!/usr/bin/env python3
"""
sensitivity_runner.py
=====================
Sensitivity sweep orchestrator for paper4 experiments.

Sweeps:
  SA1 - Vehicle density (n_vehicles): tests how density affects AoI/CBR/PDR
  SA2 - DCC method comparison: BL-A vs BL-B vs BL-C vs BL-D
  SA3 - BL-B (Simplified Adaptive) gain parameter sweep (cbr_target)
  SA4 - Scenario comparison: urban_grid vs highway

For each (param_value, seed) combination:
  - Runs SimulationRunner.run()
  - Saves per-run result to CSV
  - Aggregates to sensitivity_summary.json

Usage:
  python3 sensitivity_runner.py --sweep SA3
  python3 sensitivity_runner.py --sweep all

Author: Experimenter agent (Stage 2: implement)
"""

import os
import sys
import csv
import json
import time
import argparse
import traceback
from datetime import datetime
from typing import List, Dict, Any

# Ensure sim directory is on path
_sim_dir = os.path.dirname(os.path.abspath(__file__))
if _sim_dir not in sys.path:
    sys.path.insert(0, _sim_dir)

from sim_engine import SimulationRunner

# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------
DATA_DIR = os.environ.get("DATA_DIR", "/home/imnyj/papers/paper4/paper/data")
os.makedirs(DATA_DIR, exist_ok=True)

CSV_COLUMNS = [
    "sweep_id", "param_name", "param_value", "seed",
    "AoI_mean", "CBR_mean", "PDR_mean",
    "energy_efficiency", "ETSI_compliance",
    "runtime_sec", "n_cam_events", "status", "error"
]

# ---------------------------------------------------------------------------
# Sweep definitions
# ---------------------------------------------------------------------------

# Common settings
BASE_SEEDS = [42, 123, 456]       # 3 seeds per configuration
DURATION_STEPS = 3000             # 300 s at 0.1 s/step
WARMUP_S = 30.0
BASE_N_VEHICLES = 30
BASE_SCENARIO = "urban_grid"


def define_sweeps() -> Dict[str, List[Dict[str, Any]]]:
    """
    Returns dict mapping sweep_id -> list of run_config dicts.
    Each run_config has: param_name, param_value, seed, SimulationRunner kwargs.
    """
    sweeps = {}

    # ------------------------------------------------------------------
    # SA1: Vehicle density sweep (n_vehicles), method=BL-A
    # ------------------------------------------------------------------
    sa1_runs = []
    for n_veh in [10, 20, 30, 50, 75, 100]:
        for seed in BASE_SEEDS:
            sa1_runs.append({
                "param_name": "n_vehicles",
                "param_value": n_veh,
                "seed": seed,
                "runner_kwargs": {
                    "scenario": BASE_SCENARIO,
                    "n_vehicles": n_veh,
                    "seed": seed,
                    "method": "BL-A",
                    "method_params": {},
                    "duration_steps": DURATION_STEPS,
                    "warmup_s": WARMUP_S,
                },
            })
    sweeps["SA1"] = sa1_runs

    # ------------------------------------------------------------------
    # SA2: DCC method comparison, n_vehicles=30
    # ------------------------------------------------------------------
    sa2_runs = []
    methods = ["BL-A", "BL-B", "BL-C", "BL-D"]
    for method in methods:
        for seed in BASE_SEEDS:
            sa2_runs.append({
                "param_name": "method",
                "param_value": method,
                "seed": seed,
                "runner_kwargs": {
                    "scenario": BASE_SCENARIO,
                    "n_vehicles": BASE_N_VEHICLES,
                    "seed": seed,
                    "method": method,
                    "method_params": {},
                    "duration_steps": DURATION_STEPS,
                    "warmup_s": WARMUP_S,
                },
            })
    sweeps["SA2"] = sa2_runs

    # ------------------------------------------------------------------
    # SA3: BL-B cbr_target parameter sweep (Simplified Adaptive gain)
    # cbr_target controls the desired channel busy ratio
    # ------------------------------------------------------------------
    sa3_runs = []
    for cbr_target in [0.30, 0.40, 0.50, 0.55, 0.60, 0.65, 0.70]:
        for seed in BASE_SEEDS:
            sa3_runs.append({
                "param_name": "cbr_target",
                "param_value": cbr_target,
                "seed": seed,
                "runner_kwargs": {
                    "scenario": BASE_SCENARIO,
                    "n_vehicles": BASE_N_VEHICLES,
                    "seed": seed,
                    "method": "BL-B",
                    "method_params": {"cbr_target": cbr_target},
                    "duration_steps": DURATION_STEPS,
                    "warmup_s": WARMUP_S,
                },
            })
    sweeps["SA3"] = sa3_runs

    # ------------------------------------------------------------------
    # SA4: Scenario comparison (urban_grid vs highway), method=BL-A
    # ------------------------------------------------------------------
    sa4_runs = []
    for scenario in ["urban_grid", "highway"]:
        for n_veh in [20, 30, 50]:
            for seed in BASE_SEEDS:
                sa4_runs.append({
                    "param_name": "scenario",
                    "param_value": scenario,
                    "seed": seed,
                    "extra": {"n_vehicles": n_veh},
                    "runner_kwargs": {
                        "scenario": scenario,
                        "n_vehicles": n_veh,
                        "seed": seed,
                        "method": "BL-A",
                        "method_params": {},
                        "duration_steps": DURATION_STEPS,
                        "warmup_s": WARMUP_S,
                    },
                })
    sweeps["SA4"] = sa4_runs

    return sweeps


# ---------------------------------------------------------------------------
# Runner helpers
# ---------------------------------------------------------------------------

def run_one(sweep_id: str, run_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single SimulationRunner and return result row."""
    row = {
        "sweep_id": sweep_id,
        "param_name": run_cfg["param_name"],
        "param_value": str(run_cfg["param_value"]),
        "seed": run_cfg["seed"],
        "AoI_mean": None,
        "CBR_mean": None,
        "PDR_mean": None,
        "energy_efficiency": None,
        "ETSI_compliance": None,
        "runtime_sec": None,
        "n_cam_events": None,
        "status": "pending",
        "error": "",
    }
    try:
        runner = SimulationRunner(**run_cfg["runner_kwargs"])
        metrics = runner.run()
        row.update({
            "AoI_mean": metrics.get("AoI_mean"),
            "CBR_mean": metrics.get("CBR_mean"),
            "PDR_mean": metrics.get("PDR_mean"),
            "energy_efficiency": metrics.get("energy_efficiency"),
            "ETSI_compliance": metrics.get("ETSI_compliance"),
            "runtime_sec": metrics.get("runtime_sec"),
            "n_cam_events": metrics.get("n_cam_events"),
            "status": "ok",
        })
    except Exception as exc:
        row["status"] = "error"
        row["error"] = str(exc)
        row["runtime_sec"] = 0.0
        print(f"  [ERROR] {exc}")
        traceback.print_exc()
    return row


def run_sweep(sweep_id: str, runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run all configurations for a sweep, writing CSV incrementally."""
    csv_path = os.path.join(DATA_DIR, f"{sweep_id}_results.csv")
    results = []

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting {sweep_id}: {len(runs)} runs")
    print(f"  Output CSV: {csv_path}")

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        for i, run_cfg in enumerate(runs):
            t0 = time.time()
            print(f"  [{i+1}/{len(runs)}] {run_cfg['param_name']}={run_cfg['param_value']} seed={run_cfg['seed']} ... ", end="", flush=True)
            row = run_one(sweep_id, run_cfg)
            elapsed = time.time() - t0
            print(f"status={row['status']} AoI={row['AoI_mean']} CBR={row['CBR_mean']} PDR={row['PDR_mean']} ({elapsed:.1f}s)")

            writer.writerow(row)
            f.flush()
            results.append(row)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] {sweep_id} done. CSV saved.")
    return results


def compute_summary(sweep_id: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate results into per-param_value summary statistics."""
    from collections import defaultdict

    groups = defaultdict(list)
    for r in results:
        if r["status"] == "ok":
            groups[r["param_value"]].append(r)

    summary = {
        "sweep_id": sweep_id,
        "timestamp": datetime.now().isoformat(),
        "n_total_runs": len(results),
        "n_ok_runs": sum(1 for r in results if r["status"] == "ok"),
        "n_error_runs": sum(1 for r in results if r["status"] == "error"),
        "by_param_value": {},
    }

    for pv, rows in groups.items():
        def mean_of(key):
            vals = [float(r[key]) for r in rows if r[key] is not None]
            return round(sum(vals) / len(vals), 4) if vals else None

        def std_of(key):
            vals = [float(r[key]) for r in rows if r[key] is not None]
            if len(vals) < 2:
                return None
            m = sum(vals) / len(vals)
            var = sum((v - m) ** 2 for v in vals) / (len(vals) - 1)
            return round(var ** 0.5, 4)

        summary["by_param_value"][str(pv)] = {
            "n_seeds": len(rows),
            "AoI_mean_mean": mean_of("AoI_mean"),
            "AoI_mean_std": std_of("AoI_mean"),
            "CBR_mean_mean": mean_of("CBR_mean"),
            "CBR_mean_std": std_of("CBR_mean"),
            "PDR_mean_mean": mean_of("PDR_mean"),
            "PDR_mean_std": std_of("PDR_mean"),
            "energy_efficiency_mean": mean_of("energy_efficiency"),
            "ETSI_compliance_mean": mean_of("ETSI_compliance"),
            "runtime_sec_mean": mean_of("runtime_sec"),
        }

    return summary


def save_summary(summary: Dict[str, Any]):
    """Append/merge to sensitivity_summary.json."""
    json_path = os.path.join(DATA_DIR, "sensitivity_summary.json")

    existing = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    existing[summary["sweep_id"]] = summary

    with open(json_path, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"  Summary saved to {json_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Sensitivity sweep runner")
    parser.add_argument("--sweep", default="all",
                        help="Sweep to run: SA1, SA2, SA3, SA4, or all")
    parser.add_argument("--data-dir", default=None,
                        help="Override output data directory")
    args = parser.parse_args()

    global DATA_DIR
    if args.data_dir:
        DATA_DIR = args.data_dir
        os.makedirs(DATA_DIR, exist_ok=True)

    sweeps = define_sweeps()

    if args.sweep == "all":
        sweep_ids = ["SA1", "SA2", "SA3", "SA4"]
    else:
        sweep_ids = [args.sweep.upper()]

    for sweep_id in sweep_ids:
        if sweep_id not in sweeps:
            print(f"Unknown sweep: {sweep_id}. Available: {list(sweeps.keys())}")
            continue

        runs = sweeps[sweep_id]
        results = run_sweep(sweep_id, runs)
        summary = compute_summary(sweep_id, results)
        save_summary(summary)

        print(f"\n=== {sweep_id} Summary ===")
        print(f"  Total runs: {summary['n_total_runs']}")
        print(f"  OK:    {summary['n_ok_runs']}")
        print(f"  ERROR: {summary['n_error_runs']}")
        for pv, stats in summary["by_param_value"].items():
            print(f"  {pv}: AoI={stats['AoI_mean_mean']} CBR={stats['CBR_mean_mean']} PDR={stats['PDR_mean_mean']}")

    print("\n[sensitivity_runner.py] All requested sweeps complete.")


if __name__ == "__main__":
    main()
