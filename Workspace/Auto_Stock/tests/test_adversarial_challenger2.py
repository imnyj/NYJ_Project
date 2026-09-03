"""
tests/test_adversarial_challenger2.py
=====================================
Phase 2 제2 적대적 챌린저(Challenger 2) 전용 코너 케이스 및 상태 변이 취약점 공격 테스트 스위트

검증 영역:
1. 부동소수점 누출(Float Leakage) 공격 & Decimal 순수성 보장
2. 다종목 교차 매매(Multi-Symbol Cross Trading) & 포지션 완전 격리
3. 연속 부분 체결/취소/거절 연쇄(Cascading Rejections) 및 에러 복원력
4. 파산 경계 해머링 및 0원 잔고 방어
5. 10,000회 초고빈도 스트레스 및 회계 불변식(Accounting Invariant) 0원 오차 무결성
"""

import math
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
import numpy as np
import pandas as pd
import pytest

from modules.engine import (
    OrderSide,
    OrderType,
    OrderStatus,
    ActionType,
    FeeConfig,
    Position,
    Order,
    TradeRecord,
    AccountSnapshot,
    VirtualAccount,
    MockExecutionEngine,
    DummyStrategySimulator,
    MockEnvironment,
    to_decimal,
    quantize_krw,
    InsufficientFundsError,
    InsufficientSharesError,
    InvalidOrderError,
    AccountingInvariantError
)


class TestFloatLeakageAndDecimalPurity:
    """부동소수점 누출 방어 및 내부 상태 Decimal 순수성 검증"""

    @pytest.mark.parametrize("val_type, init_cash, price, qty, comm", [
        ("float", 10000000.0, 70000.0, 10, 105.0),
        ("int", 10000000, 70000, 10, 105),
        ("str", "10000000", "70000", 10, "105"),
        ("np.float64", np.float64(10000000.0), np.float64(70000.0), np.int64(10), np.float64(105.0)),
        ("np.float32", np.float32(10000000.0), np.float32(70000.0), np.int32(10), np.float32(105.0)),
        ("Decimal", Decimal("10000000"), Decimal("70000"), 10, Decimal("105")),
    ])
    def test_virtual_account_type_purity_across_types(self, val_type, init_cash, price, qty, comm):
        """다양한 타입 유입 시 VirtualAccount 내부 필드가 100% Decimal로 유지됨을 검증"""
        acc = VirtualAccount(initial_cash=init_cash)
        assert type(acc.cash_balance) is Decimal
        assert type(acc.initial_cash) is Decimal

        # 입출금
        acc.deposit(price)
        assert type(acc.cash_balance) is Decimal
        acc.withdraw(price)
        assert type(acc.cash_balance) is Decimal

        # 매수 적용
        acc.apply_buy("005930", price, qty, comm)
        pos = acc.get_position("005930")
        assert type(acc.cash_balance) is Decimal
        assert type(pos.avg_price) is Decimal
        assert type(pos.total_cost) is Decimal
        assert type(acc.cumulative_commission) is Decimal

        # 매도 적용
        acc.apply_sell("005930", price, qty, comm, Decimal("126"))
        assert type(acc.cash_balance) is Decimal
        assert type(acc.realized_pnl) is Decimal
        assert type(acc.cumulative_tax) is Decimal

    def test_mock_engine_trade_record_decimal_purity(self):
        """MockExecutionEngine 체결 기록(TradeRecord)의 모든 금액 필드가 Decimal임을 검증"""
        eng = MockExecutionEngine()
        rec_b = eng.execute_order("005930", "BUY", 10, 70000.0)
        assert rec_b.is_success
        assert type(rec_b.executed_price) is Decimal
        assert type(rec_b.gross_amount) is Decimal
        assert type(rec_b.commission) is Decimal
        assert type(rec_b.tax) is Decimal
        assert type(rec_b.slippage_cost) is Decimal
        assert type(rec_b.net_cash_flow) is Decimal
        assert type(rec_b.cash_after) is Decimal
        assert type(rec_b.avg_price_after) is Decimal

    def test_ieee754_epsilon_torture_5000_trades(self):
        """0.1 + 0.2 등 IEEE 754 부동소수점 엡실론 오차 주가 유입 시 1원 단위 정밀도 유지 및 0원 오차 검증"""
        acc = VirtualAccount(initial_cash=Decimal("50000000"))
        eng = MockExecutionEngine(account=acc)
        base_eps = 0.1 + 0.2  # 0.30000000000000004

        for i in range(2500):
            p = float(70000.0 + (i % 5) * 50.0 + base_eps)
            rec_b = eng.execute_order("EPS", "BUY", 2, p)
            assert rec_b.is_success
            assert rec_b.executed_price % Decimal("1") == Decimal("0")

            rec_s = eng.execute_order("EPS", "SELL", 2, p)
            assert rec_s.is_success
            assert rec_s.executed_price % Decimal("1") == Decimal("0")

        # 잔고가 정확히 1원 단위(소수점 이하 0) 유지
        assert acc.cash_balance % Decimal("1") == Decimal("0")
        # 체결 순현금흐름 합계 == 잔고 변화량
        sum_net_flows = sum(t.net_cash_flow for t in eng.trade_history if t.is_success)
        assert acc.cash_balance - Decimal("50000000") == sum_net_flows


