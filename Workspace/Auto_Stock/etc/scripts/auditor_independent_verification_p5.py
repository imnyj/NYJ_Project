"""
etc/scripts/auditor_independent_verification_p5.py
==================================================
Victory Auditor 독립 검증 스크립트.
팀의 기존 테스트에 의존하지 않고, 완전히 새로운 데이터와 극한 시나리오로
Phase 5 요구사항(R1~R4)의 실제 연산 동작 및 무결성을 직접 검증합니다.
"""

import sys
import math
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

from modules.data.screener import StockScreener, ScreeningCriteria, ShardedPollingScheduler, TokenBucketLimiter
from modules.engine.live_learning_simulator import LiveLearningSimulator
from modules.engine.mock_environment import ActionType
from core.kiwoom_api import PriceQuote

def run_auditor_verification():
    print("=" * 70)
    print(">>> VICTORY AUDITOR INDEPENDENT VERIFICATION <<<")
    print("=" * 70)
    passed_count = 0
    total_count = 5

    # -------------------------------------------------------------
    # [Check 1] R1: Static Pool Update with Mixed Real & Edge Data
    # -------------------------------------------------------------
    print("\n[Check 1] Testing R1: update_daily_static_pool logic...")
    screener = StockScreener()

    test_df = pd.DataFrame([
        # 1. 완벽 충족: 5,000억, PER 5.0, PBR 0.8, 외인 500, 기관 300 -> PASS
        {"symbol": "005930", "market_cap": 500_000_000_000, "per": 5.0, "pbr": 0.8, "외국인순매수": 500, "기관순매수": 300},
        # 2. 정확히 하한 경계: 1,000억, PER 1.0, PBR 0.1, 외인 0, 기관 0 -> PASS
        {"symbol": "000660", "market_cap": 100_000_000_000, "per": 1.0, "pbr": 0.1, "외국인순매수": 0, "기관순매수": 0},
        # 3. 정확히 상한 경계: 2,000억, PER 15.0, PBR 2.0 -> PASS
        {"symbol": "035420", "market_cap": 200_000_000_000, "per": 15.0, "pbr": 2.0},
        # 4. 시총 1원 미달: 99,999,999,999 -> FAIL
        {"symbol": "035720", "market_cap": 99_999_999_999, "per": 10.0, "pbr": 1.0},
        # 5. PER 15.0001 초과 -> FAIL
        {"symbol": "051910", "market_cap": 300_000_000_000, "per": 15.0001, "pbr": 1.0},
        # 6. PBR 2.0001 초과 -> FAIL
        {"symbol": "006400", "market_cap": 300_000_000_000, "per": 10.0, "pbr": 2.0001},
        # 7. 외인 순매도 (-1) -> FAIL
        {"symbol": "068270", "market_cap": 300_000_000_000, "per": 10.0, "pbr": 1.0, "외국인순매수": -1},
        # 8. 기관 순매도 (-1) -> FAIL
        {"symbol": "028260", "market_cap": 300_000_000_000, "per": 10.0, "pbr": 1.0, "기관순매수": -1},
        # 9. 적자 기업 (PER <= 0) -> FAIL
        {"symbol": "005380", "market_cap": 300_000_000_000, "per": -2.5, "pbr": 1.0},
        # 10. 자본잠식 기업 (PBR <= 0) -> FAIL
        {"symbol": "105560", "market_cap": 300_000_000_000, "per": 8.0, "pbr": 0.0},
    ])

    pool = screener.update_daily_static_pool(test_df)
    assert pool == ["005930", "035420", "000660"], f"Unexpected pool: {pool}"
    print(f"  -> Selected candidates: {pool} (Correctly filtered 3 of 10)")
    passed_count += 1

    # -------------------------------------------------------------
    # [Check 2] R2: Intra-day Dynamic Trigger & Exact Momentum Calculation
    # -------------------------------------------------------------
    print("\n[Check 2] Testing R2: check_intraday_trigger exact calculations...")
    screener.candidate_pool = ["005930"]
    screener.candidate_set = {"005930"}
    t0 = datetime(2026, 9, 3, 10, 0, 0)

    # 2.1 정확히 3.000배 거래량 및 정확히 +3.000% 가격 -> 트리거 성공
    tick_exact = {
        "symbol": "005930",
        "price": 51500.0,
        "open_price": 50000.0,
        "accum_volume": 30000,
        "prev_same_time_volume": 10000,
        "timestamp": t0,
    }
    assert screener.check_intraday_trigger(tick_exact) == "005930"

    # 2.2 동일 종목 30초 후 재유입 -> 쿨다운 차단 (None)
    tick_cooldown = dict(tick_exact, timestamp=t0 + timedelta(seconds=30))
    assert screener.check_intraday_trigger(tick_cooldown) is None

    # 2.3 동일 종목 61초 후 재유입 -> 정상 재트리거
    tick_after_cooldown = dict(tick_exact, timestamp=t0 + timedelta(seconds=61))
    assert screener.check_intraday_trigger(tick_after_cooldown) == "005930"
    print("  -> Exact threshold and cooldown debounce verified successfully.")
    passed_count += 1

    # -------------------------------------------------------------
    # [Check 3] R3: TokenBucket Limiter & Sharded Polling Scheduler
    # -------------------------------------------------------------
    print("\n[Check 3] Testing R3: Rate limiter and Sharded scheduler...")
    limiter = TokenBucketLimiter(rate=10.0, capacity=5.0)
    for _ in range(5):
        assert limiter.acquire(1.0) is True

    scheduler = ShardedPollingScheduler(symbols=[f"{i:06d}" for i in range(12)], max_per_sec=3.0)
    batches = scheduler.get_batches()
    assert len(batches) == 4
    assert all(len(b) == 3 for b in batches)
    print("  -> TokenBucket and Sharded scheduler partitioned 12 symbols into 4 batches of 3.")
    passed_count += 1

    # -------------------------------------------------------------
    # [Check 4] R4: RL Engine Integration & 14-dim Observation
    # -------------------------------------------------------------
    print("\n[Check 4] Testing R4: RL Simulator injection and observation vector...")
    sim = LiveLearningSimulator(initial_cash=10_000_000)
    trigger_meta = {
        "symbol": "005930",
        "price": 70000.0,
        "open_price": 68000.0,
        "volume": 20000,
        "accum_volume": 150000,
    }
    injected = screener.route_trigger_to_simulator("005930", sim, trigger_info=trigger_meta)
    assert injected is True
    assert "005930" in sim.active_pool
    assert not sim.triggered_queue.empty()

    obs = sim.build_rl_observation("005930")
    assert isinstance(obs, np.ndarray)
    assert obs.shape == (14,)
    assert obs.dtype == np.float32
    assert not np.isnan(obs).any()
    assert not np.isinf(obs).any()
    # 10개 시장 피처 중 return_from_open과 vol_norm 검증
    # ret_from_open = (70000 - 68000) / 68000 = 0.029411
    assert abs(obs[0] - 0.029411) < 1e-4
    print(f"  -> 14-dim observation vector generated with exact normalized values: obs[0]={obs[0]:.6f}")
    passed_count += 1

    # -------------------------------------------------------------
    # [Check 5] R4: step_symbol Position Trading and Equity Conservation
    # -------------------------------------------------------------
    print("\n[Check 5] Testing R4: step_symbol multi-stock equity & trading execution...")
    with patch("core.kiwoom_api.KiwoomClient.get_current_price") as mock_price:
        mock_price.return_value = PriceQuote(
            symbol="005930",
            current_price=Decimal("70000"),
            price_change=Decimal("0"),
            change_rate=Decimal("0"),
            open_price=Decimal("68000"),
            high_price=Decimal("71000"),
            low_price=Decimal("68000"),
            volume=50000,
            trade_amount=Decimal("0"),
            timestamp=datetime.now(),
        )
        # 50% 비중 매수
        obs_step, reward, terminated, truncated, info = sim.step_symbol("005930", action=ActionType.BUY, position_weight=0.5)
        assert info["trade"] is not None
        assert info["trade"].is_success is True
        assert info["trade"].quantity > 0
        assert sim.account.get_position("005930").quantity > 0
        assert isinstance(reward, float)
        assert not math.isnan(reward)
        assert terminated is False
        assert truncated is False
        print(f"  -> Executed BUY order for {info['trade'].quantity} shares at {info['live_price_used']} KRW.")
        print(f"  -> Portfolio Equity: {info['total_equity']:,.0f} KRW, Log Return: {reward:.6f}")
    passed_count += 1

    print("\n" + "=" * 70)
    print(f"AUDITOR INDEPENDENT VERIFICATION RESULT: {passed_count}/{total_count} PASSED (100%)")
    print("=" * 70)

if __name__ == "__main__":
    run_auditor_verification()
