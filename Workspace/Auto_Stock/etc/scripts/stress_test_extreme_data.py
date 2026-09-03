#!/usr/bin/env python3
"""
etc/scripts/stress_test_extreme_data.py
=======================================
적대적 검증: 0-분산 횡보, 99.999% 폭락, 초극단 수치 주입 스트레스 테스트
"""

import sys
import os
import math
import numpy as np
import pandas as pd
from decimal import Decimal

# 프로젝트 루트 sys.path 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from modules.hpo.metrics import (
    calculate_total_equity,
    calculate_total_return_pct,
    calculate_annualized_sharpe_ratio,
    calculate_max_drawdown_pct,
    calculate_win_rate,
    evaluate_trading_history,
)
from modules.engine.hybrid_trading_env import HybridTradingEnv

def test_zero_variance_adversarial():
    print("=== [1] 0-분산 횡보 및 극단 평탄 데이터 검증 ===")
    
    # 1. 100% 0.0 수익률
    r0 = [0.0] * 1000
    sr0 = calculate_annualized_sharpe_ratio(r0)
    print(f"  [Pass] All 0.0 returns -> Sharpe: {sr0} (Expected: 0.0)")
    assert sr0 == 0.0

    # 2. 동일한 비영 수익률 (예: 매일 정확히 +0.01%)
    r_const = [0.0001] * 500
    sr_const = calculate_annualized_sharpe_ratio(r_const)
    print(f"  [Pass] Constant non-zero returns -> Sharpe: {sr_const} (Expected: 0.0)")
    assert sr_const == 0.0

    # 3. 동일한 음의 수익률 (매일 정확히 -10%)
    r_neg_const = [-0.10] * 100
    sr_neg_const = calculate_annualized_sharpe_ratio(r_neg_const)
    print(f"  [Pass] Constant negative returns -> Sharpe: {sr_neg_const} (Expected: 0.0)")
    assert sr_neg_const == 0.0

    # 4. 1000개 중 단 1개만 미세하게 다르고 나머지는 동일 (std <= 1e-8)
    r_micro = [0.005] * 1000
    r_micro[500] = 0.005 + 1e-9
    sr_micro = calculate_annualized_sharpe_ratio(r_micro)
    print(f"  [Pass] Micro-variance returns (std <= 1e-8) -> Sharpe: {sr_micro} (Expected: 0.0)")
    assert sr_micro == 0.0

    # 5. 에쿼티 곡선이 완전히 일정한 경우의 evaluate_trading_history
    eq_flat = [10_000_000.0] * 100
    res_flat = evaluate_trading_history(equity_history=eq_flat, initial_cash=10_000_000.0)
    print(f"  [Pass] Flat equity curve eval -> Sharpe: {res_flat['sharpe_ratio']}, Return%: {res_flat['total_return_pct']}, MDD%: {res_flat['max_drawdown_pct']}")
    assert res_flat["sharpe_ratio"] == 0.0
    assert res_flat["total_return_pct"] == 0.0
    assert res_flat["max_drawdown_pct"] == 0.0