class TestMultiSymbolCrossTradingAndIsolation:
    """다종목 동시 교차 매매 및 포지션 완전 격리 검증"""

    def test_10_symbols_concurrent_interleaved_trading(self):
        """10개 대표 종목에 대해 5,000회 무작위 교차 매수/매도 시 포지션 격리 및 불변식 검증"""
        symbols = ["005930", "000660", "005380", "035420", "035720", "051910", "068270", "005490", "000270", "105560"]
        base_prices = {
            "005930": Decimal("70000"), "000660": Decimal("160000"), "005380": Decimal("220000"),
            "035420": Decimal("180000"), "035720": Decimal("45000"), "051910": Decimal("350000"),
            "068270": Decimal("190000"), "005490": Decimal("380000"), "000270": Decimal("110000"),
            "105560": Decimal("85000")
        }

        initial_cash = Decimal("300000000")
        acc = VirtualAccount(initial_cash=initial_cash)
        eng = MockExecutionEngine(account=acc)

        np.random.seed(42)
        curr_prices = dict(base_prices)

        for _ in range(5000):
            sym = np.random.choice(symbols)
            ret = Decimal(str(round(float(np.random.normal(0, 0.005)), 6)))
            p_new = quantize_krw(curr_prices[sym] * (Decimal("1") + ret), rounding=ROUND_HALF_UP)
            p_new = max(Decimal("1000"), p_new)
            curr_prices[sym] = p_new

            pos = acc.get_position(sym)
            if np.random.rand() > 0.5:
                # Buy
                qty = int(np.random.randint(1, 5))
                eng.execute_order(sym, OrderSide.BUY, qty, p_new)
            else:
                # Sell
                if pos.quantity > 0:
                    qty = int(np.random.randint(1, min(pos.quantity + 1, 5)))
                    eng.execute_order(sym, OrderSide.SELL, qty, p_new)

            assert acc.cash_balance >= Decimal("0")

        # Verify strict isolation
        for sym in symbols:
            pos = acc.get_position(sym)
            assert pos.quantity >= 0
            if pos.quantity == 0:
                assert pos.avg_price == Decimal("0")
                assert pos.total_cost == Decimal("0")
            else:
                cost_diff = abs(pos.total_cost - pos.avg_price * Decimal(pos.quantity))
                assert cost_diff < Decimal("0.0001")

    def test_partial_price_dictionary_resilience(self):
        """get_total_equity에 부분 딕셔너리, 빈 딕셔너리, None, 미보유 종목 유입 시 정상 fallback 검증"""
        acc = VirtualAccount(initial_cash=Decimal("10000000"))
        acc.apply_buy("SYM1", Decimal("10000"), 10, Decimal("0"))
        acc.apply_buy("SYM2", Decimal("20000"), 10, Decimal("0"))

        assert acc.get_total_equity({}) == acc.cash_balance + Decimal("300000")
        assert acc.get_total_equity(None) == acc.cash_balance + Decimal("300000")
        assert acc.get_total_equity({"SYM1": Decimal("15000")}) == acc.cash_balance + Decimal("150000") + Decimal("200000")
        assert acc.get_total_equity({"UNKNOWN": Decimal("99999")}) == acc.cash_balance + Decimal("300000")


