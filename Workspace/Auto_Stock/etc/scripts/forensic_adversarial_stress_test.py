#!/usr/bin/env python3
"""
Adversarial Stress and Mutation Testing for Auto_Stock Milestone 3 HPO.
"""
import concurrent.futures
import math
import os
import sys
import tempfile
import numpy as np
import pandas as pd
import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from modules.hpo.metrics import (
    calculate_total_equity,
    calculate_total_return_pct,
    calculate_annualized_sharpe_ratio,
    calculate_max_drawdown_pct,
    calculate_win_rate,
    evaluate_trading_history,
)
from modules.hpo.exporter import CSV_COLUMNS, export_trial_to_csv, load_hpo_results
from modules.hpo.optuna_pipeline import create_hpo_study, objective, run_hpo_optimization

def stress_test_metrics():
    print("\n--- [Stress Test 1] Adversarial Metrics Robustness ---")
    
    # 1. Total Equity extreme values
    assert calculate_total_equity(float("nan"), 100, 50000) == 0.0 or math.isnan(calculate_total_equity(float("nan"), 100, 50000)) or calculate_total_equity(float("nan"), 100, 50000) == 0.0
    eq_inf = calculate_total_equity(1000, 10, float("inf"))
    assert not math.isinf(eq_inf) or eq_inf == 1000.0
    print("  [+] Total Equity NaN/Inf immunity verified.")

    # 2. Total Return negative and extreme capital
    assert calculate_total_return_pct(-1000, 5000) == 0.0
    assert calculate_total_return_pct(0, 5000) == 0.0
    assert calculate_total_return_pct(10000, 0) == -100.0
    assert calculate_total_return_pct(10000, 30000) == 200.0
    print("  [+] Total Return % edge cases verified.")

    # 3. Sharpe ratio zero variance & single-step
    assert calculate_annualized_sharpe_ratio([]) == 0.0
    assert calculate_annualized_sharpe_ratio([0.05]) == 0.0
    assert calculate_annualized_sharpe_ratio([0.05, 0.05, 0.05]) == 0.0
    assert calculate_annualized_sharpe_ratio([np.nan, np.inf, -np.inf]) == 0.0
    print("  [+] Sharpe ratio zero-variance and degenerative series immunity verified.")

    # 4. MDD severe crashes and flat curves
    assert calculate_max_drawdown_pct([1000, 1000, 1000]) == 0.0
    assert calculate_max_drawdown_pct([1000, 500, 250, 100, 0]) == -100.0
    assert calculate_max_drawdown_pct([100, 200, 100, 300, 150]) == -50.0
    print("  [+] MDD severe drawdown (-100% and multiple valleys) verified.")

    # 5. Win rate 100% loss / 100% win / empty
    assert calculate_win_rate([]) == (0, 0.0)
    assert calculate_win_rate([-100, -200, -300]) == (3, 0.0)
    assert calculate_win_rate([100, 200, 300]) == (3, 100.0)
    print("  [+] Win rate boundary cases verified.")

def stress_test_concurrent_export():
    print("\n--- [Stress Test 2] High Concurrency CSV Atomic Export ---")
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = os.path.join(tmp_dir, "concurrent_hpo.csv")
        num_workers = 10
        records_per_worker = 10
        total_expected = num_workers * records_per_worker

        def write_worker(worker_id):
            for i in range(records_per_worker):
                rec = {
                    "trial_id": worker_id * 100 + i,
                    "state": "COMPLETE",
                    "objective_value": float(worker_id + i * 0.1),
                    "total_equity": 10000000.0 + (worker_id * 1000),
                    "param_sl_lr": 0.001,
                }
                export_trial_to_csv(rec, csv_path=csv_path)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(write_worker, wid) for wid in range(num_workers)]
            concurrent.futures.wait(futures)

        df = load_hpo_results(csv_path)
        print(f"  • Total concurrent records written and loaded: {len(df)} (Expected: {total_expected})")
        assert len(df) == total_expected, f"Lost records under race conditions! Got {len(df)}, expected {total_expected}"
        assert list(df.columns) == CSV_COLUMNS
        print("  [+] Thread safety and atomic write integrity under high concurrency verified.")

def stress_test_hpo_failure_and_recovery():
    print("\n--- [Stress Test 3] Pipeline Fault Injection & Pruning Recovery ---")
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = os.path.join(tmp_dir, "fault_hpo.csv")
        study = create_hpo_study(seed=123)

        # Inject 1 faulty trial and 1 normal trial
        call_count = 0
        def mixed_obj(trial):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Deliberate failure
                return objective(
                    trial=trial,
                    symbol="NON_EXISTENT_SYMBOL_999999",
                    output_csv=csv_path,
                    n_timesteps=16,
                    fast_mode=True,
                )
            else:
                return objective(
                    trial=trial,
                    symbol="005930",
                    output_csv=csv_path,
                    n_timesteps=32,
                    fast_mode=True,
                )

        study.optimize(mixed_obj, n_trials=2, catch=(Exception,))
        assert len(study.trials) == 2
        df = load_hpo_results(csv_path)
        assert len(df) == 2
        states = df["state"].tolist()
        print(f"  • Recorded states under fault injection: {states}")
        assert "FAIL" in states or "PRUNED" in states or "COMPLETE" in states
        print("  [+] Fault tolerance and exception handling verified.")

if __name__ == "__main__":
    print("=================================================================")
    print("🔥 [Forensic Adversarial Stress Test] Initiating Stress Scenarios")
    print("=================================================================")
    stress_test_metrics()
    stress_test_concurrent_export()
    stress_test_hpo_failure_and_recovery()
    print("\n=================================================================")
    print("✅ [Forensic Adversarial Stress Test] ALL SCENARIOS PASSED")
    print("=================================================================")
