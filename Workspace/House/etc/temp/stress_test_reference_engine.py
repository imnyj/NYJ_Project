"""
Empirical Adversarial Stress Test Harness for reference_engine.py
"""

import sys
import traceback
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root / "etc" / "tests"))

from helpers.reference_engine import (
    calculate_acquisition_tax,
    calculate_brokerage_fee,
    calculate_bond_discount,
    calculate_fixed_one_time_costs,
    calculate_total_one_time_costs,
    calculate_loan_principal,
    calculate_monthly_payment,
    calculate_living_budget,
    simulate_timeline
)

def run_stress_tests():
    print("=== STARTING ADVERSARIAL STRESS TESTS ON REFERENCE_ENGINE ===")
    passed = 0
    failed = 0
    findings = []

    def check(name, expr, detail=""):
        nonlocal passed, failed
        if expr:
            passed += 1
            print(f"[PASS] {name}")
        else:
            failed += 1
            print(f"[FAIL] {name} - {detail}")
            findings.append((name, detail))

    # 1. Price Edge Cases
    check("Acquisition tax price=0", calculate_acquisition_tax(0) == 0)
    check("Acquisition tax price=-50000", calculate_acquisition_tax(-50000) == 0)
    check("Brokerage fee price=0", calculate_brokerage_fee(0) == 0)
    check("Brokerage fee price=-1000", calculate_brokerage_fee(-1000) == 0)
    
    # 2. Cash Edge Cases (0 Cash, Full Cash, Cash > Price)
    check("Loan principal 0 cash", calculate_loan_principal(350000000, 0) == 350000000)
    check("Loan principal full cash", calculate_loan_principal(350000000, 350000000) == 0)
    check("Loan principal excess cash", calculate_loan_principal(350000000, 400000000) == 0)
    
    res_full_cash = simulate_timeline(350000000, cash=350000000)
    check("Simulate full cash status", res_full_cash["status"] == "NO_LOAN_NEEDED")
    check("Simulate full cash payoff month", res_full_cash["payoff_month"] == 0)

    # 3. Interest Rate Edge Cases (0% interest, 10% interest, negative rate)
    pmt_zero_rate = calculate_monthly_payment(120000000, 0.0, 30)
    check("Monthly payment 0% rate", pmt_zero_rate == 333333, f"got {pmt_zero_rate}")

    res_zero_rate = simulate_timeline(350000000, annual_rate=0.0, term_years=30, bonus_schedule={})
    check("Simulate 0% interest status", res_zero_rate["status"] == "PAID_OFF", f"status: {res_zero_rate['status']}")
    check("Simulate 0% interest total interest", res_zero_rate["total_interest_paid"] == 0, f"interest: {res_zero_rate['total_interest_paid']}")
    check("Simulate 0% interest payoff month", res_zero_rate["payoff_month"] == 360, f"month: {res_zero_rate['payoff_month']}")

    # Check zero rate with month > max_months potential DivisionByZero
    try:
        # Create a situation where rate is 0 and loan is not fully paid by max_months?
        # e.g., zero interest with term=1 (12 months) and loan=100M
        res_zero_rate_short = simulate_timeline(350000000, annual_rate=0.0, term_years=1, bonus_schedule={})
        check("Simulate 0% rate 1 year payoff", res_zero_rate_short["status"] == "PAID_OFF")
    except Exception as e:
        check("Simulate 0% rate exception check", False, f"Exception: {e}\n{traceback.format_exc()}")

    # High Interest (10%, 20%)
    pmt_high_rate = calculate_monthly_payment(150000000, 0.10, 30)
    check("High interest 10% PMT positive", pmt_high_rate > 1300000, f"pmt: {pmt_high_rate}")
    
    res_high_rate = simulate_timeline(375000000, annual_rate=0.10, term_years=30)
    check("Simulate high interest 10% paid off", res_high_rate["status"] == "PAID_OFF")

    # 4. Term Limits Edge Cases (1 year, 40 years, 0 years, negative years)
    check("PMT term 0 years", calculate_monthly_payment(120000000, 0.03, 0) == 0)
    check("PMT term negative years", calculate_monthly_payment(120000000, 0.03, -5) == 0)

    res_term_0 = simulate_timeline(350000000, term_years=0)
    check("Simulate term 0 status", res_term_0["status"] == "UNPAID" or res_term_0["payoff_month"] == 0, f"got {res_term_0}")

    res_term_40 = simulate_timeline(350000000, annual_rate=0.03, term_years=40, bonus_schedule={})
    check("Simulate 40yr term payoff month", res_term_40["payoff_month"] == 480)

    # 5. Bonus Over-Payment Edge Cases
    # Loan is 10M, bonus is 50M
    res_bonus_over = simulate_timeline(350000000, cash=340000000, bonus_schedule={1: 50000000})
    check("Bonus over-payment status", res_bonus_over["status"] == "PAID_OFF")
    check("Bonus over-payment end balance 0", res_bonus_over["monthly_log"][-1]["end_balance"] == 0)
    check("Bonus over-payment payoff month", res_bonus_over["payoff_month"] == 1)

    # 6. Penny Rounding / Floating Point Precision
    tax_float = calculate_acquisition_tax(375000000.49)
    fee_float = calculate_brokerage_fee(375000000.49)
    check("Acquisition tax float return int", isinstance(tax_float, int))
    check("Brokerage fee float return int", isinstance(fee_float, int))

    # 7. Bond Discount Presets vs Formula
    b350 = calculate_bond_discount(350000000)
    b375 = calculate_bond_discount(375000000)
    b400 = calculate_bond_discount(400000000)
    check("Bond discount 350M preset", b350 == 515000)
    check("Bond discount 375M preset", b375 == 574000)
    check("Bond discount 400M preset", b400 == 644000)

    b360 = calculate_bond_discount(360000000)
    # 360M * 0.7 * 0.021 * 0.10 = 529200
    check("Bond discount 360M formula", b360 == 529200, f"got {b360}")

    print(f"\nSTRESS TEST SUMMARY: Passed={passed}, Failed={failed}")
    return passed, failed, findings

if __name__ == "__main__":
    run_stress_tests()
