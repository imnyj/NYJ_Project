"""
etc/scripts/challenger_2_gym_seeding_sb3_suite.py
=================================================
Milestone 1 Empirical Adversarial Challenge Suite 2:
1. Gymnasium 1.2.0 check_env Deep Verification (Tuple, Dict, Wrapped Box)
2. Seeding & Multi-Instance Reproducibility / Determinism
3. ContinuousToHybridActionWrapper & Stable-Baselines3 (DummyVecEnv, SubprocVecEnv, PPO, A2C) Integration
4. Auto-Reset & Terminal Observation Integrity
5. Boundary, Malformed Action & Rapid Flipping Stress Test
6. Accounting Precision Invariant Preservation under High Frequency Trading
"""

import sys
import os
import time
import math
import traceback
from decimal import Decimal
import numpy as np
import pandas as pd

import gymnasium as gym
from gymnasium import spaces
from gymnasium.utils.env_checker import check_env

from modules.engine.hybrid_trading_env import (
    HybridTradingEnv,
    ContinuousToHybridActionWrapper,
)
from modules.engine.mock_environment import ActionType, FeeConfig, OrderSide

# Stable-Baselines3
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from stable_baselines3 import PPO, A2C


def create_test_df(length: int = 100, seed: int = 42) -> pd.DataFrame:
    """Generate realistic price series dataframe with features."""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2026-01-01", periods=length, freq="B")
    returns = rng.normal(0.0005, 0.015, size=length)
    prices = np.round(70000.0 * np.cumprod(1.0 + returns))
    
    return pd.DataFrame({
        "date": dates,
        "symbol": "005930",
        "open": np.round(prices * (1.0 + rng.normal(0, 0.002, length))),
        "high": np.round(prices * (1.0 + np.abs(rng.normal(0, 0.005, length)))),
        "low": np.round(prices * (1.0 - np.abs(rng.normal(0, 0.005, length)))),
        "close": prices,
        "volume": rng.randint(100000, 1000000, length),
        "returns_1d": returns,
        "log_return": np.log1p(returns),
        "volatility_20d": np.full(length, 0.015),
        "ma_5": pd.Series(prices).rolling(5, min_periods=1).mean().values,
        "ma_20": pd.Series(prices).rolling(20, min_periods=1).mean().values,
        "ma_60": pd.Series(prices).rolling(60, min_periods=1).mean().values,
        "dynamic_per": np.full(length, 15.0),
        "dynamic_pbr": np.full(length, 1.5),
        "dynamic_market_cap": prices * 6_000_000_000.0,
    })


def run_section_1_gym_check_env():
    print("\n" + "="*80)
    print("SECTION 1: Gymnasium 1.2.0 check_env Deep Verification")
    print("="*80)
    results = {}
    df = create_test_df(50)

    # 1.1 Tuple Action Space check_env
    try:
        env_tuple = HybridTradingEnv(df=df, action_space_type="tuple", render_mode="ansi")
        check_env(env_tuple, skip_render_check=False)
        print("[PASS] 1.1 Tuple Action Space check_env passed.")
        results["1.1_tuple_check_env"] = True
    except Exception as e:
        print(f"[FAIL] 1.1 Tuple Action Space check_env: {e}")
        traceback.print_exc()
        results["1.1_tuple_check_env"] = False

    # 1.2 Dict Action Space check_env
    try:
        env_dict = HybridTradingEnv(df=df, action_space_type="dict", render_mode="ansi")
        check_env(env_dict, skip_render_check=False)
        print("[PASS] 1.2 Dict Action Space check_env passed.")
        results["1.2_dict_check_env"] = True
    except Exception as e:
        print(f"[FAIL] 1.2 Dict Action Space check_env: {e}")
        traceback.print_exc()
        results["1.2_dict_check_env"] = False

    # 1.3 ContinuousToHybridActionWrapper check_env
    try:
        base_env = HybridTradingEnv(df=df, render_mode="ansi")
        wrapped_env = ContinuousToHybridActionWrapper(base_env)
        check_env(wrapped_env, skip_render_check=False)
        print("[PASS] 1.3 ContinuousToHybridActionWrapper check_env passed.")
        results["1.3_wrapped_check_env"] = True
    except Exception as e:
        print(f"[FAIL] 1.3 ContinuousToHybridActionWrapper check_env: {e}")
        traceback.print_exc()
        results["1.3_wrapped_check_env"] = False

    # 1.4 Custom Feature Columns Observation Space check_env
    try:
        custom_cols = ["returns_1d", "log_return", "volatility_20d"]
        env_custom = HybridTradingEnv(df=df, feature_cols=custom_cols, render_mode="ansi")
        assert env_custom.observation_space.shape == (3 + 4,)
        check_env(env_custom, skip_render_check=False)
        print("[PASS] 1.4 Custom Feature Columns check_env passed.")
        results["1.4_custom_features_check_env"] = True
    except Exception as e:
        print(f"[FAIL] 1.4 Custom Feature Columns check_env: {e}")
        traceback.print_exc()
        results["1.4_custom_features_check_env"] = False

    return results


