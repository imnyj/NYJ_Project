"""
tests/test_adversarial_m2_challenger2.py
========================================
Milestone 2 (Data Engine & Resource Safety) Adversarial & Stress Test Suite.
Authored by Challenger 2 (Empirical Challenger).

Verification coverage:
1. CircularBuffer: Extreme memory bounds, max_symbols eviction, multi-threaded contention, race-condition safety
2. Streamer: Rapid start/stop thrashing, zombie thread leak audit, listener exception containment, idempotent closure
3. Financial Engine: 0 KRW operating profit break-even calculations, division-by-zero guards, coalesce preservation
4. PIT Consolidator: Multi-stock isolation and strict Point-In-Time timestamp bounding
"""

import math
import threading
import time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pytest

from modules.data.streamer import (
    CircularBuffer,
    TickData,
    BarData,
    WindowBarAggregator,
    MockStreamer,
    NaverPollingStreamer,
)
from modules.data.collector_fundamental import (
    FinancialStatement,
    PeriodType,
    ValidationStatus,
    FundamentalCrossValidator,
    OpenDartCollector,
    NaverFinanceCollector,
    MockKiwoomCollector,
    FundamentalDataCollector,
)
from modules.data.collector_price import (
    PriceDataCollector,
    NaverPriceFetcher,
)
from modules.data.consolidator import (
    DataConsolidator,
)


class TestAdversarialCircularBuffer:
    """CircularBuffer 메모리 상한 및 고빈도 멀티스레드 동시성 스트레스 검증"""

    def test_max_symbols_memory_ceiling_under_high_variety_churn(self):
        """5,000개 이상의 유니크 종목 유입 시 max_symbols 한도를 넘지 않고 메모리 폭주를 원천 차단하는지 검증"""
        buf = CircularBuffer(capacity_per_symbol=100, max_symbols=50)
        for i in range(5000):
            sym = f"{i:06d}"
            tick = TickData(timestamp=datetime.now(), symbol=sym, price=1000.0 + i, volume=10)
            buf.append(tick)

        assert len(buf.symbols()) == 50
        assert buf.total_size() == 50
        # Check that old symbols were evicted and newest ones remain
        assert "004999" in buf.symbols()
        assert "000000" not in buf.symbols()

    def test_high_concurrency_race_condition_and_capacity_cap(self):
        """20개 스레드에서 50,000건의 틱을 동시 난사할 때 버퍼 용량 상한 초과 및 락 경합 무결성 검증"""
        buf = CircularBuffer(capacity_per_symbol=300, max_symbols=15)
        num_threads = 20
        ticks_per_thread = 2000

        def worker(t_id):
            for i in range(ticks_per_thread):
                sym = f"00{t_id % 10:04d}"
                tick = TickData(timestamp=datetime.now(), symbol=sym, price=50000.0 + i, volume=i + 1)
                buf.append(tick)
                if i % 400 == 0:
                    _ = buf.get_recent_ticks(sym, count=50)
                    _ = buf.to_dataframe(sym, count=20)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(buf.symbols()) <= 10
        for sym in buf.symbols():
            assert buf.size(sym) <= 300

    def test_concurrent_read_write_remove_clear_race_safety(self):
        """쓰기/읽기/종목제거/전체초기화가 동시 다발적으로 발생할 때 데드락이나 예외 없이 안전한지 검증"""
        buf = CircularBuffer(capacity_per_symbol=100, max_symbols=20)
        stop_flag = threading.Event()
        exceptions = []

        def writer():
            i = 0
            while not stop_flag.is_set():
                sym = f"S{i % 30}"
                buf.append(TickData(timestamp=datetime.now(), symbol=sym, price=float(i), volume=1))
                i += 1

        def reader():
            while not stop_flag.is_set():
                try:
                    for s in buf.symbols():
                        _ = buf.get_recent_ticks(s, count=50)
                        _ = buf.get_latest_tick(s)
                        _ = buf.to_dataframe(s)
                except Exception as e:
                    exceptions.append(e)

        def cleaner():
            i = 0
            while not stop_flag.is_set():
                time.sleep(0.005)
                try:
                    if i % 3 == 0:
                        buf.remove_symbol(f"S{i % 30}")
                    elif i % 5 == 0:
                        buf.clear(f"S{i % 30}")
                    elif i % 11 == 0:
                        buf.clear()
                except Exception as e:
                    exceptions.append(e)
                i += 1

        workers = (
            [threading.Thread(target=writer) for _ in range(4)] +
            [threading.Thread(target=reader) for _ in range(4)] +
            [threading.Thread(target=cleaner) for _ in range(2)]
        )

        for t in workers:
            t.start()
        time.sleep(0.3)
        stop_flag.set()
        for t in workers:
            t.join()

        assert len(exceptions) == 0, f"Exceptions caught in concurrent circular buffer operations: {exceptions}"


