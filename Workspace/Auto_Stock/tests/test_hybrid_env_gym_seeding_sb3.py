"""
tests/test_hybrid_env_gym_seeding_sb3.py
========================================
Milestone 1 적대적 챌린저 2 (Challenger 2) 전용 Gymnasium 규격, Seeding 재현성, SB3 연동 검증 스위트.

검증 항목:
1. Gymnasium 1.2.0 check_env 심층 검증 (Tuple, Dict, Continuous Wrapper, Custom Features, Render Modes)
2. Seeding 완벽 재현성 (Action space sampling seed, Multi-instance trajectory determinism, Reset seed isolation)
3. ContinuousToHybridActionWrapper & Stable-Baselines3 (DummyVecEnv, PPO, A2C) 연동 및 Auto-Reset / terminal_observation 무결성
4. 고빈도 매매 및 경계 조건에서의 1원 단위 회계 무결성 불변식 검증
"""

import math
from decimal import Decimal
import numpy as np
import pandas as pd
import pytest

import gymnasium as gym
from gymnasium import spaces
from gymnasium.utils.env_checker import check_env

from modules.engine.hybrid_trading_env import (
    HybridTradingEnv,
    ContinuousToHybridActionWrapper,
)
from modules.engine.mock_environment import ActionType, FeeConfig, OrderSide

from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3 import PPO, A2C


@pytest.fixture
def sample_dataset() -> pd.DataFrame:
    """재현성 있는 100일 시계열 데이터셋"""
    rng = np.random.RandomState(42)
    length = 100
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


# ==============================================================================
# 1. Gymnasium 1.2.0 check_env Deep Verification
# ==============================================================================

class TestGymnasiumCheckEnvDeep:
    """Gymnasium 1.2.0 표준 규격 및 check_env 검증"""

    def test_tuple_action_space_check_env(self, sample_dataset):
        """Tuple Action Space (Discrete(3) + Box(0~1)) check_env 검증"""
        env = HybridTradingEnv(df=sample_dataset, action_space_type="tuple", render_mode="ansi")
        assert isinstance(env.action_space, spaces.Tuple)
        assert len(env.action_space.spaces) == 2
        assert isinstance(env.action_space.spaces[0], spaces.Discrete)
        assert isinstance(env.action_space.spaces[1], spaces.Box)
        check_env(env, skip_render_check=False)

    def test_dict_action_space_check_env(self, sample_dataset):
        """Dict Action Space ('action_type' + 'position_size') check_env 검증"""
        env = HybridTradingEnv(df=sample_dataset, action_space_type="dict", render_mode="ansi")
        assert isinstance(env.action_space, spaces.Dict)
        assert "action_type" in env.action_space.spaces
        assert "position_size" in env.action_space.spaces
        check_env(env, skip_render_check=False)

    def test_continuous_action_wrapper_check_env(self, sample_dataset):
        """ContinuousToHybridActionWrapper (Box(-1~1, 0~1)) check_env 검증"""
        base_env = HybridTradingEnv(df=sample_dataset, render_mode="ansi")
        wrapped = ContinuousToHybridActionWrapper(base_env)
        assert isinstance(wrapped.action_space, spaces.Box)
        assert wrapped.action_space.shape == (2,)
        check_env(wrapped, skip_render_check=False)

    def test_custom_features_observation_space_check_env(self, sample_dataset):
        """사용자 정의 피처 컬럼 지정 시 관측 공간 형상 및 check_env 검증"""
        custom_cols = ["returns_1d", "volatility_20d"]
        env = HybridTradingEnv(df=sample_dataset, feature_cols=custom_cols, render_mode="ansi")
        assert env.observation_space.shape == (2 + 4,)
        check_env(env, skip_render_check=False)


# ==============================================================================
# 2. Seeding & Reproducibility Tests
# ==============================================================================

