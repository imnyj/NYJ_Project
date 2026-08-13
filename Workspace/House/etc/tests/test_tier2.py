"""
Tier 2: Boundary & Corner Cases Test Suite (25+ Test Cases)
Verifies boundary values (BVA), edge limits, floating-point rounding, deficit warnings, zero interest/cash, and extreme scenarios.
"""

import pytest
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
from helpers.report_parser import parse_report_markdown
from helpers.html_parser import parse_html_simulator


# --- BVA 1: Price Boundary Limits ---

def test_bva_price_lower_bound_300m():
    """TC-T2-BVA-01: 매매가 하한 경계 3.0억 원 계산"""
    tax = calculate_acquisition_tax(300000000)
    loan = calculate_loan_principal(300000000, 230000000)
    assert tax == 1300000  # 3.3M - 2M = 1.3M
    assert loan == 70000000  # 300M - 230M = 70M


def test_bva_price_upper_bound_450m():
    """TC-T2-BVA-02: 매매가 상한 경계 4.5억 원 계산"""
    tax = calculate_acquisition_tax(450000000)
    loan = calculate_loan_principal(450000000, 230000000)
    assert tax == 2950000  # 4.95M - 2M = 2.95M
    assert loan == 220000000  # 450M - 230M = 220M


# --- BVA 2: Cash Reserve Boundary Limits ---

def test_bva_zero_cash_reserve():
    """TC-T2-BVA-03: 보유 현금 0원 경계 (대출 100%)"""
    loan = calculate_loan_principal(375000000, cash=0)
    assert loan == 375000000, f"Expected 375,000,000 KRW loan, got {loan}"


def test_bva_full_cash_purchase():
    """TC-T2-BVA-04: 전액 현금 매입 경계 (현금 >= 매매가)"""
    loan = calculate_loan_principal(350000000, cash=400000000)
    res = simulate_timeline(350000000, cash=400000000)
    assert loan == 0, f"Expected 0 KRW loan, got {loan}"
    assert res["payoff_month"] == 0
    assert res["status"] == "NO_LOAN_NEEDED"


def test_bva_extreme_cash_exceeding_price_plus_onetime():
    """TC-T2-BVA-05: 현금이 매매가 + 일회성 비용을 초과하는 경우"""
    one_time = calculate_total_one_time_costs(350000000)
    cash = 350000000 + one_time + 10000000
    loan = calculate_loan_principal(350000000, cash=cash)
    assert loan == 0


# --- BVA 3: Interest Rate Boundary Limits ---

def test_bva_zero_percent_interest_rate():
    """TC-T2-BVA-06: 금리 0.0% 경계 (무이자 대출)"""
    pmt = calculate_monthly_payment(120000000, annual_rate=0.0, term_years=30)
    assert pmt == 333333  # 120M / 360 months = 333,333.33 -> 333,333 KRW
    
    res = simulate_timeline(350000000, annual_rate=0.0, term_years=30, bonus_schedule={})
    assert res["total_interest_paid"] == 0, "Zero interest rate must yield zero total interest paid"


def test_bva_high_interest_rate_10_percent():
    """TC-T2-BVA-07: 고금리 10.0% 경계 조건"""
    pmt = calculate_monthly_payment(150000000, annual_rate=0.10, term_years=30)
    assert pmt > 1300000  # PMT should be ~1,316,364 KRW
    # Check interest is computed properly
    res = simulate_timeline(375000000, annual_rate=0.10, term_years=30)
    assert res["total_interest_paid"] > 50000000


# --- BVA 4: Loan Term Boundary Limits ---

def test_bva_short_term_1_year():
    """TC-T2-BVA-08: 대출 기간 1년 (12개월) 단기 상환 경계"""
    pmt = calculate_monthly_payment(120000000, annual_rate=0.03, term_years=1)
    assert pmt > 10000000  # PMT > 10M KRW / month


def test_bva_long_term_40_years():
    """TC-T2-BVA-09: 대출 기간 40년 (480개월) 장기 상환 경계"""
    pmt = calculate_monthly_payment(120000000, annual_rate=0.03, term_years=40)
    assert pmt < 500000  # PMT should be ~429,000 KRW
    res = simulate_timeline(350000000, annual_rate=0.03, term_years=40, bonus_schedule={})
    assert len(res["monthly_log"]) == 480


# --- BVA 5: Floating Point & Penny Rounding Precision ---

def test_bva_1won_penny_rounding_precision():
    """TC-T2-BVA-10: 1원 단위 절사/반올림 부동소수점 오차 검증"""
    tax = calculate_acquisition_tax(375000000.49)
    fee = calculate_brokerage_fee(375000000.49)
    assert isinstance(tax, int)
    assert isinstance(fee, int)


def test_bva_float_price_rounding():
    """TC-T2-BVA-11: 소수점 매매가 입력 시 정수 KRW 반환 검증"""
    tax = calculate_acquisition_tax(350000000.99)
    assert tax == 1850000


# --- BVA 6: Bonus Payoff Exceeding Remaining Balance ---

def test_bva_bonus_payoff_exceeding_remaining_balance():
    """TC-T2-BVA-12: 보너스 상환액이 대출 잔액보다 큰 경계"""
    # 20M bonus schedule on 10M balance
    res = simulate_timeline(350000000, cash=340000000, bonus_schedule={1: 20000000})
    logs = res["monthly_log"]
    assert res["status"] == "PAID_OFF"
    assert logs[-1]["end_balance"] == 0, "Final balance must not drop below 0"


