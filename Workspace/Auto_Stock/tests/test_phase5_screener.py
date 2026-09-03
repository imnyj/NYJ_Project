"""
tests/test_phase5_screener.py
=============================
Auto_Stock Phase 5: 다이내믹 종목 스크리너 (Dynamic Stock Screener) 5-Tier 테스트 스위트.

Tier 1: Feature Coverage (정적 펀더멘털 필터 및 장중 모멘텀 트리거 핵심 기능)
Tier 2: Boundary & Corner Cases (시총/PER/PBR 경계값, 결측치, 0/음수 분모 방어)
Tier 3: API Rate Limit & Scheduling Optimization (청크 분할 스케줄러, 토큰 버킷, 스트리머 리스너)
Tier 4: RL Simulator Integration (종목 동적 주입, 14차원 obs 생성, step_symbol 매매 체결)
Tier 5: Adversarial & Concurrency Hardening (멀티스레드 동시성 안전, 쿨다운 방어, 수급 바이패스)
"""

import math
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from core.kiwoom_api import PriceQuote
from modules.data.screener import (
    DynamicStockScreener,
    ScreenerConfig,
    ScreeningCriteria,
    ShardedPollingScheduler,
    StockScreener,
    TokenBucketLimiter,
)
from modules.data.streamer import MockStreamer, TickData
from modules.engine.live_learning_simulator import (
    LiveLearningSimulator,
    get_live_simulator,
    reset_global_simulator,
)
from modules.engine.mock_environment import ActionType


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def sample_fundamental_df() -> pd.DataFrame:
    """10개 종목 가상 펀더멘털 데이터프레임"""
    return pd.DataFrame([
        # 1. 완벽 충족 종목 (시총 5000억, PER 8.5, PBR 0.9, 외인 1000, 기관 500)
        {
            "symbol": "005930",
            "market_cap": 500_000_000_000,
            "per": 8.5,
            "pbr": 0.9,
            "foreign_net_buy": 1000,
            "inst_net_buy": 500,
            "foreign_rate": 52.0,
        },
        # 2. 완벽 충족 종목 (시총 1500억, PER 12.0, PBR 1.4, 외인 200, 기관 100)
        {
            "symbol": "000660",
            "market_cap": 150_000_000_000,
            "per": 12.0,
            "pbr": 1.4,
            "foreign_net_buy": 200,
            "inst_net_buy": 100,
            "foreign_rate": 48.0,
        },
        # 3. 시총 미달 (시총 800억 < 1000억)
        {
            "symbol": "035420",
            "market_cap": 80_000_000_000,
            "per": 10.0,
            "pbr": 1.1,
            "foreign_net_buy": 50,
            "inst_net_buy": 50,
            "foreign_rate": 20.0,
        },
        # 4. PER 초과 (PER 25.0 > 15.0)
        {
            "symbol": "035720",
            "market_cap": 200_000_000_000,
            "per": 25.0,
            "pbr": 1.2,
            "foreign_net_buy": 100,
            "inst_net_buy": 100,
            "foreign_rate": 30.0,
        },
        # 5. PER 적자 (PER -5.0)
        {
            "symbol": "005380",
            "market_cap": 300_000_000_000,
            "per": -5.0,
            "pbr": 0.8,
            "foreign_net_buy": 100,
            "inst_net_buy": 100,
            "foreign_rate": 25.0,
        },
        # 6. PBR 초과 (PBR 3.5 > 2.0)
        {
            "symbol": "051910",
            "market_cap": 400_000_000_000,
            "per": 9.0,
            "pbr": 3.5,
            "foreign_net_buy": 100,
            "inst_net_buy": 100,
            "foreign_rate": 40.0,
        },
        # 7. PBR 0 이하 (PBR 0.0)
        {
            "symbol": "006400",
            "market_cap": 250_000_000_000,
            "per": 7.0,
            "pbr": 0.0,
            "foreign_net_buy": 100,
            "inst_net_buy": 100,
            "foreign_rate": 15.0,
        },
        # 8. 한글 컬럼명 지원 완벽 충족 종목 (시총 1200억, PER 6.0, PBR 0.5)
        {
            "symbol": "068270",
            "market_cap": 120_000_000_000,
            "per": 6.0,
            "pbr": 0.5,
            "foreign_net_buy": 500,
            "inst_net_buy": 200,
            "foreign_rate": 10.0,
        },
        # 9. 외인/기관 순매도 탈락 케이스 (외인 -500, 기관 -300)
        {
            "symbol": "105560",
            "market_cap": 180_000_000_000,
            "per": 11.0,
            "pbr": 0.7,
            "foreign_net_buy": -500,
            "inst_net_buy": -300,
            "foreign_rate": 35.0,
        },
        # 10. 완벽 충족 종목 (시총 2200억, PER 14.5, PBR 1.8)
        {
            "symbol": "028260",
            "market_cap": 220_000_000_000,
            "per": 14.5,
            "pbr": 1.8,
            "foreign_net_buy": 50,
            "inst_net_buy": 50,
            "foreign_rate": 20.0,
        },
    ])


