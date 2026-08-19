"""
Master Test Runner for Challenger (challenger_m3_2)
===================================================
Executes all 4 Challenge Test Suites:
1. Suite 1: Idempotency & Repeated Overwrite Safety (5 runs)
2. Suite 2: Clean Slate & Isolated Output Directory
3. Suite 3: LaTeX Syntax, Escaping & Structure Analysis
4. Suite 4: Visual Aesthetics, Overlap & Two-Phase Verification
"""

import os
import sys
import time

REPO_ROOT = "/home/imnyj/Workspace/paper4"
TESTS_DIR = os.path.join(REPO_ROOT, "etc", "tests")
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

from test_idempotency import run_idempotency_stress
from test_clean_slate import run_clean_slate_test
from test_latex_syntax import run_latex_stress_test
from test_visual_aesthetics import run_visual_aesthetics_test

def main():
    t_start = time.time()
    print("=" * 80)
    print("  PAPER4 VISUALIZATION PIPELINE EMPIRICAL CHALLENGE HARNESS (CHALLENGER 2)")
    print("=" * 80)
    
    results = {}
    
    # 1. Idempotency Test
    print("\n>>> EXECUTING SUITE 1: IDEMPOTENCY & OVERWRITING SAFETY (5 RUNS) <<<")
    res1, data1 = run_idempotency_stress(5)
    results["Suite 1: Idempotency & Overwriting Safety"] = res1
    
    # 2. Clean Slate Test
    print("\n>>> EXECUTING SUITE 2: CLEAN SLATE & ISOLATED DIRECTORY BUILD <<<")
    res2 = run_clean_slate_test()
    results["Suite 2: Clean Slate & Isolated Directory Build"] = res2
    
    # 3. LaTeX Syntax Test
    print("\n>>> EXECUTING SUITE 3: LATEX SYNTAX, ESCAPING & STRUCTURE <<<")
    res3 = run_latex_stress_test()
    results["Suite 3: LaTeX Syntax, Escaping & Structure"] = res3
    
    # 4. Visual Aesthetics Test
    print("\n>>> EXECUTING SUITE 4: VISUAL AESTHETICS & TWO-PHASE LAYOUT <<<")
    res4 = run_visual_aesthetics_test()
    results["Suite 4: Visual Aesthetics & Two-Phase Layout"] = res4
    
    t_total = time.time() - t_start
    print("\n" + "=" * 80)
    print("                    CHALLENGE HARNESS FINAL SUMMARY")
    print("=" * 80)
    all_passed = True
    for suite_name, status in results.items():
        st_str = "[PASS]" if status else "[FAIL]"
        if not status:
            all_passed = False
        print(f"  {st_str} | {suite_name}")
    print("=" * 80)
    print(f"Total Challenge Execution Time: {t_total:.2f} seconds")
    if all_passed:
        print("OVERALL VERDICT: ALL TEST SUITES PASSED -> RECOMMEND APPROVE")
    else:
        print("OVERALL VERDICT: ONE OR MORE SUITES FAILED -> RECOMMEND REJECT")
    print("=" * 80 + "\n")
    
    if not all_passed:
        sys.exit(1)

if __name__ == "__main__":
    main()
