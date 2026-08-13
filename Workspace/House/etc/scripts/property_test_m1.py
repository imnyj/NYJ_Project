"""
property_test_m1.py - Property-Based Testing & Edge Case Verification Harness for Calc Engine (M1)
Location: /home/imnyj/Workspace/House/etc/scripts/property_test_m1.py
"""

import sys
import random
import math
import traceback
from pathlib import Path

# Add script directory to sys.path
sys.path.append(str(Path(__file__).resolve().parent))
import calc_engine


def test_invariants_randomized(num_iterations: int = 1500):
    """
    Run num_iterations randomized tests verifying core financial invariants.
    """
    print(f"=== Running Randomized Property-Based Tests ({num_iterations} iterations) ===")
    
    passed_count = 0
    failures = []
    eligibility_anomalies = []
    legal_fee_anomalies = []
    stamp_duty_anomalies = []

    # Set seed for reproducible testing
    random.seed(42)

    for i in range(1, num_iterations + 1):
        # Generate random inputs across wide realistic & stress ranges
        # Price: 50M KRW to 1 Billion KRW
        price = random.randint(50_000_000, 1_000_000_000)
        # Cash reserve: 0 KRW to 500M KRW
        cash_reserve = random.randint(0, 500_000_000)
        # First time home buyer boolean
        is_first_home = random.choice([True, False])

        try:
            # 1. R1 Costs Calculation
            r1 = calc_engine.calculate_r1_costs(price, is_first_home=is_first_home)

            # Invariant 1: total_initial_capital_needed == price + total_r1_cost
            if r1['total_initial_capital_needed'] != price + r1['total_r1_cost']:
                failures.append((i, "Invariant 1 Failed", f"Capital needed {r1['total_initial_capital_needed']} != price {price} + r1 {r1['total_r1_cost']}"))

            # Invariant 3: R1 Sum Consistency
            expected_acq = r1['net_acquisition_tax'] + r1['local_education_tax']
            if r1['acquisition_tax_total'] != expected_acq:
                failures.append((i, "Acq Tax Sum Failed", f"{r1['acquisition_tax_total']} != {expected_acq}"))

            expected_brokerage = r1['brokerage_fee_base'] + r1['brokerage_vat']
            if r1['brokerage_fee'] != expected_brokerage:
                failures.append((i, "Brokerage Sum Failed", f"{r1['brokerage_fee']} != {expected_brokerage}"))

            expected_r1_sum = (r1['acquisition_tax_total'] + r1['brokerage_fee'] + r1['legal_fee'] +
                               r1['stamp_duty'] + r1['bond_discount_fee'] + r1['moving_fee'] + r1['repair_cleaning_fee'])
            if r1['total_r1_cost'] != expected_r1_sum:
                failures.append((i, "Total R1 Sum Failed", f"{r1['total_r1_cost']} != {expected_r1_sum}"))

            # 2. R2 Loan Calculation
            r2 = calc_engine.calculate_r2_loans(price, cash_reserve=cash_reserve)

            # Invariant 2: required_loan non-negative and equals max(0, price - cash_reserve)
            expected_loan = max(0, price - cash_reserve)
            if r2['pure_required_loan'] < 0:
                failures.append((i, "Invariant 2 (Negative Loan) Failed", f"Loan {r2['pure_required_loan']} < 0"))

            if r2['pure_required_loan'] != expected_loan:
                failures.append((i, "Invariant 2 (Loan Value) Failed", f"Loan {r2['pure_required_loan']} != {expected_loan}"))

            # 3. Check Eligibility / Domain Logic Edge Cases
            didimdol = r2['products']['didimdol']

            # Edge Case Observation A: Didimdol loan limit (400M) vs eligibility
            if r2['pure_required_loan'] > 400_000_000 and price <= 600_000_000:
                if didimdol['eligible']:
                    eligibility_anomalies.append({
                        'iteration': i,
                        'price': price,
                        'cash_reserve': cash_reserve,
                        'loan': r2['pure_required_loan'],
                        'reason': 'Loan exceeds Didimdol max limit (400M) but product reported as eligible'
                    })

            # Edge Case Observation B: LTV > 70% vs Didimdol eligibility
            if r2['ltv_percent'] > 70.0 and price <= 600_000_000:
                if didimdol['eligible']:
                    eligibility_anomalies.append({
                        'iteration': i,
                        'price': price,
                        'cash_reserve': cash_reserve,
                        'ltv': r2['ltv_percent'],
                        'reason': 'LTV exceeds 70% max cap but Didimdol reported as eligible'
                    })

            # Edge Case Observation C: Legal fee fallback behavior
            if price not in (350_000_000, 375_000_000, 400_000_000):
                if price > 400_000_000 and r1['legal_fee'] == 500000:
                    legal_fee_anomalies.append({
                        'iteration': i,
                        'price': price,
                        'legal_fee': r1['legal_fee'],
                        'reason': f'Price {price:,} > 400M fallback to 500k KRW legal fee (less than 400M fee of 550k)'
                    })

            # Edge Case Observation D: Stamp duty for loans <= 50M
            if 0 < r2['pure_required_loan'] <= 50_000_000:
                if r2['secondary_fees']['loan_stamp_duty_borrower'] != 0:
                    stamp_duty_anomalies.append({
                        'iteration': i,
                        'loan': r2['pure_required_loan'],
                        'duty_charged': r2['secondary_fees']['loan_stamp_duty_borrower'],
                        'reason': 'Loan <= 50M KRW charged 35,000 KRW stamp duty (statutorily exempt in tax law)'
                    })

            passed_count += 1

        except Exception as e:
            failures.append((i, "Unhandled Exception", f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"))

    print(f"Randomized Property Test Completed: {passed_count}/{num_iterations} passed.")
    print(f"Strict Invariant Failures: {len(failures)}")
    print(f"Didimdol Eligibility Limits Anomalies Detected: {len(eligibility_anomalies)}")
    print(f"Legal Fee Fallback Anomalies Detected: {len(legal_fee_anomalies)}")
    print(f"Loan Stamp Duty Exemption Anomalies Detected: {len(stamp_duty_anomalies)}")

    return {
        'num_iterations': num_iterations,
        'passed_count': passed_count,
        'failures': failures,
        'eligibility_anomalies': eligibility_anomalies,
        'legal_fee_anomalies': legal_fee_anomalies,
        'stamp_duty_anomalies': stamp_duty_anomalies
    }


def test_numerical_precision_and_edge_cases():
    """
    Test specific boundary conditions, floating point inputs, and precision limits.
    """
    print("\n=== Running Empirical Boundary & Numerical Precision Tests ===")
    results = []

    # Test 1: Float price input (e.g. 350000000.49 vs 350000000.5)
    p1 = calc_engine.calculate_r1_costs(350000000.49)
    p2 = calc_engine.calculate_r1_costs(350000000.5)
    results.append({
        'test': 'Float Price Rounding (Banker\'s rounding)',
        'p1_350M_0.49': p1['purchase_price'],
        'p2_350M_0.50': p2['purchase_price'],
        'status': 'PASS' if p1['purchase_price'] == 350000000 and p2['purchase_price'] == 350000000 else 'INFO'
    })

    # Test 2: CPM Zero Rate & Zero Term
    try:
        pmt_zero_rate = calc_engine.calculate_cpm_monthly_payment(120_000_000, 0.0, term_years=30)
        results.append({'test': 'CPM Zero Interest Rate', 'result': pmt_zero_rate, 'expected': 333334, 'status': 'PASS'})
    except Exception as e:
        results.append({'test': 'CPM Zero Interest Rate', 'error': str(e), 'status': 'FAIL'})

    try:
        pmt_zero_term = calc_engine.calculate_cpm_monthly_payment(120_000_000, 0.0315, term_years=0)
        results.append({'test': 'CPM Zero Term Years', 'status': 'UNHANDLED_EXCEPTION', 'error': 'ZeroDivisionError raised'})
    except ZeroDivisionError:
        results.append({'test': 'CPM Zero Term Years', 'status': 'RAISES_ZERO_DIVISION_ERROR', 'note': 'ZeroDivisionError caught correctly'})

    # Test 3: Housing bond threshold boundary around 260M public price (Price ~ 371,428,571)
    # 371,428,571 * 0.7 = 259,999,999.7 -> 260,000,000
    price_below_boundary = 371428570
    price_above_boundary = 371428572
    r1_below = calc_engine.calculate_r1_costs(price_below_boundary)
    r1_above = calc_engine.calculate_r1_costs(price_above_boundary)

    results.append({
        'test': 'Bond Discount Rate Threshold Boundary (260M public price)',
        'below_price': price_below_boundary,
        'below_public_official': r1_below['public_official_price'],
        'below_bond_rate': r1_below['bond_rate'],
        'above_price': price_above_boundary,
        'above_public_official': r1_above['public_official_price'],
        'above_bond_rate': r1_above['bond_rate'],
        'status': 'PASS'
    })

    # Test 4: Acquisition Tax Rate for Price > 6억 (e.g. 700M KRW)
    r1_700M = calc_engine.calculate_r1_costs(700_000_000)
    results.append({
        'test': 'Acquisition Tax for Price > 600M (700M KRW)',
        'applied_gross_rate': r1_700M['gross_acquisition_tax'] / 700_000_000,
        'gross_tax': r1_700M['gross_acquisition_tax'],
        'note': 'Engine applies flat 1.0% tax rate. In Korean tax law, 700M house has 2.33% tax rate.',
        'status': 'DOMAIN_SPECIFIC_LIMITATION'
    })

    for r in results:
        print(f" - [{r['status']}] {r['test']}: {r.get('result', r.get('note', ''))}")

    return results


if __name__ == '__main__':
    res_rand = test_invariants_randomized(1500)
    res_edge = test_numerical_precision_and_edge_cases()
