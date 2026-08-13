"""
test_calc_engine.py - Unit test suite for Milestone 1 Financial Calculation Engine
Location: /home/imnyj/Workspace/House/etc/tests/test_calc_engine.py
"""

import pytest
import json
from pathlib import Path
import sys

# Ensure etc/scripts is in Python path for imports
project_root = Path(__file__).resolve().parent.parent.parent
scripts_dir = project_root / 'etc' / 'scripts'
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from calc_engine import (
    load_financial_params,
    calculate_r1_costs,
    calculate_r2_loans,
    calculate_cpm_monthly_payment,
    run_all_scenarios
)


class TestFinancialParamsSchema:
    """Verify data schema and parameters in financial_params.json."""

    def test_json_file_exists(self):
        params_path = project_root / 'etc' / 'data' / 'financial_params.json'
        assert params_path.exists(), f'Missing parameter file: {params_path}'

    def test_json_structure_and_values(self):
        params = load_financial_params()
        assert params['scenarios'] == [350000000, 375000000, 400000000]
        assert params['cash_reserve'] == 230000000
        assert params['monthly_income'] == 3300000
        assert params['monthly_housing_budget'] == 500000

        # Expenses breakdown verification
        expenses = params['expenses']
        assert expenses['base_13_categories_total'] == 2390708
        assert expenses['removed_rent_and_electricity'] == 311000
        assert expenses['base_living_net'] == 2079708
        assert expenses['apartment_fixed_total'] == 240000
        assert expenses['total_monthly_fixed_expense'] == 2319708

        # Bonus schedule verification
        bonuses = params['bonuses']
        assert bonuses['annual_prepayment_total'] == 10000000
        prep_schedule = bonuses['prepayment_schedule']
        assert len(prep_schedule) == 4
        assert prep_schedule[0]['month'] == 1 and prep_schedule[0]['repayment_amount'] == 4000000
        assert prep_schedule[1]['month'] == 2 and prep_schedule[1]['repayment_amount'] == 1000000
        assert prep_schedule[2]['month'] == 7 and prep_schedule[2]['repayment_amount'] == 4000000
        assert prep_schedule[3]['month'] == 8 and prep_schedule[3]['repayment_amount'] == 1000000


class TestR1OneTimeCosts:
    """Verify R1 One-time Property Acquisition Costs."""

    def test_r1_350m_scenario(self):
        res = calculate_r1_costs(350000000, is_first_home=True)
        assert res['purchase_price'] == 350000000
        assert res['gross_acquisition_tax'] == 3500000
        assert res['acq_tax_exemption'] == 2000000
        assert res['net_acquisition_tax'] == 1500000
        assert res['local_education_tax'] == 150000
        assert res['acquisition_tax_total'] == 1650000
        assert res['brokerage_fee_base'] == 1400000
        assert res['brokerage_vat'] == 140000
        assert res['brokerage_fee'] == 1540000
        assert res['legal_fee'] == 500000
        assert res['stamp_duty'] == 150000
        assert res['public_official_price'] == 245000000
        assert res['bond_rate'] == 0.021
        assert res['bond_buy_amount'] == 5145000
        assert res['bond_discount_fee'] == 514500
        assert res['moving_fee'] == 1500000
        assert res['repair_cleaning_fee'] == 2000000
        assert res['total_r1_cost'] == 7854500
        assert res['total_initial_capital_needed'] == 357854500

    def test_r1_375m_scenario(self):
        res = calculate_r1_costs(375000000, is_first_home=True)
        assert res['purchase_price'] == 375000000
        assert res['gross_acquisition_tax'] == 3750000
        assert res['acq_tax_exemption'] == 2000000
        assert res['net_acquisition_tax'] == 1750000
        assert res['local_education_tax'] == 175000
        assert res['acquisition_tax_total'] == 1925000
        assert res['brokerage_fee'] == 1650000
        assert res['legal_fee'] == 520000
        assert res['stamp_duty'] == 150000
        assert res['public_official_price'] == 262500000
        assert res['bond_rate'] == 0.023
        assert res['bond_buy_amount'] == 6037500
        assert res['bond_discount_fee'] == 603750
        assert res['moving_fee'] == 1500000
        assert res['repair_cleaning_fee'] == 2000000
        assert res['total_r1_cost'] == 8348750
        assert res['total_initial_capital_needed'] == 383348750

    def test_r1_400m_scenario(self):
        res = calculate_r1_costs(400000000, is_first_home=True)
        assert res['purchase_price'] == 400000000
        assert res['gross_acquisition_tax'] == 4000000
        assert res['acq_tax_exemption'] == 2000000
        assert res['net_acquisition_tax'] == 2000000
        assert res['local_education_tax'] == 200000
        assert res['acquisition_tax_total'] == 2200000
        assert res['brokerage_fee'] == 1760000
        assert res['legal_fee'] == 550000
        assert res['stamp_duty'] == 150000
        assert res['public_official_price'] == 280000000
        assert res['bond_rate'] == 0.023
        assert res['bond_buy_amount'] == 6440000
        assert res['bond_discount_fee'] == 644000
        assert res['moving_fee'] == 1500000
        assert res['repair_cleaning_fee'] == 2000000
        assert res['total_r1_cost'] == 8804000
        assert res['total_initial_capital_needed'] == 408804000

    def test_first_time_buyer_exemption_toggle(self):
        res_first = calculate_r1_costs(350000000, is_first_home=True)
        assert res_first['acq_tax_exemption'] == 2000000
        assert res_first['net_acquisition_tax'] == 1500000

        res_non_first = calculate_r1_costs(350000000, is_first_home=False)
        assert res_non_first['acq_tax_exemption'] == 0
        assert res_non_first['net_acquisition_tax'] == 3500000
        assert res_non_first['local_education_tax'] == 350000
        assert res_non_first['acquisition_tax_total'] == 3850000

    def test_invalid_price_raises_error(self):
        with pytest.raises(ValueError):
            calculate_r1_costs(0)
        with pytest.raises(ValueError):
            calculate_r1_costs(-50000000)