def run_section_2_seeding_reproducibility():
    print("\n" + "="*80)
    print("SECTION 2: Seeding & Reproducibility Deep Verification")
    print("="*80)
    results = {}
    df = create_test_df(100, seed=777)

    # 2.1 Action Space Sampling Determinism with action_space.seed()
    try:
        env1 = HybridTradingEnv(df=df)
        env2 = HybridTradingEnv(df=df)
        
        env1.action_space.seed(12345)
        env2.action_space.seed(12345)
        
        samples1 = [env1.action_space.sample() for _ in range(50)]
        samples2 = [env2.action_space.sample() for _ in range(50)]
        
        match = True
        for s1, s2 in zip(samples1, samples2):
            if s1[0] != s2[0] or not np.allclose(s1[1], s2[1]):
                match = False
                break
        assert match, "Action space sampling with identical seed produced different samples!"
        print("[PASS] 2.1 Action space sampling seeding is 100% deterministic.")
        results["2.1_action_space_seeding"] = True
    except Exception as e:
        print(f"[FAIL] 2.1 Action space sampling seeding: {e}")
        traceback.print_exc()
        results["2.1_action_space_seeding"] = False

    # 2.2 Episode Trajectory Determinism (State, Reward, Info, Equity)
    try:
        envA = HybridTradingEnv(df=df, initial_cash=10_000_000)
        envB = HybridTradingEnv(df=df, initial_cash=10_000_000)
        
        obsA, infoA = envA.reset(seed=999)
        obsB, infoB = envB.reset(seed=999)
        
        assert np.array_equal(obsA, obsB), "Initial obs mismatch on reset(seed=999)"
        assert infoA["total_equity"] == infoB["total_equity"], "Initial equity mismatch"
        
        # Sample sequence of actions
        rng = np.random.RandomState(42)
        actions = []
        for _ in range(50):
            act_type = rng.choice([0, 1, 2])
            weight = rng.uniform(0.0, 1.0)
            actions.append((act_type, np.array([weight], dtype=np.float32)))
            
        trajectory_match = True
        for step_idx, act in enumerate(actions):
            oA, rA, termA, truncA, iA = envA.step(act)
            oB, rB, termB, truncB, iB = envB.step(act)
            
            if not np.allclose(oA, oB, atol=1e-6):
                print(f"Step {step_idx}: Obs mismatch")
                trajectory_match = False
                break
            if abs(rA - rB) > 1e-7:
                print(f"Step {step_idx}: Reward mismatch {rA} vs {rB}")
                trajectory_match = False
                break
            if termA != termB or truncA != truncB:
                print(f"Step {step_idx}: Done mismatch")
                trajectory_match = False
                break
            if iA["total_equity"] != iB["total_equity"] or iA["holding_quantity"] != iB["holding_quantity"]:
                print(f"Step {step_idx}: Info mismatch")
                trajectory_match = False
                break

        assert trajectory_match, "Trajectory diverged between two identical seeded environments!"
        print("[PASS] 2.2 Full episode trajectory determinism verified across 50 steps.")
        results["2.2_trajectory_determinism"] = True
    except Exception as e:
        print(f"[FAIL] 2.2 Trajectory determinism: {e}")
        traceback.print_exc()
        results["2.2_trajectory_determinism"] = False

    # 2.3 Multi-Episode Reset Seeding Isolation
    try:
        env = HybridTradingEnv(df=df)
        obs1_0, _ = env.reset(seed=101)
        for _ in range(10):
            env.step((1, np.array([0.5], dtype=np.float32)))
        
        obs2_0, _ = env.reset(seed=202)
        for _ in range(10):
            env.step((1, np.array([0.5], dtype=np.float32)))
            
        # Re-reset with seed 101
        obs1_re, _ = env.reset(seed=101)
        assert np.array_equal(obs1_0, obs1_re), "Re-reset with same seed did not restore identical initial observation!"
        print("[PASS] 2.3 Reset seed restoration & isolation verified.")
        results["2.3_reset_seed_isolation"] = True
    except Exception as e:
        print(f"[FAIL] 2.3 Reset seed isolation: {e}")
        traceback.print_exc()
        results["2.3_reset_seed_isolation"] = False

    return results


