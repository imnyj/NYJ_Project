"""
etc/scripts/verify_phase2_adversarial.py
Adversarial Stress Test & Accounting Invariant Audit for Phase 2 Mock Engine
"""

import sys
from decimal import Decimal
import numpy as np

from modules.engine import (
    VirtualAccount,
    MockExecutionEngine,
    FeeConfig,
    OrderSide,
    DummyStrategySimulator,
    MockEnvironment,
    ActionType,
    InvalidOrderError,
    InsufficientFundsError,
    InsufficientSharesError
)

def test_10k_ping_pong():
    print("=== Test 1: 10,000 Iterations High-Frequency Ping-Pong Stress Test ===")
    initial_cash = Decimal("100000000")  # 1억원
    account = VirtualAccount(initial_cash=initial_cash)
    engine = MockExecutionEngine(account=account)
    simulator = DummyStrategySimulator(engine=engine)
    
    result = simulator.run_ping_pong(
        symbol="005930",
        base_price=Decimal("70000"),
        quantity=10,
        iterations=10000
    )
    
    # Independent Accounting Verification
    cum_comm = engine.account.cumulative_commission
    cum_tax = engine.account.cumulative_tax
    cum_slip = engine.account.cumulative_slippage
    total_frictions = cum_comm + cum_tax + cum_slip
    final_cash = engine.account.cash_balance
    final_holdings = engine.account.get_position("005930").quantity
    
    discrepancy = initial_cash - (final_cash + total_frictions)
    
    print(f"Total trades: {result['total_trades']}")
    print(f"Final holdings: {final_holdings}")
    print(f"Total frictions: {total_frictions:,} KRW (Comm: {cum_comm:,}, Tax: {cum_tax:,}, Slip: {cum_slip:,})")
    print(f"Final cash: {final_cash:,} KRW")
    print(f"Independent Discrepancy: {discrepancy} KRW")
    
    assert final_holdings == 0, "Holdings must be 0 after ping-pong cleanup"
    assert final_cash >= Decimal("0"), "Final cash must be non-negative"
    assert discrepancy == Decimal("0"), f"Discrepancy must be exactly 0 KRW, got {discrepancy}"
    assert result['invariant_passed'] is True
    print("-> Test 1 PASSED (0 KRW discrepancy, 0 negative cash)!\n")

def test_extreme_boundary_and_rejection():
    print("=== Test 2: Extreme Boundary & Exhaustion Rejection Defense ===")
    account = VirtualAccount(initial_cash=Decimal("50000"))  # 5만원
    engine = MockExecutionEngine(account=account)
    
    # 70,000원 주식 1주 매수 시도 (예상 필요현금: 70,070 + 10 = 70,080원) -> 거절되어야 함
    rec1 = engine.execute_order("005930", OrderSide.BUY, 1, Decimal("70000"))
    assert rec1.is_success is False
    assert account.cash_balance == Decimal("50000")
    assert account.get_position("005930").quantity == 0
    
    # 50,000원 주식 1주 매수 (체결가: 50,050원, 수수료: 7원 -> 필요 50,057원) -> 5만원 잔고 부족으로 거절
    rec2 = engine.execute_order("005930", OrderSide.BUY, 1, Decimal("50000"))
    assert rec2.is_success is False
    assert account.cash_balance == Decimal("50000")
    
    # 49,900원 주식 1주 매수 (체결가: 49,950원, 수수료: 7원 -> 필요 49,957원 <= 50,000원) -> 체결 성공
    rec3 = engine.execute_order("005930", OrderSide.BUY, 1, Decimal("49900"))
    assert rec3.is_success is True
    assert account.cash_balance == Decimal("50000") - Decimal("49957")
    assert account.cash_balance >= Decimal("0")
    
    # 추가 매수 시도 (잔고 43원) -> 즉시 거절
    rec4 = engine.execute_order("005930", OrderSide.BUY, 1, Decimal("1000"))
    assert rec4.is_success is False
    assert account.cash_balance == Decimal("43")
    
    print("-> Test 2 PASSED (Strict rejection & non-negative cash guaranteed)!\n")

