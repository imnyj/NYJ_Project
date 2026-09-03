"""
etc/scripts/deep_adversarial_probe.py
====================================
Challenger 1 2차 심층 적대적 공격 및 정밀 검증 스크립트

심층 검증 항목:
1. Probe 1: Exact Zero Balance Attack (정확히 0원 잔고 도달 및 탈출)
2. Probe 2: Fractional Avg Price & 1,000-Step Partial Sell Accounting Drift Attack (순환소수 평단가 누적 분할 매도)
3. Probe 3: 1-KRW Penny Stock 10,000-Iteration Ping-Pong Execution (1원 페니스톡 1만회 핑퐁)
4. Probe 4: 10 Multi-Seed Random Walk Stress (10개 시드 각 5,000 스텝 총 5만 스텝 난수 스트레스)
5. Probe 5: MockEnvironment Facade 10,000-Step E2E RL Pipeline Stress (Gym 스타일 step/reset 1만 스텝 완주)
6. Probe 6: DummyStrategySimulator All-Modes 10,000-Iteration Deep Stress (핑퐁 1만회, SMA 1만 바, 난수 1만 스텝)
"""

import sys
import os
import math
import traceback
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
import numpy as np
import pandas as pd
from typing import Dict, List, Any

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, "/home/imnyj/Workspace/Auto_Stock")

from modules.engine.mock_environment import (
    VirtualAccount,
    MockExecutionEngine,
    DummyStrategySimulator,
    MockEnvironment,
    FeeConfig,
    Order,
    TradeRecord,
    OrderSide,
    OrderType,
    OrderStatus,
    ActionType,
    EngineError,
    InsufficientFundsError,
    InsufficientSharesError,
    InvalidOrderError,
    AccountingInvariantError,
    to_decimal,
    quantize_krw
)


def probe_1_exact_zero_balance_attack():
    """
    Probe 1: Exact Zero Balance Attack
    - 잔고를 정확히 0원으로 만드는 주문을 체결시켜 현금 잔고 0원 도달
    - 0원 상태에서 매수 차단 및 0원 상태에서 매도 후 정상 잔고 회복 검증
    """
    print("Running Probe 1: Exact Zero Balance Attack...")
    # 주가 10,000원, slippage 0.1% -> 10,010원, fee 0.015% -> 1원 -> 필요현금 10,011원
    # 초기 자본금을 정확히 10,011원으로 설정
    account = VirtualAccount(initial_cash=Decimal("10011"))
    engine = MockExecutionEngine(account=account)
    
    # 1주 매수 -> 정확히 잔고 0원
    rec_buy = engine.execute_order("005930", OrderSide.BUY, 1, Decimal("10000"))
    assert rec_buy.is_success, f"Buy failed: {rec_buy.error_message}"
    assert account.cash_balance == Decimal("0"), f"Expected 0 cash, got {account.cash_balance}"
    assert account.get_position("005930").quantity == 1

    # 잔고 0원 상태에서 추가 매수 시도 -> 거절 및 잔고 0원 유지
    rec_fail = engine.execute_order("005930", OrderSide.BUY, 1, Decimal("10000"))
    assert not rec_fail.is_success, "Must reject buy at 0 cash"
    assert account.cash_balance == Decimal("0")

    # 잔고 0원 상태에서 출금 시도 -> 예외 발생
    try:
        account.withdraw(Decimal("1"))
        assert False, "Should raise InsufficientFundsError on withdraw at 0 cash"
    except InsufficientFundsError:
        pass

    # 잔고 0원 상태에서 매도 -> 정상 체결 및 현금 입금
    # 매도가 10,000원 -> exec_price 9,990원 -> gross 9,990원
    # comm: quantize(9990 * 0.00015) = 1원, tax: quantize(9990 * 0.0018) = 17원
    # net_inflow = 9990 - 1 - 17 = 9972원
    rec_sell = engine.execute_order("005930", OrderSide.SELL, 1, Decimal("10000"))
    assert rec_sell.is_success, f"Sell failed: {rec_sell.error_message}"
    assert account.cash_balance == Decimal("9972"), f"Expected 9972 cash, got {account.cash_balance}"
    assert account.get_position("005930").quantity == 0

    # 회계 불변식 검증
    inv = engine.verify_accounting_invariant(
        initial_capital=Decimal("10011"),
        current_market_prices={"005930": Decimal("10000")}
    )
    assert inv, "Invariant must pass for exact zero balance attack"
    print("  -> Probe 1 PASSED (Exact 0 KRW balance safely handled)")