@pytest.fixture
def screener() -> StockScreener:
    """기본 설정 스크리너 인스턴스"""
    criteria = ScreeningCriteria(
        min_market_cap=100_000_000_000,
        min_per=1.0,
        max_per=15.0,
        min_pbr=0.1,
        max_pbr=2.0,
        min_foreign_net_buy=0,
        min_inst_net_buy=0,
        volume_surge_threshold=3.0,
        price_surge_threshold=0.03,
        cooldown_seconds=60.0,
    )
    return StockScreener(criteria=criteria)


# ==============================================================================
# Tier 1: Feature Coverage (정적 펀더멘털 필터 및 실시간 모멘텀 트리거 기본)
# ==============================================================================

class TestTier1FeatureCoverage:
    """Tier 1: 스크리너 핵심 기능 정상 동작 검증"""

    def test_update_daily_static_pool_happy_path(self, screener, sample_fundamental_df):
        """TC-P5-01: 조건 부합 종목만 감시 풀에 정확히 추출되는지 검증"""
        pool = screener.update_daily_static_pool(sample_fundamental_df)
        assert isinstance(pool, list)

        # 005930, 000660, 068270, 028260 4개 종목이 조건에 부합
        assert "005930" in pool
        assert "000660" in pool
        assert "068270" in pool
        assert "028260" in pool

        # 탈락 종목들 미포함 검증
        assert "035420" not in pool  # 시총 미달
        assert "035720" not in pool  # PER 초과
        assert "005380" not in pool  # PER 적자
        assert "051910" not in pool  # PBR 초과
        assert "006400" not in pool  # PBR 0 이하
        assert "105560" not in pool  # 외인/기관 순매도

        assert screener.candidate_pool == pool
        assert len(screener.candidate_set) == len(pool)

    def test_check_intraday_trigger_volume_and_price_surge(self, screener):
        """TC-P5-02: 거래량 300% 폭증 & 가격 3% 급등 시 정상 트리거 반환"""
        screener.candidate_pool = ["005930", "000660"]
        screener.candidate_set = {"005930", "000660"}

        # 당일 시가 70,000원 -> 현재가 72,500원 (+3.57% 급등)
        # 전일 동시간 거래량 10,000주 -> 현재 누적 거래량 35,000주 (3.5배 폭증)
        tick_dict = {
            "symbol": "005930",
            "price": 72500.0,
            "open_price": 70000.0,
            "volume": 5000,
            "accum_volume": 35000,
            "prev_same_time_volume": 10000,
            "timestamp": datetime.now(),
        }

        triggered_sym = screener.check_intraday_trigger(tick_dict)
        assert triggered_sym == "005930"

    def test_check_intraday_trigger_negative_conditions(self, screener):
        """TC-P5-03: 미충족 조건에 따른 트리거 실패(None 반환) 검증"""
        screener.candidate_pool = ["005930"]
        screener.candidate_set = {"005930"}

        now = datetime.now()

        # 케이스 1: 거래량 폭증 충족(4배) BUT 가격 상승 미달(+1.0% < 3%)
        tick_fail_price = {
            "symbol": "005930",
            "price": 70700.0,
            "open_price": 70000.0,
            "accum_volume": 40000,
            "prev_same_time_volume": 10000,
            "timestamp": now,
        }
        assert screener.check_intraday_trigger(tick_fail_price) is None

        # 케이스 2: 가격 급등 충족(+5.0%) BUT 거래량 미달(1.5배 < 3배)
        tick_fail_volume = {
            "symbol": "005930",
            "price": 73500.0,
            "open_price": 70000.0,
            "accum_volume": 15000,
            "prev_same_time_volume": 10000,
            "timestamp": now,
        }
        assert screener.check_intraday_trigger(tick_fail_volume) is None

        # 케이스 3: 조건 충족 BUT 감시 풀에 없는 미등록 종목
        tick_unregistered = {
            "symbol": "999999",
            "price": 50000.0,
            "open_price": 45000.0,
            "accum_volume": 100000,
            "prev_same_time_volume": 10000,
            "timestamp": now,
        }
        assert screener.check_intraday_trigger(tick_unregistered) is None

    def test_screening_criteria_defaults_and_custom(self):
        """TC-P5-04: 설정 데이터클래스 및 별칭(ScreenerConfig) 기본값 및 속성 검증"""
        criteria = ScreeningCriteria()
        assert criteria.min_market_cap == 100_000_000_000
        assert criteria.min_per == 1.0
        assert criteria.max_per == 15.0
        assert criteria.min_pbr == 0.1
        assert criteria.max_pbr == 2.0
        assert criteria.volume_surge_threshold == 3.0
        assert criteria.price_surge_threshold == 0.03
        assert criteria.cooldown_seconds == 60.0
        assert criteria.max_candidates == 200

        # 별칭 프로퍼티 검증
        assert criteria.per_min == 1.0
        assert criteria.per_max == 15.0
        assert criteria.volume_surge_ratio == 3.0
        assert criteria.price_surge_ratio == 0.03

        # ScreenerConfig 및 DynamicStockScreener 동일성 확인
        assert ScreenerConfig is ScreeningCriteria
        assert DynamicStockScreener is StockScreener


