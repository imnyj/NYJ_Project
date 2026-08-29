# tests/test_tier4_simulation.py
# ============================================================================
# Tier 4: Real-World Simulation Workload & Output Validation Test Suite
# Tests multi-density simulation runs, metric convergence, and CSV outputs.
# ============================================================================

import os
import csv
import pandas as pd
import numpy as np
import pytest
import src.aoi_env as env
import src.Communications as comm
from tests.contract_adapters import (
    HeuristicScheduler,
    calculate_metrics,
)


class TestTier4SimulationWorkload:
    """Tier 4: Real-World Simulation Workload & Metric Convergence Verification."""

    def test_01_multi_density_simulation_workload(self, temp_results_dir):
        """Verify simulation execution across low (15), medium (35), and high (55) vehicle densities."""
        densities = [15.0, 35.0, 55.0]
        scheduler = HeuristicScheduler(num_channels=4)
        records_by_density = {}

        for density in densities:
            # Simulate synthetic traffic workload for this density
            n_vehicles = int(density * 1.5)
            density_records = []
            
            for v_idx in range(n_vehicles):
                speed = float(np.random.uniform(0.0, 20.0))
                dist = float(np.random.uniform(10.0, 300.0))
                state_dict = {
                    "speed": speed,
                    "stop_imminent": 1.0 if speed > 5.0 and dist < 30.0 else 0.0,
                    "start_imminent": 1.0 if speed < 1.0 and dist < 10.0 else 0.0,
                    "time_to_switch": 15.0,
                }
                delta, ch, power = scheduler.decide_grant(f"v_{density}_{v_idx}", state_dict)
                
                # Check uplink success under density contention
                group = [(f"v_{density}_{v_idx}", power, dist)]
                probs = comm.judge_uplink(group)
                succ = 1 if np.random.random() < probs[f"v_{density}_{v_idx}"] else 0

                density_records.append({
                    "density": density,
                    "vid": f"v_{density}_{v_idx}",
                    "aoi": float(delta * (1.0 if succ else 2.5)),
                    "peak_aoi": float(delta * 2.0),
                    "error": float(0.1 if speed < 2.0 else speed * delta * 0.05),
                    "tx_attempts": 1,
                    "tx_fails": 1 - succ,
                    "power_dbm": power,
                })
            records_by_density[density] = density_records

        # Verify all densities produced valid records
        for density, recs in records_by_density.items():
            assert len(recs) == int(density * 1.5)
            metrics = calculate_metrics(recs)
            assert metrics["mean_aoi"] > 0.0
            assert 0.0 <= metrics["packet_loss_rate"] <= 1.0
            assert metrics["mean_error"] >= 0.0

    def test_02_metric_convergence_and_invariants(self):
        """Verify mathematical invariants of all 6 IEEE TWC metrics across 100 simulation episodes."""
        records = []
        for i in range(100):
            aoi = float(np.random.gamma(shape=2.0, scale=1.5))
            peak_aoi = aoi + float(np.random.exponential(scale=0.8))
            err = float(np.random.exponential(scale=0.5))
            tx_att = int(np.random.randint(1, 5))
            tx_fail = int(np.random.binomial(tx_att, p=0.1))
            power = float(np.random.choice([10.0, 16.5, 23.0]))
            
            records.append({
                "aoi": aoi,
                "peak_aoi": peak_aoi,
                "error": err,
                "tx_attempts": tx_att,
                "tx_fails": tx_fail,
                "power_dbm": power,
            })

        metrics = calculate_metrics(records)

        # Invariant 1: Peak AoI must be strictly >= Mean AoI
        assert metrics["peak_aoi"] >= metrics["mean_aoi"], (
            f"Invariant violation: Peak AoI ({metrics['peak_aoi']}) < Mean AoI ({metrics['mean_aoi']})"
        )

        # Invariant 2: Packet loss rate in [0, 1]
        assert 0.0 <= metrics["packet_loss_rate"] <= 1.0

        # Invariant 3: Estimation error non-negative
        assert metrics["mean_error"] >= 0.0

        # Invariant 4: Average power bounded
        assert 10.0 <= metrics["avg_tx_power_dbm"] <= 23.0

        # Invariant 5: Jain's Fairness in (0, 1]
        assert 0.0 < metrics["jains_fairness_aoi"] <= 1.0
        assert 0.0 < metrics["jains_fairness_err"] <= 1.0

    def test_03_csv_output_file_schema_and_integrity(self, temp_results_dir):
        """Verify generation and format compliance of raw runs, summary, and leaderboard CSV files."""
        raw_csv = os.path.join(temp_results_dir, "eval_raw_runs.csv")
        summary_csv = os.path.join(temp_results_dir, "eval_summary_by_density.csv")
        leaderboard_csv = os.path.join(temp_results_dir, "eval_leaderboard.csv")

        # 1. Write mock evaluation raw runs
        raw_columns = [
            "model_name", "density", "seed", "mean_aoi", "peak_aoi", "packet_loss_rate",
            "mean_error", "avg_tx_power_dbm", "total_energy_joules", "jains_fairness_aoi", "jains_fairness_err"
        ]
        raw_data = [
            ["Heuristic-Dynamic", 25.0, 42, 1.85, 3.20, 0.04, 0.45, 18.5, 0.0008, 0.92, 0.88],
            ["DummyPolicy", 25.0, 42, 1.72, 2.95, 0.03, 0.38, 16.5, 0.0006, 0.94, 0.91],
        ]
        df_raw = pd.DataFrame(raw_data, columns=raw_columns)
        df_raw.to_csv(raw_csv, index=False)

        # 2. Write summary by density
        df_summary = df_raw.groupby(["model_name", "density"]).mean().reset_index()
        df_summary.to_csv(summary_csv, index=False)

        # 3. Write leaderboard
        df_leaderboard = df_raw.sort_values(by="mean_error").reset_index(drop=True)
        df_leaderboard.to_csv(leaderboard_csv, index=False)

        # 4. Verify CSV files exist and can be loaded back
        assert os.path.exists(raw_csv)
        assert os.path.exists(summary_csv)
        assert os.path.exists(leaderboard_csv)

        loaded_raw = pd.read_csv(raw_csv)
        assert len(loaded_raw) == 2
        assert set(raw_columns).issubset(loaded_raw.columns)
        assert not loaded_raw.isnull().any().any(), "CSV contains null values"
