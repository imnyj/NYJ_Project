"""
Adversarial Stress Test Harness for Milestone 2: Data Engine & Resource Safety
Executed by Challenger 2 (Empirical Challenger)
"""

import gc
import os
import sys
import time
import math
import threading
import concurrent.futures
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Ensure project root in sys.path
sys.path.insert(0, "/home/imnyj/Workspace/Auto_Stock")

from modules.data.streamer import (
    CircularBuffer,
    RealtimeRingBuffer,
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
    clean_numeric_str,
    parse_korean_money,
)
from modules.data.collector_price import (
    NaverPriceFetcher,
    PriceDataCollector,
)
from modules.data.consolidator import (
    DataConsolidator,
)

results = {"passed": 0, "failed": 0, "errors": []}

def record_test(name, passed, detail=""):
    if passed:
        results["passed"] += 1
        print(f"  [PASS] {name} {detail}")
    else:
        results["failed"] += 1
        results["errors"].append(f"{name}: {detail}")
        print(f"  [FAIL] {name} {detail}")

print("================================================================================")
print("TEST SUITE 1: CircularBuffer Stress, Memory Ceiling & Concurrency")
print("================================================================================")

def test_circular_buffer_memory_ceiling_and_eviction():
    # 1. Test max_symbols bound under 5,000 unique symbol insertions
    buf = CircularBuffer(capacity_per_symbol=100, max_symbols=50)
    for i in range(5000):
        sym = f"{i:06d}"
        tick = TickData(timestamp=datetime.now(), symbol=sym, price=1000.0 + i, volume=10)
        buf.append(tick)
    
    current_syms = buf.symbols()
    sym_count = len(current_syms)
    total_sz = buf.total_size()
    record_test(
        "CircularBuffer.max_symbols eviction ceiling",
        sym_count == 50 and total_sz == 50,
        f"(expected 50 symbols & total 50 ticks, got {sym_count} symbols, {total_sz} total size)"
    )