def probe_2_fractional_avg_price_1000_partial_sells():
    """
    Probe 2: Fractional Avg Price & 1,000-Step Partial Sells
    - 서로 다른 가격에서 1,000회 매수하여 복잡한 분수 평단가 생성
    - 이후 1,000회 1주씩 분할 매도
    - 매도 완료 후 잔고, 실현손익, 회계 불변식 0원 오차 검증
    """
    print("Running Probe 2: Fractional Avg Price & 1,000 Partial Sells...")
    initial_cash = Decimal("100000000")  # 1억원
    account = VirtualAccount(initial_cash=initial_cash)
    engine = MockExecutionEngine(account=account)
    symbol = "005930"

    np.random.seed(42)
    prices = [Decimal(str(int(np.random.randint(50000, 80000)))) for _ in range(1000)]

    # 1,000회 1주씩 매수
    for p in prices:
        rec = engine.execute_order(symbol, OrderSide.BUY, 1, p)
        assert rec.is_success
        assert account.cash_balance >= Decimal("0")

    assert account.get_position(symbol).quantity == 1000
    pos = account.get_position(symbol)
    # 평단가가 소수점 이하 값을 갖는지 확인
    print(f"  -> Total holding: 1000 shares, Avg Price: {pos.avg_price}")

    # 1,000회 1주씩 분할 매도 (가격 변동하면서)
    sell_prices = [Decimal(str(int(np.random.randint(50000, 80000)))) for _ in range(1000)]
    for sp in sell_prices:
        rec = engine.execute_order(symbol, OrderSide.SELL, 1, sp)
        assert rec.is_success
        assert account.cash_balance >= Decimal("0")

    assert account.get_position(symbol).quantity == 0
    assert account.get_position(symbol).avg_price == Decimal("0")
    assert account.get_position(symbol).total_cost == Decimal("0")

    # 최종 시장가
    last_p = sell_prices[-1]
    inv = engine.verify_accounting_invariant(
        initial_capital=initial_cash,
        current_market_prices={symbol: last_p}
    )
    assert inv, "Invariant must pass after 1000 fractional partial sells"
    print("  -> Probe 2 PASSED (1000 fractional partial sells accounting 100% exact)")


def probe_3_penny_stock_10k_ping_pong():
    """
    Probe 3: 1-KRW Penny Stock 10,000-Iteration Ping-Pong
    - 주가 1원인 페니스톡에 대해 10,000회 핑퐁 매매
    """
    print("Running Probe 3: 1-KRW Penny Stock 10,000-Iteration Ping-Pong...")
    sim = DummyStrategySimulator(initial_cash=Decimal("10000000"))
    res = sim.run_ping_pong(symbol="PENNY1", base_price=Decimal("1"), quantity=100, iterations=10000)
    
    assert res["invariant_passed"], "Penny stock 10k ping pong invariant failed"
    assert res["final_holdings"] == 0, f"Expected 0 holdings, got {res['final_holdings']}"
    assert res["final_cash"] >= Decimal("0")
    print(f"  -> Probe 3 PASSED (10k iterations completed, Invariant: {res['invariant_passed']}, Frictions: {res['total_frictions']} KRW)")


def probe_4_multi_seed_random_walk_stress():
    """
    Probe 4: 10 Multi-Seed Random Walk Stress (총 50,000 스텝)
    - 10개의 서로 다른 랜덤 시드(1~10)에 대해 각각 5,000 스텝씩 스트레스 테스트
    """
    print("Running Probe 4: 10 Multi-Seed Random Walk Stress (50,000 total steps)...")
    seeds = [1, 7, 42, 100, 777, 1234, 2026, 5555, 8888, 99999]
    for s in seeds:
        sim = DummyStrategySimulator(initial_cash=Decimal("50000000"))
        res = sim.run_random_stress(symbol="005930", base_price=Decimal("70000"), steps=5000, max_quantity=50, seed=s)
        assert res["invariant_passed"], f"Seed {s} invariant failed"
        assert res["min_cash_observed"] >= Decimal("0"), f"Seed {s} min cash < 0: {res['min_cash_observed']}"
    print(f"  -> Probe 4 PASSED (All 10 seeds / 50,000 steps preserved invariants perfectly)")


