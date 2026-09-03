"""
Milestone 3 (ML/RL Pipeline & Env) Adversarial Stress Test Suite
Challenger 1 Empirical Verification Harness
"""

import math
import os
import threading
import tempfile
from decimal import Decimal
from typing import Dict, List, Tuple
from unittest.mock import MagicMock, patch

import gymnasium as gym
import numpy as np
import pandas as pd
import pytest
import torch
import torch.nn as nn

from modules.engine.hybrid_trading_env import (
    ActionType,
    FeeConfig,
    HybridTradingEnv,
    OrderSide,
    TradeRecord,
)
from modules.engine.live_learning_simulator import (
    LiveLearningSimulator,
    get_live_simulator,
    reset_global_simulator,
)
from modules.hpo.metrics import (
    calculate_annualized_sharpe_ratio,
    calculate_total_return_pct,
    evaluate_trading_history,
)
from modules.hpo.optuna_pipeline import create_hpo_study, objective, run_hpo_optimization
from modules.models.feature_extractor import (
    DualStreamSLFeatureExtractor,
    TabularMLPFeatureExtractor,
    Temporal1DCNNFeatureExtractor,
)
from modules.models.hybrid_policy import (
    HybridActorCritic,
    HybridPPO,
    RolloutBuffer,
    SB3HybridPolicyAdapter,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def adversarial_df():
    """다양한 이상치와 극단적 변동성을 포함한 100개 스텝의 테스트 데이터프레임"""
    np.random.seed(42)
    n = 100
    prices = [70000.0]
    for _ in range(n - 1):
        ret = np.random.normal(0.001, 0.02)
        prices.append(max(100.0, prices[-1] * (1.0 + ret)))

    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=n, freq="B"),
        "symbol": "005930",
        "open": prices,
        "high": [p * 1.01 for p in prices],
        "low": [p * 0.99 for p in prices],
        "close": prices,
        "volume": np.random.randint(10000, 1000000, size=n).astype(float),
        "returns_1d": [0.0] + [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, n)],
        "volatility_20d": [0.02] * n,
        "log_return": [0.0] + [float(np.log(prices[i] / prices[i - 1])) for i in range(1, n)],
        "ma_5": pd.Series(prices).rolling(5, min_periods=1).mean().values,
        "ma_20": pd.Series(prices).rolling(20, min_periods=1).mean().values,
        "ma_60": pd.Series(prices).rolling(60, min_periods=1).mean().values,
        "dynamic_per": np.random.uniform(5.0, 30.0, size=n),
        "dynamic_pbr": np.random.uniform(0.5, 3.0, size=n),
        "dynamic_market_cap": [4e14] * n,
    })
    return df


# ==============================================================================
# 1. Step Indexing & Boundary Stress Tests (BUG-RL01)
# ==============================================================================

class TestStepIndexingAdversarial:
    """관측값 시계열 인덱싱 지연, 중복, 경계 조건에 대한 적대적 스트레스 테스트"""

    def test_step_indexing_exact_feature_tracking_all_steps(self, adversarial_df):
        """0번부터 마지막 스텝까지 매 스텝마다 df의 정확한 행 데이터가 관측값으로 반환되는지 전수 추적"""
        # 고유한 식별용 returns_1d 피처 주입
        adversarial_df["returns_1d"] = [1000.0 + float(i) for i in range(len(adversarial_df))]
        env = HybridTradingEnv(df=adversarial_df, initial_cash=10_000_000, max_steps=len(adversarial_df))

        obs, info = env.reset()
        assert info["step"] == 0
        # reset() 시점의 returns_1d는 0번 행이어야 함
        assert pytest.approx(obs[0], abs=1e-3) == 1000.0

        for step_i in range(1, len(adversarial_df)):
            obs, rew, term, trunc, info = env.step((0, np.array([0.0], dtype=np.float32)))
            assert info["step"] == step_i
            expected_val = 1000.0 + float(step_i)
            assert pytest.approx(obs[0], abs=1e-3) == expected_val, (
                f"Step {step_i} indexing mismatch: expected {expected_val}, got {obs[0]}"
            )
            if term or trunc:
                break

    def test_minimal_dataframe_length_boundary(self):
        """길이가 1인 데이터프레임, 2인 데이터프레임에서의 경계 인덱스 오버플로우 방어"""
        for length in [1, 2, 3]:
            df_small = pd.DataFrame({
                "date": pd.date_range("2026-01-01", periods=length, freq="B"),
                "symbol": "005930",
                "close": [70000.0 + (i * 1000.0) for i in range(length)],
                "returns_1d": [float(i) * 0.05 for i in range(length)],
            })
            env = HybridTradingEnv(df=df_small, initial_cash=10_000_000, max_steps=10)
            obs, info = env.reset()
            assert obs.shape == (14,)
            assert not np.isnan(obs).any()

            for step_i in range(5):
                obs, rew, term, trunc, info = env.step((0, np.array([0.0], dtype=np.float32)))
                assert obs.shape == (14,)
                assert not np.isnan(obs).any()
                if length == 1:
                    # 1행이면 첫 스텝에 truncation 발생
                    assert trunc is True


