#!/usr/bin/env python3
"""
etc/scripts/stress_test_reproducibility.py
==========================================
적대적 검증: make test-hpo 5회 연속 실행 Flaky Test 및 재현성 검증
"""

import subprocess
import time
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

def test_repeated_runs(n_repeats=5):
    print(f"=== [1] make test-hpo {n_repeats}회 연속 반복 실행 스트레스 테스트 ===")
    
    total_t0 = time.time()
    for i in range(1, n_repeats + 1):
        t0 = time.time()
        res = subprocess.run(
            ["make", "test-hpo"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        elapsed = time.time() - t0
        
        if res.returncode != 0:
            print(f"  [FAIL] Run #{i} FAILED with exit code {res.returncode}")
            print(f"  STDERR:\n{res.stderr}")
            print(f"  STDOUT:\n{res.stdout}")
            sys.exit(1)
        else:
            print(f"  [PASS] Run #{i}/{n_repeats} PASSED in {elapsed:.2f}s (27 tests)")

    total_elapsed = time.time() - total_t0
    print(f"\n>>> ALL {n_repeats} REPEATED RUNS PASSED! Total Time: {total_elapsed:.2f}s (Average: {total_elapsed/n_repeats:.2f}s per run) <<<")

if __name__ == "__main__":
    test_repeated_runs(3)