class TestCascadingRejectionsAndResilience:
    """연속 거절 연쇄 및 파산 경계 해머링 검증"""

    def test_5000_consecutive_rejections_zero_mutation(self):
        """5,000회 연속 거절 주문 난사 시 계좌 잔고 및 누적 비용이 0원도 변형되지 않음을 검증"""
        initial_cash = Decimal("10000000")
        acc = VirtualAccount(initial_cash=initial_cash)
        eng = MockExecutionEngine(account=acc)

        for _ in range(2500):
            # Over-budget buy
            eng.execute_order("005930", OrderSide.BUY, 1000000, Decimal("70000"))
            # Unheld sell
            eng.execute_order("005930", OrderSide.SELL, 10, Decimal("70000"))

        assert acc.cash_balance == initial_cash
        assert acc.cumulative_commission == Decimal("0")
        assert acc.cumulative_tax == Decimal("0")
        assert acc.cumulative_slippage == Decimal("0")
        assert acc.realized_pnl == Decimal("0")
        assert len(eng.trade_history) == 5000
        assert all(not t.is_success for t in eng.trade_history)

    def test_bankruptcy_boundary_hammering_zero_negative_cash(self):
        """잔고를 1주 매수 가능 금액으로 설정 후 0원 소진 및 1,000회 매수 공격 시 음수 잔고 0건 검증"""
        # Exactly enough for 1 share @ 70,000 -> 70,070 + 10 = 70,080 KRW
        acc = VirtualAccount(initial_cash=Decimal("70080"))
        eng = MockExecutionEngine(account=acc)

        rec = eng.execute_order("005930", OrderSide.BUY, 1, Decimal("70000"))
        assert rec.is_success
        rem_cash = acc.cash_balance

        for _ in range(1000):
            rec_fail = eng.execute_order("005930", OrderSide.BUY, 1, Decimal("70000"))
            assert not rec_fail.is_success
            assert acc.cash_balance == rem_cash
            assert acc.cash_balance >= Decimal("0")

        # Sell and escape
        rec_sell = eng.execute_order("005930", OrderSide.SELL, 1, Decimal("70000"))
        assert rec_sell.is_success
        assert acc.cash_balance > Decimal("69000")


class TestExtremeWorkloadAndAccountingInvariants:
    """10,000회 고빈도 워크로드 및 회계 불변식 정밀 검증"""

    def test_10k_iteration_ping_pong_accounting_exactness(self):
        """10,000회 핑퐁 매매 후 초기자본 - 최종자본 == 누적비용 0원 오차 검증"""
        sim = DummyStrategySimulator(initial_cash=Decimal("100000000"))
        res = sim.run_ping_pong(symbol="005930", base_price=Decimal("70000"), quantity=10, iterations=10000)

        assert res["invariant_passed"] is True
        assert res["final_holdings"] == 0
        diff = (Decimal("100000000") - res["final_cash"]) - res["total_frictions"]
        assert diff == Decimal("0")

    def test_10k_step_random_walk_stress_invariants(self):
        """10,000스텝 랜덤워크 스트레스 테스트 완주 및 회계 불변식 통과 검증"""
        sim = DummyStrategySimulator(initial_cash=Decimal("100000000"))
        res = sim.run_random_stress(symbol="005930", base_price=Decimal("70000"), steps=10000, max_quantity=20, seed=42)

        assert res["invariant_passed"] is True
        assert res["min_cash_observed"] >= Decimal("0")