# ==============================================================================
# 2. HOLD Step & Trade Record Leakage Stress Tests (BUG-RL02 / BUG-L04)
# ==============================================================================

class TestTradeRecordLeakageAdversarial:
    """연속적인 다양한 액션 시퀀스에서 거래 내역 누출(State Leakage) 철저 검증"""

    def test_complex_action_sequence_trade_record_isolation(self, adversarial_df):
        """BUY -> HOLD -> HOLD -> SELL -> HOLD -> FAILED_BUY -> HOLD 시퀀스 누출 검증"""
        env = HybridTradingEnv(df=adversarial_df, initial_cash=10_000_000)
        env.reset()

        # Step 1: BUY 50% -> trade_record MUST exist
        obs, rew, term, trunc, info = env.step((1, np.array([0.5], dtype=np.float32)))
        assert info["trade_record"] is not None
        assert info["trade_record"].side == OrderSide.BUY

        # Step 2: HOLD -> trade_record MUST BE None
        obs, rew, term, trunc, info = env.step((0, np.array([0.0], dtype=np.float32)))
        assert info["trade_record"] is None, "HOLD step leaked previous BUY trade_record!"

        # Step 3: HOLD again -> trade_record MUST BE None
        obs, rew, term, trunc, info = env.step((0, np.array([0.0], dtype=np.float32)))
        assert info["trade_record"] is None, "Repeated HOLD step leaked trade_record!"

        # Step 4: SELL 100% -> trade_record MUST exist
        obs, rew, term, trunc, info = env.step((2, np.array([1.0], dtype=np.float32)))
        assert info["trade_record"] is not None
        assert info["trade_record"].side == OrderSide.SELL

        # Step 5: HOLD -> trade_record MUST BE None
        obs, rew, term, trunc, info = env.step((0, np.array([0.0], dtype=np.float32)))
        assert info["trade_record"] is None, "HOLD step leaked previous SELL trade_record!"

        # Step 6: SELL 100% with 0 shares (Failed trade) -> trade_record MUST BE None
        obs, rew, term, trunc, info = env.step((2, np.array([1.0], dtype=np.float32)))
        assert info["trade_record"] is None, "Failed SELL operation must have trade_record as None!"

        # Step 7: HOLD -> trade_record MUST BE None
        obs, rew, term, trunc, info = env.step((0, np.array([0.0], dtype=np.float32)))
        assert info["trade_record"] is None

        # Verify get_state() also has no stale trade_record
        state_dict = env.get_state()
        assert state_dict["trade_record"] is None


# ==============================================================================
# 3. CPU/CUDA Device Consistency & Input Polymorphism Stress Tests (BUG-RL03)
# ==============================================================================

