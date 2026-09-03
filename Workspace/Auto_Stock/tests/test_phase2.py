"""
tests/test_phase2.py
====================
Auto Stock ML/RL Trader — Phase 2: 가상 체결 엔진(Mock Environment) E2E 4-Tier 종합 테스트 스위트

[테스트 아키텍처: 4-Tier 체계]
1. Tier 1: Feature Coverage (기능별 단위 및 기본 동작 검증, 총 28개)
   - F1: VirtualAccount (가상 계좌 잔고, 평단가, 이동평균, 평가액, 스냅샷) [7개]
   - F2: MockExecutionEngine (매수/매도 체결, 수수료 0.015%, 세금 0.18%, 슬리피지 0.1%, 잔고 방어) [6개]
   - F3: DummyStrategySimulator (핑퐁 매매, SMA 이평선 교차, 무작위 스트레스) [5개]
   - F4: Accounting Invariant Engine (1원 오차 0원 회계 무결성 공식 검증) [5개]
   - F5: MockEnvironment Facade (reset, step, state, ML/RL 호환성) [5개]

2. Tier 2: Boundary & Corner Cases (경계값, 극단값, 비정상 입력 방어, 총 25개)
   - 수량 0/음수, 가격 0/음수, 잔고 1원 초과/부족 경계, 전량 매도, 슬리피지 0% 및 극단 슬리피지,
     수수료/세금 0% 및 극단치, 1원 주가 절사, 10조 원 대규모 자본금, 미세 거래 누적, 포지션 격리 등

3. Tier 3: Cross-Feature Combinations (교차 상호작용 및 파이프라인 결합, 총 5개)
   - 다종목 포트폴리오 리밸런싱, 동적 비용 설정 및 부분 매수/매도 반복, 고변동성 급등락 체결,
     Data Streamer 연동 파이프라인, 수시 입출금 연동 회계 불변식

4. Tier 4: Real-World Workload Scenarios (실제 워크로드 및 스트레스 시나리오, 총 5개)
   - Scenario 1: 1,000회 연속 고빈도 핑퐁 매매 및 회계 무결성 0원 오차 검증
   - Scenario 2: 삼성전자(005930) 10년 실데이터 Parquet 스트리밍 기반 SMA 이평선 교차 1,000스텝 시뮬레이션
   - Scenario 3: 시장 급락(-50%) 및 급반등(+100%) 시나리오 스트레스 테스트
   - Scenario 4: 파산 직전 한계 잔고 방어 및 음수 잔고 0건 검증
   - Scenario 5: 복합 수수료/세율 커스텀 설정 시뮬레이션
"""

import os
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
    EngineError,
    InsufficientFundsError,
    InsufficientSharesError,
    InvalidOrderError,
    AccountingInvariantError,
    to_decimal,
    quantize_krw,
    VirtualAccount,
    MockExecutionEngine,
    DummyStrategySimulator,
    MockEnvironment,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def default_fee_config() -> FeeConfig:
    """한국 주식 시장 표준 비용 설정: 수수료 0.015%, 세금 0.18%, 슬리피지 0.1%"""
    return FeeConfig(
        commission_rate=Decimal("0.00015"),
        tax_rate=Decimal("0.0018"),
        slippage_rate=Decimal("0.0010"),
        price_tick_size=Decimal("1")
    )


@pytest.fixture
def zero_cost_fee_config() -> FeeConfig:
    """비용 없는 설정 (수수료 0%, 세금 0%, 슬리피지 0%)"""
    return FeeConfig(
        commission_rate=Decimal("0"),
        tax_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
        price_tick_size=Decimal("1")
    )


@pytest.fixture
def account_10m() -> VirtualAccount:
    """초기 자본금 10,000,000원 가상 계좌"""
    return VirtualAccount(initial_cash=Decimal("10000000"))


@pytest.fixture
def engine_10m(account_10m, default_fee_config) -> MockExecutionEngine:
    """1,000만원 계좌와 표준 수수료가 장착된 체결 엔진"""
    return MockExecutionEngine(account=account_10m, fee_config=default_fee_config)


@pytest.fixture
def samsung_parquet_path() -> str:
    """Phase 1 삼성전자 통합 Parquet 데이터 경로"""
    path = "/home/imnyj/Workspace/Auto_Stock/data/raw/005930_consolidated.parquet"
    if not os.path.exists(path):
        pytest.skip(f"Samsung parquet file not found at {path}")
    return path


# ==============================================================================
# Tier 1: Feature Coverage (총 28개 테스트)
# ==============================================================================

