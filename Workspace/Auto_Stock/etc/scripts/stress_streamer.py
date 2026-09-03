"""
etc/scripts/stress_streamer.py
==============================
Auto Stock Phase 1 제1 적대적 스트레스 실측 벤치마크 스크립트.

검증 항목:
1. 100,000 틱 멀티스레드 링버퍼 메모리/처리량 실측
2. 100,000 틱 캔들 집계기 산술 불변성 및 레이턴시 실측
3. 52,500개 1분봉 + 불규칙 공시일자 선행 편향(Look-Ahead Bias) 전수 검사
4. 교차 검증기 10개 극한 경계치 오차율 실측
"""

import gc
import json
import math
import os
import pathlib
import sys
import threading
import time
import tracemalloc
from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from modules.data.collector_fundamental import (
    FinancialStatement,
    FundamentalCrossValidator,
    ValidationStatus,
)
from modules.data.consolidator import DataConsolidator
from modules.data.streamer import (
    BarData,
    CircularBuffer,
    TickData,
    WindowBarAggregator,
)


def run_cross_validation_stress() -> Dict[str, Any]:
    print("=== [1/4] Running CrossValidator Adversarial Stress Test ===")
    validator = FundamentalCrossValidator(warning_threshold=5.0, critical_threshold=10.0)
    
    base = 10_000_000.0
    test_cases = [
        ("0% Error", base, base, ValidationStatus.PASSED, 0.0),
        ("4.999% Boundary", base, base / (1.0 - 0.04999), ValidationStatus.PASSED, 4.999),
        ("5.001% Boundary", base, base / (1.0 - 0.05001), ValidationStatus.WARNING, 5.001),
        ("9.999% Boundary", base, base / (1.0 - 0.09999), ValidationStatus.WARNING, 9.999),
        ("10.001% Boundary", base, base / (1.0 - 0.10001), ValidationStatus.CRITICAL_DISCREPANCY, 10.001),
        ("1000% Extreme", base, base * 10.0, ValidationStatus.CRITICAL_DISCREPANCY, 90.0),
        ("Zero vs Zero", 0.0, 0.0, ValidationStatus.PASSED, 0.0),
        ("Zero vs 100", 0.0, 100.0, ValidationStatus.CRITICAL_DISCREPANCY, 99.9999),
        ("None vs 100", None, 100.0, None, 100.0),
        ("NaN vs 100", float("nan"), 100.0, None, 100.0),
    ]
    
    results = []
    for name, v1, v2, exp_status, exp_diff in test_cases:
        diff = validator.calculate_discrepancy(v1, v2)
        status = None
        if v1 is not None and v2 is not None and not math.isnan(float(v1)) and not math.isnan(float(v2)):
            s1 = FinancialStatement(ticker="005930", year=2024, quarter=1, revenue=int(v1))
            s2 = FinancialStatement(ticker="005930", year=2024, quarter=1, revenue=int(v2))
            rep = validator.validate_statements(s1, s2, metrics_to_compare=["revenue"])
            status = rep.status.value
            
        passed = (status == exp_status.value) if exp_status else True
        results.append({
            "case": name,
            "val_a": v1,
            "val_b": v2,
            "calculated_diff_pct": diff,
            "status": status,
            "passed": passed
        })
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}: diff={diff:.4f}%, status={status}")

    return {"results": results, "all_passed": all(r["passed"] for r in results)}


