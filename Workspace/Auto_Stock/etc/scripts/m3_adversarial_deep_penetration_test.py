# -*- coding: utf-8 -*-
"""
etc/scripts/m3_adversarial_deep_penetration_test.py
Challenger 2 Empirical Penetration & Adversarial Stress Test Harness for Milestone 3.
"""

import math
import os
import sys
import threading
import time
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

sys.path.insert(0, os.path.abspath("."))

import gymnasium as gym
from gymnasium import spaces
from gymnasium.utils.env_checker import check_env
import numpy as np
import pandas as pd
import torch
from stable_baselines3 import A2C, PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from core.kiwoom_api import PriceQuote
from modules.engine.hybrid_trading_env import (
    ContinuousToHybridActionWrapper,
    HybridTradingEnv,
)
from modules.engine.live_learning_simulator import (
    LiveLearningSimulator,
    get_live_simulator,
    reset_global_simulator,
)
from modules.engine.mock_environment import ActionType, FeeConfig
from modules.hpo import (
    CSV_COLUMNS,
    create_hpo_study,
    evaluate_trading_history,
    export_trial_to_csv,
    load_hpo_results,
    objective,
    run_hpo_optimization,
)
from modules.models.feature_extractor import TabularMLPFeatureExtractor
from modules.models.hybrid_policy import HybridActorCritic, HybridPPO

def generate_adversarial_df(length=100):
    rng = np.random.RandomState(42)
    dates = pd.date_range("2026-01-01", periods=length, freq="B")
    returns = rng.normal(0.0005, 0.02, size=length)
    prices = np.round(70000.0 * np.cumprod(1.0 + returns))
    return pd.DataFrame({
        "date": dates,
        "symbol": "005930",
        "open": np.round(prices * 0.995),
        "high": np.round(prices * 1.015),
        "low": np.round(prices * 0.985),
        "close": prices,
        "volume": rng.randint(100000, 1000000, length),
        "returns_1d": returns,
        "log_return": np.log1p(returns),
        "volatility_20d": np.full(length, 0.02),
        "ma_5": pd.Series(prices).rolling(5, min_periods=1).mean().values,
        "ma_20": pd.Series(prices).rolling(20, min_periods=1).mean().values,
        "ma_60": pd.Series(prices).rolling(60, min_periods=1).mean().values,
        "dynamic_per": np.full(length, 12.0),
        "dynamic_pbr": np.full(length, 1.3),
        "dynamic_market_cap": prices * 6_000_000_000.0,
    })

def test_1_gymnasium_compatibility():
    print("[Test 1] Gymnasium 1.2.0 check_env & 5-tuple verification...")
    df = generate_adversarial_df(50)
    
    # 1.1 Tuple Action Space
    env_tuple = HybridTradingEnv(df=df, action_space_type="tuple", render_mode="ansi")
    check_env(env_tuple, skip_render_check=False)
    
    obs, info = env_tuple.reset(seed=123)
    assert isinstance(obs, np.ndarray) and obs.shape == (14,)
    assert isinstance(info, dict)
    
    res = env_tuple.step((1, np.array([0.5], dtype=np.float32)))
    assert len(res) == 5, f"Expected 5-tuple, got len={len(res)}"
    obs, rew, term, trunc, info = res
    assert isinstance(obs, np.ndarray)
    assert isinstance(rew, float)
    assert isinstance(term, bool)
    assert isinstance(trunc, bool)
    assert isinstance(info, dict)
    
    # 1.2 Dict Action Space
    env_dict = HybridTradingEnv(df=df, action_space_type="dict", render_mode="ansi")
    check_env(env_dict, skip_render_check=False)
    
    # 1.3 Continuous Wrapper
    wrapped = ContinuousToHybridActionWrapper(HybridTradingEnv(df=df, render_mode="ansi"))
    check_env(wrapped, skip_render_check=False)
    res_w = wrapped.step(np.array([0.5, 0.5], dtype=np.float32))
    assert len(res_w) == 5
    print("  -> PASSED: Gymnasium 1.2.0 check_env & 5-tuple unpacking verified.")