class TestTier1FeatureCoverage:
    """Tier 1: 개별 컴포넌트 기능별 단위 동작 및 계약 검증"""

    # --- F1: VirtualAccount Manager (7 tests) ---

    def test_f1_01_account_initialization(self, account_10m):
        """가상 계좌 초기화 시 자본금, 잔고, 누적 비용 등의 초기 상태를 검증합니다."""
        assert account_10m.initial_cash == Decimal("10000000")
        assert account_10m.cash_balance == Decimal("10000000")
        assert account_10m.holdings == {}
        assert account_10m.avg_prices == {}
        assert account_10m.realized_pnl == Decimal("0")
        assert account_10m.cumulative_commission == Decimal("0")
        assert account_10m.cumulative_tax == Decimal("0")
        assert account_10m.cumulative_slippage == Decimal("0")

    def test_f1_02_deposit_and_withdraw_success_and_error(self, account_10m):
        """계좌 입금 및 출금 정상 동작과 잔고 부족/음수 입력 시의 예외 발생을 검증합니다."""
        account_10m.deposit(Decimal("5000000"))
        assert account_10m.cash_balance == Decimal("15000000")

        account_10m.withdraw(Decimal("3000000"))
        assert account_10m.cash_balance == Decimal("12000000")

        with pytest.raises(InsufficientFundsError):
            account_10m.withdraw(Decimal("20000000"))

        with pytest.raises(ValueError):
            account_10m.deposit(Decimal("-1000"))

        with pytest.raises(ValueError):
            account_10m.withdraw(Decimal("0"))

    def test_f1_03_position_buy_moving_average_price(self, account_10m):
        """분할 매수 시 이동평균법(Moving Average)에 의한 평단가 갱신을 검증합니다."""
        # 1차 매수: 10주 @ 70,000원 (수수료 105원)
        account_10m.apply_buy("005930", Decimal("70000"), 10, Decimal("105"))
        pos = account_10m.get_position("005930")
        assert pos.quantity == 10
        assert pos.avg_price == Decimal("70000")
        assert pos.total_cost == Decimal("700000")
        assert account_10m.cash_balance == Decimal("10000000") - Decimal("700105")

        # 2차 매수: 10주 @ 80,000원 (수수료 120원) -> (70만 + 80만) / 20 = 75,000원
        account_10m.apply_buy("005930", Decimal("80000"), 10, Decimal("120"))
        assert pos.quantity == 20
        assert pos.avg_price == Decimal("75000")
        assert pos.total_cost == Decimal("1500000")

    def test_f1_04_position_partial_sell_preserves_avg_price(self, account_10m):
        """부분 매도 시 수량은 차감되나 평단가는 유지됨을 검증합니다."""
        account_10m.apply_buy("005930", Decimal("75000"), 20, Decimal("0"))
        pos = account_10m.get_position("005930")
        assert pos.quantity == 20

        # 5주 부분 매도 @ 80,000원 (수수료 60원, 세금 720원)
        account_10m.apply_sell("005930", Decimal("80000"), 5, Decimal("60"), Decimal("720"))
        assert pos.quantity == 15
        assert pos.avg_price == Decimal("75000")
        assert pos.total_cost == Decimal("1125000")  # 15 * 75000

    def test_f1_05_position_full_sell_resets_avg_price(self, account_10m):
        """전량 매도 시 수량 0, 평단가 0, 총 매입비용 0으로 완전히 초기화됨을 검증합니다."""
        account_10m.apply_buy("005930", Decimal("70000"), 10, Decimal("0"))
        account_10m.apply_sell("005930", Decimal("72000"), 10, Decimal("0"), Decimal("0"))
        pos = account_10m.get_position("005930")
        assert pos.quantity == 0
        assert pos.avg_price == Decimal("0")
        assert pos.total_cost == Decimal("0")
        assert "005930" not in account_10m.holdings

    def test_f1_06_realized_and_unrealized_pnl_calculation(self, account_10m):
        """실현 손익(Realized PnL) 및 미실현 손익(Unrealized PnL), 총 평가금(Total Equity)을 검증합니다."""
        account_10m.apply_buy("005930", Decimal("70000"), 10, Decimal("105"))
        # 10주 중 5주 매도 @ 80,000원 (수수료 60원, 세금 720원)
        # 매수원가 5*70,000=350,000 / 매도총액 5*80,000=400,000 -> 총차익 50,000 - 60 - 720 = 49,220원
        account_10m.apply_sell("005930", Decimal("80000"), 5, Decimal("60"), Decimal("720"))
        assert account_10m.realized_pnl == Decimal("49220")

        # 잔여 5주에 대해 현재가 85,000원일 때 미실현 손익: 5 * (85000 - 70000) = 75,000원
        pos = account_10m.get_position("005930")
        assert pos.unrealized_pnl(Decimal("85000")) == Decimal("75000")

        # 총 평가금: 현재 현금 + 5주 * 85,000원
        equity = account_10m.get_total_equity({"005930": Decimal("85000")})
        assert equity == account_10m.cash_balance + Decimal("425000")

    def test_f1_07_account_snapshot_immutability(self, account_10m):
        """get_snapshot 반환 객체가 완벽한 불변 스냅샷이고 원본 변경에 영향받지 않음을 검증합니다."""
        account_10m.apply_buy("005930", Decimal("70000"), 10, Decimal("100"))
        snapshot = account_10m.get_snapshot(Decimal("75000"))

        assert isinstance(snapshot, AccountSnapshot)
        assert snapshot.cash_balance == account_10m.cash_balance
        assert snapshot.holdings_valuation == Decimal("750000")
        assert snapshot.positions["005930"].quantity == 10

        # 원본 계좌를 변형해도 스냅샷은 불변
        account_10m.withdraw(Decimal("1000000"))
        assert snapshot.cash_balance != account_10m.cash_balance

    # --- F2: MockExecutionEngine (6 tests) ---

    def test_f2_01_buy_order_slippage_and_commission(self, engine_10m):
        """매수 주문 시 상향 슬리피지(0.1%)와 위탁수수료(0.015% 절사) 정밀 계산을 검증합니다."""
        # 시장가 70,000원, 10주 매수
        # 슬리피지 체결가 = 70,000 * 1.001 = 70,070원
        # 매수 총액 = 70,070 * 10 = 700,700원
        # 위탁수수료 = floor(700,700 * 0.00015) = floor(105.105) = 105원
        # 슬리피지 비용 = (70,070 - 70,000) * 10 = 700원
        record = engine_10m.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))

        assert record.is_success is True
        assert record.executed_price == Decimal("70070")
        assert record.gross_amount == Decimal("700700")
        assert record.commission == Decimal("105")
        assert record.tax == Decimal("0")
        assert record.slippage_cost == Decimal("700")
        assert record.net_cash_flow == Decimal("-700805")
        assert engine_10m.account.cash_balance == Decimal("10000000") - Decimal("700805")

    def test_f2_02_sell_order_slippage_fee_and_tax(self, engine_10m):
        """매도 주문 시 하향 슬리피지(0.1%), 위탁수수료(0.015%), 증권거래세(0.18% 절사)를 검증합니다."""
        # 사전 10주 매수
        engine_10m.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        cash_before_sell = engine_10m.account.cash_balance

        # 10주 매도 @ 70,000원
        # 슬리피지 체결가 = 70,000 * (1 - 0.001) = 69,930원
        # 매도 총액 = 69,930 * 10 = 699,300원
        # 위탁수수료 = floor(699,300 * 0.00015) = floor(104.895) = 104원
        # 증권거래세 = floor(699,300 * 0.0018) = floor(1258.74) = 1258원
        # 순입금액 = 699,300 - 104 - 1,258 = 697,938원
        record = engine_10m.execute_order("005930", OrderSide.SELL, 10, Decimal("70000"))

        assert record.is_success is True
        assert record.executed_price == Decimal("69930")
        assert record.gross_amount == Decimal("699300")
        assert record.commission == Decimal("104")
        assert record.tax == Decimal("1258")
        assert record.slippage_cost == Decimal("700")
        assert record.net_cash_flow == Decimal("697938")
        assert engine_10m.account.cash_balance == cash_before_sell + Decimal("697938")

    def test_f2_03_buy_tax_is_zero(self, engine_10m):
        """한국 세법에 따라 매수 시에는 거래세가 0원임을 검증합니다."""
        record = engine_10m.execute_order("005930", OrderSide.BUY, 50, Decimal("60000"))
        assert record.tax == Decimal("0")
        assert engine_10m.account.cumulative_tax == Decimal("0")

    def test_f2_04_insufficient_cash_buy_rejection(self, engine_10m):
        """잔고 부족 시 매수 주문이 거절되고 잔고와 포지션에 부작용이 없음을 검증합니다."""
        # 1,000만원 잔고인데 2,000만원 상당 매수 시도
        initial_cash = engine_10m.account.cash_balance
        record = engine_10m.execute_order("005930", OrderSide.BUY, 300, Decimal("70000"))

        assert record.is_success is False
        assert "Insufficient cash" in record.error_message
        assert engine_10m.account.cash_balance == initial_cash
        assert engine_10m.account.get_position("005930").quantity == 0

    def test_f2_05_insufficient_shares_sell_rejection(self, engine_10m):
        """보유 수량 부족(무차입 공매도) 시 매도 주문이 거절됨을 검증합니다."""
        record = engine_10m.execute_order("005930", OrderSide.SELL, 10, Decimal("70000"))
        assert record.is_success is False
        assert "Insufficient shares" in record.error_message
        assert engine_10m.account.get_position("005930").quantity == 0

    def test_f2_06_trade_record_audit_trail_completeness(self, engine_10m):
        """체결 기록(TradeRecord)의 모든 회계 및 감사 필드가 완전하게 생성됨을 검증합니다."""
        record = engine_10m.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        assert isinstance(record.trade_id, str)
        assert isinstance(record.timestamp, datetime)
        assert record.symbol == "005930"
        assert record.side == OrderSide.BUY
        assert record.quantity == 10
        assert record.cash_after == engine_10m.account.cash_balance
        assert record.position_qty_after == 10
        assert len(engine_10m.trade_history) == 1

    # --- F3: DummyStrategySimulator (5 tests) ---

    def test_f3_01_ping_pong_strategy_execution(self, engine_10m):
        """더미 핑퐁 매매 20회 실행 시 교대 체결 및 최종 포지션 0주 도달을 검증합니다."""
        simulator = DummyStrategySimulator(engine=engine_10m)
        result = simulator.run_ping_pong(symbol="005930", base_price=Decimal("70000"), quantity=10, iterations=20)

        assert result["total_iterations"] == 20
        assert result["final_holdings"] == 0
        assert result["invariant_passed"] is True
        assert len(result["equity_curve"]) >= 20

    def test_f3_02_sma_crossover_strategy_synthetic_trend(self, engine_10m):
        """합성 주가 데이터 기반 SMA 골든/데드 크로스 전략 시뮬레이션 완주를 검증합니다."""
        # 50일간의 합성 주가 (초기 하락 후 급상승: 골든 크로스 유발)
        prices = [80000 - i * 500 for i in range(20)] + [70000 + i * 800 for i in range(30)]
        df = pd.DataFrame({"close": prices})

        simulator = DummyStrategySimulator(engine=engine_10m)
        result = simulator.run_sma_crossover(df, symbol="005930", short_window=5, long_window=10, trade_quantity=5)

        assert result["total_bars"] == 50
        assert result["total_trades"] > 0
        assert result["invariant_passed"] is True
        assert len(result["equity_curve"]) == 40  # 50 - long_window(10)

    def test_f3_03_random_stress_strategy_resilience(self, engine_10m):
        """무작위 스트레스 테스트 100스텝 완주 및 음수 잔고 미발생을 검증합니다."""
        simulator = DummyStrategySimulator(engine=engine_10m)
        result = simulator.run_random_stress(symbol="005930", base_price=Decimal("70000"), steps=100, max_quantity=5, seed=123)

        assert result["steps"] == 100
        assert result["min_cash_observed"] >= Decimal("0")
        assert result["invariant_passed"] is True

    def test_f3_04_equity_curve_tracking_integrity(self, engine_10m):
        """시뮬레이터 실행 중 에쿼티 곡선(Equity Curve)이 매 스텝 올바르게 기록됨을 검증합니다."""
        simulator = DummyStrategySimulator(engine=engine_10m)
        res = simulator.run_ping_pong(symbol="005930", base_price=Decimal("70000"), quantity=5, iterations=10)
        curve = simulator.equity_curve
        assert len(curve) > 0
        for eq in curve:
            assert isinstance(eq, Decimal)
            assert eq > Decimal("0")

    def test_f3_05_strategy_custom_parameters(self, engine_10m):
        """윈도우 크기, 수량 등 전략 파라미터 커스터마이징 동작을 검증합니다."""
        prices = [50000 + (i % 10) * 1000 for i in range(100)]
        simulator = DummyStrategySimulator(engine=engine_10m)
        res = simulator.run_sma_crossover(prices, short_window=3, long_window=8, trade_quantity=20)
        assert res["total_bars"] == 100
        assert res["invariant_passed"] is True

    # --- F4: Accounting Invariant Engine (5 tests) ---

    def test_f4_01_invariant_single_roundtrip_zero_won(self, engine_10m):
        """1회 왕복 매매 시 회계 불변식이 단 1원의 오차도 없이 0원으로 일치함을 검증합니다."""
        # Initial: 10,000,000
        # Buy 10 @ 70,000 -> Exec 70,070, Comm 105, Slip 700
        # Sell 10 @ 70,000 -> Exec 69,930, Comm 104, Tax 1258, Slip 700
        # Total Frictions = 105 + 104 + 1258 + 1400 = 2867
        # Final Cash = 10,000,000 - 700,805 + 697,938 = 9,997,133
        # Initial - Final = 2,867 == Total Frictions
        engine_10m.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        engine_10m.execute_order("005930", OrderSide.SELL, 10, Decimal("70000"))

        assert engine_10m.verify_accounting_invariant(
            initial_capital=Decimal("10000000"),
            current_market_prices={"005930": Decimal("70000")}
        ) is True

    def test_f4_02_invariant_with_holding_position(self, engine_10m):
        """주식을 보유 중인 상태에서도 회계 불변식이 정확히 0원 오차로 성립함을 검증합니다."""
        engine_10m.execute_order("005930", OrderSide.BUY, 50, Decimal("70000"))
        assert engine_10m.verify_accounting_invariant(
            initial_capital=Decimal("10000000"),
            current_market_prices={"005930": Decimal("70000")}
        ) is True

    def test_f4_03_invariant_multi_trades_constant_price(self, engine_10m):
        """고정 가격에서 50회 연속 매수/매도 후 회계 불변식이 완벽히 보존됨을 검증합니다."""
        for _ in range(25):
            engine_10m.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
            engine_10m.execute_order("005930", OrderSide.SELL, 10, Decimal("70000"))

        assert engine_10m.verify_accounting_invariant(
            initial_capital=Decimal("10000000"),
            current_market_prices={"005930": Decimal("70000")}
        ) is True

    def test_f4_04_invariant_time_varying_price_drift(self, engine_10m):
        """주가 변동 시 시계열 시장 변동 손익(Price Drift PnL)을 고려한 불변식을 검증합니다."""
        # 10주 매수 @ 70,000원
        engine_10m.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        # 주가 75,000원으로 상승 반영
        engine_10m.update_market_price("005930", Decimal("75000"))
        # 10주 추가 매수 @ 75,000원
        engine_10m.execute_order("005930", OrderSide.BUY, 10, Decimal("75000"))
        # 주가 80,000원으로 상승 반영
        engine_10m.update_market_price("005930", Decimal("80000"))

        assert engine_10m.verify_accounting_invariant(
            initial_capital=Decimal("10000000"),
            current_market_prices={"005930": Decimal("80000")}
        ) is True

    def test_f4_05_accounting_audit_dictionary(self, engine_10m):
        """get_accounting_audit 반환 딕셔너리의 모든 항목 정합성을 검증합니다."""
        engine_10m.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        audit = engine_10m.get_accounting_audit({"005930": Decimal("70000")})

        assert audit["initial_cash"] == Decimal("10000000")
        assert audit["trade_count"] == 1
        assert audit["rejected_count"] == 0
        assert audit["total_frictions"] == audit["cumulative_commission"] + audit["cumulative_tax"] + audit["cumulative_slippage"]
        assert audit["total_equity"] == audit["cash_balance"] + audit["holdings_valuation"]

    # --- F5: MockEnvironment Facade (5 tests) ---

    def test_f5_01_mock_env_initialization_and_reset(self):
        """MockEnvironment Facade의 생성 및 reset 인터페이스 동작을 검증합니다."""
        env = MockEnvironment(initial_capital=Decimal("5000000"))
        state = env.reset()
        assert state["cash_balance"] == 5000000.0
        assert state["holding_quantity"] == 0
        assert state["total_equity"] == 5000000.0

    def test_f5_02_mock_env_step_actions_buy_sell_hold(self):
        """MockEnvironment의 step(HOLD), step(BUY), step(SELL) 액션 전이를 검증합니다."""
        # 3일치 가격 시뮬레이션 데이터
        data = [
            {"symbol": "005930", "close": 70000},
            {"symbol": "005930", "close": 71000},
            {"symbol": "005930", "close": 72000}
        ]
        env = MockEnvironment(data_stream=data, initial_capital=Decimal("10000000"), default_trade_quantity=10)
        env.reset()

        # Step 1: BUY (ActionType.BUY = 1)
        state1, reward1, done1, info1 = env.step(ActionType.BUY)
        assert state1["holding_quantity"] == 10
        assert not done1

        # Step 2: HOLD (ActionType.HOLD = 0)
        state2, reward2, done2, info2 = env.step(ActionType.HOLD)
        assert state2["holding_quantity"] == 10
        assert not done2

        # Step 3: SELL (ActionType.SELL = 2)
        state3, reward3, done3, info3 = env.step(ActionType.SELL)
        assert state3["holding_quantity"] == 0
        assert done3 is True

    def test_f5_03_mock_env_dataframe_stream_stepping(self):
        """pandas DataFrame 데이터를 기반으로 MockEnvironment가 순차 진행됨을 검증합니다."""
        df = pd.DataFrame({
            "close": [70000, 70500, 71000, 71500, 72000]
        })
        env = MockEnvironment(data_stream=df.to_dict("records"), initial_capital=Decimal("10000000"))
        env.reset()

        for _ in range(5):
            state, reward, done, info = env.step(ActionType.BUY)

        assert done is True
        assert env._current_step == 5

    def test_f5_04_mock_env_done_signal_at_end(self):
        """데이터 스트림 종료 시 done == True 반환 및 추가 step 안전 처리를 검증합니다."""
        env = MockEnvironment(data_stream=[{"close": 70000}], initial_capital=Decimal("10000000"))
        env.reset()
        state, reward, done, info = env.step(0)
        assert done is True

        # 이미 종료된 상태에서 step 호출 시
        state_post, reward_post, done_post, info_post = env.step(0)
        assert done_post is True
        assert info_post["reason"] == "data_exhausted"

    def test_f5_05_mock_env_accounting_audit_method(self):
        """MockEnvironment를 통한 감사 내역 집계 및 조회 인터페이스를 검증합니다."""
        env = MockEnvironment(
            data_stream=[{"close": 70000}, {"close": 70000}],
            initial_capital=Decimal("10000000")
        )
        env.reset()
        env.step(1)
        audit = env.get_accounting_audit()
        assert audit["trade_count"] == 1
        assert audit["cumulative_commission"] > Decimal("0")


