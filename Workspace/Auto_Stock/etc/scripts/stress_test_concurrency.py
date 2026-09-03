#!/usr/bin/env python3
"""
etc/scripts/stress_test_concurrency.py
======================================
적대적 검증: 멀티스레드 및 멀티프로세스 동시 다발적 CSV 기록 무결성 스트레스 테스트
"""

import os
import sys
import time
import tempfile
import threading
import multiprocessing
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from modules.hpo.exporter import export_trial_to_csv, load_hpo_results, CSV_COLUMNS

def worker_write_trial(args):
    proc_id, trial_idx, csv_path = args
    global_trial_id = proc_id * 1000 + trial_idx
    record = {
        "trial_id": global_trial_id,
        "state": "COMPLETE",
        "objective_value": round(float(global_trial_id) * 0.1, 4),
        "total_equity": 10_000_000.0 + global_trial_id,
        "total_return_pct": round(float(trial_idx) * 1.5, 2),
        "sharpe_ratio": 1.25,
        "max_drawdown_pct": -5.0,
        "total_trades": 10,
        "win_rate": 60.0,
        "param_sl_lr": 0.001,
        "param_sl_hidden_dim": 64,
        "param_sl_batch_size": 32,
        "param_rl_lr": 0.0003,
        "param_rl_gamma": 0.99,
        "param_rl_clip_range": 0.2,
        "param_rl_ent_coef": 0.01,
        "param_rl_hidden_dim": 128,
        "duration_seconds": 0.25,
    }
    export_trial_to_csv(record, csv_path=csv_path)
    return global_trial_id

def test_multithread_concurrency():
    print("=== [1] Multi-Thread Concurrency Stress Test ===")
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = os.path.join(tmp_dir, "thread_stress.csv")
        n_threads = 16
        n_items_per_thread = 10
        total_expected = n_threads * n_items_per_thread

        tasks = []
        for t in range(n_threads):
            for i in range(n_items_per_thread):
                tasks.append((t, i, csv_path))

        t0 = time.time()
        with ThreadPoolExecutor(max_workers=n_threads) as executor:
            written_ids = list(executor.map(worker_write_trial, tasks))
        elapsed = time.time() - t0

        df = load_hpo_results(csv_path)
        print(f"  [Result] Multi-Thread: Expected {total_expected} rows, Got {len(df)} rows in {elapsed:.3f}s")
        assert len(df) == total_expected, f"Multi-thread row count mismatch: expected {total_expected}, got {len(df)}"
        assert set(df["trial_id"].tolist()) == set(written_ids), "Missing trial IDs in multi-thread test!"
        print("  >>> Multi-Thread Test PASSED! <<<")

def test_multiprocess_concurrency():
    print("\n=== [2] Multi-Process Concurrency Stress Test ===")
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = os.path.join(tmp_dir, "process_stress.csv")
        n_processes = 8
        n_items_per_proc = 10
        total_expected = n_processes * n_items_per_proc

        tasks = []
        for p in range(n_processes):
            for i in range(n_items_per_proc):
                tasks.append((p, i, csv_path))

        t0 = time.time()
        # 멀티프로세스 환경에서 동시 실행
        with ProcessPoolExecutor(max_workers=n_processes) as executor:
            written_ids = list(executor.map(worker_write_trial, tasks))
        elapsed = time.time() - t0

        df = load_hpo_results(csv_path)
        print(f"  [Result] Multi-Process: Expected {total_expected} rows, Got {len(df)} rows in {elapsed:.3f}s")
        
        missing_ids = set(written_ids) - set(df["trial_id"].tolist())
        if missing_ids:
            print(f"  [CRITICAL VULNERABILITY FOUND] Lost Updates in Multi-Process! {len(missing_ids)} trials were overwritten and lost!")
            print(f"  Sample Missing Trial IDs: {list(missing_ids)[:10]}")
            return False, len(df), total_expected, len(missing_ids)
        else:
            print("  >>> Multi-Process Test PASSED! <<<")
            return True, len(df), total_expected, 0

if __name__ == "__main__":
    test_multithread_concurrency()
    mp_passed, got_rows, expected_rows, lost_count = test_multiprocess_concurrency()
    if not mp_passed:
        print(f"\n[SUMMARY] Multi-Thread: OK | Multi-Process: VULNERABILITY CONFIRMED (Lost {lost_count}/{expected_rows} rows)")
        sys.exit(2)
    else:
        print("\n[SUMMARY] Both Multi-Thread and Multi-Process tests passed.")
