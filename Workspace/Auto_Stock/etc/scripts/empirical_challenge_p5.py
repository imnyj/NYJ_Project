#!/usr/bin/env python3
"""
etc/scripts/empirical_challenge_p5.py
======================================
Empirical Adversarial Stress Test Harness for Phase 5:
- LiveLearningSimulator (Dynamic Queue, Observation, Multi-asset Equity Conservation)
- Rate Limiting & Scheduling (TokenBucketLimiter, ShardedPollingScheduler)
"""

import sys
import os
import time
import math
import queue
import threading
import tracemalloc
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = "/home/imnyj/Workspace/Auto_Stock"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.kiwoom_api import PriceQuote
from modules.data.screener import (
    ScreeningCriteria,
    StockScreener,
    TokenBucketLimiter,
    ShardedPollingScheduler,
)
from modules.engine.live_learning_simulator import LiveLearningSimulator
from modules.engine.mock_environment import ActionType, FeeConfig, to_decimal


class ChallengeRunner:
    def __init__(self):
        self.results = {}
        self.metrics = {}

    def log_result(self, test_name: str, passed: bool, details: str):
        self.results[test_name] = passed
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"[{status}] {test_name}: {details}")

    # =========================================================================
    # Challenge 1: High-Load Queue Injection & Memory Leak Stress Test
    # =========================================================================
    def run_challenge_1(self) -> bool:
        print("\n" + "="*80)
        print("▶ CHALLENGE 1: High-Load Queue Injection & Memory Leak Stress Test")
        print("="*80)

        # 1-1. 200개 종목 순차 주입
        sim = LiveLearningSimulator(initial_cash=100_000_000)
        symbols = [f"{i:06d}" for i in range(200)]
        for sym in symbols:
            sim.inject_triggered_symbol(sym, trigger_info={"price": 50000 + int(sym), "volume": 100000})

        c1_1_pass = (len(sim.active_pool) == 200 and sim.triggered_queue.qsize() == 200)
        self.log_result(
            "C1-1. Sequential 200 symbols injection",
            c1_1_pass,
            f"Active pool count: {len(sim.active_pool)}, Queue size: {sim.triggered_queue.qsize()}"
        )

        # 1-2. 20개 스레드에서 총 1,000회 동시 주입 (Race Condition & Thread-Safety)
        sim_concurrent = LiveLearningSimulator(initial_cash=100_000_000)
        thread_errors = []
        injected_count = 0
        lock = threading.Lock()

        def concurrent_injector(thread_id: int):
            nonlocal injected_count
            try:
                for i in range(50):
                    sym = f"{(thread_id * 50 + i) % 150:06d}"
                    success = sim_concurrent.inject_triggered_symbol(
                        sym,
                        trigger_info={"price": 10000 + i * 100, "open_price": 9500}
                    )
                    if success:
                        with lock:
                            injected_count += 1
            except Exception as e:
                thread_errors.append(e)

        threads = [threading.Thread(target=concurrent_injector, args=(t,)) for t in range(20)]
        t_start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        t_elapsed = time.time() - t_start

        c1_2_pass = (len(thread_errors) == 0 and injected_count == 1000 and sim_concurrent.triggered_queue.qsize() == 1000)
        self.log_result(
            "C1-2. Concurrent 1000 injections across 20 threads",
            c1_2_pass,
            f"Elapsed: {t_elapsed*1000:.2f}ms, Injected: {injected_count}, Queue size: {sim_concurrent.triggered_queue.qsize()}, Active pool distinct: {len(sim_concurrent.active_pool)}, Errors: {len(thread_errors)}"
        )

        # 1-3. 메모리 누수 스트레스 테스트 (5,000회 주입 후 큐 처리)
        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        sim_mem = LiveLearningSimulator(initial_cash=10_000_000)
        for i in range(5000):
            sym = f"{i % 300:06d}"
            sim_mem.inject_triggered_symbol(sym, trigger_info={"price": 50000, "accum_volume": 1000000})

        snapshot_peak = tracemalloc.take_snapshot()

        # 큐 모두 소비
        drained_count = 0
        while not sim_mem.triggered_queue.empty():
            sim_mem.triggered_queue.get_nowait()
            drained_count += 1

        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        peak_stats = snapshot_peak.compare_to(snapshot_before, 'lineno')
        peak_diff_mb = sum(stat.size_diff for stat in peak_stats) / (1024 * 1024)

        after_stats = snapshot_after.compare_to(snapshot_peak, 'lineno')
        after_diff_mb = sum(stat.size_diff for stat in after_stats) / (1024 * 1024)

        c1_3_pass = (drained_count == 5000 and peak_diff_mb < 20.0)
        self.log_result(
            "C1-3. Memory stress (5000 injections & drain)",
            c1_3_pass,
            f"Drained: {drained_count}, Peak memory growth: {peak_diff_mb:.3f} MB, After drain diff: {after_diff_mb:.3f} MB"
        )

        # 1-4. 비정상 입력값 (Malformed symbol) 주입 방어
        malformed_inputs = ["", "   ", "0005930", "ABCDEF", "123", "99999999"]
        malformed_pass = True
        for m in malformed_inputs:
            try:
                res = sim.inject_triggered_symbol(m, trigger_info={"price": 1000})
                if not res:
                    malformed_pass = False
            except Exception as e:
                malformed_pass = False
                print(f"Exception on malformed {m}: {e}")

        self.log_result(
            "C1-4. Malformed symbol sanitization and injection",
            malformed_pass,
            f"Tested malformed: {malformed_inputs}, Normalized cleanly into active_pool"
        )

        return c1_1_pass and c1_2_pass and c1_3_pass and malformed_pass

    # =========================================================================
    # Challenge 2: Observation 14-dim float32 & NaN/Inf & Numerical Bounds
    # =========================================================================
    def run_challenge_2(self) -> bool:
        print("\n" + "="*80)
        print("▶ CHALLENGE 2: Observation 14-dim float32 & NaN/Inf Immunity & Bounds")
        print("="*80)

        sim = LiveLearningSimulator(initial_cash=10_000_000)

        # 2-1. 정상 관측치 규격
        sim.inject_triggered_symbol("005930", trigger_info={"price": 70000, "open_price": 68000, "volume": 500000})
        obs = sim.build_rl_observation("005930")
        c2_1_pass = (
            isinstance(obs, np.ndarray) and
            obs.shape == (14,) and
            obs.dtype == np.float32 and
            not np.isnan(obs).any() and
            not np.isinf(obs).any()
        )
        self.log_result(
            "C2-1. Baseline observation shape and dtype",
            c2_1_pass,
            f"Shape: {obs.shape}, Dtype: {obs.dtype}, NaNs: {np.isnan(obs).sum()}, Infs: {np.isinf(obs).sum()}"
        )

        # 2-2. 극단적/비정상 시장 피처 주입 시 NaN/Inf 완전 차단 및 형상 보존
        adversarial_market_features = [
            [np.nan] * 10,
            [np.inf] * 10,
            [-np.inf] * 10,
            [1e30, -1e30, np.nan, np.inf, -np.inf, 0.0, 1.0, -1.0, 999999.0, -999999.0],
            [],  # 빈 리스트
            [1.0] * 5,  # 길이 5
            [2.0] * 20, # 길이 20
        ]

        c2_2_pass = True
        obs_outputs = []
        for i, m_feats in enumerate(adversarial_market_features):
            out_obs = sim.build_rl_observation("005930", market_features=m_feats)
            valid = (
                out_obs.shape == (14,) and
                out_obs.dtype == np.float32 and
                not np.isnan(out_obs).any() and
                not np.isinf(out_obs).any()
            )
            if not valid:
                c2_2_pass = False
                print(f"Failed on feature set {i}: {out_obs}")
            obs_outputs.append(out_obs)

        self.log_result(
            "C2-2. Extreme market features NaN/Inf/Length mismatch immunity",
            c2_2_pass,
            f"Tested {len(adversarial_market_features)} adversarial feature sets. All 14-dim float32 finite."
        )

        # 2-3. 극단적 트리거 데이터 (Zero / Negative open_price, Massive volume)
        sim_adv = LiveLearningSimulator(initial_cash=10_000_000)
        extreme_triggers = [
            {"price": 70000, "open_price": 0.0, "volume": 0},          # Zero open price
            {"price": 70000, "open_price": -50000, "volume": -1000},    # Negative open price
            {"price": 0, "open_price": 10000, "volume": 1e12},          # Price 0, volume 1조
            {"price": 1e9, "open_price": 10000, "volume": 100000},      # Price 10억 (수익률 100,000배)
            {"price": 10, "open_price": 10000, "volume": 50000},        # Price 10 (수익률 -99.9%)
        ]

        c2_3_pass = True
        for i, trig in enumerate(extreme_triggers):
            sym = f"0000{i}0"
            sim_adv.inject_triggered_symbol(sym, trigger_info=trig)
            obs_trig = sim_adv.build_rl_observation(sym)
            valid = (
                obs_trig.shape == (14,) and
                obs_trig.dtype == np.float32 and
                not np.isnan(obs_trig).any() and
                not np.isinf(obs_trig).any() and
                -0.3 <= obs_trig[0] <= 0.3 and  # ret_from_open clip [-0.3, 0.3]
                0.0 <= obs_trig[9] <= 50.0      # volume clip [0.0, 50.0]
            )
            if not valid:
                c2_3_pass = False
                print(f"Failed extreme trigger {i}: obs[0]={obs_trig[0]}, obs[9]={obs_trig[9]}")

        self.log_result(
            "C2-3. Extreme trigger data clipping bounds [-0.3, 0.3] and [0.0, 50.0]",
            c2_3_pass,
            f"Tested {len(extreme_triggers)} extreme triggers. Return & volume features strictly within clipped bounds."
        )

        # 2-4. 극단적 계좌 상태 (마이너스 자산, 0 자산, 파산 경계)
        sim_acc = LiveLearningSimulator(initial_cash=10_000_000)
        sim_acc.account.cash_balance = Decimal("0")
        obs_zero_cash = sim_acc.build_rl_observation("005930")
        cash_ratio_0 = obs_zero_cash[10]

        sim_acc.account.cash_balance = Decimal("-500000")
        obs_neg_cash = sim_acc.build_rl_observation("005930")
        cash_ratio_neg = obs_neg_cash[10]

        c2_4_pass = (
            0.0 <= cash_ratio_0 <= 1.0 and
            0.0 <= cash_ratio_neg <= 1.0 and
            not np.isnan(obs_neg_cash).any() and
            not np.isinf(obs_neg_cash).any()
        )
        self.log_result(
            "C2-4. Extreme account cash zero/negative bounds protection",
            c2_4_pass,
            f"Cash=0 ratio: {cash_ratio_0:.4f}, Cash=-500k ratio: {cash_ratio_neg:.4f} (clipped to [0, 1])"
        )

        # 2-5. 2,000회 대규모 샘플링 무결성 검증 (Fuzzing)
        np.random.seed(42)
        fuzz_pass = True
        min_vals = np.full(14, np.inf, dtype=np.float32)
        max_vals = np.full(14, -np.inf, dtype=np.float32)

        for _ in range(2000):
            rand_m = np.random.uniform(-10.0, 10.0, size=10).astype(np.float32)
            f_obs = sim.build_rl_observation("005930", market_features=rand_m)
            if np.isnan(f_obs).any() or np.isinf(f_obs).any():
                fuzz_pass = False
                break
            min_vals = np.minimum(min_vals, f_obs)
            max_vals = np.maximum(max_vals, f_obs)

        self.log_result(
            "C2-5. 2,000 random adversarial fuzzing iterations",
            fuzz_pass,
            f"Min range: [{min_vals.min():.2f}], Max range: [{max_vals.max():.2f}]. All finite float32."
        )

        return c2_1_pass and c2_2_pass and c2_3_pass and c2_4_pass and fuzz_pass

    # =========================================================================
    # Challenge 3: Multi-Position Portfolio Equity Conservation & Price Shocks
    # =========================================================================
    def run_challenge_3(self) -> bool:
        print("\n" + "="*80)
        print("▶ CHALLENGE 3: Multi-Position Portfolio Equity Conservation & Shocks")
        print("="*80)

        # 가상 시세 매핑
        current_prices = {
            "005930": Decimal("70000"),
            "000660": Decimal("120000"),
            "035420": Decimal("200000"),
            "051910": Decimal("400000"),
            "005380": Decimal("250000"),
        }

        def mock_fetch(symbol: str) -> Decimal:
            return current_prices[symbol]

        sim = LiveLearningSimulator(initial_cash=50_000_000)
        sim.fetch_live_price = mock_fetch

        # 3-1. 5개 종목 순차 매수 (포지션 비중 20% 씩)
        for s, p in current_prices.items():
            sim.inject_triggered_symbol(s, trigger_info={"price": float(p), "open_price": float(p)})

        for s in current_prices.keys():
            sim.step_symbol(s, action=ActionType.BUY, position_weight=0.20)

        pos_sum = sum(
            sim.account.get_position(s).quantity * current_prices[s]
            for s in current_prices.keys()
        )
        exact_equity_1 = sim.account.cash_balance + pos_sum
        sim_equity_1 = sim.account.get_total_equity(current_prices)
        discrepancy_1 = abs(exact_equity_1 - sim_equity_1)

        c3_1_pass = (discrepancy_1 == Decimal("0"))
        self.log_result(
            "C3-1. Multi-position initial allocation equity conservation",
            c3_1_pass,
            f"Cash: {sim.account.cash_balance:,.0f}, PosValue: {pos_sum:,.0f}, Total: {sim_equity_1:,.0f}, Discrepancy: {discrepancy_1} KRW"
        )

        # 3-2. 가혹한 가격 급변동 주입 (극단적 시장 충격: +30% 폭등 및 -30% 폭락)
        shocked_prices = {
            "005930": Decimal("91000"),   # +30%
            "000660": Decimal("84000"),   # -30%
            "035420": Decimal("230000"),  # +15%
            "051910": Decimal("320000"),  # -20%
            "005380": Decimal("250000"),  # 0%
        }
        current_prices.update(shocked_prices)

        # 각 종목별로 순차 step_symbol(HOLD) 호출하여 시장가 갱신 및 에쿼티 변동 확인
        rewards = []
        equities = []
        c3_2_pass = True

        for s in shocked_prices.keys():
            obs, rew, term, trunc, info = sim.step_symbol(s, action=ActionType.HOLD)
            rewards.append(rew)
            equities.append(info["total_equity"])
            audit = info["audit"]

            # 매 스텝마다 Accounting Invariant 일관성 검증 (Cash + Holdings == Total Equity)
            cash = audit["cash_balance"]
            holdings = audit["holdings_valuation"]
            tot_eq = audit["total_equity"]
            if (cash + holdings) != tot_eq:
                c3_2_pass = False
                print(f"Accounting audit inconsistency on {s}: cash={cash}, holdings={holdings}, total={tot_eq}")

            # 현재까지 sim.engine._last_market_prices에 반영된 시장가 기준으로 에쿼티 일치 확인 (Zero Distortion)
            expected_total = float(sim.account.cash_balance + sum(
                sim.account.get_position(sym).quantity * sim.engine._last_market_prices[sym]
                for sym in current_prices.keys()
            ))
            if abs(expected_total - info["total_equity"]) > 0.01:
                c3_2_pass = False
                print(f"Equity mismatch on {s}: expected={expected_total}, got={info['total_equity']}")

        # 5개 종목이 모두 갱신된 후, 최종 에쿼티가 전체 충격 포트폴리오 에쿼티와 완벽히 일치하는지 검증
        final_expected = float(sim.account.cash_balance + sum(
            sim.account.get_position(sym).quantity * shocked_prices[sym]
            for sym in shocked_prices.keys()
        ))
        final_actual = equities[-1]
        final_mismatch = abs(final_expected - final_actual)
        if final_mismatch > 0.01:
            c3_2_pass = False
            print(f"Final fully shocked equity mismatch: expected={final_expected}, got={final_actual}")

        self.log_result(
            "C3-2. Severe market shocks (+30% / -30%) equity conservation & audit",
            c3_2_pass,
            f"Updated all 5 shocked symbols. Final Equity: {final_actual:,.0f} KRW, Mismatch: {final_mismatch:.4f} KRW (0.00 KRW distortion)."
        )

        # 3-3. 부분 청산 및 리밸런싱 중 마찰 비용(수수료/세금/슬리피지) 보존 검증
        # 005930(상한가 폭등 종목) 50% 매도
        init_frictions = (
            sim.account.cumulative_commission +
            sim.account.cumulative_tax +
            sim.account.cumulative_slippage
        )
        obs, rew, term, trunc, info = sim.step_symbol("005930", action=ActionType.SELL, position_weight=0.5)
        new_frictions = (
            sim.account.cumulative_commission +
            sim.account.cumulative_tax +
            sim.account.cumulative_slippage
        )
        friction_delta = new_frictions - init_frictions

        cash = info["audit"]["cash_balance"]
        holdings = info["audit"]["holdings_valuation"]
        tot_eq = info["audit"]["total_equity"]
        audit_consistent = (cash + holdings == tot_eq)

        c3_3_pass = (
            info["trade"] is not None and
            info["trade"].is_success is True and
            friction_delta > Decimal("0") and
            audit_consistent is True
        )
        self.log_result(
            "C3-3. Partial liquidation friction accounting & audit consistency",
            c3_3_pass,
            f"Sold 50% of 005930. Friction generated: {friction_delta:,.2f} KRW, Audit consistent: {audit_consistent}"
        )

        # 3-4. 파산 임계점 및 Log Equity Return 무결성 (Zero/Negative Equity 방어)
        sim_bankrupt = LiveLearningSimulator(initial_cash=1_000_000)
        sim_bankrupt.account.cash_balance = Decimal("40_000") # 4% (< 5% 파산)
        obs, rew, terminated, trunc, info = sim_bankrupt.step_symbol("005930", action=ActionType.HOLD)

        c3_4_pass = (
            terminated is True and
            not math.isnan(rew) and
            not math.isinf(rew)
        )
        self.log_result(
            "C3-4. Bankruptcy (<5% equity) detection & log return sanity",
            c3_4_pass,
            f"Terminated: {terminated}, Reward: {rew:.6f}, Total Equity: {info['total_equity']:,.0f}"
        )

        return c3_1_pass and c3_2_pass and c3_3_pass and c3_4_pass

    # =========================================================================
    # Challenge 4: Rate Limiting & Scheduling Strict 5 req/sec Compliance
    # =========================================================================
    def run_challenge_4(self) -> bool:
        print("\n" + "="*80)
        print("▶ CHALLENGE 4: Rate Limiter & Sharded Scheduler Strict 5 req/sec")
        print("="*80)

        # 4-1. TokenBucketLimiter 단일 스레드 연속 호출 슬라이딩 윈도우 검증
        limiter = TokenBucketLimiter(rate=5.0, capacity=5.0)

        timestamps = []
        t_start = time.time()
        for i in range(20):
            limiter.acquire(1.0)
            timestamps.append(time.time())
        t_total = time.time() - t_start

        # [t, t+1.0) 구간에 포함된 타임스탬프 개수
        max_in_1s_window = 0
        for i, t in enumerate(timestamps):
            count = sum(1 for ts in timestamps if t <= ts < t + 1.0)
            if count > max_in_1s_window:
                max_in_1s_window = count

        c4_1_pass = (t_total >= 2.8 and max_in_1s_window <= 10)
        self.log_result(
            "C4-1. TokenBucket single-thread 20 requests throughput & timing",
            c4_1_pass,
            f"Total time: {t_total:.3f}s (Theoretical min: 3.0s), Max reqs in any 1.0s window: {max_in_1s_window}"
        )

        # 4-2. ShardedPollingScheduler 보수적 rate=3.0 (Capacity=3.0) 윈도우 검증
        safe_limiter = TokenBucketLimiter(rate=3.0, capacity=3.0)
        safe_timestamps = []
        t_safe_start = time.time()
        for i in range(12):
            safe_limiter.acquire(1.0)
            safe_timestamps.append(time.time())
        t_safe_total = time.time() - t_safe_start

        max_safe_window = 0
        for i, t in enumerate(safe_timestamps):
            count = sum(1 for ts in safe_timestamps if t <= ts < t + 1.0)
            if count > max_safe_window:
                max_safe_window = count

        c4_2_pass = (t_safe_total >= 2.8 and max_safe_window <= 6)
        self.log_result(
            "C4-2. Conservative rate=3.0 sliding window compliance",
            c4_2_pass,
            f"Total time: {t_safe_total:.3f}s (Theoretical min: 3.0s), Max reqs in 1.0s window: {max_safe_window}"
        )

        # 4-3. 멀티스레드 동시 경합 환경에서 TokenBucketLimiter 스레드 안전성
        concurrent_limiter = TokenBucketLimiter(rate=4.0, capacity=2.0)
        concurrent_timestamps = []
        ts_lock = threading.Lock()

        def worker_req(w_id: int):
            for _ in range(2):
                concurrent_limiter.acquire(1.0)
                now = time.time()
                with ts_lock:
                    concurrent_timestamps.append(now)

        c_threads = [threading.Thread(target=worker_req, args=(i,)) for i in range(5)]
        t_c_start = time.time()
        for t in c_threads:
            t.start()
        for t in c_threads:
            t.join()
        t_c_total = time.time() - t_c_start

        c4_3_pass = (len(concurrent_timestamps) == 10 and t_c_total >= 1.8)
        self.log_result(
            "C4-3. Multi-thread contention (5 threads, 10 requests, rate=4.0)",
            c4_3_pass,
            f"Total acquired: {len(concurrent_timestamps)}, Total elapsed: {t_c_total:.3f}s (Expected min: 2.0s)"
        )

        # 4-4. ShardedPollingScheduler 200개 종목 분할 무결성
        scheduler_200 = ShardedPollingScheduler(
            symbols=[f"{i:06d}" for i in range(200)],
            max_per_sec=3.0
        )
        batches_200 = scheduler_200.get_batches()

        all_syms = [s for b in batches_200 for s in b]
        c4_4_pass = (
            len(batches_200) == 67 and
            all(len(b) <= 3 for b in batches_200) and
            len(all_syms) == 200 and
            len(set(all_syms)) == 200
        )
        self.log_result(
            "C4-4. ShardedPollingScheduler 200 symbols batch partitioning",
            c4_4_pass,
            f"Batch count: {len(batches_200)}, Max batch size: {max(len(b) for b in batches_200)}, Total unique: {len(set(all_syms))}"
        )

        return c4_1_pass and c4_2_pass and c4_3_pass and c4_4_pass


if __name__ == "__main__":
    runner = ChallengeRunner()
    pass1 = runner.run_challenge_1()
    pass2 = runner.run_challenge_2()
    pass3 = runner.run_challenge_3()
    pass4 = runner.run_challenge_4()

    all_passed = pass1 and pass2 and pass3 and pass4
    print("\n" + "="*80)
    print(f"OVERALL EMPIRICAL CHALLENGE RESULT: {'PASSED (APPROVE)' if all_passed else 'FAILED (REJECT)'}")
    print("="*80)
    sys.exit(0 if all_passed else 1)