# ==============================================================================
# Tier 2: Boundary & Corner Cases (총 25개 테스트)
# ==============================================================================

class TestTier2BoundaryAndCornerCases:
    """Tier 2: 경계값, 극단값, 비정상 입력 및 예외 방어 검증"""

    def test_b01_zero_quantity_order_rejected(self, engine_10m):
        """수량이 0인 주문은 즉시 거절됨을 검증합니다."""
        record = engine_10m.execute_order("005930", OrderSide.BUY, 0, Decimal("70000"))
        assert record.is_success is False
        assert "must be positive" in record.error_message

    def test_b02_negative_quantity_order_rejected(self, engine_10m):
        """음수 수량 주문은 거절됨을 검증합니다."""
        record = engine_10m.execute_order("005930", OrderSide.BUY, -10, Decimal("70000"))
        assert record.is_success is False

    def test_b03_zero_price_order_rejected(self, engine_10m):
        """주가가 0원인 주문은 거절됨을 검증합니다."""
        record = engine_10m.execute_order("005930", OrderSide.BUY, 10, Decimal("0"))
        assert record.is_success is False
        assert "must be positive" in record.error_message

    def test_b04_negative_price_order_rejected(self, engine_10m):
        """음수 주가 주문은 거절됨을 검증합니다."""
        record = engine_10m.execute_order("005930", OrderSide.BUY, 10, Decimal("-50000"))
        assert record.is_success is False

    def test_b05_cash_boundary_exact_match(self, default_fee_config):
        """매수 총 필요금액과 잔고가 정확히 1원도 남김없이 일치할 때 매수 체결 및 잔고 0원 도달을 검증합니다."""
        # 10주 @ 70,000원 -> Exec 70,070, Gross 700,700, Comm 105 -> Total Outflow 700,805원
        exact_cash = Decimal("700805")
        acc = VirtualAccount(initial_cash=exact_cash)
        eng = MockExecutionEngine(account=acc, fee_config=default_fee_config)

        record = eng.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        assert record.is_success is True
        assert acc.cash_balance == Decimal("0")

    def test_b06_cash_boundary_1_won_shortage(self, default_fee_config):
        """필요 잔고보다 단 1원이 부족할 때 주문이 정확히 거절되고 잔고가 보존됨을 검증합니다."""
        # 필요 700,805원인데 700,804원만 보유
        short_cash = Decimal("700804")
        acc = VirtualAccount(initial_cash=short_cash)
        eng = MockExecutionEngine(account=acc, fee_config=default_fee_config)

        record = eng.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        assert record.is_success is False
        assert "Insufficient cash" in record.error_message
        assert acc.cash_balance == short_cash

    def test_b07_sell_boundary_exact_quantity(self, engine_10m):
        """보유 수량과 정확히 일치하는 전량 매도 시 포지션이 0주로 깨끗이 정리됨을 검증합니다."""
        engine_10m.execute_order("005930", OrderSide.BUY, 25, Decimal("70000"))
        record = engine_10m.execute_order("005930", OrderSide.SELL, 25, Decimal("70000"))
        assert record.is_success is True
        assert engine_10m.account.get_position("005930").quantity == 0

    def test_b08_sell_boundary_1_share_excess(self, engine_10m):
        """보유 10주 상태에서 1주 초과한 11주 매도 시도시 거절됨을 검증합니다."""
        engine_10m.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        record = engine_10m.execute_order("005930", OrderSide.SELL, 11, Decimal("70000"))
        assert record.is_success is False
        assert "Insufficient shares" in record.error_message
        assert engine_10m.account.get_position("005930").quantity == 10

    def test_b09_zero_slippage_rate(self, account_10m):
        """슬리피지율 0.0% 설정 시 체결가가 시장가와 완전히 일치함을 검증합니다."""
        cfg = FeeConfig(slippage_rate=Decimal("0"))
        eng = MockExecutionEngine(account=account_10m, fee_config=cfg)

        rec = eng.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        assert rec.executed_price == Decimal("70000")
        assert rec.slippage_cost == Decimal("0")

    def test_b10_extreme_high_slippage_rate(self, account_10m):
        """슬리피지 20%(0.20) 극단적 상황에서 매수/매도 체결가 계산을 검증합니다."""
        cfg = FeeConfig(slippage_rate=Decimal("0.20"))
        eng = MockExecutionEngine(account=account_10m, fee_config=cfg)

        rec_buy = eng.execute_order("005930", OrderSide.BUY, 10, Decimal("50000"))
        assert rec_buy.executed_price == Decimal("60000")  # 50,000 * 1.2
        assert rec_buy.slippage_cost == Decimal("100000")  # 10,000 * 10

        rec_sell = eng.execute_order("005930", OrderSide.SELL, 10, Decimal("50000"))
        assert rec_sell.executed_price == Decimal("40000")  # 50,000 * 0.8
        assert rec_sell.slippage_cost == Decimal("100000")

    def test_b11_zero_fee_zero_tax(self, account_10m, zero_cost_fee_config):
        """수수료 0%, 세금 0%, 슬리피지 0% 환경에서 비용 0원 및 완전 보존을 검증합니다."""
        eng = MockExecutionEngine(account=account_10m, fee_config=zero_cost_fee_config)
        eng.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        eng.execute_order("005930", OrderSide.SELL, 10, Decimal("70000"))

        assert eng.account.cash_balance == Decimal("10000000")
        assert eng.account.cumulative_commission == Decimal("0")
        assert eng.account.cumulative_tax == Decimal("0")

    def test_b12_extreme_high_fee_and_tax(self, account_10m):
        """수수료 5%, 거래세 10% 등 고비용 환경에서의 잔고 방어 및 차감을 검증합니다."""
        cfg = FeeConfig(commission_rate=Decimal("0.05"), tax_rate=Decimal("0.10"), slippage_rate=Decimal("0"))
        eng = MockExecutionEngine(account=account_10m, fee_config=cfg)

        rec = eng.execute_order("005930", OrderSide.BUY, 10, Decimal("100000"))
        # 100만 + 5만(수수료) = 105만원 차감
        assert rec.commission == Decimal("50000")
        assert eng.account.cash_balance == Decimal("8950000")

    def test_b13_micro_price_1_won_rounding(self, engine_10m):
        """주가 1원 주식 1주 매매 시 1원 미만 수수료/세금 절사(0원) 정상 처리를 검증합니다."""
        rec = engine_10m.execute_order("MICRO", OrderSide.BUY, 1, Decimal("1"))
        assert rec.is_success is True
        assert rec.commission == Decimal("0")  # floor(1 * 0.00015) = 0

    def test_b14_huge_capital_trillion_scale(self):
        """10조 원 규모의 대규모 자본금 및 1억 주 주문 시 Decimal 정밀도 유지를 검증합니다."""
        huge_cash = Decimal("10000000000000")  # 10조
        acc = VirtualAccount(initial_cash=huge_cash)
        eng = MockExecutionEngine(account=acc)

        rec = eng.execute_order("005930", OrderSide.BUY, 10000000, Decimal("70000"))  # 7000억원
        assert rec.is_success is True
        assert acc.cash_balance > Decimal("0")
        assert eng.verify_accounting_invariant(initial_capital=huge_cash, current_market_prices={"005930": Decimal("70000")}) is True

    def test_b15_repeated_micro_transactions_truncation_accumulation(self, engine_10m):
        """1원 미만 수수료가 발생하는 미세 거래 200회 반복 시 절사 규칙 누적 무결성을 검증합니다."""
        # 1주 @ 1,000원 -> 수수료 floor(1000 * 0.00015) = 0원
        for _ in range(100):
            engine_10m.execute_order("PENNY", OrderSide.BUY, 1, Decimal("1000"))
            engine_10m.execute_order("PENNY", OrderSide.SELL, 1, Decimal("1000"))

        assert engine_10m.verify_accounting_invariant(initial_capital=Decimal("10000000"), current_market_prices={"PENNY": Decimal("1000")}) is True

    def test_b16_empty_portfolio_metrics(self, account_10m):
        """주식 미보유 시 총 자산 == 현금 잔고 및 미실현 손익 0원을 검증합니다."""
        assert account_10m.get_total_equity(Decimal("70000")) == Decimal("10000000")
        pos = account_10m.get_position("EMPTY")
        assert pos.unrealized_pnl(Decimal("70000")) == Decimal("0")
        assert pos.return_rate(Decimal("70000")) == Decimal("0")

    def test_b17_multiple_symbols_isolated_positions(self, engine_10m):
        """종목 A와 종목 B 동시 보유 시 각 포지션의 수량과 평단가가 완전 격리됨을 검증합니다."""
        engine_10m.execute_order("SYM_A", OrderSide.BUY, 10, Decimal("10000"))
        engine_10m.execute_order("SYM_B", OrderSide.BUY, 20, Decimal("20000"))

        pos_a = engine_10m.account.get_position("SYM_A")
        pos_b = engine_10m.account.get_position("SYM_B")

        assert pos_a.quantity == 10
        assert pos_a.avg_price == Decimal("10010")  # 10,000 * 1.001
        assert pos_b.quantity == 20
        assert pos_b.avg_price == Decimal("20020")  # 20,000 * 1.001

    def test_b18_consecutive_buy_price_averaging(self, engine_10m):
        """10,000원, 20,000원, 30,000원 3단계 분할 매수 시 가중평균 평단가 정밀도를 검증합니다."""
        # 10주 @ 10,000 (체결 10,010), 10주 @ 20,000 (체결 20,020), 10주 @ 30,000 (체결 30,030)
        # 평단가 = (100,100 + 200,200 + 300,300) / 30 = 600,600 / 30 = 20,020원
        engine_10m.execute_order("SCALE", OrderSide.BUY, 10, Decimal("10000"))
        engine_10m.execute_order("SCALE", OrderSide.BUY, 10, Decimal("20000"))
        engine_10m.execute_order("SCALE", OrderSide.BUY, 10, Decimal("30000"))

        pos = engine_10m.account.get_position("SCALE")
        assert pos.quantity == 30
        assert pos.avg_price == Decimal("20020")

    def test_b19_withdraw_exact_balance(self, account_10m):
        """잔고 전액 출금 후 0원 도달 및 추가 출금 불가 처리를 검증합니다."""
        account_10m.withdraw(Decimal("10000000"))
        assert account_10m.cash_balance == Decimal("0")

        with pytest.raises(InsufficientFundsError):
            account_10m.withdraw(Decimal("1"))

    def test_b20_deposit_after_exhaustion(self, account_10m, default_fee_config):
        """잔고 0원 소진 후 추가 입금 시 매수가 정상 재개됨을 검증합니다."""
        account_10m.withdraw(Decimal("10000000"))
        eng = MockExecutionEngine(account=account_10m, fee_config=default_fee_config)

        # 0원 상태 매수 실패
        rec1 = eng.execute_order("005930", OrderSide.BUY, 1, Decimal("70000"))
        assert rec1.is_success is False

        # 100만원 입금 후 매수 성공
        account_10m.deposit(Decimal("1000000"))
        rec2 = eng.execute_order("005930", OrderSide.BUY, 1, Decimal("70000"))
        assert rec2.is_success is True

    def test_b21_invalid_symbol_string(self, engine_10m):
        """빈 문자열 종목 코드 주문 처리 시 안정성을 검증합니다."""
        rec = engine_10m.execute_order("", OrderSide.BUY, 1, Decimal("1000"))
        assert rec.is_success is True  # 시스템 다운 없이 처리
        assert "" in engine_10m.account.positions

    def test_b22_non_integer_quantity_protection(self, account_10m):
        """음수 수량 입력 시 apply_buy / apply_sell 에서 InvalidOrderError 발생을 검증합니다."""
        with pytest.raises(InvalidOrderError):
            account_10m.apply_buy("005930", Decimal("70000"), -5, Decimal("0"))

        with pytest.raises(InvalidOrderError):
            account_10m.apply_sell("005930", Decimal("70000"), 0, Decimal("0"), Decimal("0"))

    def test_b23_rounding_half_up_exact_fraction(self, default_fee_config):
        """체결단가 산출 시 0.5원 경계에서의 반올림(ROUND_HALF_UP) 정확성을 검증합니다."""
        # 10,005원 * 1.001 = 10,015.005 -> ROUND_HALF_UP => 10,015원
        acc = VirtualAccount(initial_cash=Decimal("1000000"))
        eng = MockExecutionEngine(account=acc, fee_config=default_fee_config)
        p_exec = eng.calculate_executed_price(OrderSide.BUY, Decimal("10005"))
        assert p_exec == Decimal("10015")

    def test_b24_floor_truncation_exact_fraction(self, engine_10m):
        """수수료/세금 산출 시 0.9999원 등의 절사(ROUND_FLOOR) 정확성을 검증합니다."""
        # 6,666원 * 0.00015 = 0.9999원 -> floor => 0원
        comm = engine_10m.calculate_commission(Decimal("6666"))
        assert comm == Decimal("0")

    def test_b25_cancel_and_rejected_order_zero_side_effect(self, engine_10m):
        """거절된 주문 50회 연속 발생 시 계좌 잔고와 포지션에 전혀 부작용이 없음을 검증합니다."""
        initial_cash = engine_10m.account.cash_balance
        for _ in range(50):
            engine_10m.execute_order("005930", OrderSide.BUY, 10000, Decimal("70000"))  # 거절

        assert engine_10m.account.cash_balance == initial_cash
        assert engine_10m.account.holdings == {}
        assert engine_10m.account.get_position("005930").quantity == 0
        assert len(engine_10m.trade_history) == 50