def run_lookahead_bias_stress() -> Dict[str, Any]:
    print("\n=== [2/4] Running Look-Ahead Bias 52.5k-Minute PIT Merge Stress Test ===")
    total_bars = 52500  # 52,500 1-minute bars (~36.45 days)
    start_ts = pd.Timestamp("2024-01-02 09:00:00")
    timestamps = [start_ts + timedelta(minutes=i) for i in range(total_bars)]
    
    np.random.seed(42)
    close_prices = 70000.0 + np.cumsum(np.random.normal(0, 30, total_bars))
    price_df = pd.DataFrame({
        "date": timestamps,
        "symbol": "005930",
        "open": close_prices,
        "high": close_prices + 50,
        "low": close_prices - 50,
        "close": close_prices,
        "volume": np.random.randint(10, 500, total_bars),
    })

    announcements = [
        {"announcement_date": pd.Timestamp("2024-01-10 17:30:00"), "eps": 1000.0, "revenue": 70_000},
        {"announcement_date": pd.Timestamp("2024-01-18 08:45:00"), "eps": 1100.0, "revenue": 72_000},
        {"announcement_date": pd.Timestamp("2024-01-26 14:15:30"), "eps": 1250.0, "revenue": 75_000},
        {"announcement_date": pd.Timestamp("2024-02-03 16:00:00"), "eps": 1400.0, "revenue": 80_000},
    ]
    fund_df = pd.DataFrame(announcements)
    fund_df["symbol"] = "005930"

    t0 = time.perf_counter()
    consolidated = DataConsolidator.consolidate_point_in_time(
        price_df=price_df,
        fundamental_df=fund_df,
        symbol="005930"
    )
    t_merge = time.perf_counter() - t0

    leakage_count = 0
    ann_dates = [a["announcement_date"] for a in announcements]

    for _, row in consolidated.iterrows():
        d = row["date"]
        rev = row.get("revenue")
        eps = row.get("eps")

        if d < ann_dates[0]:
            if pd.notna(rev) or pd.notna(eps):
                leakage_count += 1
        elif ann_dates[0] <= d < ann_dates[1]:
            if rev != announcements[0]["revenue"] or eps != announcements[0]["eps"]:
                leakage_count += 1
        elif ann_dates[1] <= d < ann_dates[2]:
            if rev != announcements[1]["revenue"] or eps != announcements[1]["eps"]:
                leakage_count += 1
        elif ann_dates[2] <= d < ann_dates[3]:
            if rev != announcements[2]["revenue"] or eps != announcements[2]["eps"]:
                leakage_count += 1
        else:
            if rev != announcements[3]["revenue"] or eps != announcements[3]["eps"]:
                leakage_count += 1

    leakage_rate = (leakage_count / len(consolidated)) * 100.0
    print(f"  Processed {len(consolidated):,} bars in {t_merge:.3f}s")
    print(f"  Leakage Count: {leakage_count} / {len(consolidated):,}")
    print(f"  Leakage Rate: {leakage_rate:.5f}% (TARGET: 0.00000%)")

    return {
        "total_bars": len(consolidated),
        "merge_time_sec": t_merge,
        "leakage_count": leakage_count,
        "leakage_rate_pct": leakage_rate,
        "is_safe": (leakage_count == 0)
    }


def run_streamer_100k_multithread_stress() -> Dict[str, Any]:
    print("\n=== [3/4] Running 100k-Tick Multithreaded Streamer Memory & Invariants Stress Test ===")
    tracemalloc.start()
    gc.collect()

    capacity = 50000
    ring_buffer = CircularBuffer(capacity_per_symbol=capacity)
    total_ticks = 100000
    num_threads = 10
    ticks_per_thread = total_ticks // num_threads
    symbol = "005930"
    start_time = datetime(2024, 1, 1, 9, 0, 0)

    def worker(tid: int):
        for i in range(ticks_per_thread):
            seq = tid * ticks_per_thread + i
            tick = TickData(
                timestamp=start_time + timedelta(milliseconds=seq * 50),
                symbol=symbol,
                price=70000.0 + (seq % 500),
                volume=10 + (seq % 10),
                accum_volume=seq * 10
            )
            ring_buffer.append(tick)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    t_inject = time.perf_counter() - t0

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    final_size = ring_buffer.size(symbol)
    df = ring_buffer.to_dataframe(symbol)
    throughput = total_ticks / t_inject

    print(f"  Injected {total_ticks:,} ticks across {num_threads} threads in {t_inject:.3f}s")
    print(f"  Throughput: {throughput:,.1f} ticks/sec")
    print(f"  Final RingBuffer Size: {final_size:,} / {capacity:,} (Fixed Memory Cap)")
    print(f"  Peak Memory: {peak_mem / (1024 * 1024):.2f} MB")
    print(f"  DataFrame Converted Rows: {len(df):,}")

    return {
        "total_ticks": total_ticks,
        "threads": num_threads,
        "elapsed_sec": t_inject,
        "throughput_ticks_sec": throughput,
        "ringbuffer_size": final_size,
        "capacity_limit": capacity,
        "peak_memory_mb": peak_mem / (1024 * 1024),
        "is_bounded_memory": (final_size == capacity)
    }


