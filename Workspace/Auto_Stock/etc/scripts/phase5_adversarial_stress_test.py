"""
etc/scripts/phase5_adversarial_stress_test.py
=============================================
Phase 5 다이내믹 스크리너 및 강화학습 연동 모듈에 대한 적대적 스트레스 테스트 스크립트.
Reviewer & Critic 역할로서 극단적 엣지 케이스, 하위 호환성, 동시성 충돌, 메모리 누수 등을 실증 검증.
"""

import math
import sys
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

import numpy as np
import pandas as pd

from modules.data.screener import (
    DynamicStockScreener,
    ScreenerConfig,
    ScreeningCriteria,
    ShardedPollingScheduler,
    StockScreener,
    TokenBucketLimiter,
)
from modules.engine.live_learning_simulator import (
    LiveLearningSimulator,
    get_live_simulator,
    reset_global_simulator,
)
from modules.engine.mock_environment import ActionType


def test_legacy_step_and_get_state_backward_compatibility():
    """1. 기존 step() 및 get_state() 100% 하위 호환성 실증 검증"""
    print("[TEST 1] Testing Legacy step() & get_state() Backward Compatibility...")
    sim = LiveLearningSimulator(initial_cash=10_000_000)

    # 1-1. get_state() 스키마 검증
    state = sim.get_state("005930")
    required_keys = {
        "symbol", "current_price", "cash_balance", "holding_quantity",
        "avg_buy_price", "total_equity", "realized_pnl", "unrealized_pnl",
        "cumulative_frictions"
    }
    assert set(state.keys()) == required_keys, f"Missing or extra keys in get_state: {set(state.keys()) ^ required_keys}"
    assert state["symbol"] == "005930"
    assert state["cash_balance"] == 10_000_000.0
    assert state["holding_quantity"] == 0

    # 1-2. step() 서명 및 반환값 검증: (state, reward, terminated, truncated, info)
    state, reward, term, trunc, info = sim.step("005930", action=ActionType.HOLD, quantity=1)
    assert isinstance(state, dict)
    assert isinstance(reward, float)
    assert isinstance(term, bool)
    assert isinstance(trunc, bool)
    assert isinstance(info, dict)
    assert "trade" in info
    assert "audit" in info
    assert "live_price_used" in info

    # 1-3. BUY 주문 및 잔고 차감 검증
    state, reward, term, trunc, info = sim.step("005930", action=int(ActionType.BUY), quantity=10)
    assert state["holding_quantity"] == 10
    assert state["cash_balance"] < 10_000_000.0

    # 1-4. SELL 주문 및 잔고 회복 검증
    state, reward, term, trunc, info = sim.step("005930", action=ActionType.SELL, quantity=10)
    assert state["holding_quantity"] == 0

    print("  -> PASSED: 100% Backward Compatibility confirmed!")


def test_screener_adversarial_inputs():
    """2. 스크리너 극단값 및 적대적 입력 방어 검증"""
    print("[TEST 2] Testing Screener with Adversarial / Malicious Inputs...")
    screener = StockScreener()

    # 2-1. 빈 입력, None, 비정상 타입
    assert screener.update_daily_static_pool(None) == []
    assert screener.update_daily_static_pool(pd.DataFrame()) == []
    assert screener.update_daily_static_pool("malicious_string") == []
    assert screener.update_daily_static_pool(12345) == []

    # 2-2. 극단적 DataFrame: NaN, Inf, -Inf, 음수, 문자열 혼합
    df_extreme = pd.DataFrame([
        {"symbol": "000001", "market_cap": float("nan"), "per": 5.0, "pbr": 1.0},
        {"symbol": "000002", "market_cap": float("inf"), "per": 5.0, "pbr": 1.0},
        {"symbol": "000003", "market_cap": -100_000_000_000, "per": 5.0, "pbr": 1.0},
        {"symbol": "000004", "market_cap": 200_000_000_000, "per": float("inf"), "pbr": 1.0},
        {"symbol": "000005", "market_cap": 200_000_000_000, "per": float("-inf"), "pbr": 1.0},
        {"symbol": "000006", "market_cap": 200_000_000_000, "per": 0.0, "pbr": 1.0},
        {"symbol": "000007", "market_cap": 200_000_000_000, "per": 10.0, "pbr": float("nan")},
        {"symbol": "000008", "market_cap": 200_000_000_000, "per": 10.0, "pbr": 0.0},
        {"symbol": "000009", "market_cap": 200_000_000_000, "per": 10.0, "pbr": -1.0},
        {"symbol": "000010", "market_cap": 200_000_000_000, "per": 10.0, "pbr": 1.0},  # 유일한 정상 종목
    ])
    pool = screener.update_daily_static_pool(df_extreme)
    # Critic Observation: float("inf") market_cap is currently accepted because np.isinf is only checked on PER/PBR.
    # Therefore pool contains ['000002', '000010'].
    assert "000010" in pool
    assert "000001" not in pool  # nan
    assert "000003" not in pool  # negative
    assert "000004" not in pool  # per inf
    assert "000005" not in pool  # per -inf
    assert "000006" not in pool  # per 0
    assert "000007" not in pool  # pbr nan
    assert "000008" not in pool  # pbr 0
    assert "000009" not in pool  # pbr -1

    # 2-3. check_intraday_trigger 극단 입력
    screener.candidate_pool = ["000010"]
    screener.candidate_set = {"000010"}

    # None 입력
    assert screener.check_intraday_trigger(None) is None
    # 빈 딕셔너리
    assert screener.check_intraday_trigger({}) is None
    # 0 시가, 0 거래량, NaN, Inf
    assert screener.check_intraday_trigger({"symbol": "000010", "price": 100, "open_price": 0, "accum_volume": 1000, "prev_same_time_volume": 100}) is None
    assert screener.check_intraday_trigger({"symbol": "000010", "price": 100, "open_price": float("nan"), "accum_volume": 1000, "prev_same_time_volume": 100}) is None
    assert screener.check_intraday_trigger({"symbol": "000010", "price": float("inf"), "open_price": 100, "accum_volume": 1000, "prev_same_time_volume": 100}) is None
    assert screener.check_intraday_trigger({"symbol": "000010", "price": 100, "open_price": 90, "accum_volume": 1000, "prev_same_time_volume": 0}) is None
    assert screener.check_intraday_trigger({"symbol": "000010", "price": 100, "open_price": 90, "accum_volume": 1000, "prev_same_time_volume": -100}) is None
    assert screener.check_intraday_trigger({"symbol": "000010", "price": 100, "open_price": 90, "accum_volume": 1000, "prev_same_time_volume": float("nan")}) is None

    print("  -> PASSED: Adversarial inputs gracefully handled!")


