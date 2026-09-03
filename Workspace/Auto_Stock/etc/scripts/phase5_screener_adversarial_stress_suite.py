"""
etc/scripts/phase5_screener_adversarial_stress_suite.py
======================================================
Auto_Stock Phase 5: 다이내믹 종목 스크리너 적대적 실측 검증 하네스 (Adversarial Empirical Stress Suite).

검증 항목:
1. Section 1: Extreme DataFrame Robustness (결측치, 음수, NaN, Inf, 시총 0, 문자열, 수급 누락, 억원 단위 변환 한계)
2. Section 2: Adversarial Tick Stream Injection (거래량 0, 음수 가격, 시가 0, 문자열 base_volume, OverflowError 등)
3. Section 3: Ultra-High-Frequency Tick Stream & Cooldown Debounce (100만 회 틱 주입 속도 및 단 1회 트리거 실측)
4. Section 4: Massive Concurrency & Deadlock Stress (50 스레드 동시 주입 및 갱신 시 레이스 컨디션/데드락)
5. Section 5: TokenBucket Multi-Threaded Throttling & Precision
"""

import math
import os
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# Auto_Stock 루트 경로 추가
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.data.screener import (
    ScreeningCriteria,
    StockScreener,
    ShardedPollingScheduler,
    TokenBucketLimiter,
)


