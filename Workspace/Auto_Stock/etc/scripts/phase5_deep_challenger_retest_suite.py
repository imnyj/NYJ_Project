"""
etc/scripts/phase5_deep_challenger_retest_suite.py
=================================================
Independent Deep Stress & Adversarial Suite for Auto_Stock Phase 5 Screener Retest.
Executed by teamwork_preview_challenger_p5_1_retest.
"""

import math
import os
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.data.screener import (
    StockScreener,
    ScreeningCriteria,
    ShardedPollingScheduler,
    TokenBucketLimiter,
)
from modules.engine.live_learning_simulator import LiveLearningSimulator


def test_mangled_tick_structures():
    print("\n--- [Deep Test 1] Mangled Tick Structures ---")
    screener = StockScreener()
    screener.candidate_pool = ["005930", "000123"]
    screener.candidate_set = {"005930", "000123"}

    mangled_ticks = [
        ("None_tick", None),
        ("Empty_dict", {}),
        ("List_instead_of_dict", [1, 2, 3]),
        ("String_instead_of_dict", "tick_data_string"),
        ("None_symbol", {"symbol": None, "price": 75000, "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 10000}),
        ("Integer_symbol", {"symbol": 123, "price": 10500, "open_price": 10000, "accum_volume": 40000, "prev_same_time_volume": 10000}),
        ("Spaced_symbol", {"symbol": " 005930 ", "price": 75000, "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 10000}),
        ("Comma_string_price", {"symbol": "005930", "price": "75,000", "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 10000}),
        ("Complex_number_price", {"symbol": "005930", "price": complex(75000, 1), "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 10000}),
        ("Negative_accum_volume", {"symbol": "005930", "price": 75000, "open_price": 70000, "accum_volume": -100, "prev_same_time_volume": 10000}),
        ("Both_base_volumes_None", {"symbol": "005930", "price": 75000, "open_price": 70000, "accum_volume": 40000, "baseline_volume": None, "prev_same_time_volume": None}),
        ("Both_base_volumes_Zero", {"symbol": "005930", "price": 75000, "open_price": 70000, "accum_volume": 40000, "baseline_volume": 0, "prev_same_time_volume": 0}),
        ("String_timestamp", {"symbol": "005930", "price": 75000, "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 10000, "timestamp": "2026-09-03 10:00:00"}),
    ]

    crashes = []
    results = {}
    for name, tick in mangled_ticks:
        screener._last_triggered_time.clear()
        try:
            res = screener.check_intraday_trigger(tick)
            results[name] = res
        except Exception as e:
            crashes.append((name, f"{type(e).__name__}: {e}"))

    print(f"Mangled tests executed: {len(mangled_ticks)}, Crashes: {len(crashes)}")
    if crashes:
        for c in crashes:
            print(f"  FAIL: {c[0]} -> {c[1]}")
        return False

    # Check that integer symbol 123 was correctly normalized and triggered "000123"
    assert results["Integer_symbol"] == "000123", f"Expected '000123', got {results['Integer_symbol']}"
    # Check that spaced symbol " 005930 " was correctly stripped and triggered "005930"
    assert results["Spaced_symbol"] == "005930", f"Expected '005930', got {results['Spaced_symbol']}"
    # Check that invalid comma string safely returned None
    assert results["Comma_string_price"] is None
    # Check that complex number safely returned None
    assert results["Complex_number_price"] is None
    # Check that string timestamp did not crash and triggered "005930"
    assert results["String_timestamp"] == "005930"

    print("PASS: Mangled Tick Structures correctly handled.")
    return True


def test_malformed_dataframes():
    print("\n--- [Deep Test 2] Malformed & Degenerate DataFrames ---")
    screener = StockScreener()

    cases = [
        ("Empty_DF", pd.DataFrame()),
        ("Empty_Rows_With_Cols", pd.DataFrame(columns=["symbol", "market_cap", "per", "pbr"])),
        ("Missing_Symbol_Col", pd.DataFrame([{"market_cap": 1e12, "per": 10.0, "pbr": 1.0}])),
        ("All_NaN_MarketCap", pd.DataFrame([{"symbol": "005930", "market_cap": np.nan, "per": 10.0, "pbr": 1.0}])),
        ("All_Negative_MarketCap", pd.DataFrame([{"symbol": "005930", "market_cap": -1e12, "per": 10.0, "pbr": 1.0}])),
        ("String_MarketCap_Unparseable", pd.DataFrame([{"symbol": "005930", "market_cap": "천억원", "per": 10.0, "pbr": 1.0}])),
        ("String_MarketCap_Parseable", pd.DataFrame([{"symbol": "005930", "market_cap": "500000000000", "per": 10.0, "pbr": 1.0}])),
        ("Huge_PER_PBR_Boundary", pd.DataFrame([{"symbol": "005930", "market_cap": 5e11, "per": 15.000000001, "pbr": 2.0}])),
        ("Just_Below_PBR_Boundary", pd.DataFrame([{"symbol": "005930", "market_cap": 5e11, "per": 10.0, "pbr": 0.09999999}])),
    ]

    for name, df in cases:
        try:
            pool = screener.update_daily_static_pool(df)
            if name == "String_MarketCap_Parseable":
                assert pool == ["005930"], f"Expected ['005930'], got {pool}"
            elif name in ("Huge_PER_PBR_Boundary", "Just_Below_PBR_Boundary", "Empty_DF", "Empty_Rows_With_Cols", "Missing_Symbol_Col", "All_NaN_MarketCap", "All_Negative_MarketCap", "String_MarketCap_Unparseable"):
                assert pool == [], f"Expected empty pool for {name}, got {pool}"
            print(f"  PASS: {name} -> pool: {pool}")
        except Exception as e:
            print(f"  FAIL: {name} raised {type(e).__name__}: {e}")
            traceback.print_exc()
            return False

    print("PASS: Malformed DataFrames handled safely.")
    return True


def test_high_intensity_concurrency_100_threads():
    print("\n--- [Deep Test 3] 100-Thread Extreme Concurrency ---")
    screener = StockScreener()
    initial_symbols = [f"{i:06d}" for i in range(100)]
    screener.candidate_pool = list(initial_symbols)
    screener.candidate_set = set(initial_symbols)

    stop_event = threading.Event()
    exceptions = []
    counts = {"ticks": 0, "updates": 0, "reads": 0}
    counts_lock = threading.Lock()

    def tick_worker(tid):
        c = 0
        sym = f"{(tid % 100):06d}"
        tick = {
            "symbol": sym,
            "price": 10500.0,
            "open_price": 10000.0,
            "accum_volume": 40000,
            "prev_same_time_volume": 10000,
            "timestamp": datetime.now(),
        }
        while not stop_event.is_set():
            try:
                screener.check_intraday_trigger(tick)
                c += 1
            except Exception:
                exceptions.append(traceback.format_exc())
                break
        with counts_lock:
            counts["ticks"] += c

    def update_worker(tid):
        c = 0
        while not stop_event.is_set():
            try:
                df = pd.DataFrame([
                    {"symbol": f"{i:06d}", "market_cap": 200_000_000_000, "per": 10.0, "pbr": 1.0}
                    for i in range(50)
                ])
                screener.update_daily_static_pool(df)
                c += 1
                time.sleep(0.002)
            except Exception:
                exceptions.append(traceback.format_exc())
                break
        with counts_lock:
            counts["updates"] += c

    def read_worker(tid):
        c = 0
        while not stop_event.is_set():
            try:
                p = screener.get_candidate_pool()
                df = screener.get_candidate_df()
                chunks = screener.schedule_polling_chunks(chunk_size=5)
                c += 1
                time.sleep(0.002)
            except Exception:
                exceptions.append(traceback.format_exc())
                break
        with counts_lock:
            counts["reads"] += c

    threads = []
    for i in range(60):
        threads.append(threading.Thread(target=tick_worker, args=(i,)))
    for i in range(20):
        threads.append(threading.Thread(target=update_worker, args=(i,)))
    for i in range(20):
        threads.append(threading.Thread(target=read_worker, args=(i,)))

    t0 = time.time()
    for t in threads:
        t.daemon = True
        t.start()

    time.sleep(2.5)
    stop_event.set()

    deadlock = False
    for t in threads:
        t.join(timeout=4.0)
        if t.is_alive():
            deadlock = True

    elapsed = time.time() - t0
    print(f"100 threads ran for {elapsed:.2f}s. Deadlock: {deadlock}, Exceptions: {len(exceptions)}")
    print(f"Counts: {counts}")
    assert not deadlock, "Deadlock detected in 100 threads!"
    assert len(exceptions) == 0, f"Exceptions occurred: {exceptions[:2]}"
    print("PASS: 100-thread concurrency test succeeded with zero deadlocks and zero exceptions.")
    return True


def test_end_to_end_simulator_integration():
    print("\n--- [Deep Test 4] End-to-End Screener to LiveLearningSimulator Integration ---")
    screener = StockScreener()
    df_univ = pd.DataFrame([
        {"symbol": "005930", "market_cap": 500_000_000_000, "per": 10.0, "pbr": 1.0},
        {"symbol": "000660", "market_cap": 300_000_000_000, "per": 12.0, "pbr": 1.5},
    ])
    pool = screener.update_daily_static_pool(df_univ)
    assert pool == ["005930", "000660"]

    sim = LiveLearningSimulator(initial_cash=10_000_000)

    # 1. 틱 주입으로 트리거 유도
    tick_breakout = {
        "symbol": "005930",
        "price": 104000.0,
        "open_price": 100000.0,
        "accum_volume": 40000,
        "prev_same_time_volume": 10000,
        "timestamp": datetime.now(),
    }
    triggered_sym = screener.check_intraday_trigger(tick_breakout)
    assert triggered_sym == "005930"

    # 2. screener.route_trigger_to_simulator 검증
    success = screener.route_trigger_to_simulator(triggered_sym, sim, trigger_info=tick_breakout)
    assert success is True
    assert "005930" in sim.active_pool
    assert not sim.triggered_queue.empty()

    # 3. 14차원 obs 생성 확인
    obs = sim.build_rl_observation("005930")
    assert obs.shape == (14,)
    assert not np.isnan(obs).any()
    print("Simulator successfully integrated with Screener trigger.")
    print("PASS: End-to-End Simulator integration verified.")
    return True


if __name__ == "__main__":
    t1 = test_mangled_tick_structures()
    t2 = test_malformed_dataframes()
    t3 = test_high_intensity_concurrency_100_threads()
    t4 = test_end_to_end_simulator_integration()

    all_passed = t1 and t2 and t3 and t4
    print("\n" + "="*80)
    if all_passed:
        print("ALL DEEP ADVERSARIAL CHALLENGER TESTS PASSED (100% ROBUST)")
        sys.exit(0)
    else:
        print("DEEP ADVERSARIAL CHALLENGER TESTS FAILED")
        sys.exit(1)