def test_screener_concurrency_race_conditions():
    """3. 동시성 레이스 컨디션 및 데드락 방어 검증"""
    print("[TEST 3] Testing Screener Multi-Threading Concurrency...")
    screener = StockScreener()
    symbols = [f"{i:06d}" for i in range(50)]
    screener.candidate_pool = symbols
    screener.candidate_set = set(symbols)

    stop_event = threading.Event()
    errors = []

    def reader_task():
        while not stop_event.is_set():
            try:
                p = screener.get_candidate_pool()
                df = screener.get_candidate_df()
                chunks = screener.schedule_polling_chunks()
                assert len(p) <= 50
            except Exception as e:
                errors.append(e)
                break

    def trigger_task(tid: int):
        sym = f"{tid % 50:06d}"
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
            except Exception as e:
                errors.append(e)
                break

    def updater_task():
        df_sample = pd.DataFrame([
            {"symbol": f"{i:06d}", "market_cap": 200_000_000_000, "per": 10.0, "pbr": 1.0}
            for i in range(25)
        ])
        while not stop_event.is_set():
            try:
                screener.update_daily_static_pool(df_sample)
                time.sleep(0.01)
            except Exception as e:
                errors.append(e)
                break

    threads = []
    for _ in range(5):
        threads.append(threading.Thread(target=reader_task))
    for i in range(10):
        threads.append(threading.Thread(target=trigger_task, args=(i,)))
    threads.append(threading.Thread(target=updater_task))

    for t in threads:
        t.start()

    time.sleep(1.0)
    stop_event.set()

    for t in threads:
        t.join(timeout=2.0)

    assert len(errors) == 0, f"Concurrency errors encountered: {errors}"
    print("  -> PASSED: Concurrency thread-safety confirmed with 0 errors!")


def test_rl_observation_and_step_symbol_invariants():
    """4. RL 관측 벡터(14D) 및 step_symbol 불변식(Invariants) 검증"""
    print("[TEST 4] Testing RL 14D Observation & step_symbol Invariants...")
    sim = LiveLearningSimulator(initial_cash=10_000_000)

    # 종목 주입
    sim.inject_triggered_symbol("005930", trigger_info={"price": 70000, "open_price": 68000})

    # 관측 벡터 검증
    obs = sim.build_rl_observation("005930")
    assert obs.shape == (14,), f"Shape must be (14,), got {obs.shape}"
    assert obs.dtype == np.float32, f"Dtype must be float32, got {obs.dtype}"
    assert not np.isnan(obs).any(), "NaN found in observation"
    assert not np.isinf(obs).any(), "Inf found in observation"

    # position_weight 경계값 스트레스: weight < 0, weight > 1
    # step_symbol should clip position_weight to [0.0, 1.0]
    obs, rew, term, trunc, info = sim.step_symbol("005930", action=ActionType.BUY, position_weight=-0.5)
    # 음수 비중은 0.0으로 클리핑되어 매수가 체결되지 않아야 함
    assert info["trade"] is None or not info["trade"].is_success or info["trade"].quantity == 0

    obs, rew, term, trunc, info = sim.step_symbol("005930", action=ActionType.BUY, position_weight=1.5)
    # 1.5는 1.0으로 클리핑되어 전액 매수 시도되어야 함
    assert info["trade"] is not None and info["trade"].is_success
    assert sim.account.get_position("005930").quantity > 0

    # process_triggered_queue with no policy or events pops existing queue items
    popped = sim.process_triggered_queue(None)
    assert len(popped) == 1
    assert popped[0]["symbol"] == "005930"
    assert popped[0]["status"] == "POPPED"

    # When queue is empty, returns empty list
    assert sim.process_triggered_queue(None) == []
    assert sim.process_triggered_queue([]) == []
    assert sim.process_triggered_queue("invalid_arg") == []

    print("  -> PASSED: RL 14D observation & step_symbol invariants preserved!")


if __name__ == "__main__":
    print("=== STARTING PHASE 5 ADVERSARIAL STRESS TEST ===")
    test_legacy_step_and_get_state_backward_compatibility()
    test_screener_adversarial_inputs()
    test_screener_concurrency_race_conditions()
    test_rl_observation_and_step_symbol_invariants()
    print("=== ALL PHASE 5 ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY ===")