# ==============================================================================
# Tier 2: Boundary & Corner Cases (경계값 및 결측 방어)
# ==============================================================================

class TestTier2BoundaryAndCornerCases:
    """Tier 2: 임계 경계값, 결측치, 0/음수 분모 연산 방어 검증"""

    def test_boundary_market_cap_exact_threshold(self, screener):
        """TC-P5-05: 시가총액 정확히 1,000억 원 경계값 검증"""
        df_boundary = pd.DataFrame([
            {"symbol": "111111", "market_cap": 100_000_000_000, "per": 5.0, "pbr": 1.0},  # 정확히 1000억 -> 포함
            {"symbol": "222222", "market_cap": 99_999_999_999, "per": 5.0, "pbr": 1.0},   # 1원 미달 -> 제외
        ])
        pool = screener.update_daily_static_pool(df_boundary)
        assert "111111" in pool
        assert "222222" not in pool

    def test_boundary_per_pbr_zero_negative_nan_inf(self, screener):
        """TC-P5-06: PER/PBR 음수, 결측치(NaN), 무한대(Inf) 무결성 검증"""
        df_dirty = pd.DataFrame([
            {"symbol": "000010", "market_cap": 200_000_000_000, "per": 1.0, "pbr": 0.1},    # 하한 경계값 -> 포함
            {"symbol": "000020", "market_cap": 200_000_000_000, "per": 15.0, "pbr": 2.0},   # 상한 경계값 -> 포함
            {"symbol": "000030", "market_cap": 200_000_000_000, "per": np.nan, "pbr": 1.0},  # PER 결측 -> 제외
            {"symbol": "000040", "market_cap": 200_000_000_000, "per": np.inf, "pbr": 1.0},  # PER 무한대 -> 제외
            {"symbol": "000050", "market_cap": 200_000_000_000, "per": 0.0, "pbr": 1.0},     # PER 0 -> 제외
            {"symbol": "000060", "market_cap": 200_000_000_000, "per": 10.0, "pbr": -0.5},   # PBR 음수 -> 제외
            {"symbol": "000070", "market_cap": 200_000_000_000, "per": "INVALID", "pbr": 1.0}, # 문자열 -> 제외
        ])
        pool = screener.update_daily_static_pool(df_dirty)
        assert "000010" in pool
        assert "000020" in pool
        assert len(pool) == 2

    def test_boundary_surge_threshold_exact_match(self, screener):
        """TC-P5-07: 거래량 정확히 300.0% 및 가격 정확히 +3.0% 경계값 검증"""
        screener.candidate_pool = ["005930"]
        screener.candidate_set = {"005930"}
        base_time = datetime(2026, 9, 3, 10, 0, 0)

        # 1. 정확히 3.00배 거래량, 정확히 +3.00% 가격 (10,000 * 1.03 = 10,300) -> 충족
        tick_exact = {
            "symbol": "005930",
            "price": 10300.0,
            "open_price": 10000.0,
            "accum_volume": 30000,
            "prev_same_time_volume": 10000,
            "timestamp": base_time,
        }
        assert screener.check_intraday_trigger(tick_exact) == "005930"

        # 2. 거래량 2.999배 (미달)
        screener._last_triggered_time.clear()
        tick_vol_below = dict(tick_exact)
        tick_vol_below["accum_volume"] = 29999
        assert screener.check_intraday_trigger(tick_vol_below) is None

        # 3. 가격상승 2.99% (미달: 10,299 / 10,000 - 1 = 0.0299)
        screener._last_triggered_time.clear()
        tick_price_below = dict(tick_exact)
        tick_price_below["price"] = 10299.0
        assert screener.check_intraday_trigger(tick_price_below) is None

    def test_zero_open_price_and_zero_base_volume_defense(self, screener):
        """TC-P5-08: 시가 0 또는 기준 거래량 0 유입 시 ZeroDivisionError 방어"""
        screener.candidate_pool = ["005930"]
        screener.candidate_set = {"005930"}

        # 시가 0
        tick_zero_open = {
            "symbol": "005930",
            "price": 10000.0,
            "open_price": 0.0,
            "accum_volume": 100000,
            "prev_same_time_volume": 10000,
        }
        assert screener.check_intraday_trigger(tick_zero_open) is None

        # 기준 거래량 0
        tick_zero_vol = {
            "symbol": "005930",
            "price": 11000.0,
            "open_price": 10000.0,
            "accum_volume": 100000,
            "prev_same_time_volume": 0,
        }
        assert screener.check_intraday_trigger(tick_zero_vol) is None

        # 음수 시가
        tick_neg_open = dict(tick_zero_open, open_price=-5000.0)
        assert screener.check_intraday_trigger(tick_neg_open) is None


