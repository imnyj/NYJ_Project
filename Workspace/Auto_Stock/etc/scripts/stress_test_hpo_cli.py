#!/usr/bin/env python3
"""
etc/scripts/stress_test_hpo_cli.py
==================================
적대적 검증: Optuna HPO CLI & Pipeline 극한 파라미터 및 반복 스트레스 테스트
"""

import os
import sys
import subprocess
import tempfile
import time
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from modules.hpo.exporter import load_hpo_results, CSV_COLUMNS

def test_cli_extreme_arguments():
    print("=== [1] CLI 극한 파라미터 스트레스 테스트 ===")
    cli_script = os.path.abspath("scripts/run_hpo.py")
    
    test_cases = [
        # 1. timesteps=1 (초극단 최소 스텝)
        {"name": "Minimal Timesteps (1)", "args": ["--n-trials", "2", "--timesteps", "1", "--fast-mode", "--quiet"]},
        # 2. n_trials=5 (연속 5-trial)
        {"name": "5-Trials HPO", "args": ["--n-trials", "5", "--timesteps", "32", "--fast-mode", "--quiet"]},
        # 3. seed=99999 (큰 정수 시드)
        {"name": "Large Seed (99999)", "args": ["--n-trials", "2", "--seed", "99999", "--timesteps", "32", "--fast-mode", "--quiet"]},
    ]

    for tc in test_cases:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_csv = os.path.join(tmp_dir, "test_out.csv")
            cmd = [sys.executable, cli_script, "--output", out_csv] + tc["args"]
            t0 = time.time()
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            elapsed = time.time() - t0

            if proc.returncode != 0:
                print(f"  [FAIL] {tc['name']} exited with code {proc.returncode}")
                print(f"  STDERR:\n{proc.stderr}")
                assert False, f"CLI Failed for {tc['name']}"
            
            df = load_hpo_results(out_csv)
            n_expected = int(tc["args"][1])
            assert len(df) == n_expected, f"Expected {n_expected} rows, got {len(df)}"
            assert list(df.columns) == CSV_COLUMNS
            print(f"  [PASS] {tc['name']}: {len(df)} trials finished in {elapsed:.2f}s")

if __name__ == "__main__":
    test_cli_extreme_arguments()
    print("\n>>> CLI STRESS TESTS PASSED! <<<")