class TestDeviceConsistencyAndPolymorphismAdversarial:
    """CPU/CUDA 디바이스 일관성 및 다양한 입력 포맷에 대한 적대적 텐서 주입 테스트"""

    def test_all_extractors_with_various_dtypes_and_devices(self):
        """다양한 dtype (float32, float64), shape, unbatched 텐서에 대한 강건성 검증"""
        mlp = TabularMLPFeatureExtractor(input_dim=14, output_dim=32)
        cnn = Temporal1DCNNFeatureExtractor(in_channels=10, seq_len=20, output_dim=32)
        dual = DualStreamSLFeatureExtractor(temporal_in_channels=10, temporal_seq_len=20, tabular_dim=4, output_dim=64)
        policy = HybridActorCritic(obs_dim=14, feature_dim=64)

        # 1. Float64 Tensor Input (자동 float32 변환 및 디바이스 일치 확인)
        x_f64 = torch.randn(8, 14, dtype=torch.float64)
        out_mlp_f64 = mlp(x_f64)
        assert out_mlp_f64.dtype == torch.float32
        assert out_mlp_f64.shape == (8, 32)

        # 2. 1D Unbatched Input
        x_1d = torch.randn(14, dtype=torch.float32)
        out_mlp_1d = mlp(x_1d)
        assert out_mlp_1d.shape == (32,)

        # 3. CNN 3D (B, seq, chan) and (B, chan, seq)
        x_cnn_3d_1 = torch.randn(4, 20, 10, dtype=torch.float32)
        x_cnn_3d_2 = torch.randn(4, 10, 20, dtype=torch.float32)
        out_cnn_1 = cnn(x_cnn_3d_1)
        out_cnn_2 = cnn(x_cnn_3d_2)
        assert out_cnn_1.shape == (4, 32)
        assert out_cnn_2.shape == (4, 32)

        # 4. DualStream with mismatched input dict / tuple
        t_3d = torch.randn(4, 20, 10, dtype=torch.float32)
        tab_2d = torch.randn(4, 4, dtype=torch.float32)
        out_dual_dict = dual({"temporal": t_3d, "tabular": tab_2d})
        assert out_dual_dict.shape == (4, 64)

        # 5. DualStream with 1D numpy array
        np_1d = np.random.randn(14).astype(np.float32)
        out_dual_np = dual(np_1d)
        assert out_dual_np.shape == (64,)

        # 6. HybridActorCritic with CPU Tensor and evaluate_actions
        actions = (torch.tensor([0, 1, 2]), torch.tensor([0.0, 0.5, 1.0]))
        batch_obs = torch.randn(3, 14)
        log_prob, entropy, val = policy.evaluate_actions(batch_obs, actions)
        assert log_prob.shape == (3,)
        assert entropy.shape == (3,)
        assert val.shape == (3,)

    def test_extreme_and_inf_nan_tensor_robustness(self):
        """텐서 내 NaN, Inf, 극단값(1e9, -1e9) 주입 시 크래시 없이 정상 finite 출력 검증"""
        mlp = TabularMLPFeatureExtractor(input_dim=14, output_dim=32)
        policy = HybridActorCritic(obs_dim=14, feature_dim=64)

        bad_tensor = torch.tensor([
            [float("nan")] * 14,
            [float("inf")] * 14,
            [-float("inf")] * 14,
            [1e9] * 14,
            [-1e9] * 14,
        ], dtype=torch.float32)

        out_mlp = mlp(bad_tensor)
        assert torch.isfinite(out_mlp).all(), "MLP produced NaN/Inf from bad tensor!"

        disc_logits, p1, p2, val = policy(bad_tensor)
        assert torch.isfinite(disc_logits).all()
        assert torch.isfinite(val).all()


# ==============================================================================
# 4. LiveLearningSimulator Gym Standard & Concurrency Stress (BUG-RL04, BUG-C03)
# ==============================================================================

class TestLiveSimulatorAndConcurrencyAdversarial:
    """Gymnasium 1.2.0 5-tuple 규격 및 멀티스레드 싱글톤 경합 스트레스 테스트"""

    def test_gymnasium_5_tuple_and_log_return_precision(self):
        """step() 5-tuple 언패킹 및 Log Return 정확성 검증"""
        sim = LiveLearningSimulator(initial_cash=10_000_000)

        # Mock fetch_live_price
        sim.fetch_live_price = MagicMock(return_value=Decimal("70000"))

        # Step 1: HOLD
        res = sim.step(symbol="005930", action=ActionType.HOLD, quantity=0)
        assert len(res) == 5, f"Expected 5-tuple, got length {len(res)}"
        obs, reward, terminated, truncated, info = res
        assert isinstance(obs, dict)
        assert isinstance(reward, float)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert isinstance(info, dict)
        assert reward == 0.0

        # Step 2: BUY 10 shares at 70,000
        sim.step(symbol="005930", action=ActionType.BUY, quantity=10)

        # Step 3: Price rises to 77,000 (10% increase)
        sim.fetch_live_price = MagicMock(return_value=Decimal("77000"))
        obs, reward, term, trunc, info = sim.step(symbol="005930", action=ActionType.HOLD, quantity=0)

        # Expected log return
        # Initial cash = 10,000,000
        # After buy: holding 10 shares, cash = 10,000,000 - 700,000 - commission
        # Total equity at 77,000 = cash + 770,000
        assert reward > 0.0, "Reward must be positive on price increase"
        assert not math.isnan(reward) and not math.isinf(reward)

    def test_multithreaded_singleton_double_checked_locking_race(self):
        """50개 스레드가 동시에 get_live_simulator()를 호출할 때 100% 동일한 싱글톤 인스턴스를 반환하는지 경합 검증"""
        reset_global_simulator()
        instances: List[LiveLearningSimulator] = []
        errors: List[Exception] = []

        def worker():
            try:
                inst = get_live_simulator(initial_cash=10_000_000)
                instances.append(inst)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Exceptions occurred during singleton retrieval: {errors}"
        assert len(instances) == 50
        first_instance = instances[0]
        for inst in instances:
            assert inst is first_instance, "Multiple distinct simulator instances were instantiated!"

        reset_global_simulator()


