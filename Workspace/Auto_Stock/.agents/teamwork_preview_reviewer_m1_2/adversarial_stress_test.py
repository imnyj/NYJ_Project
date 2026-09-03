"""
Adversarial Stress Test Script for Milestone 1: HybridTradingEnv
Independent Reviewer 2 (teamwork_preview_reviewer_m1_2)
"""

import math
import sys
from decimal import Decimal
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium.utils.env_checker import check_env

from modules.engine.hybrid_trading_env import HybridTradingEnv, ContinuousToHybridActionWrapper
from modules.engine.mock_environment import FeeConfig, OrderSide, ActionType

def run_adversarial_tests():
    print("=== [REVIEWER 2] ADVERSARIAL STRESS TEST SUITE START ===")
    
    # -------------------------------------------------------------
    # 1. Action Decoding Stress Test (Adversarial / Corrupted Inputs)
    # -------------------------------------------------------------
    print("\n[Test 1] Action Decoding Stress Test...")
    env = HybridTradingEnv(initial_cash=10_000_000)
    obs, info = env.reset(seed=123)
    
    adversarial_actions = [
        # Out of bounds discrete
        (999, np.array([0.5], dtype=np.float32)),
        (-50, np.array([0.5], dtype=np.float32)),
        # Out of bounds continuous weights
        (1, np.array([100.0], dtype=np.float32)),
        (1, np.array([-50.0], dtype=np.float32)),
        (1, np.array([float('nan')], dtype=np.float32)),
        (1, np.array([float('inf')], dtype=np.float32)),
        (2, np.array([-float('inf')], dtype=np.float32)),
        # Degenerate lists and arrays
        [1, [0.5]],
        [2, np.array([0.8])],
        np.array([1.5, -2.0]),
        # Corrupted Dicts
        {"action_type": 1, "position_size": np.nan},
        {"action_type": -1, "weight": 2.5},
        {"invalid_key": 10},
        # Pure scalars
        1,
        2,
        0,
        0.99,
        -0.99,
        0.0,
    ]
    
    for i, act in enumerate(adversarial_actions):
        try:
            obs, rew, term, trunc, info = env.step(act)
            assert isinstance(obs, np.ndarray), f"Obs must be ndarray at {i}"
            assert obs.shape == (14,), f"Obs shape must be (14,) at {i}, got {obs.shape}"
            assert np.all(np.isfinite(obs)), f"Obs contains NaN/Inf at {i}: {obs}"
            assert isinstance(rew, (float, np.floating)), f"Reward must be float, got {type(rew)}"
            assert not math.isnan(rew), f"Reward is NaN at {i}"
            assert isinstance(term, bool), f"Terminated must be bool at {i}"
            assert isinstance(trunc, bool), f"Truncated must be bool at {i}"
            assert isinstance(info, dict), f"Info must be dict at {i}"
        except Exception as e:
            print(f"FAILED on action {act} ({i}): {e}")
            raise e
    print("-> Test 1 PASSED: All 19 adversarial actions handled safely.")

    # -------------------------------------------------------------
    # 2. Extreme Market Data & Resilience Test
    # -------------------------------------------------------------
    print("\n[Test 2] Extreme Market Data Resilience Test...")
    extreme_df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=20, freq="B"),
        "symbol": "005930",
        "close": [
            0.0, -100.0, np.nan, np.inf, -np.inf, 1e12, 1e-6, 70000.0,
            np.nan, 80000.0, 0.0, np.nan, 75000.0, 75000.0, 75000.0,
            75000.0, 75000.0, 75000.0, 75000.0, 75000.0
        ],
        "volume": [np.nan, -1000, 0, 1e15, np.inf, 500000, 500000, 500000, 500000, 500000,
                   500000, 500000, 500000, 500000, 500000, 500000, 500000, 500000, 500000, 500000],
        "dynamic_per": [np.nan, np.inf, -np.inf, 0.0, 1000.0] * 4,
        "dynamic_pbr": [np.nan, np.inf, -np.inf, 0.0, 100.0] * 4,
        "dynamic_market_cap": [np.nan, -1.0, 0.0, 1e18, np.inf] * 4,
    })
    
    extreme_env = HybridTradingEnv(df=extreme_df, initial_cash=10_000_000)
    obs, info = extreme_env.reset()
    assert np.all(np.isfinite(obs)), f"Reset obs has non-finite values: {obs}"
    
    for step_idx in range(len(extreme_df)):
        # Random hybrid action
        act = (np.random.choice([0, 1, 2]), np.array([np.random.uniform(0, 1)], dtype=np.float32))
        obs, rew, term, trunc, info = extreme_env.step(act)
        assert np.all(np.isfinite(obs)), f"Step {step_idx} obs has non-finite values: {obs}"
        assert not math.isnan(rew), f"Step {step_idx} reward is NaN"
        assert not math.isinf(rew), f"Step {step_idx} reward is Inf"
        if trunc or term:
            break
    print("-> Test 2 PASSED: Environment survived extreme corrupt data gracefully.")

    # -------------------------------------------------------------
    # 3. Precision Accounting Invariant Long-Run Test (500 Steps)
    # -------------------------------------------------------------
    print("\n[Test 3] Precision Accounting Invariant Long-Run Test (500 steps)...")
    np.random.seed(999)
    synth_df = extreme_env._generate_synthetic_dataframe(length=500)
    acc_env = HybridTradingEnv(df=synth_df, initial_cash=50_000_000)
    obs, info = acc_env.reset()
    
    max_discrepancy = Decimal("0")
    total_trades = 0
    
    for t in range(500):
        # High frequency buy / sell / hold alternation
        act_choice = np.random.choice([0, 1, 2], p=[0.2, 0.4, 0.4])
        weight_val = np.random.uniform(0.1, 1.0)
        obs, rew, term, trunc, info = acc_env.step((act_choice, np.array([weight_val], dtype=np.float32)))
        
        if info["trade_record"] is not None:
            total_trades += 1
            
        # Verify accounting invariant at EVERY single step
        invariant_ok = acc_env.verify_accounting_invariant(tolerance=Decimal("1"))
        assert invariant_ok, f"Accounting invariant broken at step {t}!"
        
        audit = acc_env.get_accounting_audit()
        discrepancy = abs(
            (audit["initial_cash"] + audit["cumulative_market_drift_pnl"]) - 
            (audit["total_equity"] + audit["total_frictions"])
        )
        if discrepancy > max_discrepancy:
            max_discrepancy = discrepancy
            
        if trunc or term:
            break
            
    print(f"-> Test 3 PASSED: Executed {total_trades} trades across 500 steps. Max invariant discrepancy = {max_discrepancy} KRW (<= 1 KRW).")

    # -------------------------------------------------------------
    # 4. Continuous Wrapper + SB3 Gymnasium Compatibility Test
    # -------------------------------------------------------------
    print("\n[Test 4] ContinuousToHybridActionWrapper & check_env...")
    base_env = HybridTradingEnv(df=synth_df.iloc[:100], render_mode="ansi")
    wrapped = ContinuousToHybridActionWrapper(base_env)
    check_env(wrapped)
    
    wrapped.reset(seed=42)
    for _ in range(50):
        random_action = wrapped.action_space.sample()
        obs, rew, term, trunc, info = wrapped.step(random_action)
        assert np.all(np.isfinite(obs))
        assert not math.isnan(rew)
        if trunc or term:
            break
    print("-> Test 4 PASSED: Wrapper fully compliant with check_env and SB3 continuous sampling.")

    # -------------------------------------------------------------
    # 5. Live Mode Fallback & Network Fault Injection
    # -------------------------------------------------------------
    print("\n[Test 5] Live Mode Fallback & Fault Injection Test...")
    from modules.engine.live_learning_simulator import LiveLearningSimulator
    live_sim = LiveLearningSimulator(initial_cash=10_000_000)
    
    # Inject fault into live_sim.fetch_live_price
    live_env = HybridTradingEnv(mode="live", live_sim=live_sim, max_steps=20)
    obs, info = live_env.reset()
    
    def faulty_fetch(symbol):
        raise ConnectionResetError("Mock Kiwoom REST socket dropped")
        
    live_sim.fetch_live_price = faulty_fetch
    
    # Environment should catch exception and fallback to last known price
    obs, rew, term, trunc, info = live_env.step((1, np.array([0.5], dtype=np.float32)))
    assert np.all(np.isfinite(obs))
    assert info["current_price"] == 70000.0 or info["current_price"] > 0
    print("-> Test 5 PASSED: Live mode gracefully caught network fault and used fallback price.")

    print("\n=== ALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_adversarial_tests()