# ==============================================================================
# Tier 3: API Rate Limit & Scheduling Optimization (호출 최적화)
# ==============================================================================

class TestTier3RateLimitAndOptimization:
    """Tier 3: 초당 5회 제한 준수 분할 스케줄러, 토큰 버킷, 스트리머 리스너 검증"""

    def test_sharded_polling_scheduler_partitioning(self):
        """TC-P5-09: 150개 후보군을 초당 3개 청크로 정확히 50개 배치 분할"""
        symbols = [f"{i:06d}" for i in range(150)]
        scheduler = ShardedPollingScheduler(symbols=symbols, max_per_sec=3.0)
        batches = scheduler.get_batches()

        assert len(batches) == 50
        assert len(batches[0]) == 3
        assert batches[0] == ["000000", "000001", "000002"]
        assert batches[-1] == ["000147", "000148", "000149"]

    def test_token_bucket_rate_limiter_throttling(self):
        """TC-P5-10: 초당 3회 제한 TokenBucket 속도 제어(Throttling) 검증"""
        # rate=5.0, capacity=2.0
        limiter = TokenBucketLimiter(rate=5.0, capacity=2.0)
        start_time = time.time()

        # 2개 토큰 즉시 소진
        limiter.acquire(1.0)
        limiter.acquire(1.0)

        # 3번째 토큰 획득 시 버킷이 채워질 때까지 대기 발생
        limiter.acquire(1.0)
        elapsed = time.time() - start_time
        assert elapsed >= 0.15  # 최소 약 0.2초 대기 확인

    def test_websocket_streamer_event_driven_integration(self, screener):
        """TC-P5-11: WebSocket 실시간 스트리머 on_tick 이벤트 디스패치 연동 검증"""
        screener.candidate_pool = ["005930"]
        screener.candidate_set = {"005930"}

        streamer = MockStreamer(base_prices={"005930": 70000.0})
        screener.attach_streamer(streamer)

        # TickData 객체를 직접 주입하여 on_tick 호출 검증
        tick = TickData(
            symbol="005930",
            price=73000.0,
            volume=5000,
            accum_volume=40000,
            open_price=70000.0,
            timestamp=datetime.now(),
        )

        # prev_same_time_volume 속성을 동적 부착하여 트리거 확인
        setattr(tick, "prev_same_time_volume", 10000)
        res = screener.on_tick(tick)
        assert res == "005930"

    def test_schedule_polling_chunks_method(self, screener):
        """TC-P5-12: StockScreener 내부 schedule_polling_chunks 메서드 검증"""
        screener.candidate_pool = [f"{i:06d}" for i in range(10)]
        chunks = screener.schedule_polling_chunks(chunk_size=3)
        assert len(chunks) == 4
        assert len(chunks[0]) == 3
        assert len(chunks[-1]) == 1


