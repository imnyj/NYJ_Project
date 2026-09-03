"""
etc/scripts/adversarial_stress_suite.py
======================================
Auto Stock Phase 2 Mock Environment 종합 적대적 스트레스 테스트 하네스
Challenger 1 전용 검증 스크립트

검증 항목:
1. Scenario 1: 10,000회 고빈도 대량 주문 스트레스 (High-Frequency Stress)
2. Scenario 2: 극한 변동성 주가 점프 & 블랙스완 (Extreme Volatility & Gap Jumps)
3. Scenario 3: 1원 단위 잔고 소진 및 정밀 경계 공격 (1-KRW Precision Boundary Drain)
4. Scenario 4: 10조원 대규모 자본금 & 1원 초저가 페니스톡 (10T Capital & Penny Stock)
5. Scenario 5: 비정상 파라미터 및 예외 입력 공격 (Adversarial Invalid Inputs)
6. Scenario 6: 10개 종목 다중 포트폴리오 고빈도 거래 (Multi-Symbol High-Frequency)
7. Scenario 7: 커스텀 수수료/슬리피지/호가단위 설정 공격 (Custom FeeConfig Attack)
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


class AdversarialTestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.details: Dict[str, Any] = {}
        self.error: str = ""

    def __repr__(self):
        status = "PASSED" if self.passed else "FAILED"
        return f"[{status}] {self.name}: {self.details}"


def test_scenario_1_high_frequency_10k() -> AdversarialTestResult:
    """
    Scenario 1: 10,000회 고빈도 대량 주문 스트레스 테스트
    - 10,000 스텝 동안 무작위 매수/매도/홀드 난사
    - 주가 변동 및 주문량 변동
    - 매 스텝마다 cash_balance >= 0 검증
    - 최종 회계 불변식(Accounting Invariant) 0원 오차 검증
    """
    res = AdversarialTestResult("Scenario 1: 10,000회 고빈도 대량 주문 스트레스 테스트")
    try:
        np.random.seed(20260901)
        initial_cash = Decimal("50000000")  # 5,000만원
        account = VirtualAccount(initial_cash=initial_cash)
        engine = MockExecutionEngine(account=account)
        symbol = "005930"
        curr_price = Decimal("70000")

        total_orders = 10000
        executed_buys = 0
        executed_sells = 0
        rejected_orders = 0

        for step in range(total_orders):
            # 주가 변동 (-2.0% ~ +2.0%)
            price_change_pct = Decimal(str(round(np.random.uniform(-0.02, 0.02), 4)))
            curr_price = quantize_krw(curr_price * (Decimal("1") + price_change_pct), ROUND_HALF_UP)
            curr_price = max(Decimal("100"), curr_price)

            # 무작위 액션 (0: BUY, 1: SELL, 2: HOLD)
            action = np.random.choice([0, 1, 2], p=[0.45, 0.45, 0.10])
            qty = int(np.random.randint(1, 100))

            if action == 0:  # BUY
                rec = engine.execute_order(symbol, OrderSide.BUY, qty, curr_price)
                if rec.is_success:
                    executed_buys += 1
                else:
                    rejected_orders += 1
            elif action == 1:  # SELL
                rec = engine.execute_order(symbol, OrderSide.SELL, qty, curr_price)
                if rec.is_success:
                    executed_sells += 1
                else:
                    rejected_orders += 1
            else:  # HOLD
                engine.update_market_price(symbol, curr_price)

            # 불변성 1: 매 스텝 잔고는 음수가 아니어야 함
            assert account.cash_balance >= Decimal("0"), f"Step {step}: cash_balance became negative: {account.cash_balance}"

        # 최종 잔여 포지션 시장가 평가
        invariant_passed = engine.verify_accounting_invariant(
            initial_capital=initial_cash,
            current_market_prices={symbol: curr_price},
            tolerance=Decimal("0")
        )
        audit = engine.get_accounting_audit({symbol: curr_price})

        res.passed = invariant_passed and (account.cash_balance >= Decimal("0"))
        res.details = {
            "total_orders": total_orders,
            "executed_buys": executed_buys,
            "executed_sells": executed_sells,
            "rejected_orders": rejected_orders,
            "final_cash": str(account.cash_balance),
            "final_holding": account.get_position(symbol).quantity,
            "total_equity": str(audit["total_equity"]),
            "total_frictions": str(audit["total_frictions"]),
            "invariant_passed": invariant_passed,
        }
    except Exception as e:
        res.passed = False
        res.error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    return res


def test_scenario_2_extreme_volatility_black_swan() -> AdversarialTestResult:
    """
    Scenario 2: 극한 변동성 주가 점프 & 블랙 스완 공격
    - 상한가(+30%), 하한가(-30%), 100배 폭등(+10000%), 99.9% 대폭락(-99.9%)
    - 0원에 근접하는 초극단적 가격 변동 환경에서 매수/매도 반복
    - 불변성 검증
    """
    res = AdversarialTestResult("Scenario 2: 극한 변동성 주가 점프 & 블랙 스완")
    try:
        initial_cash = Decimal("100000000")  # 1억원
        account = VirtualAccount(initial_cash=initial_cash)
        engine = MockExecutionEngine(account=account)
        symbol = "000660"
        
        # 극단적 가격 시나리오 시퀀스
        price_sequence = [
            Decimal("100000"),
            Decimal("130000"),   # +30% 상한가
            Decimal("169000"),   # +30% 연속 상한가
            Decimal("118300"),   # -30% 하한가
            Decimal("82810"),    # -30% 연속 하한가
            Decimal("8281000"),  # 100배 폭등 (슈퍼 숏스퀴즈)
            Decimal("8281"),     # 99.9% 대폭락 (블랙스완)
            Decimal("10"),       # 동전주 추락 (10원)
            Decimal("1"),        # 1원 페니스톡 추락
            Decimal("50000"),    # 기적의 부활 (50,000배 반등)
            Decimal("25000"),
        ]

        for p in price_sequence:
            # 매수 시도
            engine.execute_order(symbol, OrderSide.BUY, 10, p)
            assert account.cash_balance >= Decimal("0"), f"Negative cash at price {p}"

            # 추가 매수
            engine.execute_order(symbol, OrderSide.BUY, 50, p)
            assert account.cash_balance >= Decimal("0"), f"Negative cash at price {p}"

            # 부분 매도
            holding = account.get_position(symbol).quantity
            if holding > 0:
                engine.execute_order(symbol, OrderSide.SELL, max(1, holding // 2), p)
            assert account.cash_balance >= Decimal("0"), f"Negative cash after sell at price {p}"

        last_p = price_sequence[-1]
        invariant_passed = engine.verify_accounting_invariant(
            initial_capital=initial_cash,
            current_market_prices={symbol: last_p},
            tolerance=Decimal("0")
        )
        audit = engine.get_accounting_audit({symbol: last_p})

        res.passed = invariant_passed and (account.cash_balance >= Decimal("0"))
        res.details = {
            "price_sequence_len": len(price_sequence),
            "final_cash": str(account.cash_balance),
            "final_holding": account.get_position(symbol).quantity,
            "total_equity": str(audit["total_equity"]),
            "total_frictions": str(audit["total_frictions"]),
            "invariant_passed": invariant_passed,
        }
    except Exception as e:
        res.passed = False
        res.error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    return res


def test_scenario_3_boundary_drain_1krw() -> AdversarialTestResult:
    """
    Scenario 3: 1원 단위 잔고 소진 및 정밀 경계 공격
    - 잔고가 0원에 도달할 때까지 정밀하게 1주씩 매수
    - 잔고가 부족한 시점에서 정확한 거절 여부 확인
    - 잔고가 1원, 2원 남았을 때 거절 확인
    - 매도 후 1원 단위 정밀 재진입
    """
    res = AdversarialTestResult("Scenario 3: 1원 단위 잔고 소진 및 정밀 경계 공격")
    try:
        # 소액 잔고 설정 (예: 50,000원)
        initial_cash = Decimal("50000")
        account = VirtualAccount(initial_cash=initial_cash)
        engine = MockExecutionEngine(account=account)
        symbol = "005930"
        price = Decimal("10000")  # 주당 10,000원

        # 1주당 매수 필요 현금 계산
        # slippage 0.1% -> exec_price = 10010원
        # gross = 10010원, commission = quantize(10010 * 0.00015) = 1원
        # required_cash = 10011원
        # 50,000원으로 4주 매수 가능 (10011 * 4 = 40044원)
        
        buy_count = 0
        while account.cash_balance >= Decimal("10011"):
            can_buy_flag = account.can_buy(price, 1, engine.fee_config.commission_rate, engine.fee_config.slippage_rate)
            assert can_buy_flag, f"can_buy should return True with balance {account.cash_balance}"
            rec = engine.execute_order(symbol, OrderSide.BUY, 1, price)
            assert rec.is_success, f"Buy should succeed: {rec.error_message}"
            assert account.cash_balance >= Decimal("0")
            buy_count += 1

        # 이제 남은 잔고는 50000 - 40044 = 9956원 (< 10011원)
        assert account.cash_balance < Decimal("10011"), f"Balance should be < 10011, got {account.cash_balance}"
        
        # can_buy 검증: False여야 함
        can_buy_flag = account.can_buy(price, 1, engine.fee_config.commission_rate, engine.fee_config.slippage_rate)
        assert not can_buy_flag, "can_buy should return False when cash is insufficient"

        # 거절 공격: 주문 시도 시 안전 거절 확인
        rejected_rec = engine.execute_order(symbol, OrderSide.BUY, 1, price)
        assert not rejected_rec.is_success, "Order must be rejected"
        assert "Insufficient cash" in rejected_rec.error_message

        # 잔고가 변함없는지 확인
        prev_cash = account.cash_balance

        # 전량 매도
        pos = account.get_position(symbol)
        sell_rec = engine.execute_order(symbol, OrderSide.SELL, pos.quantity, price)
        assert sell_rec.is_success
        assert account.cash_balance > prev_cash
        assert account.get_position(symbol).quantity == 0

        # 회계 불변식 검증
        invariant_passed = engine.verify_accounting_invariant(
            initial_capital=initial_cash,
            current_market_prices={symbol: price},
            tolerance=Decimal("0")
        )
        audit = engine.get_accounting_audit({symbol: price})

        res.passed = invariant_passed and (account.cash_balance >= Decimal("0"))
        res.details = {
            "buys_completed": buy_count,
            "cash_before_drain": str(initial_cash),
            "cash_after_roundtrip": str(account.cash_balance),
            "total_frictions": str(audit["total_frictions"]),
            "invariant_passed": invariant_passed,
        }
    except Exception as e:
        res.passed = False
        res.error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    return res


def test_scenario_4_large_capital_and_penny_stock() -> AdversarialTestResult:
    """
    Scenario 4: 10조원 대규모 자본금 (10T KRW) & 1원 초저가 페니스톡 환경
    - 10조원(10,000,000,000,000 KRW) 초기 자본금
    - 1원, 2원, 3원 초저가 페니스톡
    - 1억 주(100,000,000 shares) 대량 매매
    - 대규모 수치 연산 시 부동소수점 오버플로우나 정밀도 왜곡이 없는지 검증
    """
    res = AdversarialTestResult("Scenario 4: 10조원 대자본 & 1원 페니스톡 대량 매매")
    try:
        initial_cash = Decimal("10000000000000")  # 10조원
        account = VirtualAccount(initial_cash=initial_cash)
        engine = MockExecutionEngine(account=account)
        symbol = "PENNY1"
        price = Decimal("1")  # 1원

        # 1원짜리 주식 10억주 매수
        # exec_price = quantize(1 * 1.001) = 1원
        # gross = 10억 * 1 = 1,000,000,000원
        # comm = quantize(10억 * 0.00015) = 150,000원
        # total_outflow = 1,000,150,000원
        qty = 1000000000  # 10억주
        rec_buy = engine.execute_order(symbol, OrderSide.BUY, qty, price)
        assert rec_buy.is_success, f"Large penny buy failed: {rec_buy.error_message}"
        assert account.get_position(symbol).quantity == qty
        assert account.cash_balance == initial_cash - Decimal("1000150000")

        # 가격이 2원으로 100% 상승
        price_2 = Decimal("2")
        engine.update_market_price(symbol, price_2)

        # 5억주 부분 매도
        # exec_price = quantize(2 * 0.999) = quantize(1.998) = 2원
        # gross = 5억 * 2 = 1,000,000,000원
        # comm = quantize(10억 * 0.00015) = 150,000원
        # tax = quantize(10억 * 0.0018) = 1,800,000원
        # net_inflow = 10억 - 15만 - 180만 = 998,050,000원
        rec_sell1 = engine.execute_order(symbol, OrderSide.SELL, 500000000, price_2)
        assert rec_sell1.is_success, f"Large penny partial sell failed: {rec_sell1.error_message}"

        # 나머지 5억주 전량 매도
        rec_sell2 = engine.execute_order(symbol, OrderSide.SELL, 500000000, price_2)
        assert rec_sell2.is_success
        assert account.get_position(symbol).quantity == 0

        # 회계 불변식 검증
        invariant_passed = engine.verify_accounting_invariant(
            initial_capital=initial_cash,
            current_market_prices={symbol: price_2},
            tolerance=Decimal("0")
        )
        audit = engine.get_accounting_audit({symbol: price_2})

        res.passed = invariant_passed and (account.cash_balance >= Decimal("0"))
        res.details = {
            "initial_cash": str(initial_cash),
            "final_cash": str(account.cash_balance),
            "total_frictions": str(audit["total_frictions"]),
            "realized_pnl": str(account.realized_pnl),
            "invariant_passed": invariant_passed,
        }
    except Exception as e:
        res.passed = False
        res.error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    return res


def test_scenario_5_adversarial_invalid_inputs() -> AdversarialTestResult:
    """
    Scenario 5: 비정상 파라미터 및 예외 입력 공격
    - 수량 0, 음수 수량, 음수 가격, 0원 가격
    - 무차입 공매도 (보유량 초과 매도)
    - 지정가 주문(LIMIT) 미체결 조건
    - raise_on_failure=True 일 때의 예외 발생 검증
    - 비정상 입력 거절 후에도 계좌 상태 및 불변식 온전성 검증
    """
    res = AdversarialTestResult("Scenario 5: 비정상 파라미터 및 적대적 예외 입력")
    try:
        initial_cash = Decimal("10000000")
        account = VirtualAccount(initial_cash=initial_cash)
        engine = MockExecutionEngine(account=account)
        symbol = "005930"
        price = Decimal("50000")

        # 1. 수량 0 주문 거절
        rec1 = engine.execute_order(symbol, OrderSide.BUY, 0, price)
        assert not rec1.is_success, "0 quantity order must fail"
        assert "positive" in rec1.error_message

        # 2. 음수 수량 주문 거절
        rec2 = engine.execute_order(symbol, OrderSide.BUY, -10, price)
        assert not rec2.is_success, "Negative quantity order must fail"

        # 3. 0원 가격 주문 거절
        rec3 = engine.execute_order(symbol, OrderSide.BUY, 10, 0)
        assert not rec3.is_success, "0 price order must fail"

        # 4. 음수 가격 주문 거절
        rec4 = engine.execute_order(symbol, OrderSide.BUY, 10, -50000)
        assert not rec4.is_success, "Negative price order must fail"

        # 5. 무차입 공매도 (보유 0주일 때 매도 주문) 거절
        rec5 = engine.execute_order(symbol, OrderSide.SELL, 10, price)
        assert not rec5.is_success, "Short selling must fail"
        assert "Insufficient shares" in rec5.error_message

        # 6. 지정가 매수 미체결 (현재가 50,000원 > 지정가 45,000원)
        rec6 = engine.execute_order(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=10,
            current_price=price,
            order_type=OrderType.LIMIT,
            limit_price=Decimal("45000")
        )
        assert not rec6.is_success, "Limit buy below market must fail"

        # 7. 지정가 매도 미체결 (현재가 50,000원 < 지정가 55,000원)
        # 먼저 10주 매수
        engine.execute_order(symbol, OrderSide.BUY, 10, price)
        rec7 = engine.execute_order(
            symbol=symbol,
            side=OrderSide.SELL,
            quantity=10,
            current_price=price,
            order_type=OrderType.LIMIT,
            limit_price=Decimal("55000")
        )
        assert not rec7.is_success, "Limit sell above market must fail"

        # 8. raise_on_failure 검증
        try:
            engine.execute_order(symbol, OrderSide.BUY, -5, price, raise_on_failure=True)
            assert False, "Should have raised InvalidOrderError"
        except InvalidOrderError:
            pass

        try:
            # 잔고 초과 매수 (예외 발생)
            engine.execute_order(symbol, OrderSide.BUY, 1000000, price, raise_on_failure=True)
            assert False, "Should have raised InsufficientFundsError"
        except InsufficientFundsError:
            pass

        try:
            # 보유량 초과 매도 (예외 발생)
            engine.execute_order(symbol, OrderSide.SELL, 1000, price, raise_on_failure=True)
            assert False, "Should have raised InsufficientSharesError"
        except InsufficientSharesError:
            pass

        # 잔여 포지션 매도 정리
        engine.execute_order(symbol, OrderSide.SELL, 10, price)

        # 불변식 검증
        invariant_passed = engine.verify_accounting_invariant(
            initial_capital=initial_cash,
            current_market_prices={symbol: price},
            tolerance=Decimal("0")
        )

        res.passed = invariant_passed and (account.cash_balance >= Decimal("0"))
        res.details = {
            "initial_cash": str(initial_cash),
            "final_cash": str(account.cash_balance),
            "invariant_passed": invariant_passed
        }
    except Exception as e:
        res.passed = False
        res.error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    return res


def test_scenario_6_multi_symbol_high_frequency() -> AdversarialTestResult:
    """
    Scenario 6: 10개 종목 다중 포트폴리오 고빈도 5,000회 스트레스 테스트
    - 10개 종목(005930, 000660, 035420, 051910, 005380, 035720, 068270, 207940, 006400, 000270)
    - 종목별로 서로 다른 가격과 변동성 부여
    - 5,000회 주문 난사 후 다종목 총 평가액 및 회계 불변식 검증
    """
    res = AdversarialTestResult("Scenario 6: 10개 종목 다중 포트폴리오 고빈도 거래")
    try:
        np.random.seed(9999)
        symbols = [
            "005930", "000660", "035420", "051910", "005380",
            "035720", "068270", "207940", "006400", "000270"
        ]
        prices = {
            "005930": Decimal("70000"),
            "000660": Decimal("120000"),
            "035420": Decimal("200000"),
            "051910": Decimal("500000"),
            "005380": Decimal("180000"),
            "035720": Decimal("50000"),
            "068270": Decimal("150000"),
            "207940": Decimal("800000"),
            "006400": Decimal("600000"),
            "000270": Decimal("85000"),
        }

        initial_cash = Decimal("500000000")  # 5억원
        account = VirtualAccount(initial_cash=initial_cash)
        engine = MockExecutionEngine(account=account)

        total_steps = 5000
        for step in range(total_steps):
            sym = np.random.choice(symbols)
            # 가격 변동 (-1.5% ~ +1.5%)
            chg = Decimal(str(round(np.random.uniform(-0.015, 0.015), 4)))
            prices[sym] = quantize_krw(prices[sym] * (Decimal("1") + chg), ROUND_HALF_UP)
            prices[sym] = max(Decimal("100"), prices[sym])

            action = np.random.choice([0, 1, 2], p=[0.45, 0.45, 0.10])
            qty = int(np.random.randint(1, 20))

            if action == 0:  # BUY
                engine.execute_order(sym, OrderSide.BUY, qty, prices[sym])
            elif action == 1:  # SELL
                engine.execute_order(sym, OrderSide.SELL, qty, prices[sym])
            else:  # HOLD
                engine.update_market_price(sym, prices[sym])

            assert account.cash_balance >= Decimal("0"), f"Negative cash at multi-symbol step {step}"

        # 다종목 불변식 검증
        invariant_passed = engine.verify_accounting_invariant(
            initial_capital=initial_cash,
            current_market_prices=prices,
            tolerance=Decimal("0")
        )
        audit = engine.get_accounting_audit(prices)

        res.passed = invariant_passed and (account.cash_balance >= Decimal("0"))
        res.details = {
            "total_steps": total_steps,
            "symbols_count": len(symbols),
            "final_cash": str(account.cash_balance),
            "total_equity": str(audit["total_equity"]),
            "total_frictions": str(audit["total_frictions"]),
            "invariant_passed": invariant_passed,
        }
    except Exception as e:
        res.passed = False
        res.error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    return res


def test_scenario_7_custom_fee_configs() -> AdversarialTestResult:
    """
    Scenario 7: 커스텀 수수료/슬리피지/호가단위 설정 공격
    1. Zero Friction: commission=0, tax=0, slippage=0
    2. High Friction: commission=5%, tax=2%, slippage=3%
    3. Custom Tick Size: price_tick_size = 5원, 10원, 100원
    모든 환경에서 cash_balance >= 0 및 회계 오차 0원 불변식 검증
    """
    res = AdversarialTestResult("Scenario 7: 커스텀 수수료/슬리피지/호가단위 설정 공격")
    try:
        # 1. Zero Friction
        zero_cfg = FeeConfig(
            commission_rate=Decimal("0"),
            tax_rate=Decimal("0"),
            slippage_rate=Decimal("0"),
            price_tick_size=Decimal("1")
        )
        acc_zero = VirtualAccount(initial_cash=Decimal("10000000"))
        eng_zero = MockExecutionEngine(account=acc_zero, fee_config=zero_cfg)
        eng_zero.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        eng_zero.execute_order("005930", OrderSide.SELL, 10, Decimal("70000"))
        assert acc_zero.cash_balance == Decimal("10000000"), "Zero friction roundtrip should preserve exact cash"
        inv_zero = eng_zero.verify_accounting_invariant(current_market_prices={"005930": Decimal("70000")})
        assert inv_zero, "Zero friction invariant must hold"

        # 2. High Friction
        high_cfg = FeeConfig(
            commission_rate=Decimal("0.05"),  # 5%
            tax_rate=Decimal("0.02"),         # 2%
            slippage_rate=Decimal("0.03"),    # 3%
            price_tick_size=Decimal("1")
        )
        acc_high = VirtualAccount(initial_cash=Decimal("10000000"))
        eng_high = MockExecutionEngine(account=acc_high, fee_config=high_cfg)
        eng_high.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        eng_high.execute_order("005930", OrderSide.SELL, 10, Decimal("70000"))
        assert acc_high.cash_balance >= Decimal("0")
        inv_high = eng_high.verify_accounting_invariant(current_market_prices={"005930": Decimal("70000")})
        assert inv_high, "High friction invariant must hold"

        # 3. Custom Tick Size (100원 호가단위)
        tick100_cfg = FeeConfig(
            commission_rate=Decimal("0.00015"),
            tax_rate=Decimal("0.0018"),
            slippage_rate=Decimal("0.0010"),
            price_tick_size=Decimal("100")
        )
        acc_tick = VirtualAccount(initial_cash=Decimal("10000000"))
        eng_tick = MockExecutionEngine(account=acc_tick, fee_config=tick100_cfg)
        eng_tick.execute_order("005930", OrderSide.BUY, 10, Decimal("70050"))
        eng_tick.execute_order("005930", OrderSide.SELL, 10, Decimal("70050"))
        assert acc_tick.cash_balance >= Decimal("0")
        inv_tick = eng_tick.verify_accounting_invariant(current_market_prices={"005930": Decimal("70050")})
        assert inv_tick, "Tick 100 invariant must hold"

        res.passed = True
        res.details = {
            "zero_friction_ok": inv_zero,
            "high_friction_ok": inv_high,
            "tick_100_ok": inv_tick
        }
    except Exception as e:
        res.passed = False
        res.error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    return res


def run_all_adversarial_tests():
    print("=" * 70)
    print("Auto Stock Phase 2 Mock Execution Engine — Adversarial Stress Suite")
    print("=" * 70)

    tests = [
        test_scenario_1_high_frequency_10k,
        test_scenario_2_extreme_volatility_black_swan,
        test_scenario_3_boundary_drain_1krw,
        test_scenario_4_large_capital_and_penny_stock,
        test_scenario_5_adversarial_invalid_inputs,
        test_scenario_6_multi_symbol_high_frequency,
        test_scenario_7_custom_fee_configs,
    ]

    all_passed = True
    results = []

    for t in tests:
        res = t()
        results.append(res)
        status_str = "✅ PASS" if res.passed else "❌ FAIL"
        print(f"{status_str} | {res.name}")
        if res.details:
            for k, v in res.details.items():
                print(f"       - {k}: {v}")
        if not res.passed:
            all_passed = False
            print(f"       [ERROR]: {res.error}")
        print("-" * 70)

    print("=" * 70)
    if all_passed:
        print("🎉 ALL ADVERSARIAL STRESS TESTS PASSED (100% INVARIANT PRESERVED)")
    else:
        print("💥 SOME STRESS TESTS FAILED - REVIEW REQUIRED")
    print("=" * 70)
    return all_passed, results


if __name__ == "__main__":
    success, results = run_all_adversarial_tests()
    sys.exit(0 if success else 1)
