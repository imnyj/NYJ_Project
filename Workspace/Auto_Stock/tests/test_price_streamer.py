"""
tests/test_price_streamer.py
============================
Milestone 2 (Price Data Collector & Real-time Streamer) 종합 단위 테스트.

테스트 구성:
1. TestNaverPriceFetcher: 네이버 일봉 XML / 분봉 JSON 파싱, 날짜 필터링, 에러 핸들링
2. TestMockPriceFetcher: 가상 OHLCV 생성기 무결성 및 시드 재현성
3. TestPriceDataCollector: 표준 컬럼 검증, 다중 소스 Fallback, 타임프레임 리샘플링, 무결성 검증/정제
4. TestTickDataAndOrderbook: 틱 및 호가 데이터 모델 직렬화/역직렬화
5. TestCircularBuffer: 링 버퍼 동시성, 고정 용량(maxlen=50,000) 제한, 메모리 안전성
6. TestWindowBarAggregator: 틱-캔들 동적 집계, 윈도우 마감 콜백, OHLCV 산출 정확도
7. TestStreamers: MockStreamer 및 NaverPollingStreamer 생명주기 및 이벤트 전파
8. TestRealWorldLive: 실제 네이버 금융 엔드포인트(005930) 연결성 및 실데이터 정합성
"""

import threading
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import requests

from modules.data.collector_price import (
    BasePriceFetcher,
    FetchError,
    MockPriceFetcher,
    NaverPriceFetcher,
    PriceDataCollector,
    TimeFrame,
    ValidationError
)
from modules.data.streamer import (
    BarData,
    BaseStreamer,
    CircularBuffer,
    MockStreamer,
    NaverPollingStreamer,
    OrderbookData,
    OrderbookLevel,
    RealtimeRingBuffer,
    TickData,
    WindowBarAggregator
)


# ==========================================
# 1. TestNaverPriceFetcher
# ==========================================

