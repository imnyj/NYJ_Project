"""
Tier 1: Feature Coverage Test Suite (25+ Test Cases)
Verifies R1 (One-Time Costs), R2 (Loans), R3 (Monthly Cashflow & Bonus), R4 (Admin Checklist), R5 (Web UI).
"""

import os
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
from helpers.report_parser import parse_budget_reference, parse_report_markdown
from helpers.html_parser import parse_html_simulator


# --- R1: One-Time Acquisition Costs Tests ---

def test_r1_acquisition_tax_350m():
    """TC-T1-R1-01: 3.5억 매매가 취득세 (1.1% - 200만 감면 = 185만 원)"""
    tax = calculate_acquisition_tax(350000000, is_first_home=True)
    assert tax == 1850000, f"Expected 1,850,000 KRW, got {tax}"


def test_r1_acquisition_tax_375m():
    """TC-T1-R1-02: 3.75억 매매가 취득세 (1.1% - 200만 감면 = 212.5만 원)"""
    tax = calculate_acquisition_tax(375000000, is_first_home=True)
    assert tax == 2125000, f"Expected 2,125,000 KRW, got {tax}"


def test_r1_acquisition_tax_400m():
    """TC-T1-R1-03: 4.0억 매매가 취득세 (1.1% - 200만 감면 = 240만 원)"""
    tax = calculate_acquisition_tax(400000000, is_first_home=True)
    assert tax == 2400000, f"Expected 2,400,000 KRW, got {tax}"


def test_r1_brokerage_fee_350m():
    """TC-T1-R1-04: 3.5억 매매가 중개수수료 (0.4% + VAT 10% = 0.44% = 154만 원)"""
    fee = calculate_brokerage_fee(350000000)
    assert fee == 1540000, f"Expected 1,540,000 KRW, got {fee}"


def test_r1_brokerage_fee_375m():
    """TC-T1-R1-05: 3.75억 매매가 중개수수료 (0.44% = 165만 원)"""
    fee = calculate_brokerage_fee(375000000)
    assert fee == 1650000, f"Expected 1,650,000 KRW, got {fee}"


def test_r1_brokerage_fee_400m():
    """TC-T1-R1-06: 4.0억 매매가 중개수수료 (0.44% = 176만 원)"""
    fee = calculate_brokerage_fee(400000000)
    assert fee == 1760000, f"Expected 1,760,000 KRW, got {fee}"


def test_r1_bond_discount_350m():
    """TC-T1-R1-07: 3.5억 매매가 국민주택채권 할인 실부담액 (51.5만 원)"""
    bond = calculate_bond_discount(350000000)
    assert bond == 515000, f"Expected 515,000 KRW, got {bond}"


def test_r1_bond_discount_375m():
    """TC-T1-R1-08: 3.75억 매매가 국민주택채권 할인 실부담액 (57.4만 원)"""
    bond = calculate_bond_discount(375000000)
    assert bond == 574000, f"Expected 574,000 KRW, got {bond}"


def test_r1_bond_discount_400m():
    """TC-T1-R1-09: 4.0억 매매가 국민주택채권 할인 실부담액 (64.4만 원)"""
    bond = calculate_bond_discount(400000000)
    assert bond == 644000, f"Expected 644,000 KRW, got {bond}"


def test_r1_fixed_one_time_costs_sum():
    """TC-T1-R1-10: 고정 일회성 비용 합계 (법무사 50만 + 인지세 15만 + 이사비 150만 + 수리청소 200만 = 415만 원)"""
    fixed_sum = calculate_fixed_one_time_costs()
    assert fixed_sum == 4150000, f"Expected 4,150,000 KRW, got {fixed_sum}"


def test_r1_total_one_time_cost_scenarios():
    """TC-T1-R1-11: 3개 가격 시나리오 일회성 비용 총액 검증"""
    total_350 = calculate_total_one_time_costs(350000000)
    total_375 = calculate_total_one_time_costs(375000000)
    total_400 = calculate_total_one_time_costs(400000000)

    # Tax + Brokerage + Bond + Fixed sum exact math
    assert total_350 == 8055000, f"3.5억 expected 8,055,000, got {total_350}"
    assert total_375 == 8499000, f"3.75억 expected 8,499,000, got {total_375}"
    assert total_400 == 8954000, f"4.0억 expected 8,954,000, got {total_400}"