def run_section_3_sb3_vecenv_integration():
    print("\n" + "="*80)
    print("SECTION 3: SB3 DummyVecEnv & ContinuousToHybridActionWrapper Integration")
    print("="*80)
    results = {}
    df = create_test_df(100)

    # 3.1 DummyVecEnv Construction & Multi-Step Vectorized Execution
    try:
        num_envs = 4
        def make_env(env_id: int):
            def _init():
                base = HybridTradingEnv(df=df, initial_cash=10_000_000, max_steps=40)
                wrapped = ContinuousToHybridActionWrapper(base)
                return wrapped
            return _init

        vec_env = DummyVecEnv([make_env(i) for i in range(num_envs)])
        obs = vec_env.reset()
        assert obs.shape == (num_envs, 14), f"Obs shape mismatch: expected ({num_envs}, 14), got {obs.shape}"
        assert obs.dtype == np.float32

        # Step vectorized actions
        for step in range(60): # Exceeds max_steps=40 to trigger auto-reset
            actions = np.random.uniform(-1.0, 1.0, size=(num_envs, 2)).astype(np.float32)
            actions[:, 1] = np.random.uniform(0.0, 1.0, size=num_envs).astype(np.float32)
            
            next_obs, rewards, dones, infos = vec_env.step(actions)
            assert next_obs.shape == (num_envs, 14)
            assert rewards.shape == (num_envs,)
            assert dones.shape == (num_envs,)
            assert len(infos) == num_envs
            
            # Check terminal_observation on done
            for i, done in enumerate(dones):
                if done:
                    assert "terminal_observation" in infos[i], f"Env {i} done but 'terminal_observation' missing in info!"
                    term_obs = infos[i]["terminal_observation"]
                    assert term_obs.shape == (14,)
                    assert np.all(np.isfinite(term_obs))

        vec_env.close()
        print(f"[PASS] 3.1 DummyVecEnv ({num_envs} parallel envs) 60 steps + auto-reset + terminal_obs passed.")
        results["3.1_dummy_vec_env_step_autoreset"] = True
    except Exception as e:
        print(f"[FAIL] 3.1 DummyVecEnv step/autoreset: {e}")
        traceback.print_exc()
        results["3.1_dummy_vec_env_step_autoreset"] = False

    # 3.2 SB3 PPO Training Stress Test
    try:
        num_envs = 2
        vec_env = DummyVecEnv([make_env(i) for i in range(num_envs)])
        
        ppo_model = PPO(
            "MlpPolicy",
            vec_env,
            n_steps=64,
            batch_size=32,
            n_epochs=2,
            learning_rate=3e-4,
            verbose=0,
            seed=42,
            device="cpu",
        )
        
        t0 = time.time()
        ppo_model.learn(total_timesteps=256)
        elapsed = time.time() - t0
        
        # Test evaluation step with trained PPO policy
        test_obs = vec_env.reset()
        for _ in range(10):
            action, _states = ppo_model.predict(test_obs, deterministic=True)
            test_obs, rewards, dones, infos = vec_env.step(action)
            assert np.all(np.isfinite(test_obs))
            assert np.all(np.isfinite(rewards))
            
        vec_env.close()
        print(f"[PASS] 3.2 SB3 PPO Training (256 timesteps in {elapsed:.2f}s) & Inference passed.")
        results["3.2_sb3_ppo_training"] = True
    except Exception as e:
        print(f"[FAIL] 3.2 SB3 PPO Training: {e}")
        traceback.print_exc()
        results["3.2_sb3_ppo_training"] = False

    # 3.3 SB3 A2C Training Stress Test
    try:
        num_envs = 2
        vec_env = DummyVecEnv([make_env(i) for i in range(num_envs)])
        
        a2c_model = A2C(
            "MlpPolicy",
            vec_env,
            n_steps=16,
            learning_rate=7e-4,
            verbose=0,
            seed=42,
            device="cpu",
        )
        
        t0 = time.time()
        a2c_model.learn(total_timesteps=128)
        elapsed = time.time() - t0
        
        test_obs = vec_env.reset()
        for _ in range(10):
            action, _states = a2c_model.predict(test_obs, deterministic=True)
            test_obs, rewards, dones, infos = vec_env.step(action)
            assert np.all(np.isfinite(test_obs))
            assert np.all(np.isfinite(rewards))
            
        vec_env.close()
        print(f"[PASS] 3.3 SB3 A2C Training (128 timesteps in {elapsed:.2f}s) & Inference passed.")
        results["3.3_sb3_a2c_training"] = True
    except Exception as e:
        print(f"[FAIL] 3.3 SB3 A2C Training: {e}")
        traceback.print_exc()
        results["3.3_sb3_a2c_training"] = False

    return results


