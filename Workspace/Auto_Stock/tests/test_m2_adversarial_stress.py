"""
tests/test_m2_adversarial_stress.py
===================================
Challenger 1 Adversarial Stress Test Suite for Milestone 2.
Extreme stress scenarios, edge cases, boundary conditions, and concurrency safety.
"""

import math
import threading
import time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pytest
import requests

from modules.data.collector_price import (
    BasePriceFetcher,
    NaverPriceFetcher,
    MockPriceFetcher,
    PriceDataCollector
)
from modules.data.collector_fundamental import (
    BaseFundamentalSource,
    OpenDartCollector,
    NaverFinanceCollector,
    MockKiwoomCollector,
    FundamentalDataCollector,
    FundamentalCrossValidator,
    FinancialStatement,
    PeriodType,
    ValidationStatus,
    clean_numeric_str,
    parse_korean_money
)
from modules.data.consolidator import DataConsolidator
from modules.data.streamer import (
    BaseStreamer,
    CircularBuffer,
    WindowBarAggregator,
    NaverPollingStreamer,
    MockStreamer,
    TickData,
    BarData
)
from modules.data.pipeline import DataCollectionPipeline


class TestAdversarialPriceCleaning:
    """주가 데이터 정제 관련 극한 스트레스 테스트"""

    def test_all_nans_and_zeros_dataframe(self):
        """모든 OHLCV 값이 NaN, 0, 음수로 가득 찬 데이터프레임 방어"""
        raw_df = pd.DataFrame([
            {"date": "2026-08-01", "symbol": "005930", "open": np.nan, "high": 0.0, "low": -100.0, "close": np.nan, "volume": -50},
            {"date": "2026-08-02", "symbol": "005930", "open": -500.0, "high": np.nan, "low": 0.0, "close": -10.0, "volume": np.nan},
            {"date": "2026-08-03", "symbol": "005930", "open": None, "high": None, "low": None, "close": None, "volume": "malformed"},
        ])

        cleaned_df, summary = PriceDataCollector.validate_and_clean_ohlcv(raw_df)

        assert len(cleaned_df) == 3
        # 모든 가격 컬럼이 양수(기본값 100.0)로 보정되어야 함
        for col in ['open', 'high', 'low', 'close']:
            assert (cleaned_df[col] > 0.0).all()
            assert not cleaned_df[col].isna().any()
        # low <= open <= high, low <= close <= high 무결성
        assert (cleaned_df['low'] <= cleaned_df['high']).all()
        assert (cleaned_df['volume'] >= 0).all()
        assert cleaned_df['volume'].dtype == int

    def test_inverted_high_low_extreme_anomaly(self):
        """high가 low보다 훨씬 낮거나 open/close가 범위를 벗어난 이상치 교정"""
        raw_df = pd.DataFrame([
            {"date": "2026-08-01", "symbol": "005930", "open": 75000.0, "high": 50000.0, "low": 90000.0, "close": 80000.0, "volume": 1000},
        ])

        cleaned_df, summary = PriceDataCollector.validate_and_clean_ohlcv(raw_df)

        row = cleaned_df.iloc[0]
        assert row['high'] == 90000.0  # max(75000, 50000, 90000, 80000)
        assert row['low'] == 50000.0   # min(75000, 50000, 90000, 80000)
        assert row['low'] <= row['open'] <= row['high']
        assert row['low'] <= row['close'] <= row['high']
        assert summary['anomalies_corrected'] >= 1

    def test_resample_ohlcv_edge_cases(self):
        """리샘플링 시 빈 데이터프레임 및 단일 행, 비정규 타임프레임 처리"""
        # 빈 DataFrame
        empty_df = pd.DataFrame(columns=['date', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'timeframe'])
        resampled_empty = PriceDataCollector.resample_ohlcv(empty_df, target_timeframe='5m')
        assert resampled_empty.empty

        # 1분봉 데이터
        dates = pd.date_range("2026-08-01 09:00:00", periods=10, freq="1min")
        df_1m = pd.DataFrame({
            "date": dates,
            "symbol": "005930",
            "open": [70000 + i * 100 for i in range(10)],
            "high": [70500 + i * 100 for i in range(10)],
            "low": [69500 + i * 100 for i in range(10)],
            "close": [70200 + i * 100 for i in range(10)],
            "volume": [100] * 10,
            "timeframe": "1m"
        })

        res_5m = PriceDataCollector.resample_ohlcv(df_1m, target_timeframe='5m')
        assert len(res_5m) == 2
        assert res_5m.iloc[0]['open'] == 70000
        assert res_5m.iloc[0]['volume'] == 500
        assert res_5m.iloc[0]['timeframe'] == '5m'


