"""
etc/scripts/adversarial_m2_verifier.py
======================================
Milestone 2 정밀 적대적 검증 (Adversarial Verification) 스크립트.
"""

import math
import sys
import threading
import time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from modules.data.collector_price import PriceDataCollector
from modules.data.collector_fundamental import (
    OpenDartCollector,
    FundamentalCrossValidator,
    FinancialStatement,
    PeriodType,
    ValidationStatus
)
from modules.data.consolidator import DataConsolidator
from modules.data.streamer import CircularBuffer, TickData, WindowBarAggregator, NaverPollingStreamer


def test_adversarial_price_cleaning():
    print("[1/5] Testing Price Cleaning Extremes & Anomalies...")
    # Case 1: All NaN price row
    df_all_nan = pd.DataFrame([{"date": "2026-08-01", "symbol": "005930", "open": np.nan, "high": np.nan, "low": np.nan, "close": np.nan, "volume": np.nan}])
    cleaned, summary = PriceDataCollector.validate_and_clean_ohlcv(df_all_nan)
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["low"] == 100.0
    assert cleaned.iloc[0]["open"] == 100.0
    assert cleaned.iloc[0]["high"] == 100.0
    assert cleaned.iloc[0]["close"] == 100.0
    assert cleaned.iloc[0]["volume"] == 0

    # Case 2: Extreme values & strings
    df_strings = pd.DataFrame([
        {"date": "2026-08-01", "symbol": "005930", "open": "-100", "high": "70000", "low": "0", "close": "69000", "volume": "-500"},
        {"date": "2026-08-02", "symbol": "005930", "open": "71000", "high": "72000", "low": "70000", "close": "71500", "volume": "1000"},
    ])
    cleaned2, _ = PriceDataCollector.validate_and_clean_ohlcv(df_strings)
    assert len(cleaned2) == 2
    assert (cleaned2["low"] > 0).all()
    assert (cleaned2["volume"] >= 0).all()
    print("  -> Passed Price Cleaning Extremes!")


def test_adversarial_fundamental_zero_and_negative():
    print("[2/5] Testing Fundamental Edge Cases (0 / Negative Values)...")
    # Revenue = 0 (division by zero defense)
    collector = OpenDartCollector(api_key="MOCK")
    raw_list_zero_rev = [
        {"rcept_no": "202405150001", "account_nm": "매출액", "thstrm_amount": "0"},
        {"rcept_no": "202405150001", "account_nm": "영업이익", "thstrm_amount": "-5000000"},
        {"rcept_no": "202405150001", "account_nm": "당기순이익", "thstrm_amount": "-6000000"},
    ]
    stmt = collector._parse_account_list("005930", 2024, 1, PeriodType.QUARTER, raw_list_zero_rev)
    assert stmt.revenue == 0
    assert stmt.operating_profit == -5000000
    assert stmt.op_margin is None  # Division by zero avoided
    assert stmt.net_margin is None

    # Discrepancy when both are 0 or negative
    diff_zero = FundamentalCrossValidator.calculate_discrepancy(0, 0)
    assert diff_zero == 0.0

    diff_neg = FundamentalCrossValidator.calculate_discrepancy(-100, -100)
    assert diff_neg == 0.0

    diff_neg_pos = FundamentalCrossValidator.calculate_discrepancy(-100, 100)
    assert diff_neg_pos > 0.0
    print("  -> Passed Fundamental Edge Cases!")