def run_window_aggregator_invariants_stress() -> Dict[str, Any]:
    print("\n=== [4/4] Running 100k-Tick WindowBarAggregator Mathematical Invariants Test ===")
    symbol = "005930"
    
    aggregator = WindowBarAggregator(
        symbol=symbol,
        interval_seconds=60,
        timeframe_name="1m"
    )

    total_ticks = 100000
    start_ts = datetime(2024, 1, 1, 9, 0, 0)
    np.random.seed(999)
    prices = 70000.0 + np.cumsum(np.random.normal(0, 5, total_ticks))
    volumes = np.random.randint(1, 50, total_ticks)

    total_injected_vol = int(np.sum(volumes))
    total_injected_val = float(np.sum(prices * volumes))

    t0 = time.perf_counter()
    for i in range(total_ticks):
        ts = start_ts + timedelta(milliseconds=i * 100)
        tick = TickData(
            timestamp=ts,
            symbol=symbol,
            price=float(prices[i]),
            volume=int(volumes[i])
        )
        aggregator.process_tick(tick)

    aggregator.force_close()
    closed_bars = aggregator.get_closed_bars()
    t_agg = time.perf_counter() - t0

    # Invariants verification
    ohlc_valid = all(
        (b.high >= b.open) and (b.high >= b.close) and (b.high >= b.low) and
        (b.low <= b.open) and (b.low <= b.close) and (b.low <= b.high)
        for b in closed_bars
    )
    sum_vol = sum(b.volume for b in closed_bars)
    sum_val = sum(b.value for b in closed_bars)
    sum_ticks = sum(b.tick_count for b in closed_bars)

    vol_preserved = (sum_vol == total_injected_vol)
    val_preserved = math.isclose(sum_val, total_injected_val, rel_tol=1e-5)
    ticks_preserved = (sum_ticks == total_ticks)

    print(f"  Processed {total_ticks:,} ticks -> {len(closed_bars)} 1m bars in {t_agg:.3f}s")
    print(f"  Aggregation Rate: {total_ticks / t_agg:,.1f} ticks/sec")
    print(f"  [1] OHLC Invariant Valid: {ohlc_valid}")
    print(f"  [2] Volume Conservation: {vol_preserved} ({sum_vol:,} == {total_injected_vol:,})")
    print(f"  [3] Value Conservation: {val_preserved} ({sum_val:,.1f} == {total_injected_val:,.1f})")
    print(f"  [4] Tick Count Conservation: {ticks_preserved} ({sum_ticks:,} == {total_ticks:,})")

    all_invariants_pass = ohlc_valid and vol_preserved and val_preserved and ticks_preserved
    return {
        "total_ticks": total_ticks,
        "generated_bars": len(closed_bars),
        "aggregation_time_sec": t_agg,
        "ohlc_valid": ohlc_valid,
        "volume_conserved": vol_preserved,
        "value_conserved": val_preserved,
        "tick_count_conserved": ticks_preserved,
        "all_pass": all_invariants_pass
    }


if __name__ == "__main__":
    t_start_all = time.perf_counter()
    r1 = run_cross_validation_stress()
    r2 = run_lookahead_bias_stress()
    r3 = run_streamer_100k_multithread_stress()
    r4 = run_window_aggregator_invariants_stress()
    t_total = time.perf_counter() - t_start_all

    all_passed = r1["all_passed"] and r2["is_safe"] and r3["is_bounded_memory"] and r4["all_pass"]
    verdict = "APPROVE" if all_passed else "FAIL"

    summary = {
        "timestamp": datetime.now().isoformat(),
        "final_verdict": verdict,
        "total_elapsed_sec": t_total,
        "cross_validator": r1,
        "lookahead_bias": r2,
        "streamer_ringbuffer": r3,
        "window_aggregator": r4
    }

    log_path = pathlib.Path("/home/imnyj/Workspace/Auto_Stock/etc/logs/stress_benchmark.log")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"🏁 FINAL ADVERSARIAL VERDICT: [{verdict}] (Total Time: {t_total:.3f}s)")
    print(f"Detailed log saved to: {log_path}")
    print("=" * 60)