# ==============================================================================
# Tier 3: Cross-Feature Combinations (총 5개 테스트)
# ==============================================================================

class TestTier3CrossFeatureCombinations:
    """Tier 3: 다종목, 동적 비용, 시세 스트리머 파이프라인 결합 검증"""

    def test_cross_01_multi_symbol_portfolio_rebalancing(self, engine_10m):
        """3개 종목(삼성전자, SK하이닉스, 현대차) 교차 매수/매도 후 전체 포트폴리오 회계 무결성을 검증합니다."""
        # 1. 3종목 분할 매수
        engine_10m.execute_order("005930", OrderSide.BUY, 20, Decimal("70000"))   # 삼성전자 20주
        engine_10m.execute_order("000660", OrderSide.BUY, 10, Decimal("150000"))  # SK하이닉스 10주
        engine_10m.execute_order("005380", OrderSide.BUY, 5, Decimal("200000"))   # 현대차 5주

        # 2. 리밸런싱 부분 매도
        engine_10m.execute_order("005930", OrderSide.SELL, 10, Decimal("72000"))
        engine_10m.execute_order("000660", OrderSide.SELL, 5, Decimal("155000"))

        # 3. 불변식 검증
        current_prices = {
            "005930": Decimal("72000"),
            "000660": Decimal("155000"),
            "005380": Decimal("200000")
        }
        assert engine_10m.verify_accounting_invariant(
            initial_capital=Decimal("10000000"),
            current_market_prices=current_prices
        ) is True

    def test_cross_02_dynamic_cost_and_slippage_with_partial_fills(self, account_10m):
        """거래 도중 수수료율/슬리피지 설정이 변경되어도 누적 비용 회계가 일치함을 검증합니다."""
        eng = MockExecutionEngine(account=account_10m)

        # 설정 1: 기본 비용
        eng.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        # 설정 2: 고비용 변경
        eng.fee_config = FeeConfig(commission_rate=Decimal("0.001"), slippage_rate=Decimal("0.005"))
        eng.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        # 설정 3: 무비용 변경
        eng.fee_config = FeeConfig(commission_rate=Decimal("0"), tax_rate=Decimal("0"), slippage_rate=Decimal("0"))
        eng.execute_order("005930", OrderSide.SELL, 20, Decimal("70000"))

        assert eng.verify_accounting_invariant(
            initial_capital=Decimal("10000000"),
            current_market_prices={"005930": Decimal("70000")}
        ) is True

    def test_cross_03_high_volatility_price_swing_execution(self, engine_10m):
        """주가가 ±30% 급등락하는 시계열에서 매매 체결 및 평가손익 추적을 검증합니다."""
        prices = [Decimal(str(p)) for p in [70000, 91000, 63700, 82000, 58000, 75000]]
        for p in prices:
            engine_10m.execute_order("VOLATILE", OrderSide.BUY, 5, p)
            engine_10m.update_market_price("VOLATILE", p)

        audit = engine_10m.get_accounting_audit({"VOLATILE": Decimal("75000")})
        assert audit["trade_count"] == 6
        assert engine_10m.account.cash_balance >= Decimal("0")
        assert engine_10m.verify_accounting_invariant(
            initial_capital=Decimal("10000000"),
            current_market_prices={"VOLATILE": Decimal("75000")}
        ) is True

    def test_cross_04_streamer_feeder_to_mock_environment_pipeline(self):
        """Data Streamer BarData 형태의 시세 유입과 MockEnvironment 매매 E2E 결합을 검증합니다."""
        class MockBar:
            def __init__(self, sym, close_p, dt):
                self.symbol = sym
                self.close = close_p
                self.timestamp = dt

        bars = [
            MockBar("005930", 70000 + i * 100, datetime(2026, 1, 1, 9, i))
            for i in range(10)
        ]

        env = MockEnvironment(data_stream=bars, initial_capital=Decimal("10000000"))
        env.reset()

        for step_idx in range(10):
            action = ActionType.BUY if step_idx % 2 == 0 else ActionType.SELL
            state, reward, done, info = env.step(action)

        assert done is True
        assert env.account.cash_balance >= Decimal("0")

    def test_cross_05_rapid_buy_sell_churn_with_intermittent_deposits(self, engine_10m):
        """매매 도중 수시 입출금이 발생할 때 총 자본금 대비 회계 불변식 유지를 검증합니다."""
        # 1. 매수
        engine_10m.execute_order("005930", OrderSide.BUY, 10, Decimal("70000"))
        # 2. 200만원 추가 입금
        engine_10m.account.deposit(Decimal("2000000"))
        # 3. 추가 매수
        engine_10m.execute_order("005930", OrderSide.BUY, 20, Decimal("70000"))
        # 4. 100만원 출금
        engine_10m.account.withdraw(Decimal("1000000"))
        # 5. 전량 매도
        engine_10m.execute_order("005930", OrderSide.SELL, 30, Decimal("70000"))

        # 순 입금액 = +200만 - 100만 = +100만 -> 유효 초기자본 = 11,000,000원
        effective_initial = Decimal("11000000")
        assert engine_10m.verify_accounting_invariant(
            initial_capital=effective_initial,
            current_market_prices={"005930": Decimal("70000")}
        ) is True


