import sys, os; sys.path.insert(0, os.path.abspath(".")); """
etc/scripts/test_empirical_challenger_p5.py
===========================================
Pytest-executable Adversarial Challenge Suite for Phase 5 RL Engine & Rate Limiter.
"""

import math
import threading
import time
from decimal import Decimal
from unittest.mock import patch

import numpy as np
import pytest

from core.kiwoom_api import PriceQuote
from modules.data.screener import (
    ScreeningCriteria,
    ShardedPollingScheduler,
    StockScreener,
    TokenBucketLimiter,
)
from modules.engine.live_learning_simulator import LiveLearningSimulator
from modules.engine.mock_environment import ActionType


class TestEmpiricalChallengerPhase5:
    """적대적 극한 환경 실측 검증 테스트 스위트"""

    def test_c1_high_load_concurrent_queue_injection(self):
        """[C1] 20개 스레드 동시 1,000회 주입 및 큐 오버플로우/경쟁상태 무결성 검증"""
        sim = LiveLearningSimulator(initial_cash=50_000_000)
        errors = []
        injected = 0
        lock = threading.Lock()

        def worker(t_id):
            nonlocal injected
            for i in range(50):
                sym = f"{(t_id * 50 + i) % 150:06d}"
                try:
                    ok = sim.inject_triggered_symbol(sym, trigger_info={"price": 50000 + i * 10})
                    if ok:
                        with lock:
                            injected += 1
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert injected == 1000
        assert sim.triggered_queue.qsize() == 1000
        assert len(sim.active_pool) <= 150

    def test_c2_observation_vector_adversarial_invariance(self):
        """[C2] 14차원 float32 관측 벡터의 극단적/비정상 피처 및 결측치 완전 차단 검증"""
        sim = LiveLearningSimulator(initial_cash=10_000_000)

        # 1. NaN/Inf 시장 피처 주입
        bad_features = [np.nan, np.inf, -np.inf, 1e25, -1e25, 0.0, 1.0, -1.0, 999.0, -999.0]
        obs = sim.build_rl_observation("005930", market_features=bad_features)
        assert obs.shape == (14,)
        assert obs.dtype == np.float32
        assert not np.isnan(obs).any()
        assert not np.isinf(obs).any()

        # 2. 극단적 트리거 데이터 클리핑 검증
        sim.inject_triggered_symbol("000660", trigger_info={
            "price": 200000,
            "open_price": 50000, # +300% 급등 -> [-0.3, 0.3] 클리핑
            "volume": 100_000_000, # 1억 주 -> [0.0, 50.0] 클리핑
        })
        obs2 = sim.build_rl_observation("000660")
        assert obs2.shape == (14,)
        assert obs2[0] == pytest.approx(0.3, abs=1e-5) # clipped to 0.3
        assert obs2[9] == pytest.approx(50.0, abs=1e-5) # clipped to 50.0

    def test_c3_multi_position_portfolio_equity_conservation_under_shocks(self):
        """[C3] 다중 포지션 보유 중 시장 충격(+30%/-30%) 시 에쿼티 왜곡 0원 및 회계 불변성 검증"""
        prices = {
            "005930": Decimal("70000"),
            "000660": Decimal("120000"),
            "035420": Decimal("200000"),
        }
        sim = LiveLearningSimulator(initial_cash=30_000_000)
        sim.fetch_live_price = lambda sym: prices[sym]

        # 3개 종목 각각 30% 비중 매수
        for s, p in prices.items():
            sim.inject_triggered_symbol(s, trigger_info={"price": float(p)})
            sim.step_symbol(s, action=ActionType.BUY, position_weight=0.30)

        # 에쿼티 보존식 확인
        pos_val = sum(sim.account.get_position(s).quantity * prices[s] for s in prices)
        exact_eq = sim.account.cash_balance + pos_val
        assert sim.account.get_total_equity(prices) == exact_eq

        # 극단적 가격 변동 주입: 005930 +30%, 000660 -30%
        shocked_prices = {
            "005930": Decimal("91000"),
            "000660": Decimal("84000"),
            "035420": Decimal("200000"),
        }
        prices.update(shocked_prices)

        # 갱신 및 검증
        for s in shocked_prices.keys():
            obs, rew, term, trunc, info = sim.step_symbol(s, action=ActionType.HOLD)
            audit = info["audit"]
            assert audit["cash_balance"] + audit["holdings_valuation"] == audit["total_equity"]
            assert isinstance(rew, float)

        final_pos_val = sum(sim.account.get_position(s).quantity * shocked_prices[s] for s in shocked_prices)
        final_expected = float(sim.account.cash_balance + final_pos_val)
        assert abs(final_expected - info["total_equity"]) < 0.01

    def test_c4_sharded_scheduler_and_token_bucket_strict_rate_limiting(self):
        """[C4] ShardedPollingScheduler 및 TokenBucketLimiter의 초당 5회 제한 엄격 준수 검증"""
        # 보수적 설정: rate=3.0, capacity=3.0
        limiter = TokenBucketLimiter(rate=3.0, capacity=3.0)
        timestamps = []
        t0 = time.time()
        for _ in range(9):
            limiter.acquire(1.0)
            timestamps.append(time.time())
        elapsed = time.time() - t0

        # 9개 요청에 대해 최소 (9-3)/3 = 2.0초 이상 소요되어야 함
        assert elapsed >= 1.9

        # 슬라이딩 1초 윈도우 내 최대 요청 수가 6개 이하 (t=0에 3개, 이후 0.33초마다 1개)
        max_in_window = max(
            sum(1 for ts in timestamps if t <= ts < t + 1.0)
            for t in timestamps
        )
        assert max_in_window <= 6

        # 200개 종목 샤딩 분할 검증
        scheduler = ShardedPollingScheduler([f"{i:06d}" for i in range(200)], max_per_sec=3.0)
        batches = scheduler.get_batches()
        assert len(batches) == 67
        assert all(len(b) <= 3 for b in batches)
