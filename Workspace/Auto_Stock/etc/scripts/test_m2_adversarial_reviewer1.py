"""
etc/scripts/test_m2_adversarial_reviewer1.py
Adversarial Stress-Testing Script for Milestone 2 by Reviewer 1
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import time
import threading
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from modules.data.collector_price import BasePriceFetcher, PriceDataCollector, NaverPriceFetcher, MockPriceFetcher
from modules.data.collector_fundamental import (
    OpenDartCollector, NaverFinanceCollector, MockKiwoomCollector,
    FundamentalDataCollector, FinancialStatement, PeriodType
)
from modules.data.consolidator import DataConsolidator
from modules.data.streamer import CircularBuffer, NaverPollingStreamer, MockStreamer, TickData
from modules.data.pipeline import DataCollectionPipeline

def test_price_cleaning_adversarial():
    print("Running Adversarial Test 1: Price Cleaning Extreme Cases...")
    
    # Extreme Case 1: All NaN
    df_all_nan = pd.DataFrame({
        "date": ["2026-08-01", "2026-08-02"],
        "symbol": ["005930", "005930"],
        "open": [np.nan, np.nan],
        "high": [np.nan, np.nan],
        "low": [np.nan, np.nan],
        "close": [np.nan, np.nan],
        "volume": [np.nan, np.nan],
    })
    clean_nan, _ = PriceDataCollector.validate_and_clean_ohlcv(df_all_nan)
    assert (clean_nan["low"] == 100.0).all()
    assert (clean_nan["high"] == 100.0).all()
    assert (clean_nan["volume"] == 0).all()

    # Extreme Case 2: Negative and Inf and 0 values
    df_extreme = pd.DataFrame({
        "date": ["2026-08-01", "2026-08-02", "2026-08-03"],
        "symbol": ["005930", "005930", "005930"],
        "open": [-1000.0, 0.0, 70000.0],
        "high": [np.nan, 71000.0, 71000.0],
        "low": [0.0, -50000.0, 69000.0],
        "close": [70000.0, 0.0, 70500.0],
        "volume": [-50, 1000, 2000],
    })
    clean_ext, _ = PriceDataCollector.validate_and_clean_ohlcv(df_extreme)
    assert (clean_ext["low"] > 0).all(), f"Low has non-positive values: {clean_ext['low']}"
    assert (clean_ext["high"] >= clean_ext["low"]).all()
    assert (clean_ext["volume"] >= 0).all()
    print("PASS: Adversarial Test 1")

def test_fundamental_zero_and_edge_adversarial():
    print("Running Adversarial Test 2: Fundamental Zero & Boundary Checks...")
    
    collector = OpenDartCollector(api_key="MOCK")
    
    # 0 Operating profit with positive revenue
    raw1 = [
        {"account_nm": "매출액", "thstrm_amount": "50,000,000,000"},
        {"account_nm": "영업이익", "thstrm_amount": "0"},
        {"account_nm": "당기순이익", "thstrm_amount": "0"},
        {"account_nm": "자산총계", "thstrm_amount": "100,000,000,000"},
        {"account_nm": "자본총계", "thstrm_amount": "50,000,000,000"},
    ]
    stmt1 = collector._parse_account_list("005930", 2024, 1, PeriodType.QUARTER, raw1)
    assert stmt1.op_margin == 0.0
    assert stmt1.net_margin == 0.0
    assert stmt1.roe == 0.0

    # 0 Revenue (Div by 0 prevention)
    raw2 = [
        {"account_nm": "매출액", "thstrm_amount": "0"},
        {"account_nm": "영업이익", "thstrm_amount": "0"},
        {"account_nm": "당기순이익", "thstrm_amount": "0"},
    ]
    stmt2 = collector._parse_account_list("005930", 2024, 1, PeriodType.QUARTER, raw2)
    assert stmt2.op_margin is None
    assert stmt2.net_margin is None

    # Negative Operating Profit
    raw3 = [
        {"account_nm": "매출액", "thstrm_amount": "100,000,000,000"},
        {"account_nm": "영업이익", "thstrm_amount": "-10,000,000,000"},
        {"account_nm": "당기순이익", "thstrm_amount": "-15,000,000,000"},
    ]
    stmt3 = collector._parse_account_list("005930", 2024, 1, PeriodType.QUARTER, raw3)
    assert stmt3.op_margin == -10.0
    assert stmt3.net_margin == -15.0
    print("PASS: Adversarial Test 2")

def test_pit_and_lookahead_adversarial():
    print("Running Adversarial Test 3: PIT & Lookahead Bias Stress Test...")
    
    # 3 stocks
    prices = pd.DataFrame([
        {"date": "2024-03-14", "symbol": "005930", "open": 70000, "high": 71000, "low": 69000, "close": 70000, "volume": 1000},
        {"date": "2024-03-15", "symbol": "005930", "open": 71000, "high": 72000, "low": 70000, "close": 71000, "volume": 1000},
        {"date": "2024-03-16", "symbol": "005930", "open": 72000, "high": 73000, "low": 71000, "close": 72000, "volume": 1000},
    ])
    
    # Mixed fundamental data with different announcement dates
    funds = pd.DataFrame([
        {"symbol": "005930", "announcement_date": "2024-03-15", "eps": 5000.0, "bps": 50000.0},
        {"symbol": "000660", "announcement_date": "2024-03-14", "eps": 99999.0, "bps": 999999.0}, # Contaminant
    ])
    
    merged = DataConsolidator.consolidate_point_in_time(prices, funds, symbol="005930")
    
    # Pre-announcement (2024-03-14) must have NaN eps / PRE_ANNOUNCEMENT_PERIOD
    assert pd.isna(merged.iloc[0]["eps"])
    assert "PRE_ANNOUNCEMENT_PERIOD" in merged.iloc[0]["warning_flags"]
    
    # Post-announcement (2024-03-15, 2024-03-16) must have 005930 EPS (5000.0), NOT 000660 EPS (99999.0)
    assert merged.iloc[1]["eps"] == 5000.0
    assert merged.iloc[2]["eps"] == 5000.0
    assert (merged["eps"] != 99999.0).all()
    
    # Leap year period end date
    fund_leap = pd.DataFrame([
        {"symbol": "005930", "period_end": "2024-02-29", "eps": 4000.0, "bps": 40000.0}
    ])
    merged_leap = DataConsolidator.consolidate_point_in_time(prices, fund_leap, symbol="005930")
    assert not merged_leap.empty
    print("PASS: Adversarial Test 3")

def test_concurrency_and_ringbuffer_adversarial():
    print("Running Adversarial Test 4: Concurrency & RingBuffer Memory Safety...")
    
    buf = CircularBuffer(capacity_per_symbol=50, max_symbols=5)
    errors = []
    
    def writer_task(thread_id):
        try:
            for i in range(200):
                sym = f"SYM_{(thread_id * 10 + i) % 20:03d}"
                tick = TickData(
                    timestamp=datetime.now(),
                    symbol=sym,
                    price=1000.0 + i,
                    volume=10
                )
                buf.append(tick)
        except Exception as e:
            errors.append(e)
            
    threads = [threading.Thread(target=writer_task, args=(tid,)) for tid in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    assert len(errors) == 0, f"Concurrency errors: {errors}"
    assert len(buf.symbols()) <= 5, f"Buffer exceeded max_symbols: {len(buf.symbols())}"
    print("PASS: Adversarial Test 4")

def test_context_manager_exception_safety():
    print("Running Adversarial Test 5: Context Manager Exception Safety...")
    
    fetcher_closed = False
    class CustomFetcher(BasePriceFetcher):
        def fetch_daily(self, *args, **kwargs): return pd.DataFrame()
        def fetch_minute(self, *args, **kwargs): return pd.DataFrame()
        def is_available(self): return True
        def close(self):
            nonlocal fetcher_closed
            fetcher_closed = True
            
    try:
        with CustomFetcher() as f:
            raise RuntimeError("Intentional error inside with block")
    except RuntimeError:
        pass
        
    assert fetcher_closed is True, "Fetcher close() was not called on exception!"
    
    # Test DataCollectionPipeline Context Manager
    with DataCollectionPipeline() as p:
        pass
    print("PASS: Adversarial Test 5")

if __name__ == "__main__":
    test_price_cleaning_adversarial()
    test_fundamental_zero_and_edge_adversarial()
    test_pit_and_lookahead_adversarial()
    test_concurrency_and_ringbuffer_adversarial()
    test_context_manager_exception_safety()
    print("\nALL ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY!")