def test_circular_buffer_high_concurrency_race_condition():
    # 2. 20 concurrent threads writing 50,000 ticks across 10 shared symbols
    buf = CircularBuffer(capacity_per_symbol=500, max_symbols=20)
    num_threads = 20
    ticks_per_thread = 2500
    
    def worker_writer(t_id):
        for i in range(ticks_per_thread):
            sym = f"00{t_id % 10:04d}"
            tick = TickData(
                timestamp=datetime.now(),
                symbol=sym,
                price=10000.0 + i,
                volume=i + 1
            )
            buf.append(tick)
            if i % 500 == 0:
                _ = buf.get_recent_ticks(sym, count=50)
                _ = buf.to_dataframe(sym, count=20)

    threads = [threading.Thread(target=worker_writer, args=(t,)) for t in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify per-symbol capacity ceiling
    all_valid = True
    for s in buf.symbols():
        sz = buf.size(s)
        if sz > 500:
            all_valid = False
            break
            
    record_test(
        "CircularBuffer multi-thread concurrent spam capacity integrity",
        all_valid and len(buf.symbols()) <= 10,
        f"(symbols: {len(buf.symbols())}, max single sym size: {max([buf.size(s) for s in buf.symbols()]) if buf.symbols() else 0})"
    )

def test_circular_buffer_concurrent_clear_and_eviction():
    # 3. Concurrent clear, remove_symbol, and reads while writing
    buf = CircularBuffer(capacity_per_symbol=200, max_symbols=30)
    stop_flag = threading.Event()
    exceptions = []

    def writer():
        i = 0
        while not stop_flag.is_set():
            sym = f"SYM{i % 40}"
            tick = TickData(timestamp=datetime.now(), symbol=sym, price=float(i), volume=1)
            buf.append(tick)
            i += 1

    def reader():
        while not stop_flag.is_set():
            try:
                for s in buf.symbols():
                    _ = buf.get_recent_ticks(s, count=100)
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
                    buf.remove_symbol(f"SYM{i % 40}")
                elif i % 5 == 0:
                    buf.clear(f"SYM{i % 40}")
                elif i % 11 == 0:
                    buf.clear()
            except Exception as e:
                exceptions.append(e)
            i += 1

    w_threads = [threading.Thread(target=writer) for _ in range(4)]
    r_threads = [threading.Thread(target=reader) for _ in range(4)]
    c_threads = [threading.Thread(target=cleaner) for _ in range(2)]

    for t in w_threads + r_threads + c_threads:
        t.start()

    time.sleep(0.5)
    stop_flag.set()

    for t in w_threads + r_threads + c_threads:
        t.join()

    record_test(
        "CircularBuffer concurrent reader/writer/cleaner race safety",
        len(exceptions) == 0,
        f"(exceptions caught: {len(exceptions)})"
    )

test_circular_buffer_memory_ceiling_and_eviction()
test_circular_buffer_high_concurrency_race_condition()
test_circular_buffer_concurrent_clear_and_eviction()

print("\n================================================================================")
print("TEST SUITE 2: Streamer Lifecycle, Rapid Thrashing & Zombie Thread Leak Audit")
print("================================================================================")

def test_streamer_rapid_thrashing_and_thread_cleanup():
    # 1. MockStreamer rapid start/stop (25 iterations)
    initial_threads = threading.active_count()
    ms = MockStreamer(tick_interval=0.01)
    
    for _ in range(25):
        ms.start()
        time.sleep(0.01)
        ms.stop()
        
    final_mock_threads = threading.active_count()
    record_test(
        "MockStreamer start/stop rapid thrashing thread leak check",
        abs(final_mock_threads - initial_threads) <= 1,
        f"(initial threads: {initial_threads}, final threads: {final_mock_threads})"
    )

    # 2. NaverPollingStreamer start/stop rapid thrashing (20 iterations)
    streamer = NaverPollingStreamer(poll_interval=0.1, timeout=1)
    streamer.subscribe("005930")
    
    for _ in range(20):
        streamer.start()
        time.sleep(0.01)
        streamer.stop()

    # Check active thread count and thread names
    active_threads = threading.enumerate()
    zombie_polling_threads = [t for t in active_threads if "NaverPollingStreamerThread" in t.name and t.is_alive()]
    
    record_test(
        "NaverPollingStreamer zombie thread leak check after 20 start/stop cycles",
        len(zombie_polling_threads) == 0,
        f"(zombie threads remaining: {len(zombie_polling_threads)})"
    )

    # 3. Context manager double close safety
    try:
        with NaverPollingStreamer(poll_interval=0.1, timeout=1) as s:
            s.subscribe("005930")
            s.start()
            time.sleep(0.05)
            s.stop()
        # Exiting context calls close() which calls stop() again
        s.close()
        s.stop()
        double_close_safe = True
    except Exception as e:
        double_close_safe = False

    record_test(
        "NaverPollingStreamer idempotent stop/close / context manager safety",
        double_close_safe,
        ""
    )

def test_streamer_listener_and_aggregator_exception_containment():
    # Test that malfunctioning listener/aggregator does not crash streamer or block other listeners
    streamer = MockStreamer(tick_interval=0.01)
    received_good = []

    def bad_listener(tick):
        raise RuntimeError("Simulated crash in external user callback!")

    def good_listener(tick):
        received_good.append(tick.price)

    streamer.add_listener(bad_listener)
    streamer.add_listener(good_listener)
    streamer.subscribe("005930")

    streamer.start()
    time.sleep(0.1)
    streamer.stop()

    record_test(
        "Streamer callback exception isolation (bad callback doesn't block good callback)",
        len(received_good) > 0,
        f"(good listener received {len(received_good)} ticks)"
    )

test_streamer_rapid_thrashing_and_thread_cleanup()
test_streamer_listener_and_aggregator_exception_containment()

print("\n================================================================================")
print("TEST SUITE 3: Financial Zero Break-even & Arithmetic Integrity")
print("================================================================================")

def test_financial_zero_break_even_calculations():
    # 1. FinancialStatement with operating_profit = 0 (Break-even)
    stmt_zero_op = FinancialStatement(
        ticker="005930",
        year=2024,
        revenue=100_000_000_000,
        operating_profit=0,
        net_income=0,
        total_assets=200_000_000_000,
        total_equity=100_000_000_000,
        total_liabilities=100_000_000_000,
    )
    d = stmt_zero_op.to_dict()
    record_test(
        "FinancialStatement 0 KRW operating_income in to_dict() preserved",
        d["operating_income"] == 0 and d["net_income"] == 0,
        f"(operating_income: {d['operating_income']}, net_income: {d['net_income']})"
    )

    # 2. OpenDartCollector._parse_account_list with 0 KRW operating profit & net income
    dart = OpenDartCollector()
    raw_dart_data = [
        {"rcept_no": "20240315000123", "account_nm": "매출액", "thstrm_amount": "50000000000"},
        {"rcept_no": "20240315000123", "account_nm": "영업이익", "thstrm_amount": "0"},
        {"rcept_no": "20240315000123", "account_nm": "당기순이익", "thstrm_amount": "0"},
        {"rcept_no": "20240315000123", "account_nm": "자산총계", "thstrm_amount": "100000000000"},
        {"rcept_no": "20240315000123", "account_nm": "자본총계", "thstrm_amount": "80000000000"},
        {"rcept_no": "20240315000123", "account_nm": "부채총계", "thstrm_amount": "20000000000"},
    ]
    parsed_dart = dart._parse_account_list(
        ticker="005930",
        year=2023,
        quarter=None,
        period_type=PeriodType.ANNUAL,
        raw_list=raw_dart_data
    )
    
    record_test(
        "OpenDartCollector parses 0 KRW OP/Net income into op_margin=0.0 & roe=0.0",
        parsed_dart.operating_profit == 0 and parsed_dart.op_margin == 0.0 and parsed_dart.roe == 0.0,
        f"(op: {parsed_dart.operating_profit}, op_margin: {parsed_dart.op_margin}, roe: {parsed_dart.roe})"
    )

    # 3. Division by Zero guards when revenue = 0 or total_equity = 0
    raw_dart_zero_rev = [
        {"rcept_no": "20240315000123", "account_nm": "매출액", "thstrm_amount": "0"},
        {"rcept_no": "20240315000123", "account_nm": "영업이익", "thstrm_amount": "0"},
        {"rcept_no": "20240315000123", "account_nm": "자본총계", "thstrm_amount": "0"},
    ]
    parsed_zero_rev = dart._parse_account_list(
        ticker="005930",
        year=2023,
        quarter=None,
        period_type=PeriodType.ANNUAL,
        raw_list=raw_dart_zero_rev
    )
    record_test(
        "OpenDartCollector zero revenue / zero equity division by zero safely returns None",
        parsed_zero_rev.op_margin is None and parsed_zero_rev.roe is None,
        f"(op_margin: {parsed_zero_rev.op_margin}, roe: {parsed_zero_rev.roe})"
    )

    # 4. Discrepancy calculation edge cases
    disc_0_0 = FundamentalCrossValidator.calculate_discrepancy(0, 0)
    disc_0_100 = FundamentalCrossValidator.calculate_discrepancy(0, 100)
    disc_none_none = FundamentalCrossValidator.calculate_discrepancy(None, None)
    disc_none_0 = FundamentalCrossValidator.calculate_discrepancy(None, 0)
    disc_nan_nan = FundamentalCrossValidator.calculate_discrepancy(float('nan'), float('nan'))

    disc_valid = (
        disc_0_0 == 0.0 and
        disc_0_100 == 100.0 and
        disc_none_none == 0.0 and
        disc_none_0 == 100.0 and
        disc_nan_nan == 0.0
    )
    record_test(
        "FundamentalCrossValidator.calculate_discrepancy edge cases (0/0, None/None, NaN/NaN)",
        disc_valid,
        f"(0/0: {disc_0_0}, 0/100: {disc_0_100}, None/None: {disc_none_none}, None/0: {disc_none_0}, NaN/NaN: {disc_nan_nan})"
    )

    # 5. Coalesce statement preserves 0-values in primary without overwriting from secondary
    primary_stmt = FinancialStatement(
        ticker="005930",
        year=2023,
        revenue=100_000_000_000,
        operating_profit=0,  # 0 is NOT None!
        net_income=None,     # missing
        per=None,            # missing
    )
    secondary_stmt = FinancialStatement(
        ticker="005930",
        year=2023,
        revenue=100_000_000_000,
        operating_profit=50_000_000_000,  # Should NOT overwrite primary 0!
        net_income=10_000_000_000,        # Should coalesce
        per=12.5,                         # Should coalesce
    )
    coalesced = FundamentalCrossValidator.coalesce_statements(primary_stmt, secondary_stmt)
    record_test(
        "FundamentalCrossValidator.coalesce_statements preserves 0 values in primary without overwriting",
        coalesced.operating_profit == 0 and coalesced.net_income == 10_000_000_000 and coalesced.per == 12.5,
        f"(operating_profit: {coalesced.operating_profit}, net_income: {coalesced.net_income}, per: {coalesced.per})"
    )

test_financial_zero_break_even_calculations()

print("\n================================================================================")
print("TEST SUITE 4: Price Engine & Consolidator PIT Multi-Stock Stress")
print("================================================================================")

def test_price_engine_and_consolidator_pit():
    # 1. validate_and_clean_ohlcv extreme noisy / corrupt values
    df_corrupt = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=5, freq="D"),
        "symbol": "005930",
        "open": [100.0, np.nan, 0.0, -50.0, 110.0],
        "high": [105.0, 110.0, 0.0, 120.0, 115.0],
        "low": [95.0, np.nan, 0.0, 80.0, 90.0],
        "close": [102.0, 108.0, 0.0, 115.0, 105.0],
        "volume": [1000, np.nan, -100, 2000, 1500],
        "timeframe": "1d"
    })

    cleaned, summary = PriceDataCollector.validate_and_clean_ohlcv(df_corrupt)
    # Check no 0 or negative prices, low <= min(o,h,c), high >= max(o,l,c)
    has_no_zero_or_neg_prices = (cleaned[["open", "high", "low", "close"]] > 0).all().all()
    valid_bounds = (cleaned["low"] <= cleaned[["open", "high", "close"]].min(axis=1) + 1e-5).all() and \
                   (cleaned["high"] >= cleaned[["open", "low", "close"]].max(axis=1) - 1e-5).all()

    record_test(
        "PriceDataCollector.validate_and_clean_ohlcv sanitizes 0/negative/NaN and maintains OHLC bounding invariants",
        has_no_zero_or_neg_prices and valid_bounds,
        f"(no 0/neg: {has_no_zero_or_neg_prices}, valid bounds: {valid_bounds})"
    )

    # 2. DataConsolidator multi-symbol PIT isolation under interleaved timestamps
    dates = pd.date_range("2024-01-01", "2024-06-30", freq="D")
    df_price_005930 = pd.DataFrame({
        "date": dates,
        "symbol": "005930",
        "open": 70000.0, "high": 71000.0, "low": 69000.0, "close": 70500.0, "volume": 10000
    })
    
    df_fund = pd.DataFrame([
        {
            "symbol": "005930",
            "period_end": pd.to_datetime("2023-12-31"),
            "announcement_date": pd.to_datetime("2024-03-31"), # 90 days
            "revenue": 300_000_000_000_000,
            "operating_income": 30_000_000_000_000,
            "net_income": 25_000_000_000_000,
            "per": 15.0,
            "pbr": 1.5,
            "roe": 10.0,
            "eps": 5000.0,
            "bps": 45000.0,
            "div_yield": 2.0,
            "assets": 400_000_000_000_000,
            "liabilities": 100_000_000_000_000,
            "equity": 300_000_000_000_000,
            "is_consensus": False,
            "source": "MOCK",
            "validation_status": "PASSED"
        },
        {
            "symbol": "000660",
            "period_end": pd.to_datetime("2023-12-31"),
            "announcement_date": pd.to_datetime("2024-03-15"), # earlier
            "revenue": 60_000_000_000_000,
            "operating_income": 10_000_000_000_000,
            "net_income": 8_000_000_000_000,
            "per": 8.0,
            "pbr": 2.0,
            "roe": 25.0,
            "eps": 20000.0,
            "bps": 80000.0,
            "div_yield": 1.0,
            "assets": 100_000_000_000_000,
            "liabilities": 30_000_000_000_000,
            "equity": 70_000_000_000_000,
            "is_consensus": False,
            "source": "MOCK",
            "validation_status": "PASSED"
        }
    ])

    consolidator = DataConsolidator()
    merged = consolidator.consolidate_point_in_time(
        price_df=df_price_005930,
        fundamental_df=df_fund,
        symbol="005930"
    )

    merged = merged.set_index("date")
    # Before announcement_date (2024-03-31), fundamental features must be NaN (no lookahead)
    before_ann = merged.loc[: "2024-03-30"]
    after_ann = merged.loc["2024-03-31":]

    no_lookahead = before_ann["operating_income"].isna().all()
    correct_post_ann = (after_ann["operating_income"] == 30_000_000_000_000).all()
    no_cross_contamination = (after_ann["operating_income"] != 10_000_000_000_000).all()

    record_test(
        "DataConsolidator strictly isolates 005930 fundamentals without cross-contamination from 000660 and strictly enforces PIT no-lookahead",
        no_lookahead and correct_post_ann and no_cross_contamination,
        f"(no lookahead: {no_lookahead}, correct after ann: {correct_post_ann}, no 000660 contamination: {no_cross_contamination})"
    )

test_price_engine_and_consolidator_pit()

print("\n================================================================================")
print(f"STRESS TEST SUMMARY: {results['passed']} PASSED, {results['failed']} FAILED")
print("================================================================================")
if results["failed"] > 0:
    print("FAILED TESTS:")
    for err in results["errors"]:
        print(f"  - {err}")
    sys.exit(1)
else:
    print("ALL EMPIRICAL CHALLENGES PASSED PERFECTLY.")
    sys.exit(0)