class TestAdversarialStreamerLifecycleAndSafety:
    """스트리머의 라이프사이클 반복, 좀비 스레드 방지 및 결함 격리 검증"""

    def test_rapid_start_stop_thrashing_no_zombie_threads(self):
        """NaverPollingStreamer를 20회 연속 고속 start/stop 시 좀비 스레드가 남지 않는지 검증"""
        streamer = NaverPollingStreamer(poll_interval=0.05, timeout=1)
        streamer.subscribe("005930")

        for _ in range(20):
            streamer.start()
            time.sleep(0.01)
            streamer.stop()

        active_threads = threading.enumerate()
        zombies = [t for t in active_threads if "NaverPollingStreamerThread" in t.name and t.is_alive()]
        assert len(zombies) == 0, f"Found {len(zombies)} zombie polling threads after start/stop thrashing!"

    def test_idempotent_closure_and_context_manager(self):
        """close 및 stop의 멱등성 및 컨텍스트 매니저 정상 종료 검증"""
        with NaverPollingStreamer(poll_interval=0.1, timeout=1) as s:
            s.subscribe("005930")
            s.start()
            time.sleep(0.02)
            s.stop()

        # Double close/stop outside context
        s.close()
        s.stop()
        assert not s.is_running()

    def test_faulty_listener_callback_exception_containment(self):
        """사용자 리스너 콜백에서 예외가 발생해도 스트리머 스레드가 중단되지 않고 타 리스너로 정상 전파되는지 검증"""
        streamer = MockStreamer(tick_interval=0.01)
        received_ticks = []

        def failing_callback(tick: TickData):
            raise ValueError("Simulated listener exception!")

        def healthy_callback(tick: TickData):
            received_ticks.append(tick)

        streamer.add_listener(failing_callback)
        streamer.add_listener(healthy_callback)
        streamer.subscribe("005930")

        streamer.start()
        time.sleep(0.08)
        streamer.stop()

        assert len(received_ticks) > 0