class TestSeedingAndReproducibility:
    """시딩 및 에피소드 재현성 검증"""

    def test_action_space_sampling_determinism(self, sample_dataset):
        """action_space.seed() 설정 시 샘플링 시퀀스 100% 동일성 검증"""
        env1 = HybridTradingEnv(df=sample_dataset)
        env2 = HybridTradingEnv(df=sample_dataset)
        
        env1.action_space.seed(777)
        env2.action_space.seed(777)
        
        for _ in range(50):
            s1 = env1.action_space.sample()
            s2 = env2.action_space.sample()
            assert s1[0] == s2[0]
            assert np.allclose(s1[1], s2[1])

    def test_multi_instance_trajectory_determinism(self, sample_dataset):
        """동일 시드 및 동일 액션 시퀀스 주입 시 두 독립 환경의 전체 상태 궤적 완벽 일치 검증"""
        envA = HybridTradingEnv(df=sample_dataset, initial_cash=10_000_000)
        envB = HybridTradingEnv(df=sample_dataset, initial_cash=10_000_000)
        
        obsA, infoA = envA.reset(seed=1234)
        obsB, infoB = envB.reset(seed=1234)
        
        assert np.array_equal(obsA, obsB)
        assert infoA["total_equity"] == infoB["total_equity"]
        
        rng = np.random.RandomState(99)
        for step in range(50):
            act_type = int(rng.choice([0, 1, 2]))
            weight = float(rng.uniform(0.0, 1.0))
            action = (act_type, np.array([weight], dtype=np.float32))
            
            oA, rA, termA, truncA, iA = envA.step(action)
            oB, rB, termB, truncB, iB = envB.step(action)
            
            assert np.allclose(oA, oB, atol=1e-6), f"Obs mismatch at step {step}"
            assert abs(rA - rB) < 1e-7, f"Reward mismatch at step {step}"
            assert termA == termB and truncA == truncB
            assert iA["total_equity"] == iB["total_equity"]
            assert iA["cash_balance"] == iB["cash_balance"]
            assert iA["holding_quantity"] == iB["holding_quantity"]

    def test_reset_seed_isolation_and_restoration(self, sample_dataset):
        """다양한 시드로 리셋 후 이전 시드로 재리셋 시 초기 상태 복원 검증"""
        env = HybridTradingEnv(df=sample_dataset)
        
        obs1_0, _ = env.reset(seed=501)
        for _ in range(10):
            env.step((1, np.array([0.5], dtype=np.float32)))
            
        obs2_0, _ = env.reset(seed=602)
        for _ in range(10):
            env.step((1, np.array([0.5], dtype=np.float32)))
            
        obs1_re, _ = env.reset(seed=501)
        assert np.array_equal(obs1_0, obs1_re)


# ==============================================================================
# 3. ContinuousToHybridActionWrapper & SB3 Integration Tests
# ==============================================================================