# ==============================================================================
# Tier 4: Real-World Workload Scenarios (총 5개 테스트)
# ==============================================================================

class TestTier4RealWorldWorkloadScenarios:
    """Tier 4: 실제 환경 및 1,000+ 스텝 대규모 시뮬레이션 회계 무결성 검증"""

    def test_scenario_1_high_frequency_1000_ping_pong_accounting_invariant(self, engine_10m):
        """
        [Scenario 1] 1,000회 연속 고빈도 핑퐁 매매 및 0원 오차 회계 무결성 검증
        - 1,000회 연속 BUY/SELL 반복 체결
        - Initial Capital == Final Cash + Cumulative (Fee + Tax + Slippage)
        - 오차 허용 범위: 정확히 0원 (단 1원의 오차도 불허)
        """
        simulator = DummyStrategySimulator(engine=engine_10m)
        initial_cash = engine_10m.account.cash_balance

        result = simulator.run_ping_pong(
            symbol="005930",
            base_price=Decimal("70000"),
            quantity=10,
            iterations=1000
        )

        assert result["total_iterations"] == 1000
        assert result["total_trades"] >= 1000
        assert result["final_holdings"] == 0
        assert engine_10m.account.cash_balance >= Decimal("0")
        assert result["invariant_passed"] is True

        # 수동 2중 검증 (Zero Discrepancy Assertion)
        audit = engine_10m.get_accounting_audit({"005930": Decimal("70000")})
        expected_final_cash = initial_cash - audit["total_frictions"]
        assert engine_10m.account.cash_balance == expected_final_cash
        assert (initial_cash - (engine_10m.account.cash_balance + audit["total_frictions"])) == Decimal("0")

    def test_scenario_2_samsung_10yr_parquet_sma_crossover_1000_steps(self, engine_10m, samsung_parquet_path):
        """
        [Scenario 2] 삼성전자(005930) 실데이터 Parquet 스트리밍 기반 SMA 이평선 교차 1,000스텝 시뮬레이션
        - 실제 Parquet 파일 로드 및 시계열 스트리밍
        - 1,000스텝 이상 완주 및 음수 잔고 0건 검증
        """
        df_real = pd.read_parquet(samsung_parquet_path)
        assert len(df_real) >= 100, f"Real parquet dataset has {len(df_real)} rows"

        # 1,000스텝 시뮬레이션을 위해 데이터를 1,000행 이상으로 확장 또는 순환 피딩
        if len(df_real) < 1000:
            repeat_factor = int(np.ceil(1000 / len(df_real)))
            df_stream = pd.concat([df_real] * repeat_factor, ignore_index=True).iloc[:1000]
        else:
            df_stream = df_real.iloc[:1000]

        simulator = DummyStrategySimulator(engine=engine_10m)
        result = simulator.run_sma_crossover(
            prices_or_df=df_stream,
            symbol="005930",
            short_window=5,
            long_window=20,
            trade_quantity=10
        )

        assert result["total_bars"] == 1000
        assert result["final_cash"] >= Decimal("0")
        assert result["invariant_passed"] is True
        assert len(result["equity_curve"]) == 980  # 1000 - long_window(20)

    def test_scenario_3_market_crash_and_rebound_stress(self, engine_10m):
        """
        [Scenario 3] 시장 급락(-50%) 및 급반등(+100%) 시나리오 스트레스 테스트
        - 가격 급락 구간에서의 잔고 방어 및 반등 시 회복 추적
        """
        # 100,000원 -> 50,000원 (-50%) -> 100,000원 (+100%) 시계열
        crash_prices = [Decimal(str(int(100000 - i * 1000))) for i in range(51)]
        rebound_prices = [Decimal(str(int(50000 + i * 1000))) for i in range(51)]
        full_cycle = crash_prices + rebound_prices

        for p in full_cycle:
            # 5주씩 지속 매수
            engine_10m.execute_order("CRASH_TEST", OrderSide.BUY, 2, p)
            engine_10m.update_market_price("CRASH_TEST", p)

        # 잔고가 음수가 되지 않았는지 검증
        assert engine_10m.account.cash_balance >= Decimal("0")
        assert engine_10m.verify_accounting_invariant(
            initial_capital=Decimal("10000000"),
            current_market_prices={"CRASH_TEST": full_cycle[-1]}
        ) is True

    def test_scenario_4_exhaustion_bankruptcy_defensive_rejection(self, default_fee_config):
        """
        [Scenario 4] 파산 직전 한계 잔고 방어 및 음수 잔고 0건 검증
        - 소액 자본금(100만원)에서 잔고가 고갈될 때까지 무한 매수 시도
        - 잔고 부족 거절이 완벽히 작동하여 cash >= 0 항상 유지
        """
        acc = VirtualAccount(initial_cash=Decimal("1000000"))
        eng = MockExecutionEngine(account=acc, fee_config=default_fee_config)

        # 70,000원 주식을 잔고가 끝날 때까지 20회 연속 1주씩 매수
        for _ in range(20):
            eng.execute_order("005930", OrderSide.BUY, 1, Decimal("70000"))

        assert acc.cash_balance >= Decimal("0")
        assert eng.verify_accounting_invariant(
            initial_capital=Decimal("1000000"),
            current_market_prices={"005930": Decimal("70000")}
        ) is True

    def test_scenario_5_custom_complex_fee_tax_regime_simulation(self):
        """
        [Scenario 5] 복합 수수료/세율 커스텀 설정 시뮬레이션
        - 다양한 증권사 수수료율(0.004%, 0.015%, 0.05%) 및 세법 개정안(0.15%, 0.20%) 복합 검증
        """
        regimes = [
            FeeConfig(commission_rate=Decimal("0.00004"), tax_rate=Decimal("0.0015"), slippage_rate=Decimal("0.0005")),
            FeeConfig(commission_rate=Decimal("0.00015"), tax_rate=Decimal("0.0018"), slippage_rate=Decimal("0.0010")),
            FeeConfig(commission_rate=Decimal("0.00050"), tax_rate=Decimal("0.0020"), slippage_rate=Decimal("0.0020")),
        ]

        for idx, cfg in enumerate(regimes):
            acc = VirtualAccount(initial_cash=Decimal("5000000"))
            eng = MockExecutionEngine(account=acc, fee_config=cfg)
            sim = DummyStrategySimulator(engine=eng)

            res = sim.run_ping_pong(symbol=f"REGIME_{idx}", base_price=Decimal("50000"), quantity=5, iterations=100)
            assert res["invariant_passed"] is True
            assert acc.cash_balance >= Decimal("0")