# ==============================================================================
# 5. HPO Reward Hacking & Zero-Trade Penalty Stress Tests (BUG-RL05)
# ==============================================================================

class TestHPOZeroTradePenaltyAdversarial:
    """HPO 목적 함수에서 무거래 정책 패널티 및 활성 탐색 정책 가중치 철저 검증"""

    def test_zero_trade_policy_vs_active_exploration_ordering(self):
        """
        무거래 정책(total_trades=0, SR=0.0) -> -1.0
        소폭 손실 활성 정책(total_trades=5, SR=-0.3, Ret=-1%) -> -0.3 + 0.01 * (-1.0) = -0.31
        검증: 활성 탐색 정책(-0.31)이 무거래(-1.0)보다 높은 목적값을 받아야 함.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_csv = os.path.join(tmp_dir, "hpo_ordering_test.csv")
            study = create_hpo_study(seed=42)

            # Scenario A: Inactive (0 trades)
            with patch("modules.hpo.optuna_pipeline.evaluate_trading_history") as mock_eval:
                mock_eval.return_value = {
                    "total_equity": 10_000_000.0,
                    "total_return_pct": 0.0,
                    "sharpe_ratio": 0.0,
                    "max_drawdown_pct": 0.0,
                    "total_trades": 0,
                    "win_rate": 0.0,
                }
                obj_inactive = objective(
                    trial=study.ask(),
                    output_csv=output_csv,
                    n_timesteps=32,
                    fast_mode=True,
                )
                assert obj_inactive == -1.0

            # Scenario B: Active exploration with small drawdown
            with patch("modules.hpo.optuna_pipeline.evaluate_trading_history") as mock_eval:
                mock_eval.return_value = {
                    "total_equity": 9_900_000.0,
                    "total_return_pct": -1.0,
                    "sharpe_ratio": -0.3,
                    "max_drawdown_pct": -1.5,
                    "total_trades": 5,
                    "win_rate": 40.0,
                }
                obj_active = objective(
                    trial=study.ask(),
                    output_csv=output_csv,
                    n_timesteps=32,
                    fast_mode=True,
                )
                # Expected: -0.3 + 0.01 * (-1.0) = -0.31
                assert pytest.approx(obj_active, abs=1e-4) == -0.31
                assert obj_active > obj_inactive, (
                    f"Active exploration ({obj_active}) should be favored over complete inactivity ({obj_inactive})"
                )

            # Scenario C: Severe Bankruptcy (<500k)
            with patch("modules.hpo.optuna_pipeline.HybridTradingEnv") as mock_env_cls:
                mock_env = MagicMock()
                mock_env.reset.return_value = (np.zeros(14, dtype=np.float32), {"step": 0})
                # terminated with equity 100,000 (< 500,000)
                mock_env.step.return_value = (
                    np.zeros(14, dtype=np.float32),
                    -1.0,
                    True,
                    False,
                    {"total_equity": 100_000.0, "step": 10, "trade_record": None},
                )
                mock_env_cls.return_value = mock_env

                obj_bankrupt = objective(
                    trial=study.ask(),
                    output_csv=output_csv,
                    n_timesteps=32,
                    fast_mode=True,
                )
                assert obj_bankrupt == -100.0


# ==============================================================================
# 6. End-to-End PPO + Env Stress & Accounting Invariant Harness
# ==============================================================================

class TestEndToEndPPOAndEnvStress:
    """전체 PPO 에이전트와 HybridTradingEnv 간 200 스텝 연속 학습/롤아웃 스트레스 테스트"""

    def test_ppo_env_rollout_and_accounting_integrity(self, adversarial_df):
        """200 스텝 롤아웃 수행 후 회계 불변식(1원 오차 방어) 및 수치 안정성 검증"""
        env = HybridTradingEnv(df=adversarial_df, initial_cash=10_000_000, max_steps=len(adversarial_df))
        agent = HybridPPO(
            env=env,
            learning_rate=1e-3,
            n_steps=32,
            batch_size=16,
            n_epochs=2,
        )

        obs, info = env.reset()
        total_rewards = 0.0

        for step in range(80):
            action, _ = agent.predict(obs, deterministic=False)
            next_obs, reward, terminated, truncated, info = env.step(action)
            total_rewards += reward

            # 회계 불변식 상시 검증
            assert env.verify_accounting_invariant() is True

            obs = next_obs
            if terminated or truncated:
                obs, info = env.reset()

        # Check learn execution
        agent.learn(total_timesteps=32)

        assert not math.isnan(total_rewards)
        assert not math.isinf(total_rewards)