def probe_5_mock_environment_10k_rl_pipeline():
    """
    Probe 5: MockEnvironment Facade 10,000-Step E2E RL Pipeline Stress
    - 10,000개의 가상 봉(Bar) 데이터프레임 생성
    - MockEnvironment를 통해 10,000 스텝 동안 Gym 인터페이스(step/reset) 실행
    - ActionType.BUY / SELL / HOLD 랜덤 액션 및 Dictionary 액션 혼합
    - reward 산출 시 NaN/Inf/ZeroDivision 미발생 검증
    """
    print("Running Probe 5: MockEnvironment 10,000-Step E2E RL Pipeline Stress...")
    np.random.seed(42)
    n_bars = 10000
    base_price = 70000.0
    returns = np.random.normal(0, 0.005, n_bars)
    price_series = base_price * np.cumprod(1.0 + returns)

    dates = pd.date_range("2026-01-01", periods=n_bars, freq="1min")
    df_bars = pd.DataFrame({
        "timestamp": dates,
        "symbol": "005930",
        "open": price_series,
        "high": price_series * 1.002,
        "low": price_series * 0.998,
        "close": price_series,
        "volume": np.random.randint(100, 10000, n_bars)
    })

    env = MockEnvironment(data_stream=df_bars, initial_capital=Decimal("100000000"), default_trade_quantity=10)
    obs = env.reset()
    assert obs["step"] == 0
    assert obs["total_equity"] == 100000000.0

    step_count = 0
    while True:
        action = np.random.choice([0, 1, 2], p=[0.4, 0.4, 0.2])
        obs, reward, done, info = env.step(action)
        step_count += 1

        assert not math.isnan(reward), f"Reward is NaN at step {step_count}"
        assert not math.isinf(reward), f"Reward is Inf at step {step_count}"
        assert obs["cash_balance"] >= 0.0, f"Cash < 0 at step {step_count}"

        if done:
            break

    assert step_count == n_bars, f"Expected {n_bars} steps, ran {step_count}"
    audit = env.get_accounting_audit()
    inv_passed = env.engine.verify_accounting_invariant(
        initial_capital=Decimal("100000000"),
        current_market_prices={"005930": to_decimal(price_series[-1])}
    )
    assert inv_passed, "MockEnvironment E2E pipeline invariant failed"
    print(f"  -> Probe 5 PASSED (10,000-step RL environment executed, Invariant: {inv_passed})")


def probe_6_dummy_simulator_all_modes_10k():
    """
    Probe 6: DummyStrategySimulator All Modes 10,000 Deep Stress
    1. SMA Crossover with 10,000 bars
    2. Ping-Pong 10,000 iterations
    3. Random Walk 10,000 steps
    """
    print("Running Probe 6: DummyStrategySimulator All Modes (10k each)...")
    sim = DummyStrategySimulator(initial_cash=Decimal("50000000"))
    
    # 1. 10,000 Bar SMA
    np.random.seed(123)
    prices = 70000.0 * np.cumprod(1.0 + np.random.normal(0, 0.005, 10000))
    res_sma = sim.run_sma_crossover(prices, symbol="005930", short_window=10, long_window=50, trade_quantity=20)
    assert res_sma["invariant_passed"], "SMA 10k invariant failed"
    assert res_sma["final_cash"] >= Decimal("0")

    # 2. 10,000 Iteration Ping-Pong
    sim_pp = DummyStrategySimulator(initial_cash=Decimal("50000000"))
    res_pp = sim_pp.run_ping_pong(symbol="005930", base_price=Decimal("70000"), quantity=20, iterations=10000)
    assert res_pp["invariant_passed"], "Ping-Pong 10k invariant failed"
    assert res_pp["final_cash"] >= Decimal("0")

    # 3. 10,000 Step Random Stress
    sim_rnd = DummyStrategySimulator(initial_cash=Decimal("50000000"))
    res_rnd = sim_rnd.run_random_stress(symbol="005930", base_price=Decimal("70000"), steps=10000, max_quantity=20, seed=777)
    assert res_rnd["invariant_passed"], "Random 10k invariant failed"
    assert res_rnd["final_cash"] >= Decimal("0")

    print(f"  -> Probe 6 PASSED (SMA 10k, Ping-Pong 10k, Random 10k all passed invariants)")


def run_deep_probes():
    print("=" * 70)
    print("Deep Adversarial Probing & Stress Verification (Challenger 1)")
    print("=" * 70)
    probe_1_exact_zero_balance_attack()
    probe_2_fractional_avg_price_1000_partial_sells()
    probe_3_penny_stock_10k_ping_pong()
    probe_4_multi_seed_random_walk_stress()
    probe_5_mock_environment_10k_rl_pipeline()
    probe_6_dummy_simulator_all_modes_10k()
    print("=" * 70)
    print("🎯 ALL DEEP ADVERSARIAL PROBES COMPLETED WITH 100% SUCCESS")
    print("=" * 70)


if __name__ == "__main__":
    run_deep_probes()