def test_market_crash_adversarial():
    print("\n=== [2] 99% 이상 초극단 폭락 데이터 검증 ===")
    
    # 1. 1스텝만에 99.99% 폭락 (70,000원 -> 1원)
    length = 20
    dates = pd.date_range("2026-01-01", periods=length, freq="B")
    crash_prices = [70000.0] + [1.0] * (length - 1)
    
    df_flash_crash = pd.DataFrame({
        "date": dates,
        "symbol": "005930",
        "open": crash_prices,
        "high": crash_prices,
        "low": crash_prices,
        "close": crash_prices,
        "volume": [100000] * length,
        "returns_1d": [0.0] + [-0.999985] + [0.0] * (length - 2),
        "log_return": [0.0] + [-11.156] + [0.0] * (length - 2),
        "volatility_20d": [0.5] * length,
        "ma_5": crash_prices,
        "ma_20": crash_prices,
        "ma_60": crash_prices,
        "dynamic_per": [0.01] * length,
        "dynamic_pbr": [0.01] * length,
        "dynamic_market_cap": [1000000.0] * length,
    })

    env = HybridTradingEnv(df=df_flash_crash, initial_cash=10_000_000, bankruptcy_threshold_ratio=0.05)
    obs, info = env.reset(seed=42)
    
    # 전량 매수 (weight=1.0)
    obs, rew, term, trunc, info = env.step((1, np.array([1.0], dtype=np.float32)))
    print(f"  [Step 1 Buy] Equity: {info['total_equity']}, Cash: {info['cash_balance']}, Holding: {info['holding_quantity']}")
    
    # 폭락 발생 스텝
    obs, rew, term, trunc, info = env.step((0, np.array([0.0], dtype=np.float32)))
    print(f"  [Step 2 Flash Crash] Equity: {info['total_equity']}, Terminated: {term}, Cash: {info['cash_balance']}")
    
    # 파산 트리거 확인 (equity < 500,000원)
    assert term is True, "Flash crash to 1 KRW must trigger bankruptcy termination (terminated=True)"
    assert info["total_equity"] < 500_000.0
    assert env.verify_accounting_invariant()

    # 2. 극단적 MDD 계산 검증 (자산이 100억 -> 1원)
    extreme_eq = [10_000_000_000.0, 100.0, 1.0, 0.01, 1e-8]
    mdd = calculate_max_drawdown_pct(extreme_eq)
    print(f"  [Pass] Extreme drawdown (10B -> 1e-8) -> MDD: {mdd:.6f}%")
    assert -100.0 <= mdd <= -99.999999

    # 3. 자산이 0.0 또는 음수 경계일 때 MDD 및 Return 계산
    zero_eq = [10_000_000.0, 0.0, 0.0]
    mdd_zero = calculate_max_drawdown_pct(zero_eq)
    ret_zero = calculate_total_return_pct(10_000_000.0, 0.0)
    print(f"  [Pass] Total bankruptcy (Equity=0.0) -> MDD: {mdd_zero}%, Return: {ret_zero}%")
    assert mdd_zero == -100.0
    assert ret_zero == -100.0

def test_inf_nan_denormal_injection():
    print("\n=== [3] NaN / Inf / Denormal 부동소수점 이상치 주입 검증 ===")
    
    # NaN/Inf 수익률
    dirty_returns = [0.01, float('nan'), -0.02, float('inf'), -float('inf'), 0.015, float('-nan'), 1e-300, -1e-300]
    sr_dirty = calculate_annualized_sharpe_ratio(dirty_returns)
    print(f"  [Pass] Dirty returns (NaN/Inf/Denormal) -> Sharpe: {sr_dirty}")
    assert isinstance(sr_dirty, float) and not math.isnan(sr_dirty) and not math.isinf(sr_dirty)

    # NaN/Inf 에쿼티 시계열
    dirty_equity = [10_000_000.0, float('nan'), 12_000_000.0, float('inf'), 9_000_000.0]
    mdd_dirty = calculate_max_drawdown_pct(dirty_equity)
    print(f"  [Pass] Dirty equity (NaN/Inf) -> MDD: {mdd_dirty}%")
    assert isinstance(mdd_dirty, float) and not math.isnan(mdd_dirty) and not math.isinf(mdd_dirty)

    # evaluate_trading_history에 모두 None / NaN 전달
    eval_dirty = evaluate_trading_history(
        equity_history=[float('nan'), float('inf'), -float('inf')],
        returns_history=[float('nan'), float('inf')],
        trades_history=[float('nan')],
    )
    print(f"  [Pass] evaluate_trading_history with all NaN/Inf -> {eval_dirty}")
    for k, v in eval_dirty.items():
        assert not (math.isnan(v) or math.isinf(v)), f"Metric {k} has invalid value {v}"

if __name__ == "__main__":
    test_zero_variance_adversarial()
    test_market_crash_adversarial()
    test_inf_nan_denormal_injection()
    print("\n>>> ALL EXTREME DATA TESTS PASSED SUCCESSFULLY! <<<")