class TestAdversarialFundamentalEngine:
    """펀더멘털 엔진 및 교차 검증 스트레스 테스트"""

    def test_clean_numeric_str_adversarial_inputs(self):
        """특수 문자, 결측치, 무한대 등 극한 입력에 대한 clean_numeric_str 안전성"""
        assert clean_numeric_str(None) is None
        assert clean_numeric_str(float('nan')) is None
        assert clean_numeric_str("-") is None
        assert clean_numeric_str("N/A") is None
        assert clean_numeric_str("null") is None
        assert clean_numeric_str("1,234,567원") == 1234567.0
        assert clean_numeric_str(" -12.34% ") == -12.34
        assert clean_numeric_str("15.5배") == 15.5
        assert clean_numeric_str("invalid_text") is None

    def test_parse_korean_money_adversarial_inputs(self):
        """한국어 화폐 표기 파싱 극한 케이스"""
        assert parse_korean_money(None) is None
        assert parse_korean_money("") is None
        assert parse_korean_money("1조 5,000억") == 1_500_000_000_000
        assert parse_korean_money("300조") == 300_000_000_000_000
        assert parse_korean_money("500만") == 5_000_000
        assert parse_korean_money("70,000") == 70000

    def test_zero_division_and_infinite_margin_defense(self):
        """매출액=0, 자본총계=0, 자산총계=0 등 0 나누기 유발 조건 방어"""
        collector = OpenDartCollector(api_key="TEST_KEY")

        raw_list = [
            {"rcept_no": "202405150001", "account_nm": "매출액", "thstrm_amount": "0"},
            {"rcept_no": "202405150001", "account_nm": "영업이익", "thstrm_amount": "50,000,000"},
            {"rcept_no": "202405150001", "account_nm": "당기순이익", "thstrm_amount": "30,000,000"},
            {"rcept_no": "202405150001", "account_nm": "자산총계", "thstrm_amount": "0"},
            {"rcept_no": "202405150001", "account_nm": "자본총계", "thstrm_amount": "0"},
        ]

        stmt = collector._parse_account_list(
            ticker="005930",
            year=2024,
            quarter=1,
            period_type=PeriodType.QUARTER,
            raw_list=raw_list
        )

        # 매출액 0 -> op_margin, net_margin이 None이어야 하며 ZeroDivisionError 발생하지 않아야 함
        assert stmt.op_margin is None
        assert stmt.net_margin is None
        # 자본총계 0 -> roe, debt_ratio None
        assert stmt.roe is None
        assert stmt.roa is None

    def test_cross_validator_extreme_discrepancy(self):
        """교차 검증기 부호 불일치, 0 vs 양수, NaN vs 정상치 등 극한 비교"""
        validator = FundamentalCrossValidator(warning_threshold=5.0, critical_threshold=10.0)

        # 0과 0 비교 -> 0.0%
        assert validator.calculate_discrepancy(0, 0) == 0.0
        # None과 None -> 0.0%
        assert validator.calculate_discrepancy(None, None) == 0.0
        # None과 수치 -> 100.0%
        assert validator.calculate_discrepancy(None, 100) == 100.0
        # 100과 100 -> 0.0%
        assert validator.calculate_discrepancy(100, 100) == 0.0
        # 100과 -100 (부호 반대) -> 200%에 가까운 오차
        assert validator.calculate_discrepancy(100, -100) >= 100.0


class TestAdversarialPITConsolidation:
    """Point-in-Time 병합 및 파생 피처 산출 스트레스 테스트"""

    def test_multi_symbol_unordered_and_duplicate_dates(self):
        """다중 종목 주가 및 중복/무작위 순서 공시일 병합 시 데이터 무결성 검증"""
        prices = pd.DataFrame([
            {"date": pd.to_datetime("2024-06-01"), "symbol": "005930", "open": 70000.0, "high": 71000.0, "low": 69500.0, "close": 70000.0, "volume": 1000},
            {"date": pd.to_datetime("2024-04-01"), "symbol": "005930", "open": 68000.0, "high": 69000.0, "low": 67500.0, "close": 68500.0, "volume": 1000},
            {"date": pd.to_datetime("2024-05-16"), "symbol": "005930", "open": 69000.0, "high": 70000.0, "low": 68500.0, "close": 69500.0, "volume": 1000},
        ])

        # 공시일이 무작위 순서로 입력된 펀더멘털 데이터
        fundamentals = pd.DataFrame([
            {"symbol": "005930", "announcement_date": pd.to_datetime("2024-05-15"), "eps": 5500.0, "bps": 52000.0},
            {"symbol": "005930", "announcement_date": pd.to_datetime("2024-03-15"), "eps": 5000.0, "bps": 50000.0},
            {"symbol": "000660", "announcement_date": pd.to_datetime("2024-05-20"), "eps": 15000.0, "bps": 95000.0},
        ])

        merged = DataConsolidator.consolidate_point_in_time(prices, fundamentals, symbol="005930")

        # 시간순 정렬 확인 (2024-04-01, 2024-05-16, 2024-06-01)
        assert len(merged) == 3
        assert list(merged['date']) == sorted(list(merged['date']))

        # 2024-04-01: 2024-03-15 공시(EPS 5000) 매핑
        assert merged.iloc[0]['eps'] == 5000.0
        # 2024-05-16: 2024-05-15 공시(EPS 5500) 매핑
        assert merged.iloc[1]['eps'] == 5500.0
        # 2024-06-01: 2024-05-15 공시(EPS 5500) 유지 (000660 공시 오염 없음)
        assert merged.iloc[2]['eps'] == 5500.0

    def test_dynamic_valuation_with_zero_or_negative_metrics(self):
        """EPS <= 0 (적자), BPS <= 0 (완전자본잠식)일 때 Dynamic PER/PBR이 NaN으로 안전 처리되는지 검증"""
        prices = pd.DataFrame([
            {"date": pd.to_datetime("2024-05-20"), "symbol": "005930", "open": 70000.0, "high": 71000.0, "low": 69500.0, "close": 70000.0, "volume": 1000},
        ])
        fundamentals = pd.DataFrame([
            {"symbol": "005930", "announcement_date": pd.to_datetime("2024-05-15"), "eps": -1500.0, "bps": 0.0, "operating_profit": -500000000}
        ])

        merged = DataConsolidator.consolidate_point_in_time(prices, fundamentals, symbol="005930")

        assert np.isnan(merged.iloc[0]['dynamic_per'])
        assert np.isnan(merged.iloc[0]['dynamic_pbr'])
        assert "NEGATIVE_EPS" in merged.iloc[0]['warning_flags']
        assert "OPERATING_LOSS" in merged.iloc[0]['warning_flags']


