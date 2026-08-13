"""
stress_test_m1.py - Milestone 1 Calculation Engine & Parameters Stress Test Harness
Location: /home/imnyj/Workspace/House/etc/scripts/stress_test_m1.py

Empirically tests:
1. National Housing Bond rate threshold at 2.6억 KRW public official price (2.1% vs 2.3%).
2. Didimdol price limit boundary at 6.0억 KRW (eligible vs ineligible).
3. Loan stamp duty threshold at 1.0억 KRW (3.5만 vs 7.5만 KRW).
4. Zero cash reserve, full cash reserve (zero loan), high interest rates, large property values.
5. Numerical precision, integer rounding, and schema integrity.
"""

import sys
import json
import math
import traceback
from pathlib import Path
from typing import List, Dict, Any

# Ensure project root & script path in sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(script_dir))

from calc_engine import (
    load_financial_params,
    calculate_r1_costs,
    calculate_r2_loans,
    calculate_cpm_monthly_payment,
    run_all_scenarios
)

class TestResult:
    def __init__(self, name: str, passed: bool, detail: str):
        self.name = name
        self.passed = passed
        self.detail = detail

    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}: {self.detail}"


def run_stress_test_suite() -> List[TestResult]:
    results = []

    def add_res(name: str, passed: bool, detail: str):
        results.append(TestResult(name, passed, detail))

    params = load_financial_params()

    # ==========================================
    # Category 1: National Housing Bond Threshold (2.6억 Public Price)
    # ==========================================
    # Public Price = Purchase Price * 0.7
    # 2.6억 Public Price corresponds to Purchase Price = 260,000,000 / 0.7 = 371,428,571.43 KRW
    try:
        # Case 1.1: 3.5억 KRW (Public Price 2.45억 < 2.6억 -> 2.1%)
        r1_35 = calculate_r1_costs(350000000, params=params)
        c1_1 = (r1_35['public_official_price'] == 245000000 and 
                r1_35['bond_rate'] == 0.021 and 
                r1_35['bond_buy_amount'] == 5145000 and 
                r1_35['bond_discount_fee'] == 514500)
        add_res("Bond Rate 3.5억 KRW (Public 2.45억)", c1_1, 
                f"Rate={r1_35['bond_rate']}, Discount={r1_35['bond_discount_fee']:,} KRW")

        # Case 1.2: Just below threshold (Public Price 259,999,950 -> 2.1%)
        price_below = 371428500  # 371428500 * 0.7 = 259,999,950
        r1_below = calculate_r1_costs(price_below, params=params)
        c1_2 = (r1_below['public_official_price'] < 260000000 and r1_below['bond_rate'] == 0.021)
        add_res("Bond Rate Below 2.6억 Public Price", c1_2,
                f"Public Price={r1_below['public_official_price']:,}, Rate={r1_below['bond_rate']}")

        # Case 1.3: At/above threshold (Price 371,428,572 -> Public Price 260,000,000 -> 2.3%)
        price_at = 371428572  # 371428572 * 0.7 = 260,000,000.4 -> 260,000,000
        r1_at = calculate_r1_costs(price_at, params=params)
        c1_3 = (r1_at['public_official_price'] >= 260000000 and r1_at['bond_rate'] == 0.023)
        add_res("Bond Rate At/Above 2.6억 Public Price", c1_3,
                f"Public Price={r1_at['public_official_price']:,}, Rate={r1_at['bond_rate']}")

        # Case 1.4: 3.75억 KRW (Public Price 2.625억 > 2.6억 -> 2.3%)
        r1_375 = calculate_r1_costs(375000000, params=params)
        c1_4 = (r1_375['public_official_price'] == 262500000 and 
                r1_375['bond_rate'] == 0.023 and 
                r1_375['bond_buy_amount'] == 6037500 and 
                r1_375['bond_discount_fee'] == 603750)
        add_res("Bond Rate 3.75억 KRW (Public 2.625억)", c1_4,
                f"Rate={r1_375['bond_rate']}, Discount={r1_375['bond_discount_fee']:,} KRW")

        # Case 1.5: 4.0억 KRW (Public Price 2.8억 > 2.6억 -> 2.3%)
        r1_40 = calculate_r1_costs(400000000, params=params)
        c1_5 = (r1_40['public_official_price'] == 280000000 and 
                r1_40['bond_rate'] == 0.023 and 
                r1_40['bond_buy_amount'] == 6440000 and 
                r1_40['bond_discount_fee'] == 644000)
        add_res("Bond Rate 4.0억 KRW (Public 2.8억)", c1_5,
                f"Rate={r1_40['bond_rate']}, Discount={r1_40['bond_discount_fee']:,} KRW")

    except Exception as e:
        add_res("Category 1 Bond Threshold", False, f"Crash: {str(e)}")

    # ==========================================
    # Category 2: Didimdol Price Limit Boundary (6.0억 KRW)
    # ==========================================
    try:
        # Case 2.1: Price = 5.99999999억 (Eligible)
        r2_below_600 = calculate_r2_loans(599999999, cash_reserve=230000000, params=params)
        did_below = r2_below_600['products']['didimdol']
        c2_1 = did_below['eligible'] is True
        add_res("Didimdol Price < 6.0억 Eligibility", c2_1, f"Eligible={did_below['eligible']}")

        # Case 2.2: Price = 6.0억 (Eligible)
        r2_at_600 = calculate_r2_loans(600000000, cash_reserve=230000000, params=params)
        did_at = r2_at_600['products']['didimdol']
        c2_2 = did_at['eligible'] is True
        add_res("Didimdol Price == 6.0억 Boundary Eligibility", c2_2, f"Eligible={did_at['eligible']}")

        # Case 2.3: Price = 6.00000001억 (Ineligible)
        r2_above_600 = calculate_r2_loans(600000001, cash_reserve=230000000, params=params)
        did_above = r2_above_600['products']['didimdol']
        c2_3 = (did_above['eligible'] is False and "exceeds Didimdol cap" in did_above['ineligible_reason'])
        add_res("Didimdol Price > 6.0억 Ineligibility", c2_3, f"Eligible={did_above['eligible']}, Reason={did_above['ineligible_reason']}")

    except Exception as e:
        add_res("Category 2 Didimdol Boundary", False, f"Crash: {str(e)}")

    # ==========================================
    # Category 3: Loan Stamp Duty Boundary (1.0억 KRW Loan)
    # ==========================================
    try:
        # Case 3.1: Required loan = 99,999,999 (Stamp duty = 35,000 KRW)
        r2_loan_99m = calculate_r2_loans(329999999, cash_reserve=230000000, params=params) # Loan = 99,999,999
        sd_99m = r2_loan_99m['secondary_fees']['loan_stamp_duty_borrower']
        c3_1 = (sd_99m == 35000)
        add_res("Loan Stamp Duty <= 1.0억 KRW (99.99M)", c3_1, f"Loan={r2_loan_99m['pure_required_loan']:,}, Stamp Duty={sd_99m:,} KRW")

        # Case 3.2: Required loan = 100,000,000 (Stamp duty = 35,000 KRW)
        r2_loan_100m = calculate_r2_loans(330000000, cash_reserve=230000000, params=params) # Loan = 100,000,000
        sd_100m = r2_loan_100m['secondary_fees']['loan_stamp_duty_borrower']
        c3_2 = (sd_100m == 35000)
        add_res("Loan Stamp Duty == 1.0억 KRW (100M)", c3_2, f"Loan={r2_loan_100m['pure_required_loan']:,}, Stamp Duty={sd_100m:,} KRW")

        # Case 3.3: Required loan = 100,000,001 (Stamp duty = 75,000 KRW)
        r2_loan_100m1 = calculate_r2_loans(330000001, cash_reserve=230000000, params=params) # Loan = 100,000,001
        sd_100m1 = r2_loan_100m1['secondary_fees']['loan_stamp_duty_borrower']
        c3_3 = (sd_100m1 == 75000)
        add_res("Loan Stamp Duty > 1.0억 KRW (100M+1)", c3_3, f"Loan={r2_loan_100m1['pure_required_loan']:,}, Stamp Duty={sd_100m1:,} KRW")

    except Exception as e:
        add_res("Category 3 Loan Stamp Duty Boundary", False, f"Crash: {str(e)}")

    # ==========================================
    # Category 4: Cash Reserve Edge Cases (Zero Cash & Full Cash)
    # ==========================================
    try:
        # Case 4.1: Cash Reserve = 0 (Loan = Purchase Price)
        r2_zero_cash = calculate_r2_loans(350000000, cash_reserve=0, params=params)
        c4_1 = (r2_zero_cash['pure_required_loan'] == 350000000 and r2_zero_cash['ltv_percent'] == 100.0)
        add_res("Zero Cash Reserve Handling", c4_1, f"Loan={r2_zero_cash['pure_required_loan']:,}, LTV={r2_zero_cash['ltv_percent']}%")

        # Case 4.2: Cash Reserve >= Purchase Price (Loan = 0)
        r2_full_cash = calculate_r2_loans(350000000, cash_reserve=400000000, params=params)
        c4_2 = (r2_full_cash['pure_required_loan'] == 0 and r2_full_cash['ltv_percent'] == 0.0)
        add_res("Full Cash Reserve (Zero Loan)", c4_2, f"Loan={r2_full_cash['pure_required_loan']:,}, LTV={r2_full_cash['ltv_percent']}%")

    except Exception as e:
        add_res("Category 4 Cash Reserve Edge Cases", False, f"Crash: {str(e)}")

    # ==========================================
    # Category 5: High Interest Rates & Large Property Values
    # ==========================================
    try:
        # Case 5.1: High Interest Rate (20%, 50%)
        pmt_20pct = calculate_cpm_monthly_payment(200000000, 0.20, term_years=30)
        pmt_50pct = calculate_cpm_monthly_payment(200000000, 0.50, term_years=30)
        c5_1 = (pmt_20pct > 0 and pmt_50pct > 0 and pmt_50pct > pmt_20pct)
        add_res("High Interest Rate Calculation (20%, 50%)", c5_1, f"20% PMT={pmt_20pct:,}, 50% PMT={pmt_50pct:,}")

        # Case 5.2: Zero Interest Rate (0%)
        pmt_0pct = calculate_cpm_monthly_payment(360000000, 0.0, term_years=30)
        c5_2 = (pmt_0pct == 1000000) # 3.6억 / 360개월 = 100만원
        add_res("Zero Interest Rate Calculation (0%)", c5_2, f"0% PMT={pmt_0pct:,} (Expected 1,000,000)")

        # Case 5.3: Large Property Value (100억 KRW)
        r1_10b = calculate_r1_costs(10000000000, params=params)
        r2_10b = calculate_r2_loans(10000000000, cash_reserve=230000000, params=params)
        c5_3 = (r1_10b['total_r1_cost'] > 0 and r2_10b['pure_required_loan'] == 9770000000)
        add_res("Large Property Value (100억 KRW)", c5_3, f"R1 Total={r1_10b['total_r1_cost']:,}, Required Loan={r2_10b['pure_required_loan']:,}")

        # Case 5.4: Exception handling for invalid inputs (negative price)
        try:
            calculate_r1_costs(-50000, params=params)
            c5_4 = False
            detail_5_4 = "Failed to raise ValueError on negative price"
        except ValueError:
            c5_4 = True
            detail_5_4 = "Successfully caught ValueError on negative price"
        add_res("Negative Input Exception Handling", c5_4, detail_5_4)

    except Exception as e:
        add_res("Category 5 Extreme Values", False, f"Crash: {str(e)}")

    # ==========================================
    # Category 6: Numerical Stability, Integer Types & Schema Validation
    # ==========================================
    try:
        r1_test = calculate_r1_costs(350000000, params=params)
        int_fields = [
            'gross_acquisition_tax', 'acq_tax_exemption', 'net_acquisition_tax',
            'local_education_tax', 'acquisition_tax_total', 'brokerage_fee_base',
            'brokerage_vat', 'brokerage_fee', 'legal_fee', 'stamp_duty',
            'public_official_price', 'bond_buy_amount', 'bond_discount_fee',
            'moving_fee', 'repair_cleaning_fee', 'total_r1_cost', 'total_initial_capital_needed'
        ]
        all_int = all(isinstance(r1_test[f], int) for f in int_fields)
        add_res("Integer Type Enforcement in R1 Output", all_int, f"All {len(int_fields)} fields are pure int: {all_int}")

        # Check full scenario execution runner
        all_scen = run_all_scenarios()
        c6_2 = len(all_scen['scenarios']) == 3
        add_res("Full 3-Scenario Runner Execution", c6_2, f"Executed {len(all_scen['scenarios'])} scenarios successfully")

    except Exception as e:
        add_res("Category 6 Precision & Schema", False, f"Crash: {str(e)}")

    return results


def main():
    print("=" * 70)
    print("      MILESTONE 1 FINANCIAL DATA ENGINE STRESS TEST HARNESS")
    print("=" * 70)

    results = run_stress_test_suite()

    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.passed)
    failed_tests = total_tests - passed_tests

    for idx, r in enumerate(results, 1):
        print(f"{idx:02d}. {r}")

    print("-" * 70)
    print(f"Summary: Total = {total_tests} | Passed = {passed_tests} | Failed = {failed_tests}")
    print("-" * 70)

    if failed_tests == 0:
        print("VERDICT: ALL TESTS PASSED (100%) - NUMERICAL ENGINE VERIFIED & STABLE.")
        sys.exit(0)
    else:
        print("VERDICT: FAILURES DETECTED IN STRESS HARNESS.")
        sys.exit(1)


if __name__ == "__main__":
    main()