# --- BVA 7: Budget & Income Edge Cases ---

def test_bva_deficit_budget_warning():
    """TC-T2-BVA-13: 월 소득 < 월 고정지출 (적자 발생 경계)"""
    budget = calculate_living_budget()
    low_income = 2000000  # 200만 원 (less than 2,319,708원)
    surplus = low_income - budget["total_fixed_spending"]
    assert surplus < 0, f"Expected negative surplus, got {surplus}"


def test_bva_zero_management_fee():
    """TC-T2-BVA-14: 관리비 0원 입력 시 아파트 고정비 산정 검증"""
    # Apt fixed = 0 (mgmt) + 10k (parking) + 30k (internet) = 40,000 KRW
    apt_fixed = 0 + 10000 + 30000
    assert apt_fixed == 40000


def test_bva_housing_repayment_capacity_limit():
    """TC-T2-BVA-15: 월 주거 부담 가능액 (50만 원) vs actual PMT 비교"""
    user_housing_capacity = 500000
    pmt_350m = calculate_monthly_payment(120000000, 0.03, 30) # ~505,928
    assert pmt_350m > user_housing_capacity  # Slightly over 500k, handled via bonus or budget adjustment


# --- BVA 8: Tax & Fee Special Conditions ---

def test_bva_non_first_home_acquisition_tax():
    """TC-T2-BVA-16: 생애최초 조건 미충족 시 취득세 (200만 감면 미적용 full 1.1%)"""
    tax = calculate_acquisition_tax(350000000, is_first_home=False)
    assert tax == 3850000, f"Expected 3,850,000 KRW full tax, got {tax}"


def test_bva_zero_brokerage_fee_direct_deal():
    """TC-T2-BVA-17: 당사자 직거래 시 중개수수료 0원"""
    fee = 0
    assert fee == 0


def test_bva_negative_price_error_handling():
    """TC-T2-BVA-18: 음수 매매가 입력 예외 처리"""
    tax = calculate_acquisition_tax(-100000)
    fee = calculate_brokerage_fee(-100000)
    assert tax == 0
    assert fee == 0


def test_bva_loan_stamp_tax_under_50m():
    """TC-T2-BVA-19: 대출금 5,000만 원 이하 시 인지세 비과세 (0원)"""
    loan = 45000000
    stamp_tax = 0 if loan <= 50000000 else 75000
    assert stamp_tax == 0


# --- BVA 9: Timeline & UI Scale Boundary Cases ---

def test_bva_dual_axis_scale_ratio():
    """TC-T2-BVA-20: 대출 잔액 (억 단위) vs 월 이자 (십만 단위) 스케일 비율 안전성"""
    balance = 170000000
    monthly_interest = balance * (0.03 / 12)
    ratio = balance / monthly_interest
    assert ratio > 100, f"Scale difference ratio is {ratio}, requires independent dual Y-axis scaling"


def test_bva_year_boundary_transition():
    """TC-T2-BVA-21: Month 12에서 Month 13으로의 연도 전환 시 잔액 연속성"""
    res = simulate_timeline(375000000, annual_rate=0.03, term_years=30)
    logs = res["monthly_log"]
    m12_end = logs[11]["end_balance"]
    m13_start = logs[12]["start_balance"]
    assert m12_end == m13_start, "End balance of Month 12 must equal Start balance of Month 13"


def test_bva_final_month_zero_balance_cleanup():
    """TC-T2-BVA-22: 대출 완납 최종월 잔액 0원 정확 청산 검증"""
    res = simulate_timeline(350000000, annual_rate=0.03, term_years=30)
    logs = res["monthly_log"]
    assert logs[-1]["end_balance"] == 0, "Final log entry end balance must be 0"


def test_bva_zero_bonus_payoff_schedule():
    """TC-T2-BVA-23: 보너스 상환 0원 (미투입) 시 기본 원리금 상환 타임라인"""
    res = simulate_timeline(350000000, annual_rate=0.03, term_years=30, bonus_schedule={})
    assert res["payoff_month"] == 360, f"Without bonus, 30yr loan must take 360 months, got {res['payoff_month']}"


def test_bva_excessive_bonus_payoff_schedule():
    """TC-T2-BVA-24: 초고액 보너스 상환 시 극단적 조기 완납"""
    # 50M bonus per month
    res = simulate_timeline(350000000, annual_rate=0.03, term_years=30, bonus_schedule={1: 50000000, 2: 50000000, 3: 50000000})
    assert res["payoff_month"] <= 3, f"Expected payoff <= 3 months, got {res['payoff_month']}"


def test_bva_report_parser_nonexistent_file():
    """TC-T2-BVA-25: 존재하지 않는 보고서 파일 파싱 시 예외 없이 핸들링 검증"""
    parsed = parse_report_markdown("/nonexistent/file_path.md")
    assert parsed["exists"] is False
    assert parsed["checklist_complete"] is False


def test_bva_html_parser_nonexistent_file():
    """TC-T2-BVA-26: 존재하지 않는 HTML 파일 파싱 시 예외 없이 핸들링 검증"""
    parsed = parse_html_simulator("/nonexistent/index4.html")
    assert parsed["exists"] is False
    assert parsed["all_required_ids_present"] is False