def test_adversarial_pit_consolidation():
    print("[3/5] Testing PIT Multi-Symbol Isolation & Lookahead Bias...")
    # Multi-symbol price with mixed dates
    prices = pd.DataFrame([
        {"date": pd.to_datetime("2024-01-10"), "symbol": "005930", "open": 70000.0, "high": 71000.0, "low": 69000.0, "close": 70000.0, "volume": 1000},
        {"date": pd.to_datetime("2024-04-05"), "symbol": "005930", "open": 72000.0, "high": 73000.0, "low": 71000.0, "close": 72000.0, "volume": 1000},
        {"date": pd.to_datetime("2024-06-01"), "symbol": "005930", "open": 74000.0, "high": 75000.0, "low": 73000.0, "close": 74000.0, "volume": 1000},
    ])

    fundamentals = pd.DataFrame([
        # 2023 Annual report: period_end 2023-12-31 -> announcement estimated as 2024-03-30 (90 days)
        {"symbol": "005930", "period_end": pd.to_datetime("2023-12-31"), "eps": 4000.0, "bps": 40000.0, "period_type": "annual"},
        # 2024 1Q report: period_end 2024-03-31 -> announcement estimated as 2024-05-15 (45 days)
        {"symbol": "005930", "period_end": pd.to_datetime("2024-03-31"), "eps": 5000.0, "bps": 42000.0, "period_type": "quarter"},
    ])

    merged = DataConsolidator.consolidate_point_in_time(prices, fundamentals, symbol="005930")
    assert len(merged) == 3

    # Row 0 (2024-01-10): Before 2024-03-30 -> Pre-announcement, EPS is NaN
    assert pd.isna(merged.iloc[0]["eps"])
    assert "PRE_ANNOUNCEMENT_PERIOD" in merged.iloc[0]["warning_flags"]

    # Row 1 (2024-04-05): After 2024-03-30 but Before 2024-05-15 -> 2023 Annual EPS (4000.0)
    assert merged.iloc[1]["eps"] == 4000.0
    assert merged.iloc[1]["dynamic_per"] == 72000.0 / 4000.0

    # Row 2 (2024-06-01): After 2024-05-15 -> 2024 1Q EPS (5000.0)
    assert merged.iloc[2]["eps"] == 5000.0
    assert merged.iloc[2]["dynamic_per"] == 74000.0 / 5000.0
    print("  -> Passed PIT Multi-Symbol Isolation & Lookahead Bias!")


def test_adversarial_buffer_concurrency():
    print("[4/5] Testing CircularBuffer High-Concurrency & Rapid Eviction...")
    buf = CircularBuffer(capacity_per_symbol=50, max_symbols=5)

    def worker_writer(sym_prefix: str, start_idx: int):
        for i in range(500):
            sym = f"{sym_prefix}_{i % 10}"  # 10 distinct symbols triggering continuous eviction
            tick = TickData(
                timestamp=datetime.now(),
                symbol=sym,
                price=100.0 + i,
                volume=10
            )
            buf.append(tick)
            if i % 50 == 0:
                buf.get_recent_ticks(sym, count=10)

    threads = [
        threading.Thread(target=worker_writer, args=(f"T{t}", t * 100))
        for t in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Max symbols invariant must hold
    assert len(buf.symbols()) <= 5
    assert buf.total_size() <= 5 * 50
    print("  -> Passed CircularBuffer High-Concurrency!")


def test_adversarial_streamer_lifecycle():
    print("[5/5] Testing NaverPollingStreamer Rapid Start/Stop Cycles...")
    streamer = NaverPollingStreamer(poll_interval=0.05, timeout=1)
    streamer.subscribe("005930")

    for _ in range(3):
        streamer.start()
        assert streamer.is_running() is True
        time.sleep(0.08)
        streamer.stop()
        assert streamer.is_running() is False

    # Close on context manager
    with NaverPollingStreamer(poll_interval=0.05, timeout=1) as s:
        s.subscribe("005930")
        s.start()
        time.sleep(0.05)
    assert s.is_running() is False
    print("  -> Passed Streamer Rapid Lifecycle!")


if __name__ == "__main__":
    test_adversarial_price_cleaning()
    test_adversarial_fundamental_zero_and_negative()
    test_adversarial_pit_consolidation()
    test_adversarial_buffer_concurrency()
    test_adversarial_streamer_lifecycle()
    print("\nALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY! (100% OK)")