class TestAdversarialConcurrencyAndResources:
    """동시성, 멀티스레드 부하 및 리소스 해제 스트레스 테스트"""

    def test_circular_buffer_multithreaded_high_throughput(self):
        """10개 스레드가 동시에 대량의 틱을 주입/조회할 때 CircularBuffer의 Deadlock 및 경합 방어"""
        buf = CircularBuffer(capacity_per_symbol=1000, max_symbols=5)
        symbols = ["005930", "000660", "035420", "035720", "005380", "051910", "006400"]
        errors = []

        def worker_append(worker_id: int):
            try:
                for i in range(500):
                    sym = symbols[i % len(symbols)]
                    tick = TickData(
                        timestamp=datetime.now(),
                        symbol=sym,
                        price=50000.0 + i,
                        volume=10
                    )
                    buf.append(tick)
            except Exception as e:
                errors.append(e)

        def worker_read(worker_id: int):
            try:
                for i in range(500):
                    sym = symbols[i % len(symbols)]
                    _ = buf.get_recent_ticks(sym, count=50)
                    _ = buf.get_latest_tick(sym)
                    _ = buf.to_dataframe(sym, count=20)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t1 = threading.Thread(target=worker_append, args=(i,))
            t2 = threading.Thread(target=worker_read, args=(i,))
            threads.extend([t1, t2])

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert len(errors) == 0, f"Errors in concurrent circular buffer: {errors}"
        assert len(buf.symbols()) <= 5

    def test_naver_polling_streamer_rapid_start_stop_cycles(self):
        """NaverPollingStreamer를 빠르게 start/stop 반복 시 좀비 스레드 및 세션 누수 없음 검증"""
        for _ in range(3):
            streamer = NaverPollingStreamer(poll_interval=0.05, timeout=1)
            streamer.subscribe("005930")
            streamer.start()
            assert streamer.is_running() is True
            time.sleep(0.1)
            streamer.stop()
            assert streamer.is_running() is False
            assert streamer._thread is None or not streamer._thread.is_alive()

    def test_window_bar_aggregator_out_of_order_and_rapid_ticks(self):
        """WindowBarAggregator에 시간 역순 틱 및 다수 틱 유입 시 캔들 계산 정합성"""
        closed_bars = []
        agg = WindowBarAggregator(
            symbol="005930",
            interval_seconds=60,
            on_bar_closed=lambda b: closed_bars.append(b)
        )

        base_time = datetime(2026, 8, 1, 9, 0, 0)

        # 9:00:10 틱 100주 @ 70000
        agg.process_tick(TickData(timestamp=base_time + timedelta(seconds=10), symbol="005930", price=70000.0, volume=100))
        # 9:00:30 틱 50주 @ 71000
        agg.process_tick(TickData(timestamp=base_time + timedelta(seconds=30), symbol="005930", price=71000.0, volume=50))
        # 9:00:20 (지연 수신 틱) 30주 @ 69000
        agg.process_tick(TickData(timestamp=base_time + timedelta(seconds=20), symbol="005930", price=69000.0, volume=30))

        # 다음 윈도우 시작 (9:01:05) -> 이전 캔들 마감
        closed = agg.process_tick(TickData(timestamp=base_time + timedelta(seconds=65), symbol="005930", price=70500.0, volume=80))

        assert closed is not None
        assert len(closed_bars) == 1
        b1 = closed_bars[0]
        assert b1.open == 70000.0
        assert b1.high == 71000.0
        assert b1.low == 69000.0
        assert b1.close == 69000.0 or b1.close == 71000.0  # 지연 틱 반영
        assert b1.volume == 180  # 100 + 50 + 30
        assert b1.is_closed is True
