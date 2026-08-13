"""
Tier 4: Workload & Real-World Timeline Simulation Test Suite (5+ Scenarios)
Verifies full timeline simulations for 3.5억, 3.75억, 4.0억 standard scenarios, conservative, and aggressive scenarios.
"""

import pytest
from helpers.reference_engine import simulate_timeline, calculate_living_budget


def test_tier4_sim_01_350m_standard():
    """TC-T4-SIM-01: 3.5억 원 타임라인 시뮬레이션 (디딤돌 3.0%, 30년, 보너스 연 1,000만 원 상환)"""
    bonus_schedule = {1: 4000000, 2: 1000000, 7: 4000000, 8: 1000000}
    res = simulate_timeline(350000000, cash=230000000, annual_rate=0.03, term_years=30, bonus_schedule=bonus_schedule)
    
    assert res["status"] == "PAID_OFF"
    assert 80 <= res["payoff_month"] <= 110, f"Expected payoff between 80 and 110 months, got {res['payoff_month']}"
    assert res["total_interest_paid"] > 0
    assert res["monthly_log"][0]["interest"] == 300000


def test_tier4_sim_02_375m_standard():
    """TC-T4-SIM-02: 3.75억 원 타임라인 시뮬레이션 (디딤돌 3.15%, 30년, 보너스 연 1,000만 원 상환)"""
    bonus_schedule = {1: 4000000, 2: 1000000, 7: 4000000, 8: 1000000}
    res = simulate_timeline(375000000, cash=230000000, annual_rate=0.0315, term_years=30, bonus_schedule=bonus_schedule)
    
    assert res["status"] == "PAID_OFF"
    assert 100 <= res["payoff_month"] <= 135, f"Expected payoff between 100 and 135 months, got {res['payoff_month']}"
    assert res["total_interest_paid"] > 0


def test_tier4_sim_03_400m_standard():
    """TC-T4-SIM-03: 4.0억 원 타임라인 시뮬레이션 (디딤돌 3.3%, 30년, 보너스 연 1,000만 원 상환)"""
    bonus_schedule = {1: 4000000, 2: 1000000, 7: 4000000, 8: 1000000}
    res = simulate_timeline(400000000, cash=230000000, annual_rate=0.033, term_years=30, bonus_schedule=bonus_schedule)
    
    assert res["status"] == "PAID_OFF"
    assert 120 <= res["payoff_month"] <= 160, f"Expected payoff between 120 and 160 months, got {res['payoff_month']}"
    assert res["total_interest_paid"] > 0


def test_tier4_sim_04_conservative_scenario():
    """TC-T4-SIM-04: 보수적 시나리오 (3.75억 원, 시중은행 4.5%, 보너스 50% = 연 500만 원 상환)"""
    bonus_schedule = {1: 2000000, 2: 500000, 7: 2000000, 8: 500000}
    res = simulate_timeline(375000000, cash=230000000, annual_rate=0.045, term_years=30, bonus_schedule=bonus_schedule)
    
    assert res["status"] == "PAID_OFF"
    assert 160 <= res["payoff_month"] <= 220, f"Expected payoff between 160 and 220 months, got {res['payoff_month']}"
    std_res = simulate_timeline(375000000, cash=230000000, annual_rate=0.0315, term_years=30, bonus_schedule={1: 4000000, 2: 1000000, 7: 4000000, 8: 1000000})
    assert res["total_interest_paid"] > std_res["total_interest_paid"]


def test_tier4_sim_05_aggressive_scenario():
    """TC-T4-SIM-05: 공격적 시나리오 (3.5억 원, 디딤돌 3.0%, 100% 보너스 + 추가 현금 상환)"""
    aggressive_bonus = {1: 5000000, 2: 1000000, 7: 5000000, 8: 1000000}
    res = simulate_timeline(350000000, cash=230000000, annual_rate=0.03, term_years=30, bonus_schedule=aggressive_bonus)
    
    assert res["status"] == "PAID_OFF"
    assert res["payoff_month"] <= 90, f"Expected payoff <= 90 months, got {res['payoff_month']}"