class TestR2LoanScenarios:
    """Verify R2 Mortgage loan requirements, LTV, secondary fees, and comparisons."""

    @pytest.mark.parametrize("price, cash, expected_loan, expected_ltv", [
        (350000000, 230000000, 120000000, 34.29),
        (375000000, 230000000, 145000000, 38.67),
        (400000000, 230000000, 170000000, 42.50),
    ])
    def test_loan_requirements_and_ltv(self, price, cash, expected_loan, expected_ltv):
        res = calculate_r2_loans(price, cash_reserve=cash)
        assert res['pure_required_loan'] == expected_loan
        assert abs(res['ltv_percent'] - expected_ltv) <= 0.01

    def test_secondary_loan_fees(self):
        res = calculate_r2_loans(350000000, cash_reserve=230000000)
        sec = res['secondary_fees']
        assert sec['loan_stamp_duty_borrower'] == 75000
        assert sec['mortgage_setup_borrower'] == 20000
        assert sec['annual_guarantee_fee_rate'] == 0.0005
        assert sec['annual_guarantee_fee'] == 60000  # 1.2억 * 0.05% = 60,000
        assert sec['total_upfront_fees'] == 95000

    def test_didimdol_vs_commercial_product_details(self):
        res = calculate_r2_loans(350000000, cash_reserve=230000000)
        prods = res['products']

        # Didimdol
        didimdol = prods['didimdol']
        assert didimdol['eligible'] is True
        assert didimdol['applied_rate'] == 0.0315
        assert didimdol['required_loan'] == 120000000
        # 1.2억 at 3.15% 30y CPM -> 515,684 KRW/mo
        assert abs(didimdol['monthly_payment_30y'] - 515684) <= 100

        # Commercial bank
        commercial = prods['commercial']
        assert commercial['eligible'] is True
        assert commercial['applied_rate'] == 0.0425
        # 1.2억 at 4.25% 30y CPM -> 590,328 KRW/mo
        assert abs(commercial['monthly_payment_30y'] - 590328) <= 100

    def test_cpm_calculation_helper(self):
        # 1억 at 3% 30 years
        pmt = calculate_cpm_monthly_payment(100000000, 0.03, 30)
        assert abs(pmt - 421604) <= 10
        # Zero principal returns 0
        assert calculate_cpm_monthly_payment(0, 0.03, 30) == 0

    def test_invalid_cash_reserve_raises_error(self):
        with pytest.raises(ValueError):
            calculate_r2_loans(350000000, cash_reserve=-1000)


class TestRunAllScenarios:
    """Verify aggregated scenario runner."""

    def test_run_all_scenarios(self):
        res = run_all_scenarios()
        assert res['cash_reserve'] == 230000000
        assert res['monthly_income'] == 3300000
        assert res['total_monthly_fixed_expense_no_loan'] == 2319708
        scenarios = res['scenarios']
        assert len(scenarios) == 3
        prices = [s['scenario_price'] for s in scenarios]
        assert prices == [350000000, 375000000, 400000000]