class EmpiricalVerifier:
    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.vulnerabilities: List[Dict[str, Any]] = []

    def log_result(self, test_name: str, passed: bool, details: Dict[str, Any]):
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] {test_name}: {details.get('summary', '')}")
        self.results[test_name] = {
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        if not passed:
            self.vulnerabilities.append({
                "test": test_name,
                "details": details,
            })


verifier = EmpiricalVerifier()


# ==============================================================================
# SECTION 1: Extreme DataFrame Robustness
# ==============================================================================
def test_section_1_extreme_dataframe():
    print("\n" + "="*80)
    print(">>> [SECTION 1] Extreme DataFrame Robustness Stress Test")
    print("="*80)

    screener = StockScreener()

    # 1.1 결측치/이상치 DataFrame 주입 (음수, NaN, 0원, 문자열, 수급 결측)
    dirty_data = [
        # 정상 종목 1
        {"symbol": "005930", "market_cap": 500_000_000_000, "per": 10.0, "pbr": 1.0, "foreign_net_buy": 100, "inst_net_buy": 100},
        # PER 음수 (적자)
        {"symbol": "000001", "market_cap": 200_000_000_000, "per": -5.0, "pbr": 1.0},
        # PER 0.0
        {"symbol": "000002", "market_cap": 200_000_000_000, "per": 0.0, "pbr": 1.0},
        # PER NaN / Inf / -Inf
        {"symbol": "000003", "market_cap": 200_000_000_000, "per": np.nan, "pbr": 1.0},
        {"symbol": "000004", "market_cap": 200_000_000_000, "per": np.inf, "pbr": 1.0},
        {"symbol": "000005", "market_cap": 200_000_000_000, "per": -np.inf, "pbr": 1.0},
        # PER 문자열 ("N/A", "--", "완전적자")
        {"symbol": "000006", "market_cap": 200_000_000_000, "per": "N/A", "pbr": 1.0},
        {"symbol": "000007", "market_cap": 200_000_000_000, "per": "--", "pbr": 1.0},
        {"symbol": "000008", "market_cap": 200_000_000_000, "per": "완전적자", "pbr": 1.0},
        # PBR 음수 (자본잠식) / 0.0 / NaN / Inf
        {"symbol": "000009", "market_cap": 200_000_000_000, "per": 10.0, "pbr": -1.5},
        {"symbol": "000010", "market_cap": 200_000_000_000, "per": 10.0, "pbr": 0.0},
        {"symbol": "000011", "market_cap": 200_000_000_000, "per": 10.0, "pbr": np.nan},
        {"symbol": "000012", "market_cap": 200_000_000_000, "per": 10.0, "pbr": np.inf},
        # 시총 0원 / 음수 / NaN
        {"symbol": "000013", "market_cap": 0, "per": 10.0, "pbr": 1.0},
        {"symbol": "000014", "market_cap": -100_000_000_000, "per": 10.0, "pbr": 1.0},
        {"symbol": "000015", "market_cap": np.nan, "per": 10.0, "pbr": 1.0},
        # 수급 컬럼 음수 (외인 -500 탈락 대상)
        {"symbol": "000018", "market_cap": 200_000_000_000, "per": 10.0, "pbr": 1.0, "foreign_net_buy": -500},
        # 정상 종목 2
        {"symbol": "000660", "market_cap": 300_000_000_000, "per": 12.0, "pbr": 1.5, "foreign_net_buy": 200, "inst_net_buy": 300},
    ]
    pool = screener.update_daily_static_pool(pd.DataFrame(dirty_data))
    assert "005930" in pool and "000660" in pool
    excluded_bad = [f"{i:06d}" for i in range(1, 16)] + ["000018"]
    leaked_bad = [s for s in excluded_bad if s in pool]
    verifier.log_result("1.1_Dirty_Data_Exclusion", len(leaked_bad) == 0, {
        "summary": f"Exclusion rate 100% ({len(pool)} selected: {pool}, 0 leaks from {len(excluded_bad)} dirty items)",
        "pool": pool,
    })

    # 1.2 시가총액 Inf 누수 결함 실측 탐지
    df_inf = pd.DataFrame([
        {"symbol": "000016", "market_cap": np.inf, "per": 10.0, "pbr": 1.0},
    ])
    pool_inf = screener.update_daily_static_pool(df_inf)
    inf_leaked = ("000016" in pool_inf)
    verifier.log_result("1.2_MarketCap_Inf_Leakage_Vulnerability", not inf_leaked, {
        "summary": f"Market Cap Inf leak: {inf_leaked} (Selected: {pool_inf})",
        "root_cause": "Line 240: df['market_cap'] >= crit.min_market_cap evaluates to True for np.inf; lacks ~np.isinf() check unlike PER/PBR.",
        "impact": "A corrupted ticker with market_cap=inf is ranked #1 in candidate pool during descending sort.",
    })

    # 1.3 10,000행 대규모 유니버스 필터링 지연시간 측정
    n_rows = 10_000
    large_df = pd.DataFrame({
        "symbol": [f"{i:06d}" for i in range(n_rows)],
        "market_cap": np.random.uniform(5e10, 5e11, n_rows),
        "per": np.random.uniform(-5.0, 30.0, n_rows),
        "pbr": np.random.uniform(-1.0, 4.0, n_rows),
        "foreign_net_buy": np.random.randint(-1000, 1000, n_rows),
        "inst_net_buy": np.random.randint(-1000, 1000, n_rows),
    })
    t0 = time.time()
    large_pool = screener.update_daily_static_pool(large_df)
    t_elapsed = time.time() - t0
    verifier.log_result("1.3_Large_Universe_10k_Performance", t_elapsed < 0.1 and len(large_pool) == 200, {
        "summary": f"10,000 rows filtered in {t_elapsed*1000:.2f}ms (capped at 200: {len(large_pool)})",
        "elapsed_ms": t_elapsed * 1000,
    })

    # 1.4 '억원' 단위 입력 시 메가캡(100조 이상) 누락 결함 실측 탐지
    df_eok = pd.DataFrame([
        {"symbol": "005930", "market_cap": 5_000_000, "per": 10.0, "pbr": 1.0}, # 삼성전자 500조 원 (500만 억원)
        {"symbol": "000660", "market_cap": 1_500_000, "per": 12.0, "pbr": 1.5}, # SK하이닉스 150조 원 (150만 억원)
        {"symbol": "068270", "market_cap": 5_000, "per": 8.0, "pbr": 0.8},     # 셀트리온 5천억 원 (5,000 억원)
    ])
    eok_pool = screener.update_daily_static_pool(df_eok)
    eok_bug = (len(eok_pool) == 0)
    verifier.log_result("1.4_MegaCap_EokWon_Unit_Conversion_Limit", not eok_bug, {
        "summary": f"Mega-cap Eok-won test: Expected 3 stocks, got {len(eok_pool)}. (All dropped: {eok_bug})",
        "root_cause": "Line 238: 'if 0 < max_cap < 1_000_000:' skips multiplication for mega-caps >= 100조 KRW (1,000,000 억원), causing all stocks to be dropped by line 240.",
        "impact": "If data is passed in 억원 unit with Samsung/Hynix, the entire screening pool becomes empty [].",
    })


# ==============================================================================
# SECTION 2: Adversarial Tick Stream Injection
# ==============================================================================
def test_section_2_adversarial_ticks():
    print("\n" + "="*80)
    print(">>> [SECTION 2] Adversarial Tick Stream Injection")
    print("="*80)

    screener = StockScreener()
    screener.candidate_pool = ["005930", "000660"]
    screener.candidate_set = {"005930", "000660"}

    # 2.1 0/음수/NaN/Inf/비등록 종목 틱 파라미터 방어
    edge_ticks = [
        ("zero_open_price", {"symbol": "005930", "price": 75000, "open_price": 0.0, "accum_volume": 40000, "prev_same_time_volume": 10000}),
        ("negative_open_price", {"symbol": "005930", "price": 75000, "open_price": -70000.0, "accum_volume": 40000, "prev_same_time_volume": 10000}),
        ("nan_open_price", {"symbol": "005930", "price": 75000, "open_price": float('nan'), "accum_volume": 40000, "prev_same_time_volume": 10000}),
        ("nan_price", {"symbol": "005930", "price": float('nan'), "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 10000}),
        ("inf_price", {"symbol": "005930", "price": float('inf'), "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 10000}),
        ("negative_price", {"symbol": "005930", "price": -75000, "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 10000}),
        ("zero_accum_volume", {"symbol": "005930", "price": 75000, "open_price": 70000, "accum_volume": 0, "prev_same_time_volume": 10000}),
        ("zero_base_volume", {"symbol": "005930", "price": 75000, "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 0}),
        ("negative_base_volume", {"symbol": "005930", "price": 75000, "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": -10000}),
        ("unregistered_symbol", {"symbol": "999999", "price": 75000, "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 10000}),
        ("empty_symbol", {"symbol": "", "price": 75000, "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 10000}),
        ("null_code_symbol", {"symbol": "000000", "price": 75000, "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 10000}),
    ]

    crashes = []
    triggers = []
    for name, t in edge_ticks:
        screener._last_triggered_time.clear()
        try:
            r = screener.check_intraday_trigger(t)
            if r is not None:
                triggers.append((name, r))
        except Exception as e:
            crashes.append((name, str(e)))

    verifier.log_result("2.1_Adversarial_Tick_Defenses", len(crashes) == 0 and len(triggers) == 0, {
        "summary": f"12 edge ticks safely rejected without crash. Crashes: {len(crashes)}, Triggers: {len(triggers)}",
    })

    # 2.2 문자열 baseline_volume 주입 시 TypeError 크래시 실측 탐지
    str_base_ticks = [
        {"symbol": "000660", "price": 105000, "open_price": 100000, "accum_volume": 40000, "prev_same_time_volume": "10000"},
        {"symbol": "000660", "price": 105000, "open_price": 100000, "accum_volume": 40000, "prev_same_time_volume": "N/A"},
    ]
    type_errors = []
    for t in str_base_ticks:
        screener._last_triggered_time.clear()
        try:
            screener.check_intraday_trigger(t)
        except TypeError as te:
            type_errors.append(str(te))
        except Exception as e:
            type_errors.append(f"{type(e).__name__}: {e}")

    has_type_error = len(type_errors) > 0
    verifier.log_result("2.2_String_Baseline_Volume_TypeError_Vulnerability", not has_type_error, {
        "summary": f"TypeError on string baseline_volume: {has_type_error} (Count: {len(type_errors)})",
        "error": type_errors[0] if type_errors else None,
        "root_cause": "Line 400: 'base_vol <= 0' raises TypeError when base_vol is a string because no float conversion was performed.",
        "impact": "Crashes the real-time screening loop when Kiwoom REST/WS string payloads are injected without manual conversion.",
    })

    # 2.3 무한대/초대형 거래량 주입 시 OverflowError 크래시 실측 탐지
    overflow_ticks = [
        ("inf_accum_vol", {"symbol": "005930", "price": 75000, "open_price": 70000, "accum_volume": float('inf'), "prev_same_time_volume": 10000}),
        ("huge_accum_vol", {"symbol": "005930", "price": 75000, "open_price": 70000, "accum_volume": 10**400, "prev_same_time_volume": 10000}),
        ("huge_price", {"symbol": "005930", "price": 10**400, "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 10000}),
    ]
    overflow_errors = []
    for name, t in overflow_ticks:
        screener._last_triggered_time.clear()
        try:
            screener.check_intraday_trigger(t)
        except OverflowError as oe:
            overflow_errors.append((name, str(oe)))
        except Exception as e:
            overflow_errors.append((name, f"{type(e).__name__}: {e}"))

    has_overflow = len(overflow_errors) > 0
    verifier.log_result("2.3_OverflowError_Vulnerability", not has_overflow, {
        "summary": f"OverflowError on extreme numbers: {has_overflow} (Count: {len(overflow_errors)})",
        "errors": overflow_errors,
        "root_cause": "Lines 373, 392, 409 catch only (ValueError, TypeError), omitting OverflowError from float('inf') or 10**400.",
        "impact": "Process crashes when receiving corrupt market data with float infinity or extreme integer volume.",
    })


# ==============================================================================
# SECTION 3: Ultra-High-Frequency (1,000,000 Ticks) & Cooldown Debounce
# ==============================================================================
def test_section_3_ultra_high_frequency_and_cooldown():
    print("\n" + "="*80)
    print(">>> [SECTION 3] Ultra-High-Frequency (1,000,000 Ticks) & Cooldown Debounce")
    print("="*80)

    screener = StockScreener(criteria=ScreeningCriteria(cooldown_seconds=60.0))
    screener.candidate_pool = ["005930"]
    screener.candidate_set = {"005930"}

    total_ticks = 1_000_000
    tick = {
        "symbol": "005930",
        "price": 75000.0,
        "open_price": 70000.0,
        "accum_volume": 50000,
        "prev_same_time_volume": 10000,
        "timestamp": datetime(2026, 9, 3, 10, 0, 0),
    }

    trigger_count = 0
    t0 = time.time()
    for _ in range(total_ticks):
        if screener.check_intraday_trigger(tick) is not None:
            trigger_count += 1
    t_elapsed = time.time() - t0
    ops_per_sec = total_ticks / t_elapsed if t_elapsed > 0 else 0

    passed_3_1 = (trigger_count == 1) and (len(screener._triggered_history) == 1)
    verifier.log_result("3.1_One_Million_Ticks_Debounce", passed_3_1, {
        "summary": f"1,000,000 ticks processed in {t_elapsed:.3f}s ({ops_per_sec:,.0f} ticks/s). Trigger count: {trigger_count} (Expected: 1)",
        "throughput_ticks_per_sec": ops_per_sec,
        "trigger_count": trigger_count,
        "history_size": len(screener._triggered_history),
    })

    # 3.2 쿨다운 타임라인 정밀도 (t=0s, 59.9s, 60.1s, 120.2s)
    base_dt = datetime(2026, 9, 3, 9, 0, 0)
    timeline = [
        (0.0, True),
        (30.0, False),
        (59.9, False),
        (60.1, True),
        (90.0, False),
        (120.2, True),
    ]
    screener._last_triggered_time.clear()
    screener._triggered_history.clear()
    timeline_pass = True
    for offset, expected in timeline:
        cur_tick = dict(tick, timestamp=base_dt + timedelta(seconds=offset))
        trig = (screener.check_intraday_trigger(cur_tick) == "005930")
        if trig != expected:
            timeline_pass = False

    verifier.log_result("3.2_Cooldown_Timeline_Debounce_Precision", timeline_pass, {
        "summary": f"Cooldown timeline verified at 0s(T), 59.9s(F), 60.1s(T), 120.2s(T). All matched: {timeline_pass}",
    })


# ==============================================================================
# SECTION 4: Massive Concurrency & Deadlock Stress Test (50 Threads)
# ==============================================================================
def test_section_4_concurrency_and_deadlock():
    print("\n" + "="*80)
    print(">>> [SECTION 4] Massive Concurrency & Deadlock Stress Test (50 Threads)")
    print("="*80)

    screener = StockScreener()
    init_symbols = [f"{i:06d}" for i in range(50)]
    screener.candidate_pool = list(init_symbols)
    screener.candidate_set = set(init_symbols)

    stop_event = threading.Event()
    exceptions = []
    stats = {
        "ticks": 0,
        "pool_updates": 0,
        "chunks": 0,
        "reads": 0,
    }
    stats_lock = threading.Lock()

    def tick_worker(idx: int):
        sym = f"{(idx % 50):06d}"
        local_c = 0
        while not stop_event.is_set():
            try:
                screener.check_intraday_trigger({
                    "symbol": sym,
                    "price": 10500.0,
                    "open_price": 10000.0,
                    "accum_volume": 40000,
                    "prev_same_time_volume": 10000,
                    "timestamp": datetime.now(),
                })
                local_c += 1
            except Exception:
                exceptions.append(traceback.format_exc())
                break
        with stats_lock:
            stats["ticks"] += local_c

    def update_worker(idx: int):
        local_c = 0
        while not stop_event.is_set():
            try:
                df = pd.DataFrame([
                    {"symbol": f"{i:06d}", "market_cap": 200_000_000_000, "per": 10.0, "pbr": 1.0}
                    for i in range(20)
                ])
                screener.update_daily_static_pool(df)
                local_c += 1
                time.sleep(0.005)
            except Exception:
                exceptions.append(traceback.format_exc())
                break
        with stats_lock:
            stats["pool_updates"] += local_c

    def polling_worker(idx: int):
        local_c = 0
        while not stop_event.is_set():
            try:
                screener.schedule_polling_chunks(chunk_size=3)
                local_c += 1
                time.sleep(0.005)
            except Exception:
                exceptions.append(traceback.format_exc())
                break
        with stats_lock:
            stats["chunks"] += local_c

    def read_worker(idx: int):
        local_c = 0
        while not stop_event.is_set():
            try:
                screener.get_candidate_pool()
                screener.get_candidate_df()
                local_c += 1
                time.sleep(0.005)
            except Exception:
                exceptions.append(traceback.format_exc())
                break
        with stats_lock:
            stats["reads"] += local_c

    threads: List[threading.Thread] = []
    for i in range(25): threads.append(threading.Thread(target=tick_worker, args=(i,)))
    for i in range(15): threads.append(threading.Thread(target=update_worker, args=(i,)))
    for i in range(5): threads.append(threading.Thread(target=polling_worker, args=(i,)))
    for i in range(5): threads.append(threading.Thread(target=read_worker, args=(i,)))

    t_start = time.time()
    for t in threads:
        t.daemon = True
        t.start()

    time.sleep(3.0)
    stop_event.set()

    deadlocked = False
    for t in threads:
        t.join(timeout=5.0)
        if t.is_alive():
            deadlocked = True

    passed_4 = (len(exceptions) == 0) and (not deadlocked)
    verifier.log_result("4.1_50_Threads_Concurrency_and_Deadlock", passed_4, {
        "summary": f"50 threads executed for 3.1s. Deadlock: {deadlocked}. Exceptions: {len(exceptions)}. Stats: {stats}",
        "stats": stats,
    })


# ==============================================================================
# SECTION 5: TokenBucket Multi-Threaded Throttling
# ==============================================================================
def test_section_5_token_bucket():
    print("\n" + "="*80)
    print(">>> [SECTION 5] TokenBucket Multi-Threaded Throttling & Precision")
    print("="*80)

    limiter = TokenBucketLimiter(rate=10.0, capacity=5.0)
    acquired_count = 0
    t_start = time.time()
    acq_lock = threading.Lock()

    def tb_worker():
        nonlocal acquired_count
        for _ in range(2):
            limiter.acquire(1.0)
            with acq_lock:
                acquired_count += 1

    threads = [threading.Thread(target=tb_worker) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=5.0)

    t_elapsed = time.time() - t_start
    passed_tb = (acquired_count == 20) and (t_elapsed >= 1.4)
    verifier.log_result("5.1_TokenBucket_Thread_Throttling", passed_tb, {
        "summary": f"Acquired {acquired_count}/20 tokens in {t_elapsed:.2f}s (Expected: >= 1.40s)",
    })


# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    print("\n" + "#"*80)
    print("### AUTO_STOCK PHASE 5 SCREENER EMPIRICAL ADVERSARIAL SUITE ###")
    print("#"*80)

    test_section_1_extreme_dataframe()
    test_section_2_adversarial_ticks()
    test_section_3_ultra_high_frequency_and_cooldown()
    test_section_4_concurrency_and_deadlock()
    test_section_5_token_bucket()

    print("\n" + "#"*80)
    print("### EMPIRICAL VERIFICATION SUMMARY ###")
    print("#"*80)
    total = len(verifier.results)
    passed = sum(1 for v in verifier.results.values() if v["passed"])
    failed = total - passed

    print(f"Total Tests Executed: {total}")
    print(f"Verified Robust: {passed}")
    print(f"Empirical Vulnerabilities Discovered: {failed}")

    for name, res in verifier.results.items():
        flag = "✅ PASS" if res["passed"] else "❌ FAIL"
        print(f"{flag} - {name}")

    if verifier.vulnerabilities:
        print("\n" + "!"*80)
        print("!!! DISCOVERED VULNERABILITIES !!!")
        print("!"*80)
        for f in verifier.vulnerabilities:
            print(f"\n[VULNERABILITY] {f['test']}")
            print(f"  Summary: {f['details'].get('summary')}")
            if "root_cause" in f["details"]:
                print(f"  Root Cause: {f['details']['root_cause']}")
            if "impact" in f["details"]:
                print(f"  Impact: {f['details']['impact']}")

    # Exit with code 1 if vulnerabilities found, 0 if all clean
    sys.exit(0 if failed == 0 else 1)