class TestNaverPriceFetcher:
    """네이버 금융 수집기 단위 테스트"""

    @pytest.fixture
    def sample_daily_xml(self):
        """가상 일봉 EUC-KR XML 응답"""
        return (
            '<?xml version="1.0" encoding="EUC-KR" ?>\n'
            '<protocol>\n'
            '<chartdata symbol="005930" name="삼성전자" count="3" timeframe="day">\n'
            '  <item data="20260827|270000|271000|262500|266000|16829395" />\n'
            '  <item data="20260828|262500|266000|256000|257000|15106746" />\n'
            '  <item data="20260831|249000|260000|246000|260000|17009810" />\n'
            '</chartdata>\n'
            '</protocol>'
        ).encode("euc-kr")

    @pytest.fixture
    def sample_minute_json(self):
        """가상 분봉 JSON 응답"""
        return {
            "code": "005930",
            "infoType": "item",
            "periodType": "day",
            "priceInfos": [
                {
                    "localDateTime": "20260831090000",
                    "currentPrice": 249000.0,
                    "openPrice": 249000.0,
                    "highPrice": 250500.0,
                    "lowPrice": 248500.0,
                    "accumulatedTradingVolume": 709866
                },
                {
                    "localDateTime": "20260831090100",
                    "currentPrice": 248000.0,
                    "openPrice": 249000.0,
                    "highPrice": 249000.0,
                    "lowPrice": 247500.0,
                    "accumulatedTradingVolume": 833255
                },
                {
                    "localDateTime": "20260831090200",
                    "currentPrice": 248500.0,
                    "openPrice": 247750.0,
                    "highPrice": 249000.0,
                    "lowPrice": 247500.0,
                    "accumulatedTradingVolume": 1011776
                }
            ]
        }

    def test_daily_xml_parsing(self, sample_daily_xml):
        """EUC-KR 일봉 XML 응답 정상 파싱 검증"""
        fetcher = NaverPriceFetcher()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sample_daily_xml

        with patch.object(fetcher.session, "get", return_value=mock_response):
            df = fetcher.fetch_daily("005930", count=3)

        assert len(df) == 3
        assert list(df.columns) == [
            "date", "symbol", "open", "high", "low", "close", "volume",
            "value", "timeframe", "adj_factor", "is_trading_halt"
        ]
        assert df["symbol"].iloc[0] == "005930"
        assert df["close"].iloc[0] == 266000.0
        assert df["volume"].iloc[2] == 17009810
        assert df["date"].iloc[0] == pd.to_datetime("2026-08-27")

    def test_minute_json_parsing(self, sample_minute_json):
        """분봉 JSON 응답 정상 파싱 및 구간 거래량 차분 검증"""
        fetcher = NaverPriceFetcher()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_minute_json

        with patch.object(fetcher.session, "get", return_value=mock_response):
            df = fetcher.fetch_minute("005930")

        assert len(df) == 3
        assert df["volume"].iloc[0] == 709866
        # 두 번째 봉의 구간 거래량 = 833255 - 709866 = 123389
        assert df["volume"].iloc[1] == 123389
        # 세 번째 봉의 구간 거래량 = 1011776 - 833255 = 178521
        assert df["volume"].iloc[2] == 178521
        assert df["timeframe"].iloc[0] == "1m"

    def test_daily_date_filtering(self, sample_daily_xml):
        """start_date / end_date 필터링 동작 검증"""
        fetcher = NaverPriceFetcher()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sample_daily_xml

        with patch.object(fetcher.session, "get", return_value=mock_response):
            df = fetcher.fetch_daily("005930", start_date="2026-08-28", end_date="2026-08-30")

        assert len(df) == 1
        assert df["date"].iloc[0] == pd.to_datetime("2026-08-28")

    def test_symbol_normalization(self):
        """다양한 종목코드 형태('A005930', '5930', 5930) 정규화 검증"""
        fetcher = NaverPriceFetcher()
        assert fetcher._normalize_symbol("005930") == "005930"
        assert fetcher._normalize_symbol("A005930") == "005930"
        assert fetcher._normalize_symbol("5930") == "005930"

    def test_empty_response_handling(self):
        """빈 응답 수신 시 빈 데이터프레임 정상 반환"""
        fetcher = NaverPriceFetcher()
        empty_xml = (
            '<?xml version="1.0" encoding="EUC-KR" ?>\n'
            '<protocol><chartdata symbol="999999"></chartdata></protocol>'
        ).encode("euc-kr")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = empty_xml

        with patch.object(fetcher.session, "get", return_value=mock_response):
            df = fetcher.fetch_daily("999999")

        assert df.empty
        assert "date" in df.columns
        assert "close" in df.columns

    def test_network_failure_retry_and_raise(self):
        """네트워크 에러 시 지정된 재시도 횟수 후 FetchError 발생 검증"""
        fetcher = NaverPriceFetcher(max_retries=2, timeout=1, backoff_factor=1.0)
        with patch.object(fetcher.session, "get", side_effect=requests.exceptions.ConnectionError("Network Down")):
            with pytest.raises(FetchError):
                fetcher.fetch_daily("005930")


# ==========================================
# 2. TestMockPriceFetcher
# ==========================================

class TestMockPriceFetcher:
    """합성 데이터 생성기 단위 테스트"""

    def test_mock_daily_generation(self):
        """일봉 합성 데이터 스키마 및 정합성 검증"""
        fetcher = MockPriceFetcher(base_price=50000.0, seed=100)
        df = fetcher.fetch_daily("005930", count=30)

        assert len(df) == 30
        assert (df["high"] >= df["low"]).all()
        assert (df["high"] >= df["open"]).all()
        assert (df["high"] >= df["close"]).all()
        assert (df["low"] <= df["open"]).all()
        assert (df["low"] <= df["close"]).all()
        assert (df["volume"] > 0).all()
        assert df["timeframe"].iloc[0] == "1d"

    def test_mock_minute_generation(self):
        """분봉 합성 데이터 스키마 및 타임프레임 검증"""
        fetcher = MockPriceFetcher(base_price=50000.0, seed=100)
        df = fetcher.fetch_minute("005930", date="2026-08-31", timeframe="1m")

        assert len(df) == 391
        assert df["timeframe"].iloc[0] == "1m"
        assert df["date"].iloc[0].hour == 9
        assert df["date"].iloc[0].minute == 0

    def test_seed_reproducibility(self):
        """동일 시드 부여 시 동일한 데이터 재현성 검증"""
        f1 = MockPriceFetcher(seed=777)
        f2 = MockPriceFetcher(seed=777)

        df1 = f1.fetch_daily("005930", count=10)
        df2 = f2.fetch_daily("005930", count=10)

        pd.testing.assert_frame_equal(df1, df2)