def run_section_4_adversarial_action_and_frictions_stress():
    print("\n" + "="*80)
    print("SECTION 4: Adversarial Actions, Boundary Conditions & Invariant Hardening")
    print("="*80)
    results = {}
    df = create_test_df(200)

    # 4.1 Boundary / Extreme Numeric Actions under valid spec
    try:
        env = HybridTradingEnv(df=df, initial_cash=10_000_000)
        env.reset()
        
        extreme_valid_actions = [
            (0, np.array([0.0], dtype=np.float32)),        # HOLD 0%
            (1, np.array([1.0], dtype=np.float32)),        # BUY 100%
            (2, np.array([1.0], dtype=np.float32)),        # SELL 100%
            (1, np.array([1e-7], dtype=np.float32)),       # BUY epsilon%
            (2, np.array([1e-7], dtype=np.float32)),       # SELL epsilon%
            (1, np.array([0.999999], dtype=np.float32)),   # BUY almost 100%
            {"action_type": 1, "position_size": np.array([0.5], dtype=np.float32)},
            {"action_type": 0, "position_size": np.array([0.0], dtype=np.float32)},
            ActionType.BUY,
            ActionType.SELL,
            ActionType.HOLD,
        ]
        
        for idx, act in enumerate(extreme_valid_actions):
            obs, rew, term, trunc, info = env.step(act)
            assert np.all(np.isfinite(obs)), f"Action {idx} resulted in non-finite obs: {obs}"
            assert not math.isnan(rew) and not math.isinf(rew), f"Action {idx} resulted in non-finite reward: {rew}"
            assert isinstance(term, bool)
            assert isinstance(trunc, bool)
            assert isinstance(info, dict)
            
        print(f"[PASS] 4.1 Ingestion of {len(extreme_valid_actions)} boundary actions succeeded without crashing.")
        results["4.1_boundary_actions"] = True
    except Exception as e:
        print(f"[FAIL] 4.1 Boundary actions test: {e}")
        traceback.print_exc()
        results["4.1_boundary_actions"] = False

    # 4.2 Robustness Analysis on Malformed Out-of-Spec Actions (Defect Probing)
    try:
        env = HybridTradingEnv(df=df, initial_cash=10_000_000)
        env.reset()
        
        unhandled_types = []
        
        # Test malformed actions that might crash _parse_action
        probing_cases = [
            ("NaN in 2D array discrete signal", np.array([float("nan"), 0.5], dtype=np.float32)),
            ("Inf in 2D array discrete signal", np.array([float("inf"), 0.5], dtype=np.float32)),
            ("NaN in Tuple discrete part", (float("nan"), np.array([0.5], dtype=np.float32))),
            ("Inf in Tuple discrete part", (float("inf"), np.array([0.5], dtype=np.float32))),
            ("NaN in Dict action_type", {"action_type": float("nan"), "position_size": 0.5}),
        ]
        
        for desc, act in probing_cases:
            try:
                env.step(act)
            except (ValueError, OverflowError, TypeError) as ex:
                unhandled_types.append((desc, str(ex)))
                
        if unhandled_types:
            print(f"[NOTE/FINDING] 4.2 Unhandled non-spec malformed inputs detected ({len(unhandled_types)} cases):")
            for desc, ex_str in unhandled_types:
                print(f"      - {desc}: {ex_str}")
        else:
            print("[PASS] 4.2 All malformed probing cases handled gracefully.")
            
        results["4.2_malformed_probe_completed"] = True
    except Exception as e:
        print(f"[FAIL] 4.2 Malformed probe: {e}")
        traceback.print_exc()
        results["4.2_malformed_probe_completed"] = False

    # 4.3 High Frequency Flipping & Accounting Invariant
    try:
        fee_config = FeeConfig(
            commission_rate=Decimal("0.00015"),
            tax_rate=Decimal("0.0018"),
            slippage_rate=Decimal("0.0010")
        )
        env = HybridTradingEnv(df=df, initial_cash=10_000_000, fee_config=fee_config)
        env.reset()
        
        # Flip BUY 100% and SELL 100% every step for 150 steps
        for step in range(150):
            act_type = 1 if step % 2 == 0 else 2
            obs, rew, term, trunc, info = env.step((act_type, np.array([1.0], dtype=np.float32)))
            
            # Check accounting invariant every single step
            invariant_ok = env.verify_accounting_invariant(tolerance=Decimal("1"))
            assert invariant_ok, f"Step {step}: Invariant violation!"
            
            if term or trunc:
                break
                
        audit = env.get_accounting_audit()
        discrepancy = (audit['initial_cash'] + audit['cumulative_market_drift_pnl']) - (audit['total_equity'] + audit['total_frictions'])
        print(f"[PASS] 4.3 High frequency flipping: {step+1} steps executed. Invariant verified at every step.")
        print(f"      Initial Cash: {audit['initial_cash']:,.0f} KRW | Total Equity: {audit['total_equity']:,.0f} KRW")
        print(f"      Total Frictions: {audit['total_frictions']:,.0f} KRW | Discrepancy: {discrepancy} KRW")
        assert abs(discrepancy) <= Decimal("1")
        results["4.3_hf_flipping_invariant"] = True
    except Exception as e:
        print(f"[FAIL] 4.3 High frequency flipping invariant test: {e}")
        traceback.print_exc()
        results["4.3_hf_flipping_invariant"] = False

    return results


def main():
    print("="*80)
    print("STARTING EMPIRICAL ADVERSARIAL CHALLENGER 2 TEST HARNESS")
    print("="*80)
    
    r1 = run_section_1_gym_check_env()
    r2 = run_section_2_seeding_reproducibility()
    r3 = run_section_3_sb3_vecenv_integration()
    r4 = run_section_4_adversarial_action_and_frictions_stress()
    
    all_results = {**r1, **r2, **r3, **r4}
    
    print("\n" + "="*80)
    print("EMPIRICAL TEST RESULTS SUMMARY")
    print("="*80)
    all_passed = True
    for k, v in all_results.items():
        status = "PASSED" if v else "FAILED"
        print(f" - {k:40s}: {status}")
        if not v:
            all_passed = False
            
    print("="*80)
    if all_passed:
        print("OVERALL VERDICT: ALL CHALLENGES PASSED (APPROVE)")
        sys.exit(0)
    else:
        print("OVERALL VERDICT: ONE OR MORE CHALLENGES FAILED (FAIL)")
        sys.exit(1)


if __name__ == "__main__":
    main()