def test_random_walk_2000_steps_with_independent_audit():
    print("=== Test 3: 2,000 Steps Random Walk Market with Independent Accounting Audit ===")
    initial_cash = Decimal("20000000")
    account = VirtualAccount(initial_cash=initial_cash)
    engine = MockExecutionEngine(account=account)
    simulator = DummyStrategySimulator(engine=engine)
    
    result = simulator.run_random_stress(
        symbol="005930",
        base_price=Decimal("70000"),
        steps=2000,
        max_quantity=10,
        seed=999
    )
    
    pos = engine.account.get_position("005930")
    last_price = engine._last_market_prices["005930"]
    stock_eval = pos.market_value(last_price)
    
    total_eq = engine.account.cash_balance + stock_eval
    total_frictions = (
        engine.account.cumulative_commission +
        engine.account.cumulative_tax +
        engine.account.cumulative_slippage
    )
    drift = engine._cumulative_market_drift_pnl
    
    # Independent Invariant Check:
    # Initial + Drift == Total_Equity + Total_Frictions
    lhs = initial_cash + drift
    rhs = total_eq + total_frictions
    diff = lhs - rhs
    
    print(f"Steps: {result['steps']}, Trades: {result['total_trades']}, Rejections: {result['rejected_trades']}")
    print(f"Final Cash: {engine.account.cash_balance:,} KRW, Holdings: {pos.quantity} shares")
    print(f"Stock Valuation: {stock_eval:,} KRW, Total Equity: {total_eq:,} KRW")
    print(f"Total Frictions: {total_frictions:,} KRW, Drift PnL: {drift:,} KRW")
    print(f"LHS (Initial + Drift): {lhs:,} KRW")
    print(f"RHS (Equity + Frictions): {rhs:,} KRW")
    print(f"Difference: {diff} KRW")
    
    assert diff == Decimal("0"), f"Discrepancy must be 0 KRW, got {diff}"
    assert engine.account.cash_balance >= Decimal("0"), "Cash balance must be non-negative"
    assert result['invariant_passed'] is True
    print("-> Test 3 PASSED (2,000 steps random walk independent audit exact 0 KRW)!\n")

def test_fractional_precision_and_immutability():
    print("=== Test 4: Fractional Precision & Immutability ===")
    account = VirtualAccount(initial_cash=Decimal("1000000"))
    engine = MockExecutionEngine(account=account)
    
    # Decimal 1원 단위 정밀 절사 확인
    # 33,333원 * 1.001 = 33,366.333 -> 반올림 33,366원
    p_exec = engine.calculate_executed_price(OrderSide.BUY, Decimal("33333"))
    assert p_exec == Decimal("33366")
    
    # 33,366 * 10 = 333,660원 -> 수수료: 333,660 * 0.00015 = 50.049 -> floor 50원
    comm = engine.calculate_commission(Decimal("333660"))
    assert comm == Decimal("50")
    
    # 333,660 * 0.0018 = 600.588 -> floor 600원
    tax = engine.calculate_tax(OrderSide.SELL, Decimal("333660"))
    assert tax == Decimal("600")
    
    # Snapshot Immutability Check
    snap1 = account.get_snapshot(Decimal("70000"))
    account.deposit(Decimal("500000"))
    assert snap1.cash_balance == Decimal("1000000")
    assert account.cash_balance == Decimal("1500000")
    
    print("-> Test 4 PASSED (Precision & snapshot immutability verified)!\n")

if __name__ == "__main__":
    try:
        test_10k_ping_pong()
        test_extreme_boundary_and_rejection()
        test_random_walk_2000_steps_with_independent_audit()
        test_fractional_precision_and_immutability()
        print("🎉 ALL ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY WITH 100% INTEGRITY!")
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        sys.exit(1)