class TestSB3IntegrationAndAutoReset:
    """SB3 DummyVecEnv 및 RL 알고리즘 연동성 검증"""

    def test_dummy_vec_env_step_and_auto_reset(self, sample_dataset):
        """DummyVecEnv 멀티 환경 스텝 및 max_steps 도달 시 auto-reset 및 terminal_observation 검증"""
        num_envs = 4
        def make_env():
            def _init():
                base = HybridTradingEnv(df=sample_dataset, initial_cash=10_000_000, max_steps=30)
                return ContinuousToHybridActionWrapper(base)
            return _init

        vec_env = DummyVecEnv([make_env() for _ in range(num_envs)])
        obs = vec_env.reset()
        assert obs.shape == (num_envs, 14)
        assert obs.dtype == np.float32

        # 50 스텝 실행하여 auto-reset 발생 유도 (max_steps=30)
        for step in range(50):
            actions = np.random.uniform(-1.0, 1.0, size=(num_envs, 2)).astype(np.float32)
            actions[:, 1] = np.random.uniform(0.0, 1.0, size=num_envs).astype(np.float32)
            
            next_obs, rewards, dones, infos = vec_env.step(actions)
            assert next_obs.shape == (num_envs, 14)
            assert rewards.shape == (num_envs,)
            assert dones.shape == (num_envs,)
            assert len(infos) == num_envs
            
            for i, done in enumerate(dones):
                if done:
                    assert "terminal_observation" in infos[i]
                    assert infos[i]["terminal_observation"].shape == (14,)
                    assert np.all(np.isfinite(infos[i]["terminal_observation"]))

        vec_env.close()

    def test_sb3_ppo_training_and_predict(self, sample_dataset):
        """SB3 PPO 모델 학습(learn) 및 추론(predict) 파이프라인 검증"""
        def make_env():
            def _init():
                base = HybridTradingEnv(df=sample_dataset, initial_cash=10_000_000, max_steps=50)
                return ContinuousToHybridActionWrapper(base)
            return _init

        vec_env = DummyVecEnv([make_env() for _ in range(2)])
        model = PPO(
            "MlpPolicy",
            vec_env,
            n_steps=32,
            batch_size=16,
            n_epochs=2,
            learning_rate=3e-4,
            verbose=0,
            seed=42,
            device="cpu",
        )
        model.learn(total_timesteps=128)
        
        test_obs = vec_env.reset()
        for _ in range(5):
            action, _ = model.predict(test_obs, deterministic=True)
            assert action.shape == (2, 2)
            test_obs, rewards, dones, infos = vec_env.step(action)
            assert np.all(np.isfinite(test_obs))
            assert np.all(np.isfinite(rewards))
            
        vec_env.close()

    def test_sb3_a2c_training_and_predict(self, sample_dataset):
        """SB3 A2C 모델 학습 및 추론 파이프라인 검증"""
        def make_env():
            def _init():
                base = HybridTradingEnv(df=sample_dataset, initial_cash=10_000_000, max_steps=50)
                return ContinuousToHybridActionWrapper(base)
            return _init

        vec_env = DummyVecEnv([make_env() for _ in range(2)])
        model = A2C(
            "MlpPolicy",
            vec_env,
            n_steps=16,
            learning_rate=7e-4,
            verbose=0,
            seed=42,
            device="cpu",
        )
        model.learn(total_timesteps=64)
        
        test_obs = vec_env.reset()
        for _ in range(5):
            action, _ = model.predict(test_obs, deterministic=True)
            assert action.shape == (2, 2)
            test_obs, rewards, dones, infos = vec_env.step(action)
            assert np.all(np.isfinite(test_obs))
            assert np.all(np.isfinite(rewards))
            
        vec_env.close()


# ==============================================================================
# 4. Accounting Invariant Under Rapid Flipping Tests
# ==============================================================================

class TestHighFrequencyAccountingInvariant:
    """고빈도 반전 매매 시 회계 불변식 정밀 검증"""

    def test_rapid_buy_sell_flipping_invariant(self, sample_dataset):
        """BUY 100%와 SELL 100%를 매 스텝 교차 실행 시 회계 불변식 0원 오차 유지 검증"""
        fee_config = FeeConfig(
            commission_rate=Decimal("0.00015"),
            tax_rate=Decimal("0.0018"),
            slippage_rate=Decimal("0.0010")
        )
        env = HybridTradingEnv(df=sample_dataset, initial_cash=10_000_000, fee_config=fee_config)
        env.reset()

        for step in range(80):
            act_type = 1 if step % 2 == 0 else 2
            obs, rew, term, trunc, info = env.step((act_type, np.array([1.0], dtype=np.float32)))
            assert env.verify_accounting_invariant(tolerance=Decimal("1")) is True
            if term or trunc:
                break

        audit = env.get_accounting_audit()
        discrepancy = abs(
            (audit["initial_cash"] + audit["cumulative_market_drift_pnl"])
            - (audit["total_equity"] + audit["total_frictions"])
        )
        assert discrepancy <= Decimal("1")