def test_2_live_learning_simulator_concurrency_and_contract():
    print("[Test 2] LiveLearningSimulator concurrency & contract stress...")
    reset_global_simulator()
    
    # 2.1 Multi-threaded Singleton initialization stress (50 threads)
    instances = []
    def _inst_worker():
        inst = get_live_simulator(initial_cash=5_000_000)
        instances.append(inst)
        
    threads = [threading.Thread(target=_inst_worker) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    assert len(instances) == 50
    first = instances[0]
    for inst in instances:
        assert inst is first, "Singleton violation under multi-threading!"
    assert first.initial_cash == Decimal("5000000")
    print("  -> PASSED: Singleton thread-safety with 50 concurrent threads.")
    
    # 2.2 Mock Kiwoom live stepping & 5-tuple contract
    with patch("core.kiwoom_api.KiwoomClient.get_current_price") as mock_price:
        mock_price.return_value = PriceQuote(
            symbol="005930",
            current_price=Decimal("75000"),
            price_change=Decimal("0"),
            change_rate=Decimal("0"),
            open_price=Decimal("75000"),
            high_price=Decimal("75000"),
            low_price=Decimal("75000"),
            volume=5000,
            trade_amount=Decimal("0"),
            timestamp=datetime.now(),
        )
        sim = LiveLearningSimulator(initial_cash=1_000_000)
        
        # BUY 13 shares at 75,000 (total ~975,000 + friction) -> remaining cash ~24,800
        s, r, term, trunc, info = sim.step("005930", ActionType.BUY, quantity=13)
        assert len((s, r, term, trunc, info)) == 5
        assert isinstance(s, dict)
        assert isinstance(r, float)
        assert isinstance(term, bool)
        assert isinstance(trunc, bool)
        assert isinstance(info, dict)
        assert info["trade"].is_success is True
        assert s["holding_quantity"] == 13
        
        # Log Return verification: r == log(E_t / E_{t-1})
        prev_eq = 1_000_000.0
        curr_eq = s["total_equity"]
        expected_rew = float(np.log(curr_eq / prev_eq))
        assert abs(r - expected_rew) < 1e-6, f"Reward mismatch: {r} vs {expected_rew}"
        
        # Bankruptcy trigger: drop price to 100 won (equity becomes 13 * 100 + 24,800 = 26,100 < 50,000)
        mock_price.return_value = PriceQuote(
            symbol="005930",
            current_price=Decimal("100"),
            price_change=Decimal("-74900"),
            change_rate=Decimal("-0.998"),
            open_price=Decimal("100"),
            high_price=Decimal("100"),
            low_price=Decimal("100"),
            volume=5000,
            trade_amount=Decimal("0"),
            timestamp=datetime.now(),
        )
        s, r, term, trunc, info = sim.step("005930", ActionType.HOLD)
        assert s["total_equity"] < 50_000.0
        assert term is True, "Bankruptcy (<5% equity) did not trigger terminated=True"
        
    reset_global_simulator()
    print("  -> PASSED: LiveLearningSimulator 5-tuple contract, log-return, and bankruptcy verified.")

def test_3_hpo_reward_penalty_defense():
    print("[Test 3] HPO Reward Hacking Defense (BUG-RL05)...")
    
    # 3.1 Zero trades (total_trades == 0) -> objective_value == -1.0
    with patch("modules.hpo.optuna_pipeline.evaluate_trading_history") as mock_eval:
        mock_eval.return_value = {
            "total_equity": 10_000_000.0,
            "total_return_pct": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "total_trades": 0,
            "win_rate": 0.0,
        }
        study = create_hpo_study(seed=42)
        def _obj_inactive(trial):
            return objective(trial=trial, symbol="005930", output_csv="/tmp/test_hpo_pen.csv", n_timesteps=16, fast_mode=True)
        study.optimize(_obj_inactive, n_trials=1)
        assert study.trials[0].value == -1.0, f"Expected -1.0 penalty, got {study.trials[0].value}"

    # 3.2 Active trading with minor negative Sharpe (-0.2) -> objective_value == -0.2 > -1.0
    with patch("modules.hpo.optuna_pipeline.evaluate_trading_history") as mock_eval:
        mock_eval.return_value = {
            "total_equity": 9_900_000.0,
            "total_return_pct": -1.0,
            "sharpe_ratio": -0.2,
            "max_drawdown_pct": -1.5,
            "total_trades": 5,
            "win_rate": 40.0,
        }
        study = create_hpo_study(seed=42)
        def _obj_active(trial):
            return objective(trial=trial, symbol="005930", output_csv="/tmp/test_hpo_pen.csv", n_timesteps=16, fast_mode=True)
        study.optimize(_obj_active, n_trials=1)
        expected_val = -0.2 + 0.01 * (-1.0) # -0.21
        assert abs(study.trials[0].value - expected_val) < 1e-4
        assert study.trials[0].value > -1.0, "Active trading must not be penalized below total inertia (-1.0)"

    print("  -> PASSED: HPO BUG-RL05 penalty defense verified.")

def test_4_sb3_vectorized_multi_env_stress():
    print("[Test 4] SB3 Vectorized Multi-Env & Auto-Reset Stress...")
    df = generate_adversarial_df(100)
    num_envs = 4
    
    def make_env():
        def _init():
            base = HybridTradingEnv(df=df, initial_cash=10_000_000, max_steps=25)
            return ContinuousToHybridActionWrapper(base)
        return _init
        
    vec_env = DummyVecEnv([make_env() for _ in range(num_envs)])
    
    # Train PPO for 128 steps across 4 vectorized environments
    model = PPO("MlpPolicy", vec_env, n_steps=32, batch_size=16, n_epochs=2, learning_rate=3e-4, verbose=0, seed=42, device="cpu")
    model.learn(total_timesteps=128)
    
    # Rollout with deterministic prediction
    obs = vec_env.reset()
    for _ in range(60): # triggers auto-reset (max_steps=25)
        actions, _ = model.predict(obs, deterministic=True)
        obs, rewards, dones, infos = vec_env.step(actions)
        assert np.all(np.isfinite(obs))
        assert np.all(np.isfinite(rewards))
        for i, d in enumerate(dones):
            if d:
                assert "terminal_observation" in infos[i]
                assert np.all(np.isfinite(infos[i]["terminal_observation"]))
                
    vec_env.close()
    print("  -> PASSED: SB3 Multi-Env PPO training and auto-reset terminal_observation verified.")

def test_5_concurrent_csv_exporter_stress():
    print("[Test 5] Concurrent CSV Exporter Stress (30 threads)...")
    csv_path = "/tmp/concurrent_stress_test.csv"
    if os.path.exists(csv_path):
        os.remove(csv_path)
        
    n_threads = 30
    def _writer(idx):
        rec = {
            "trial_id": idx,
            "state": "COMPLETE",
            "objective_value": float(idx) * 0.1,
            "total_equity": 10_000_000.0 + idx * 50_000,
            "total_return_pct": float(idx) * 0.5,
            "sharpe_ratio": float(idx) * 0.1,
            "max_drawdown_pct": -0.5,
            "total_trades": idx + 1,
            "win_rate": 50.0,
            "param_sl_lr": 0.001,
            "param_sl_hidden_dim": 64,
            "param_sl_batch_size": 32,
            "param_rl_lr": 0.0003,
            "param_rl_gamma": 0.99,
            "param_rl_clip_range": 0.2,
            "param_rl_ent_coef": 0.01,
            "param_rl_hidden_dim": 128,
            "duration_seconds": 0.05,
        }
        export_trial_to_csv(rec, csv_path=csv_path)
        
    threads = [threading.Thread(target=_writer, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    df_res = load_hpo_results(csv_path)
    assert len(df_res) == n_threads, f"Expected {n_threads} rows, got {len(df_res)}"
    assert set(df_res["trial_id"].tolist()) == set(range(n_threads))
    assert list(df_res.columns) == CSV_COLUMNS
    if os.path.exists(csv_path):
        os.remove(csv_path)
    print("  -> PASSED: Concurrent CSV atomic exporter verified without data race.")

if __name__ == "__main__":
    print("==================================================================")
    print("=== STARTING CHALLENGER 2 DEEP ADVERSARIAL PENETRATION SUITE ===")
    print("==================================================================")
    t0 = time.time()
    test_1_gymnasium_compatibility()
    test_2_live_learning_simulator_concurrency_and_contract()
    test_3_hpo_reward_penalty_defense()
    test_4_sb3_vectorized_multi_env_stress()
    test_5_concurrent_csv_exporter_stress()
    print(f"=== ALL ADVERSARIAL TESTS PASSED IN {time.time() - t0:.2f}s ===")