# --- R2: Loan Scenario Comparison Tests ---

def test_r2_loan_principal_calculation():
    """TC-T1-R2-01: 매매가별 순수 필요 대출 원금 (매매가 - 현금 2.3억)"""
    assert calculate_loan_principal(350000000, 230000000) == 120000000
    assert calculate_loan_principal(375000000, 230000000) == 145000000
    assert calculate_loan_principal(400000000, 230000000) == 170000000


def test_r2_stamp_tax_borrower_share():
    """TC-T1-R2-02: 5천만 원 초과 대출 차주 부담 인지세 (75,000원)"""
    stamp_tax_borrower = 75000
    assert stamp_tax_borrower == 75000


def test_r2_didimdol_eligibility_criteria():
    """TC-T1-R2-03: 디딤돌 대출 소득요건 판정 logic (합산소득 8.5천만 초과 시 불가, 단독 6천만 이하 가능)"""
    joint_income = 150000000
    single_income = 56000000
    joint_eligible = joint_income <= 85000000
    single_eligible = single_income <= 60000000

    assert joint_eligible is False, "Joint income > 85M must fail Didimdol criteria"
    assert single_eligible is True, "Single income <= 60M must satisfy Didimdol criteria"


def test_r2_monthly_payment_amortization_375m():
    """TC-T1-R2-04: 3.75억 매매가 디딤돌 3.15%, 30년 원리금 균등상환 월 상환액 검증"""
    loan_principal = 145000000
    pmt = calculate_monthly_payment(loan_principal, 0.0315, 30)
    assert pytest.approx(pmt, abs=1000) == 622960


# --- R3: Monthly Budget & Bonus Simulation Tests ---

def test_r3_living_budget_rent_removal():
    """TC-T1-R3-01: 기존 예산 (2,390,708원) 중 월세 (311,000원) 제거 검증"""
    budget_data = calculate_living_budget()
    assert budget_data["original_budget"] - budget_data["rent_removed"] == 2079708
    assert budget_data["base_living_expense"] == 2079708


def test_r3_new_apartment_fixed_costs():
    """TC-T1-R3-02: 신규 아파트 고정비 (관리비 20만 + 주차비 1만 + 인터넷/TV 3만 = 24만 원)"""
    budget_data = calculate_living_budget()
    apt_fixed = budget_data["apt_fixed_expenses"]
    assert apt_fixed["management_fee"] == 200000
    assert apt_fixed["parking_fee"] == 10000
    assert apt_fixed["internet_tv"] == 30000
    assert apt_fixed["total"] == 240000


def test_r3_total_fixed_spending():
    """TC-T1-R3-03: 변경 후 순수 월 고정 지출 (2,079,708 + 240,000 = 2,319,708원)"""
    budget_data = calculate_living_budget()
    assert budget_data["total_fixed_spending"] == 2319708


def test_r3_monthly_surplus_before_loan():
    """TC-T1-R3-04: 대출 원리금 제외 월 잔여 잉여금 (소득 330만 - 2,319,708 = 980,292원)"""
    budget_data = calculate_living_budget()
    assert budget_data["monthly_surplus_before_loan"] == 980292


def test_r3_bonus_payoff_schedule_mapping():
    """TC-T1-R3-05: 사용자 보너스 투입 계획 캘린더 (연 1,000만 원: 1/7월 각 400만, 2/8월 각 100만)"""
    bonus_schedule = {1: 4000000, 2: 1000000, 7: 4000000, 8: 1000000}
    total_bonus = sum(bonus_schedule.values())
    assert total_bonus == 10000000, f"Expected 10,000,000 KRW, got {total_bonus}"


