"""
Empirical Test Falsification (Mutation Testing) Script for challenger_e2e_1 - Updated
"""

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REF_ENGINE_PATH = ROOT / "etc" / "tests" / "helpers" / "reference_engine.py"
PYTEST_BIN = "/home/imnyj/venv/bin/pytest"
TEST_DIR = ROOT / "etc" / "tests"

def run_pytest():
    res = subprocess.run([PYTEST_BIN, str(TEST_DIR), "-q"], capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

def run_falsification_suite():
    original_code = REF_ENGINE_PATH.read_text(encoding="utf-8")
    
    print("=== BASELINE TEST RUN ===")
    code, stdout, stderr = run_pytest()
    print(f"Baseline return code: {code}")
    assert code == 0, f"Baseline must pass! Stderr: {stderr}"
    
    mutations = [
        {
            "name": "Mutation 1: Acquisition Tax Rate 1.1% -> 1.2%",
            "target": "base_tax = price * 0.011",
            "replacement": "base_tax = price * 0.012",
            "expected_fail_substr": "test_r1_acquisition_tax"
        },
        {
            "name": "Mutation 2: Brokerage Fee 0.44% -> 0.40% (Missing VAT)",
            "target": "fee = price * 0.0044",
            "replacement": "fee = price * 0.0040",
            "expected_fail_substr": "test_r1_brokerage_fee"
        },
        {
            "name": "Mutation 3: Loan Principal +1M KRW artificial error",
            "target": "return int(max(0, price - cash))",
            "replacement": "return int(max(0, price - cash)) + 1000000",
            "expected_fail_substr": "test_r2_loan_principal_calculation"
        },
        {
            "name": "Mutation 4: PMT formula +5000 KRW artificial error",
            "target": "return int(round(pmt))",
            "replacement": "return int(round(pmt)) + 5000",
            "expected_fail_substr": "test_r2_monthly_payment_amortization"
        },
        {
            "name": "Mutation 5: Completely disable bonus prepayment deduction",
            "target": "loan_balance -= bonus_paid",
            "replacement": "# loan_balance -= bonus_paid",
            "expected_fail_substr": "test_tier4_sim_01_350m_standard"
        },
        {
            "name": "Mutation 6: Fixed Costs Sum 4.15M -> 4.0M",
            "target": "return 500000 + 150000 + 1500000 + 2000000",
            "replacement": "return 4000000",
            "expected_fail_substr": "test_r1_fixed_one_time_costs_sum"
        }
    ]

    results = []

    try:
        for idx, mut in enumerate(mutations, 1):
            print(f"\n--- Running {mut['name']} ---")
            assert mut['target'] in original_code, f"Target string not found in original code: {mut['target']}"
            
            mutated_code = original_code.replace(mut['target'], mut['replacement'], 1)
            REF_ENGINE_PATH.write_text(mutated_code, encoding="utf-8")
            
            retcode, stdout, stderr = run_pytest()
            falsified = (retcode != 0) and (mut['expected_fail_substr'] in stdout or mut['expected_fail_substr'] in stderr)
            
            print(f"Exit code: {retcode} (Expected non-zero)")
            print(f"Falsification Success: {falsified}")
            
            failed_lines = [line for line in stdout.splitlines() if "FAILED" in line]
            print(f"Failed tests count: {len(failed_lines)}")
            for fl in failed_lines[:3]:
                print(f"  - {fl}")

            results.append({
                "mutation": mut['name'],
                "exit_code": retcode,
                "falsified": falsified,
                "failed_count": len(failed_lines),
                "sample_failures": failed_lines[:3]
            })

    finally:
        # ALWAYS RESTORE ORIGINAL CODE
        REF_ENGINE_PATH.write_text(original_code, encoding="utf-8")
        print("\n=== RESTORED ORIGINAL REFERENCE_ENGINE ===")
        code, stdout, stderr = run_pytest()
        print(f"Post-restoration return code: {code} (Must be 0)")
        assert code == 0, "Failed to restore reference engine clean state!"

    return results

if __name__ == "__main__":
    res = run_falsification_suite()
    print("\n================ FALSIFICATION SUMMARY ================")
    all_passed = True
    for r in res:
        status = "PASSED" if r["falsified"] else "FAILED"
        if not r["falsified"]:
            all_passed = False
        print(f"[{status}] {r['mutation']}: exit_code={r['exit_code']}, failed_tests={r['failed_count']}")
    
    if all_passed:
        print(">>> ALL FALSIFICATION TESTS PASSED! Test assertions are empirically verified to detect bugs.")
    else:
        print(">>> SOME FALSIFICATION TESTS FAILED! Assertion sensitivity check failed.")