# ==========================================
# 3. TestPriceDataCollector
# ==========================================

class TestPriceDataCollector:
    """PriceDataCollector 오케스트레이터 단위 테스트"""

    @pytest.fixture
    def sample_1m_df(self):
        """1분봉 10개 샘플 데이터프레임"""
        base_time = pd.to_datetime("2026-08-31 09:00:00")
        records = [
            # 09:00 ~ 09:04 (5개 1m 봉)
            {"date": base_time + timedelta(minutes=0), "symbol": "005930", "open": 100.0, "high": 105.0, "low": 98.0, "close": 102.0, "volume": 100, "value": 10200.0, "timeframe": "1m"},
            {"date": base_time + timedelta(minutes=1), "symbol": "005930", "open": 102.0, "high": 108.0, "low": 101.0, "close": 107.0, "volume": 200, "value": 21400.0, "timeframe": "1m"},
            {"date": base_time + timedelta(minutes=2), "symbol": "005930", "open": 107.0, "high": 110.0, "low": 106.0, "close": 109.0, "volume": 150, "value": 16350.0, "timeframe": "1m"},
            {"date": base_time + timedelta(minutes=3), "symbol": "005930", "open": 109.0, "high": 109.0, "low": 103.0, "close": 104.0, "volume": 80, "value": 8320.0, "timeframe": "1m"},
            {"date": base_time + timedelta(minutes=4), "symbol": "005930", "open": 104.0, "high": 106.0, "low": 100.0, "close": 105.0, "volume": 120, "value": 12600.0, "timeframe": "1m"},
            # 09:05 ~ 09:09 (5개 1m 봉)
            {"date": base_time + timedelta(minutes=5), "symbol": "005930", "open": 105.0, "high": 112.0, "low": 104.0, "close": 111.0, "volume": 300, "value": 33300.0, "timeframe": "1m"},
            {"date": base_time + timedelta(minutes=6), "symbol": "005930", "open": 111.0, "high": 115.0, "low": 110.0, "close": 114.0, "volume": 250, "value": 28500.0, "timeframe": "1m"},
            {"date": base_time + timedelta(minutes=7), "symbol": "005930", "open": 114.0, "high": 114.0, "low": 108.0, "close": 109.0, "volume": 110, "value": 11990.0, "timeframe": "1m"},
            {"date": base_time + timedelta(minutes=8), "symbol": "005930", "open": 109.0, "high": 110.0, "low": 107.0, "close": 108.0, "volume": 90, "value": 9720.0, "timeframe": "1m"},
            {"date": base_time + timedelta(minutes=9), "symbol": "005930", "open": 108.0, "high": 113.0, "low": 108.0, "close": 112.0, "volume": 180, "value": 20160.0, "timeframe": "1m"},
        ]
        return pd.DataFrame(records)

    def test_resample_ohlcv_accuracy(self, sample_1m_df):
        """
        1분봉 -> 5분봉 리샘플링 수학적 무결성 검증:
        - Open = 첫 번째 봉의 Open
        - High = 구간 최대 High
        - Low = 구간 최소 Low
        - Close = 마지막 봉의 Close
        - Volume = 구간 합산 Volume
        """
        df_5m = PriceDataCollector.resample_ohlcv(sample_1m_df, target_timeframe="5m")

        assert len(df_5m) == 2

        # 첫 번째 5분봉 (09:00:00)
        bar0 = df_5m.iloc[0]
        assert bar0["open"] == 100.0          # 09:00 open
        assert bar0["high"] == 110.0          # max(105, 108, 110, 109, 106)
        assert bar0["low"] == 98.0            # min(98, 101, 106, 103, 100)
        assert bar0["close"] == 105.0         # 09:04 close
        assert bar0["volume"] == 650          # 100 + 200 + 150 + 80 + 120
        assert bar0["timeframe"] == "5m"

        # 두 번째 5분봉 (09:05:00)
        bar1 = df_5m.iloc[1]
        assert bar1["open"] == 105.0          # 09:05 open
        assert bar1["high"] == 115.0          # max(112, 115, 114, 110, 113)
        assert bar1["low"] == 104.0           # min(104, 110, 108, 107, 108)
        assert bar1["close"] == 112.0         # 09:09 close
        assert bar1["volume"] == 930          # 300 + 250 + 110 + 90 + 180
        assert bar1["timeframe"] == "5m"

    def test_validate_and_clean_ohlcv_corrections(self):
        """데이터 무결성 검증 및 이상치 자동 교정 기능 검증"""
        corrupted_data = pd.DataFrame([
            # 정상 행
            {"date": "2026-08-25", "symbol": "005930", "open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0, "volume": 1000},
            # 중복 날짜 행 (이후 행이 유지되어야 함)
            {"date": "2026-08-25", "symbol": "005930", "open": 100.0, "high": 112.0, "low": 90.0, "close": 106.0, "volume": 1200},
            # High < Low 모순 행
            {"date": "2026-08-26", "symbol": "005930", "open": 105.0, "high": 95.0, "low": 110.0, "close": 100.0, "volume": 800},
            # 음수 거래량 행
            {"date": "2026-08-27", "symbol": "005930", "open": 100.0, "high": 105.0, "low": 95.0, "close": 100.0, "volume": -50},
            # 거래 정지일 (Volume == 0, Open == High == Low == Close)
            {"date": "2026-08-28", "symbol": "005930", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 0},
        ])

        cleaned, summary = PriceDataCollector.validate_and_clean_ohlcv(corrupted_data)

        assert summary["duplicates_removed"] == 1
        assert summary["anomalies_corrected"] >= 1
        assert summary["trading_halts_detected"] == 1
        assert len(cleaned) == 4

        # High >= Low 보장 확인
        assert (cleaned["high"] >= cleaned["low"]).all()
        assert (cleaned["volume"] >= 0).all()

        # 거래정지 행 플래그 확인
        halt_row = cleaned[cleaned["date"] == pd.to_datetime("2026-08-28")].iloc[0]
        assert halt_row["is_trading_halt"] is True or halt_row["is_trading_halt"] == 1

    def test_collector_fallback_mechanism(self):
        """Primary 수집기 실패 시 Secondary Fallback 자동 동작 검증"""
        failing_fetcher = MagicMock(spec=BasePriceFetcher)
        failing_fetcher.is_available.return_value = True
        failing_fetcher.fetch_daily.side_effect = Exception("API Outage")

        success_fetcher = MockPriceFetcher(base_price=70000.0, seed=42)

        collector = PriceDataCollector(fetchers=[failing_fetcher, success_fetcher])
        df = collector.get_daily_price("005930", count=5)

        assert len(df) == 5
        assert set(PriceDataCollector.STANDARD_COLUMNS).issubset(set(df.columns))


# ==========================================
# 4. TestTickDataAndOrderbook
# ==========================================

class TestTickDataAndOrderbook:
    """시세 데이터 구조체 단위 테스트"""

    def test_tick_data_serialization(self):
        """TickData to_dict 및 from_dict 양방향 변환 검증"""
        now = datetime.now()
        tick = TickData(
            timestamp=now,
            symbol="005930",
            price=260000.0,
            volume=50,
            accum_volume=17000000,
            side="BUY",
            bid_price=259900.0,
            ask_price=260100.0
        )

        d = tick.to_dict()
        assert d["price"] == 260000.0
        assert d["side"] == "BUY"

        restored = TickData.from_dict(d)
        assert restored.symbol == "005930"
        assert restored.price == 260000.0
        assert restored.volume == 50

    def test_orderbook_dataclass(self):
        """OrderbookData 구성 및 잔량 검증"""
        bids = [OrderbookLevel(price=259900.0, volume=1000), OrderbookLevel(price=259800.0, volume=2000)]
        asks = [OrderbookLevel(price=260100.0, volume=1500), OrderbookLevel(price=260200.0, volume=2500)]

        ob = OrderbookData(
            timestamp=datetime.now(),
            symbol="005930",
            bids=bids,
            asks=asks,
            total_bid_volume=3000,
            total_ask_volume=4000
        )

        assert len(ob.bids) == 2
        assert len(ob.asks) == 2
        assert ob.total_bid_volume == 3000


# ==========================================
# 5. TestCircularBuffer
# ==========================================

class TestCircularBuffer:
    """CircularBuffer 링 버퍼 단위 테스트"""

    def test_capacity_and_fifo_eviction(self):
        """최대 용량 초과 시 FIFO 방식으로 가장 오래된 틱 폐기 검증"""
        buf = CircularBuffer(capacity_per_symbol=5)
        base_time = datetime.now()

        for i in range(10):
            buf.append(TickData(
                timestamp=base_time + timedelta(seconds=i),
                symbol="005930",
                price=float(100 + i),
                volume=1
            ))

        assert buf.size("005930") == 5
        recent = buf.get_recent_ticks("005930", count=5)
        assert len(recent) == 5
        # 최근 5개: 105, 106, 107, 108, 109
        assert recent[0].price == 105.0
        assert recent[-1].price == 109.0

    def test_multi_symbol_isolation(self):
        """종목별 버퍼 격리 검증"""
        buf = CircularBuffer(capacity_per_symbol=100)
        buf.append(TickData(timestamp=datetime.now(), symbol="005930", price=70000.0, volume=10))
        buf.append(TickData(timestamp=datetime.now(), symbol="000660", price=150000.0, volume=20))

        assert buf.size("005930") == 1
        assert buf.size("000660") == 1
        assert buf.total_size() == 2
        assert set(buf.symbols()) == {"005930", "000660"}

    def test_thread_safe_concurrent_writes(self):
        """멀티스레드 동시 쓰기 환경에서 버퍼 무결성 및 경쟁 조건 방어 검증"""
        buf = CircularBuffer(capacity_per_symbol=10000)
        num_threads = 8
        ticks_per_thread = 500

        def worker(thread_idx):
            for i in range(ticks_per_thread):
                buf.append(TickData(
                    timestamp=datetime.now(),
                    symbol="005930",
                    price=float(thread_idx * 1000 + i),
                    volume=1
                ))

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert buf.size("005930") == num_threads * ticks_per_thread

    def test_to_dataframe_conversion(self):
        """to_dataframe 변환 결과 정합성 검증"""
        buf = CircularBuffer(capacity_per_symbol=10)
        buf.append(TickData(timestamp=datetime.now(), symbol="005930", price=70000.0, volume=10))
        df = buf.to_dataframe("005930")

        assert len(df) == 1
        assert df["symbol"].iloc[0] == "005930"
        assert df["price"].iloc[0] == 70000.0


# ==========================================
# 6. TestWindowBarAggregator
# ==========================================

class TestWindowBarAggregator:
    """틱-캔들 동적 집계기 단위 테스트"""

    def test_single_window_aggregation(self):
        """동일 윈도우 내 틱 누적 업데이트 검증"""
        agg = WindowBarAggregator(symbol="005930", interval_seconds=60)
        base_t = datetime(2026, 8, 31, 9, 0, 0)

        agg.process_tick(TickData(timestamp=base_t + timedelta(seconds=1), symbol="005930", price=100.0, volume=10))
        agg.process_tick(TickData(timestamp=base_t + timedelta(seconds=15), symbol="005930", price=110.0, volume=20))
        agg.process_tick(TickData(timestamp=base_t + timedelta(seconds=30), symbol="005930", price=95.0, volume=30))
        agg.process_tick(TickData(timestamp=base_t + timedelta(seconds=55), symbol="005930", price=105.0, volume=40))

        bar = agg.get_current_bar()
        assert bar is not None
        assert bar.open == 100.0
        assert bar.high == 110.0
        assert bar.low == 95.0
        assert bar.close == 105.0
        assert bar.volume == 100
        assert bar.tick_count == 4
        assert bar.is_closed is False

    def test_window_closure_and_callback(self):
        """다음 윈도우 틱 수신 시 이전 캔들 마감 및 콜백 호출 검증"""
        closed_events = []
        agg = WindowBarAggregator(
            symbol="005930",
            interval_seconds=60,
            on_bar_closed=lambda b: closed_events.append(b)
        )
        base_t = datetime(2026, 8, 31, 9, 0, 0)

        # 09:00:00 윈도우 틱
        agg.process_tick(TickData(timestamp=base_t + timedelta(seconds=10), symbol="005930", price=100.0, volume=10))
        agg.process_tick(TickData(timestamp=base_t + timedelta(seconds=40), symbol="005930", price=120.0, volume=15))

        # 09:01:00 윈도우 틱 -> 마감 트리거
        closed_bar = agg.process_tick(TickData(timestamp=base_t + timedelta(seconds=65), symbol="005930", price=115.0, volume=25))

        assert closed_bar is not None
        assert closed_bar.is_closed is True
        assert closed_bar.open == 100.0
        assert closed_bar.high == 120.0
        assert closed_bar.low == 100.0
        assert closed_bar.close == 120.0
        assert closed_bar.volume == 25
        assert len(closed_events) == 1

        # 새 캔들 상태 확인
        current_bar = agg.get_current_bar()
        assert current_bar.open == 115.0
        assert current_bar.volume == 25

    def test_force_close(self):
        """force_close 호출 시 진행 중인 캔들 즉시 마감 검증"""
        agg = WindowBarAggregator(symbol="005930", interval_seconds=60)
        base_t = datetime(2026, 8, 31, 9, 0, 0)
        agg.process_tick(TickData(timestamp=base_t + timedelta(seconds=10), symbol="005930", price=100.0, volume=10))

        closed = agg.force_close()
        assert closed is not None
        assert closed.is_closed is True
        assert agg.get_current_bar() is None


# ==========================================
# 7. TestStreamers
# ==========================================

class TestStreamers:
    """MockStreamer 및 NaverPollingStreamer 단위 테스트"""

    def test_mock_streamer_lifecycle_and_listeners(self):
        """MockStreamer 시작, 리스너 수신, 중지 생명주기 검증"""
        streamer = MockStreamer(tick_interval=0.02, volatility=0.001)
        received_ticks = []
        streamer.add_listener(lambda t: received_ticks.append(t))

        streamer.subscribe("005930")
        assert not streamer.is_running()

        streamer.start()
        assert streamer.is_running()

        time.sleep(0.15)
        streamer.stop()
        assert not streamer.is_running()

        assert len(received_ticks) >= 3
        assert streamer.get_latest_tick("005930") is not None

        cached_df = streamer.get_cached_window("005930", count=50)
        assert not cached_df.empty
        assert "price" in cached_df.columns

    def test_mock_streamer_generate_ticks(self):
        """일괄 가상 틱 생성 및 캔들 어그리게이터 연동 검증"""
        streamer = MockStreamer()
        agg = WindowBarAggregator(symbol="005930", interval_seconds=60)
        streamer.attach_aggregator(agg)

        start_t = datetime(2026, 8, 31, 9, 0, 0)
        ticks = streamer.generate_ticks(
            symbol="005930",
            count=150,
            start_price=70000.0,
            start_time=start_t,
            time_step_ms=1000  # 1초 간격 150틱 = 2분 30초 (2개 캔들 마감 + 1개 진행 중)
        )

        assert len(ticks) == 150
        closed_bars = agg.get_closed_bars()
        assert len(closed_bars) == 2
        assert closed_bars[0].is_closed is True
        assert closed_bars[1].is_closed is True

    def test_naver_polling_streamer_parsing(self):
        """네이버 폴링 응답 파싱 및 차분 거래량 산출 검증"""
        streamer = NaverPollingStreamer(poll_interval=1.0)
        streamer.subscribe("005930")

        mock_payload = {
            "datas": [{
                "itemCode": "005930",
                "stockName": "삼성전자",
                "closePriceRaw": "260000",
                "openPriceRaw": "249000",
                "highPriceRaw": "260000",
                "lowPriceRaw": "246000",
                "accumulatedTradingVolumeRaw": "17000000",
                "localTradedAt": "2026-08-31T15:30:00+09:00"
            }]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch.object(streamer.session, "get", return_value=mock_resp):
            ticks = streamer.poll_once()

        assert len(ticks) == 1
        assert ticks[0].price == 260000.0
        assert ticks[0].open_price == 249000.0
        assert ticks[0].high_price == 260000.0


# ==========================================
# 8. TestRealWorldLive (네이버 금융 실데이터 테스트)
# ==========================================

class TestRealWorldLive:
    """실제 네트워크 연결을 통한 네이버 금융 실데이터 수집 및 정합성 검증"""

    def test_live_naver_daily_fetch(self):
        """실제 네이버 일봉 엔드포인트 수집 (삼성전자 005930)"""
        fetcher = NaverPriceFetcher()
        if not fetcher.is_available():
            pytest.skip("네이버 금융 네트워크 엔드포인트 접근 불가")

        df = fetcher.fetch_daily("005930", count=5)
        assert not df.empty
        assert len(df) >= 3
        assert list(df.columns) == [
            "date", "symbol", "open", "high", "low", "close", "volume",
            "value", "timeframe", "adj_factor", "is_trading_halt"
        ]
        assert (df["high"] >= df["low"]).all()
        assert (df["volume"] > 0).all()

    def test_live_naver_minute_fetch(self):
        """실제 네이버 당일 분봉 엔드포인트 수집 (삼성전자 005930)"""
        fetcher = NaverPriceFetcher()
        if not fetcher.is_available():
            pytest.skip("네이버 금융 네트워크 엔드포인트 접근 불가")

        df = fetcher.fetch_minute("005930")
        assert not df.empty
        assert "date" in df.columns
        assert "close" in df.columns
        assert df["timeframe"].iloc[0] == "1m"

    def test_live_naver_polling(self):
        """실제 네이버 실시간 폴링 엔드포인트 수집 (삼성전자 005930)"""
        streamer = NaverPollingStreamer()
        streamer.subscribe("005930")
        ticks = streamer.poll_once()
        if not ticks:
            pytest.skip("장 마감 또는 네트워크 지연으로 실시간 틱 미수신")

        assert len(ticks) == 1
        assert ticks[0].symbol == "005930"
        assert ticks[0].price > 0


# ==========================================
# 9. TestEdgeCasesAndAnomalies
# ==========================================

class TestEdgeCasesAndAnomalies:
    """경계 조건, 결측치, 예외 방어 및 부가 기능 단위 테스트"""

    def test_circular_buffer_clear_and_get_all(self):
        """CircularBuffer clear 및 get_all 기능 검증"""
        buf = CircularBuffer(capacity_per_symbol=10)
        t1 = TickData(timestamp=datetime.now(), symbol="005930", price=100.0, volume=1)
        t2 = TickData(timestamp=datetime.now(), symbol="000660", price=200.0, volume=2)
        buf.extend([t1, t2])

        assert len(buf.get_all("005930")) == 1
        assert len(buf.get_all("000660")) == 1

        # 특정 종목만 clear
        buf.clear("005930")
        assert buf.size("005930") == 0
        assert buf.size("000660") == 1

        # 전체 clear
        buf.clear()
        assert buf.total_size() == 0

    def test_window_bar_aggregator_to_dataframe(self):
        """WindowBarAggregator to_dataframe 및 get_closed_bars 검증"""
        agg = WindowBarAggregator(symbol="005930", interval_seconds=60)
        base_t = datetime(2026, 8, 31, 9, 0, 0)
        agg.process_tick(TickData(timestamp=base_t, symbol="005930", price=100.0, volume=10))

        df = agg.to_dataframe()
        assert len(df) == 1
        assert df["symbol"].iloc[0] == "005930"
        assert df["open"].iloc[0] == 100.0

    def test_window_bar_aggregator_delayed_tick(self):
        """지연되어 도착한 과거 틱의 안전한 현재 캔들 병합 처리 검증"""
        agg = WindowBarAggregator(symbol="005930", interval_seconds=60)
        base_t = datetime(2026, 8, 31, 9, 0, 30)
        agg.process_tick(TickData(timestamp=base_t, symbol="005930", price=100.0, volume=10))

        # 10초 전 지연 틱 도착
        delayed_t = datetime(2026, 8, 31, 9, 0, 20)
        agg.process_tick(TickData(timestamp=delayed_t, symbol="005930", price=110.0, volume=5))

        bar = agg.get_current_bar()
        assert bar.high == 110.0
        assert bar.volume == 15

    def test_window_bar_aggregator_callback_exception_safety(self):
        """on_bar_closed 콜백 내부에서 예외 발생 시 어그리게이터 중단 없이 안전 처리 검증"""
        def faulty_callback(b):
            raise RuntimeError("Callback crash simulation")

        agg = WindowBarAggregator(symbol="005930", interval_seconds=60, on_bar_closed=faulty_callback)
        base_t = datetime(2026, 8, 31, 9, 0, 0)
        agg.process_tick(TickData(timestamp=base_t, symbol="005930", price=100.0, volume=10))

        # 새 윈도우 틱으로 마감 시도 -> 예외가 외부로 전파되지 않고 로깅됨
        closed = agg.process_tick(TickData(timestamp=base_t + timedelta(seconds=65), symbol="005930", price=105.0, volume=20))
        assert closed is not None
        assert closed.is_closed is True

    def test_streamer_unsubscribe_and_remove_listener(self):
        """구독 해제 및 리스너 제거 검증"""
        streamer = MockStreamer()
        streamer.subscribe("005930")
        assert "005930" in streamer._subscribed_symbols

        streamer.unsubscribe("005930")
        assert "005930" not in streamer._subscribed_symbols

        dummy_cb = lambda t: None
        streamer.add_listener(dummy_cb)
        assert dummy_cb in streamer._listeners
        streamer.remove_listener(dummy_cb)
        assert dummy_cb not in streamer._listeners

    def test_collector_get_minute_with_resampling(self):
        """PriceDataCollector에서 1m 데이터 수집 후 5m 리샘플링 통합 검증"""
        mock_fetcher = MockPriceFetcher(base_price=60000.0, seed=10)
        collector = PriceDataCollector(fetchers=[mock_fetcher])

        df_5m = collector.get_minute_price("005930", timeframe="5m")
        assert not df_5m.empty
        assert df_5m["timeframe"].iloc[0] == "5m"
        assert set(PriceDataCollector.STANDARD_COLUMNS).issubset(set(df_5m.columns))

    def test_validate_and_clean_empty_dataframe(self):
        """빈 DataFrame 검증 시 에러 없이 빈 결과와 요약 반환 검증"""
        empty_df = pd.DataFrame()
        cleaned, summary = PriceDataCollector.validate_and_clean_ohlcv(empty_df)
        assert cleaned.empty
        assert summary["final_rows"] == 0

    def test_timeframe_enum_values(self):
        """TimeFrame Enum 지원 값 확인"""
        assert TimeFrame.MINUTE_1.value == "1m"
        assert TimeFrame.MINUTE_5.value == "5m"
        assert TimeFrame.DAILY.value == "1d"