# ==============================================================================
# Tier 4: Real-World E2E Pipeline & Simulator Integration (R4)
# ==============================================================================

class TestTier4SimulatorIntegration:
    """Tier 4: LiveLearningSimulator 동적 주입, 14차원 obs 생성, step_symbol 매매 연동"""

    @patch("core.kiwoom_api.KiwoomClient.get_current_price")
    def test_screener_to_live_learning_simulator_handoff(self, mock_get_price, screener, sample_fundamental_df):
        """TC-P5-13: 스크리너 포착 종목의 LiveLearningSimulator 주입 및 14차원 관측/주문 연동"""
        mock_get_price.return_value = PriceQuote(
            symbol="005930",
            current_price=Decimal("80000"),
            price_change=Decimal("0"),
            change_rate=Decimal("0"),
            open_price=Decimal("75000"),
            high_price=Decimal("81000"),
            low_price=Decimal("75000"),
            volume=20000,
            trade_amount=Decimal("0"),
            timestamp=datetime.now(),
        )

        # 1. 정적 감시 풀 추출
        screener.update_daily_static_pool(sample_fundamental_df)
        assert "005930" in screener.candidate_pool

        # 2. 장중 모멘텀 돌파 발생
        tick = {
            "symbol": "005930",
            "price": 80000.0,
            "open_price": 75000.0,
            "accum_volume": 100000,
            "prev_same_time_volume": 20000,
            "timestamp": datetime.now(),
        }
        triggered_symbol = screener.check_intraday_trigger(tick)
        assert triggered_symbol == "005930"

        # 3. LiveLearningSimulator 초기화 및 동적 주입
        sim = LiveLearningSimulator(initial_cash=10_000_000)
        success = screener.route_trigger_to_simulator(triggered_symbol, sim, trigger_info=tick)
        assert success is True
        assert "005930" in sim.active_pool
        assert not sim.triggered_queue.empty()

        # 4. 14차원 관측 벡터 생성 검증
        obs = sim.build_rl_observation("005930")
        assert isinstance(obs, np.ndarray)
        assert obs.shape == (14,)
        assert obs.dtype == np.float32
        assert not np.isnan(obs).any()

        # 5. step_symbol 하이브리드 주문 비중(50% 매수) 체결 검증
        obs, reward, terminated, truncated, info = sim.step_symbol(
            symbol="005930",
            action=ActionType.BUY,
            position_weight=0.5,
        )
        assert obs.shape == (14,)
        assert info["trade"] is not None
        assert info["trade"].is_success is True
        assert info["trade"].quantity > 0
        assert sim.account.get_position("005930").quantity > 0
        assert terminated is False
        assert truncated is False
        assert isinstance(reward, float)

    @patch("core.kiwoom_api.KiwoomClient.get_current_price")
    def test_process_triggered_queue_batch(self, mock_get_price):
        """TC-P5-14: process_triggered_queue를 통한 배치 큐 처리 검증"""
        mock_get_price.return_value = PriceQuote(
            symbol="000660",
            current_price=Decimal("120000"),
            price_change=Decimal("0"),
            change_rate=Decimal("0"),
            open_price=Decimal("115000"),
            high_price=Decimal("121000"),
            low_price=Decimal("115000"),
            volume=5000,
            trade_amount=Decimal("0"),
            timestamp=datetime.now(),
        )

        sim = LiveLearningSimulator(initial_cash=10_000_000)
        sim.inject_triggered_symbol("000660", trigger_info={"price": 120000, "open_price": 115000})

        # 정책 함수: 무조건 30% 매수
        def dummy_policy(obs: np.ndarray):
            return int(ActionType.BUY), 0.3

        results = sim.process_triggered_queue(policy_fn=dummy_policy)
        assert len(results) == 1
        assert results[0]["symbol"] == "000660"
        assert results[0]["action"] == int(ActionType.BUY)
        assert results[0]["info"]["trade"].is_success is True