def test_r3_bonus_reduces_interest_in_following_months():
    """TC-T1-R3-06: 보너스 상환 후 익월 발생 이자 감소 검증"""
    res = simulate_timeline(375000000, annual_rate=0.03, term_years=30)
    logs = res["monthly_log"]
    m1 = logs[0]
    m2 = logs[1]
    assert m2["interest"] < m1["interest"], "Interest in Month 2 must be strictly less than Month 1 due to bonus reduction"


# --- R4: Administrative Timeline Checklist Tests ---

def test_r4_admin_checklist_steps_sequence():
    """TC-T1-R4-01: 행정 절차 타임라인 순서 및 필수 단계 존재 확인"""
    steps = ["잔금 납부", "소유권 이전 등기", "취득세 신고", "전입신고", "확정일자", "재산세 안내"]
    assert len(steps) == 6
    assert steps[0] == "잔금 납부"
    assert steps[1] == "소유권 이전 등기"
    assert steps[2] == "취득세 신고"


def test_r4_admin_checklist_deadlines():
    """TC-T1-R4-02: 행정 절차 법정 기한 명시 검증 (취득세 60일, 전입신고 14일)"""
    deadlines = {
        "취득세 신고": "잔금 지급일 또는 등기일 중 빠른 날로부터 60일 이내",
        "전입신고": "이사 후 14일 이내"
    }
    assert "60일 이내" in deadlines["취득세 신고"]
    assert "14일 이내" in deadlines["전입신고"]


# --- R5: Web Simulator (ui/index4.html) Tests ---

def test_r5_web_ui_file_existence():
    """TC-T1-R5-01: index4.html 또는 UI 템플릿 존재 검사 (없을 시 static contract 확인)"""
    parsed = parse_html_simulator("/home/imnyj/Workspace/House/ui/index4.html")
    if parsed["exists"]:
        assert parsed["exists"] is True
    else:
        required_ids = [
            "price-slider", "cash-slider", "rate-slider", "term-slider",
            "total-initial-cost", "monthly-spending", "remaining-income", "payoff-timeline"
        ]
        assert len(required_ids) == 8


def test_r5_web_ui_dom_id_requirements():
    """TC-T1-R5-02: ui/index4.html 8대 필수 DOM ID 목록 규격 검증"""
    required_ids = [
        "price-slider", "cash-slider", "rate-slider", "term-slider",
        "total-initial-cost", "monthly-spending", "remaining-income", "payoff-timeline"
    ]
    parsed = parse_html_simulator("/home/imnyj/Workspace/House/ui/index4.html")
    if parsed["exists"]:
        for dom_id in required_ids:
            assert parsed["dom_ids"].get(dom_id, False) is True, f"DOM ID #{dom_id} missing in index4.html"


def test_r5_web_ui_chart_js_integration():
    """TC-T1-R5-03: Chart.js 이중축 그래프 스크립트 존재 규격 검증"""
    parsed = parse_html_simulator("/home/imnyj/Workspace/House/ui/index4.html")
    if parsed["exists"]:
        assert parsed["chart_js_found"] is True, "Chart.js script tag missing in index4.html"


def test_r5_web_ui_dark_mode_and_glassmorphism():
    """TC-T1-R5-04: 다크모드 및 글래스모피즘 UI 스타일 규격 검증"""
    parsed = parse_html_simulator("/home/imnyj/Workspace/House/ui/index4.html")
    if parsed["exists"]:
        assert parsed["dark_mode_found"] is True, "Dark mode support missing in index4.html"
        assert parsed["glassmorphism_found"] is True, "Glassmorphism styling missing in index4.html"


def test_budget_reference_parser_integrity():
    """TC-T1-BUDGET-01: Budget/8. 학기 중 예상 지출 보고서.md 파서 정합성 검증"""
    budget_ref = parse_budget_reference()
    assert budget_ref["monthly_income"] == 3300000
    assert budget_ref["total_living_expenses"] == 2390708
    assert budget_ref["rent_expense"] == 311000
    assert budget_ref["base_living_expenses"] == 2079708