class TestAdversarialFinancialBreakEvenAndMathIntegrity:
    """0원 손익분기점, 영/결측 분모 방어 및 교차검증 병합 무결성 검증"""

    def test_zero_operating_profit_break_even_parsed_correctly(self):
        """영업이익 0원(손익분기) 시 Falsy 처리로 누락되지 않고 op_margin=0.0%로 정확히 산출되는지 검증"""
        dart = OpenDartCollector()
        raw_dart = [
            {"rcept_no": "20240315000123", "account_nm": "매출액", "thstrm_amount": "10000000000"},
            {"rcept_no": "20240315000123", "account_nm": "영업이익", "thstrm_amount": "0"},
            {"rcept_no": "20240315000123", "account_nm": "당기순이익", "thstrm_amount": "0"},
            {"rcept_no": "20240315000123", "account_nm": "자본총계", "thstrm_amount": "5000000000"},
        ]
        parsed = dart._parse_account_list(
            ticker="005930",
            year=2023,
            quarter=None,
            period_type=PeriodType.ANNUAL,
            raw_list=raw_dart
        )

        assert parsed.operating_profit == 0
        assert parsed.net_income == 0
        assert parsed.op_margin == 0.0
        assert parsed.net_margin == 0.0
        assert parsed.roe == 0.0

    def test_zero_denominator_division_by_zero_safety(self):
        """매출액=0 또는 자본총계=0일 때 ZeroDivisionError 없이 안전하게 None으로 처리되는지 검증"""
        dart = OpenDartCollector()
        raw_dart = [
            {"rcept_no": "20240315000123", "account_nm": "매출액", "thstrm_amount": "0"},
            {"rcept_no": "20240315000123", "account_nm": "영업이익", "thstrm_amount": "0"},
            {"rcept_no": "20240315000123", "account_nm": "자본총계", "thstrm_amount": "0"},
        ]
        parsed = dart._parse_account_list(
            ticker="005930",
            year=2023,
            quarter=None,
            period_type=PeriodType.ANNUAL,
            raw_list=raw_dart
        )

        assert parsed.op_margin is None
        assert parsed.roe is None

    def test_coalesce_statements_preserves_zero_value_in_primary(self):
        """1차 소스의 0원 값이 결측(None)으로 오인되어 2차 소스 값으로 덮어씌워지지 않는지 검증"""
        primary = FinancialStatement(
            ticker="005930",
            year=2023,
            revenue=100_000_000_000,
            operating_profit=0,  # Valid break-even 0
            net_income=None,     # Missing
            per=None             # Missing
        )
        secondary = FinancialStatement(
            ticker="005930",
            year=2023,
            revenue=100_000_000_000,
            operating_profit=20_000_000_000,
            net_income=10_000_000_000,
            per=15.0
        )

        coalesced = FundamentalCrossValidator.coalesce_statements(primary, secondary)
        assert coalesced.operating_profit == 0
        assert coalesced.net_income == 10_000_000_000
        assert coalesced.per == 15.0


class TestAdversarialConsolidatorAndPITIsolation:
    """다중 종목 PIT 병합 격리 및 선행 편향 차단 검증"""

    def test_multi_symbol_fundamental_cross_talk_defense(self):
        """서로 다른 종목의 펀더멘털 데이터가 병합 시 교차 오염되지 않고 자기 종목 데이터만 정확히 결합되는지 검증"""
        dates = pd.date_range("2024-01-01", "2024-06-30", freq="D")
        df_price = pd.DataFrame({
            "date": dates,
            "symbol": "005930",
            "open": 70000.0, "high": 71000.0, "low": 69000.0, "close": 70000.0, "volume": 1000
        })

        df_fund = pd.DataFrame([
            {
                "symbol": "005930",
                "period_end": pd.to_datetime("2023-12-31"),
                "announcement_date": pd.to_datetime("2024-03-31"),
                "operating_income": 50_000_000_000,
                "eps": 5000.0,
                "bps": 50000.0,
                "roe": 10.0,
                "is_consensus": False,
                "source": "DART",
                "validation_status": "PASSED"
            },
            {
                "symbol": "000660",
                "period_end": pd.to_datetime("2023-12-31"),
                "announcement_date": pd.to_datetime("2024-02-15"),
                "operating_income": 99_999_999_999,
                "eps": 25000.0,
                "bps": 80000.0,
                "roe": 30.0,
                "is_consensus": False,
                "source": "DART",
                "validation_status": "PASSED"
            }
        ])

        consolidator = DataConsolidator()
        merged = consolidator.consolidate_point_in_time(
            price_df=df_price,
            fundamental_df=df_fund,
            symbol="005930"
        )
        merged = merged.set_index("date")

        # Prior to announcement date, features must be NaN
        assert merged.loc[:"2024-03-30", "operating_income"].isna().all()
        # Post announcement date, features must match 005930 exactly, NEVER 000660
        post_ann = merged.loc["2024-03-31":, "operating_income"]
        assert (post_ann == 50_000_000_000).all()
        assert not (post_ann == 99_999_999_999).any()