# ==============================================================================
# Tier 5: Adversarial & Concurrency Hardening (동시성/안전성)
# ==============================================================================

class TestTier5AdversarialAndConcurrency:
    """Tier 5: 멀티스레드 동시 주입, 쿨다운 채터링 방지, 결측 컬럼 안전 바이패스 검증"""

    def test_concurrent_tick_injection_thread_safety(self, screener):
        """TC-P5-15: 8개 스레드에서 동시에 틱 주입 시 Thread-Safe 무결성 검증"""
        screener.candidate_pool = [f"{i:06d}" for i in range(20)]
        screener.candidate_set = set(screener.candidate_pool)

        results = []
        errors = []

        def worker(sym_idx: int):
            try:
                sym = f"{sym_idx:06d}"
                tick = {
                    "symbol": sym,
                    "price": 10500.0,
                    "open_price": 10000.0,
                    "accum_volume": 40000,
                    "prev_same_time_volume": 10000,
                    "timestamp": datetime.now(),
                }
                res = screener.check_intraday_trigger(tick)
                if res:
                    results.append(res)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i % 20,)) for i in range(40)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) > 0

    def test_screener_trigger_cooldown_defense(self, screener):
        """TC-P5-16: 동일 종목 연속 틱 주입 시 60초 쿨다운 디바운스 작동 검증"""
        screener.candidate_pool = ["005930"]
        screener.candidate_set = {"005930"}

        t0 = datetime(2026, 9, 3, 10, 0, 0)
        tick1 = {
            "symbol": "005930",
            "price": 10500.0,
            "open_price": 10000.0,
            "accum_volume": 40000,
            "prev_same_time_volume": 10000,
            "timestamp": t0,
        }
        # 1회차: 정상 트리거
        assert screener.check_intraday_trigger(tick1) == "005930"

        # 30초 후(쿨다운 60초 미경과): 2회차 트리거 거부 (None)
        t1 = t0 + timedelta(seconds=30)
        tick2 = dict(tick1, timestamp=t1)
        assert screener.check_intraday_trigger(tick2) is None

        # 61초 후(쿨다운 60초 경과): 3회차 정상 재트리거
        t2 = t0 + timedelta(seconds=61)
        tick3 = dict(tick1, timestamp=t2)
        assert screener.check_intraday_trigger(tick3) == "005930"

    def test_foreign_and_inst_net_buy_filtering_and_bypass(self, screener):
        """TC-P5-17: 수급 컬럼 존재 시 엄격 검증 및 부재 시 안전 바이패스(무중단) 검증"""
        # 케이스 1: 수급 컬럼이 아예 없는 DataFrame (시총 1000억, PER 10, PBR 1)
        df_no_supply = pd.DataFrame([
            {"symbol": "111111", "market_cap": 200_000_000_000, "per": 10.0, "pbr": 1.0},
        ])
        pool1 = screener.update_daily_static_pool(df_no_supply)
        assert "111111" in pool1  # 에러 없이 안전 바이패스 통과

        # 케이스 2: 수급 컬럼 존재 시 음수 순매수 엄격 차단
        df_with_negative_supply = pd.DataFrame([
            {
                "symbol": "222222",
                "market_cap": 200_000_000_000,
                "per": 10.0,
                "pbr": 1.0,
                "foreign_net_buy": -100,  # 외인 순매도
                "inst_net_buy": 100,
            },
        ])
        pool2 = screener.update_daily_static_pool(df_with_negative_supply)
        assert "222222" not in pool2  # min_foreign_net_buy=0 미달 탈락

    def test_duck_typing_tick_formats(self, screener):
        """TC-P5-18: TickData 인스턴스, Dict, Mock 객체 등 다형성 입력 처리 검증"""
        screener.candidate_pool = ["005930"]
        screener.candidate_set = {"005930"}

        # 1. 딕셔너리 포맷
        d_tick = {
            "symbol": "005930",
            "price": 10400.0,
            "open_price": 10000.0,
            "accum_volume": 40000,
            "prev_same_time_volume": 10000,
            "timestamp": datetime(2026, 9, 3, 9, 30, 0),
        }
        assert screener.check_intraday_trigger(d_tick) == "005930"

        # 2. TickData 객체 포맷
        screener._last_triggered_time.clear()
        obj_tick = TickData(
            symbol="005930",
            price=10400.0,
            volume=5000,
            accum_volume=40000,
            open_price=10000.0,
            timestamp=datetime(2026, 9, 3, 9, 35, 0),
        )
        setattr(obj_tick, "prev_same_time_volume", 10000)
        assert screener.check_intraday_trigger(obj_tick) == "005930"

    def test_string_baseline_volume_defenses(self, screener):
        """TC-P5-19: [BUG-P5-01] 문자열 baseline_volume 유입 시 TypeError 방어 및 안전 처리 검증"""
        screener.candidate_pool = ["000660"]
        screener.candidate_set = {"000660"}

        # 1. 정상 숫자 문자열 ("10000"): float 변환되어 정상 트리거
        tick_valid_str = {
            "symbol": "000660",
            "price": 105000.0,
            "open_price": 100000.0,
            "accum_volume": 40000,
            "prev_same_time_volume": "10000",
            "timestamp": datetime.now(),
        }
        assert screener.check_intraday_trigger(tick_valid_str) == "000660"

        # 2. 비정상 문자열 ("N/A", "--", ""): TypeError 없이 안전하게 None 반환
        screener._last_triggered_time.clear()
        for invalid_val in ["N/A", "--", "", "invalid"]:
            tick_invalid_str = {
                "symbol": "000660",
                "price": 105000.0,
                "open_price": 100000.0,
                "accum_volume": 40000,
                "prev_same_time_volume": invalid_val,
                "timestamp": datetime.now(),
            }
            assert screener.check_intraday_trigger(tick_invalid_str) is None

    def test_overflow_and_inf_numeric_defenses(self, screener):
        """TC-P5-20: [BUG-P5-02] float('inf') 및 10**400 초대형 수치 주입 시 OverflowError 방어 검증"""
        screener.candidate_pool = ["005930"]
        screener.candidate_set = {"005930"}

        extreme_ticks = [
            # 1. float('inf') 누적 거래량
            {"symbol": "005930", "price": 75000, "open_price": 70000, "accum_volume": float("inf"), "prev_same_time_volume": 10000},
            # 2. float('inf') 기준 거래량
            {"symbol": "005930", "price": 75000, "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": float("inf")},
            # 3. 10**400 초대형 정수 거래량
            {"symbol": "005930", "price": 75000, "open_price": 70000, "accum_volume": 10**400, "prev_same_time_volume": 10000},
            # 4. 10**400 초대형 정수 가격
            {"symbol": "005930", "price": 10**400, "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 10000},
            # 5. float('inf') 가격
            {"symbol": "005930", "price": float("inf"), "open_price": 70000, "accum_volume": 40000, "prev_same_time_volume": 10000},
        ]

        for tick in extreme_ticks:
            screener._last_triggered_time.clear()
            # 예외 없이 안전하게 None 반환 확인
            result = screener.check_intraday_trigger(tick)
            assert result is None

    def test_market_cap_inf_leakage_defense(self, screener):
        """TC-P5-21: [BUG-P5-03] market_cap = np.inf 종목의 감시 풀 누수 및 1위 탈취 철저 배제 검증"""
        df = pd.DataFrame([
            # 정상 종목 (시총 5000억)
            {"symbol": "005930", "market_cap": 500_000_000_000, "per": 10.0, "pbr": 1.0},
            # 정상 종목 (시총 3000억)
            {"symbol": "000660", "market_cap": 300_000_000_000, "per": 12.0, "pbr": 1.5},
            # 시총 무한대 오염 종목
            {"symbol": "000016", "market_cap": np.inf, "per": 10.0, "pbr": 1.0},
            {"symbol": "000017", "market_cap": -np.inf, "per": 10.0, "pbr": 1.0},
        ])

        pool = screener.update_daily_static_pool(df)
        assert "000016" not in pool
        assert "000017" not in pool
        assert pool == ["005930", "000660"]
        assert pool[0] == "005930"  # 정상 1위 보존

    def test_megacap_eok_won_unit_conversion(self, screener):
        """TC-P5-22: [BUG-P5-04] '억원' 단위 메가캡(100조 원 이상) 데이터 주입 시 정상 변환 및 풀 포함 검증"""
        df_eok = pd.DataFrame([
            {"symbol": "005930", "market_cap": 5_000_000, "per": 10.0, "pbr": 1.0},  # 삼성전자 500조 원 (500만 억원)
            {"symbol": "000660", "market_cap": 1_500_000, "per": 12.0, "pbr": 1.5},  # SK하이닉스 150조 원 (150만 억원)
            {"symbol": "068270", "market_cap": 5_000, "per": 8.0, "pbr": 0.8},        # 셀트리온 5천억 원 (5,000 억원)
            {"symbol": "999999", "market_cap": 500, "per": 10.0, "pbr": 1.0},          # 소형주 500억 원 (1,000억 미만 -> 탈락)
        ])

        pool = screener.update_daily_static_pool(df_eok)
        assert len(pool) == 3
        assert pool == ["005930", "000660", "068270"]
        assert "999999" not in pool
        # 변환된 시가총액 검증 (500만 억원 -> 500조 원)
        assert screener.candidate_pool_df.loc[screener.candidate_pool_df["symbol"] == "005930", "market_cap"].iloc[0] == 500_000_000_000_000

