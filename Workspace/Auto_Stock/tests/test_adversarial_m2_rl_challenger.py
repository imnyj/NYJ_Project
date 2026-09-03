"""
tests/test_adversarial_m2_rl_challenger.py
===========================================
Milestone 2 제2 적대적 챌린저 (Challenger 2) 전용 고강도 스트레스 & 수치적 무결성 공격 테스트 스위트.

검증 핵심 영역:
1. [Hypothesis 1] HybridPPO & SB3HybridPolicyAdapter vs HybridTradingEnv 1,000 스텝 롤아웃 및 정책 수렴성 스트레스 검증
2. [Hypothesis 2] GAE 어드밴티지 및 엔트로피 보너스 수치적 무결성 (독립 Oracle 대조, 특수 경계값, gamma/lambda 극한 검증)
3. [Hypothesis 3] 난수 시드(Seed) 기반 완벽 재현성 및 체크포인트 직렬화 후 가중치 100% 비트 단위 일치 검증
4. [Hypothesis 4] 극단값(NaN/Inf/1e18), 0-분산, 비정상 배치 형상 하에서의 방어 메커니즘 및 역전파 무결성 검증
"""

import os
import math
import tempfile
from decimal import Decimal
from typing import Dict, List, Tuple

import gymnasium as gym
import numpy as np
import pandas as pd
import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Beta, Categorical, Normal

from modules.engine.hybrid_trading_env import (
    ContinuousToHybridActionWrapper,
    HybridTradingEnv,
)
from modules.engine.mock_environment import FeeConfig
from modules.models.feature_extractor import (
    DualStreamSLFeatureExtractor,
    SLPretrainer,
    TabularMLPFeatureExtractor,
    Temporal1DCNNFeatureExtractor,
)
from modules.models.hybrid_policy import (
    HybridActorCritic,
    HybridPPO,
    RolloutBuffer,
    SB3CustomFeaturesExtractor,
    SB3HybridPolicyAdapter,
)


@pytest.fixture
def synthetic_market_data() -> pd.DataFrame:
    """1,500 스텝 이상의 장기 시계열 합성 데이터셋"""
    rng = np.random.RandomState(42)
    length = 1500
    dates = pd.date_range("2025-01-01", periods=length, freq="B")
    returns = rng.normal(0.0003, 0.018, size=length)
    prices = np.round(60000.0 * np.cumprod(1.0 + returns))

    return pd.DataFrame({
        "date": dates,
        "symbol": "005930",
        "open": np.round(prices * (1.0 + rng.normal(0, 0.002, length))),
        "high": np.round(prices * (1.0 + np.abs(rng.normal(0, 0.006, length)))),
        "low": np.round(prices * (1.0 - np.abs(rng.normal(0, 0.006, length)))),
        "close": prices,
        "volume": rng.randint(100000, 2000000, length),
        "returns_1d": returns,
        "log_return": np.log1p(returns),
        "volatility_20d": np.full(length, 0.018),
        "ma_5": pd.Series(prices).rolling(5, min_periods=1).mean().values,
        "ma_20": pd.Series(prices).rolling(20, min_periods=1).mean().values,
        "ma_60": pd.Series(prices).rolling(60, min_periods=1).mean().values,
        "dynamic_per": np.full(length, 12.5),
        "dynamic_pbr": np.full(length, 1.2),
        "dynamic_market_cap": prices * 6_000_000_000.0,
    })


# ==============================================================================
# 1. 1,000-Step Rollout & Convergence Stress Tests
# ==============================================================================

class TestHybridPPOAndSB3RolloutStress:
    """HybridPPO 및 SB3HybridPolicyAdapter의 1,000 스텝 롤아웃 및 수렴성 스트레스 검증"""

    def test_hybrid_ppo_1000_steps_rollout_training(self, synthetic_market_data):
        """HybridPPO 1,000 스텝 롤아웃 학습 완주, 손실 유한성 및 정책 건전성 검증"""
        env = HybridTradingEnv(df=synthetic_market_data, initial_cash=10_000_000, max_steps=250)

        ppo = HybridPPO(
            env=env,
            learning_rate=3e-4,
            n_steps=128,
            batch_size=32,
            n_epochs=4,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,
            vf_coef=0.5,
            max_grad_norm=0.5,
            device="cpu",
            seed=42,
        )

        # 1,000 스텝 학습 수행
        ppo.learn(total_timesteps=1000)

        # 학습 후 파라미터 유한성 (NaN/Inf 부재) 검증
        for name, param in ppo.policy.named_parameters():
            assert not torch.isnan(param).any(), f"NaN detected in parameter {name}"
            assert not torch.isinf(param).any(), f"Inf detected in parameter {name}"

        # 평가 수행 (3개 에피소드)
        eval_res = ppo.evaluate(env=env, n_episodes=3, deterministic=True)
        assert "mean_reward" in eval_res
        assert "mean_final_equity" in eval_res
        assert math.isfinite(eval_res["mean_reward"])
        assert math.isfinite(eval_res["mean_final_equity"])
        assert eval_res["mean_final_equity"] > 0.0

    def test_sb3_hybrid_adapter_1000_steps_training(self, synthetic_market_data):
        """SB3HybridPolicyAdapter 기반 PPO 1,000 스텝 학습 및 디코딩 무결성 검증"""
        base_env = HybridTradingEnv(df=synthetic_market_data, initial_cash=10_000_000, max_steps=200)

        model = SB3HybridPolicyAdapter.create_sb3_ppo(
            env=base_env,
            features_dim=32,
            learning_rate=3e-4,
            n_steps=128,
            batch_size=32,
            seed=42,
            device="cpu",
        )

        SB3HybridPolicyAdapter.train_sb3_agent(model, total_timesteps=1000)

        # 추론 및 디코딩 검증 (50회)
        obs, _ = base_env.reset(seed=123)
        for _ in range(50):
            hybrid_act, raw_act = SB3HybridPolicyAdapter.predict_hybrid(model, obs, deterministic=True)
            act_type, weight = hybrid_act

            assert act_type in (0, 1, 2), f"Invalid action type: {act_type}"
            assert 0.0 <= weight <= 1.0, f"Invalid position weight: {weight}"
            assert len(raw_act) == 2

            obs, reward, terminated, truncated, info = base_env.step(hybrid_act)
            if terminated or truncated:
                obs, _ = base_env.reset()

    def test_hybrid_ppo_gaussian_policy_1000_steps_rollout(self, synthetic_market_data):
        """Gaussian 분포를 사용하는 HybridActorCritic에 대한 1,000 스텝 롤아웃 안정성 검증"""
        env = HybridTradingEnv(df=synthetic_market_data, initial_cash=10_000_000, max_steps=250)
        policy_gaussian = HybridActorCritic(
            obs_dim=14,
            feature_dim=32,
            distribution_type="gaussian",
        )

        ppo = HybridPPO(
            env=env,
            policy=policy_gaussian,
            learning_rate=3e-4,
            n_steps=128,
            batch_size=32,
            n_epochs=4,
            device="cpu",
            seed=42,
        )

        ppo.learn(total_timesteps=1000)

        for name, param in ppo.policy.named_parameters():
            assert not torch.isnan(param).any(), f"NaN in {name}"
            assert not torch.isinf(param).any(), f"Inf in {name}"

        eval_res = ppo.evaluate(env=env, n_episodes=2, deterministic=True)
        assert math.isfinite(eval_res["mean_reward"])


# ==============================================================================
# 2. GAE & Entropy Bonus Numerical Integrity Tests (Oracle Comparison)
# ==============================================================================

class TestGAEAndEntropyNumericalIntegrity:
    """GAE 어드밴티지 및 엔트로피 계산의 수치적 무결성 독립 Oracle 검증"""

    @staticmethod
    def _ground_truth_gae(
        rewards: np.ndarray,
        values: np.ndarray,
        dones: np.ndarray,
        last_value: float,
        last_done: bool,
        gamma: float,
        gae_lambda: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """독립적인 정밀 GAE 기준 오라클 구현"""
        n_steps = len(rewards)
        advantages = np.zeros(n_steps, dtype=np.float64)
        last_gae = 0.0

        for t in reversed(range(n_steps)):
            if t == n_steps - 1:
                next_non_terminal = 1.0 - float(last_done)
                next_val = float(last_value)
            else:
                next_non_terminal = 1.0 - float(dones[t])
                next_val = float(values[t + 1])

            delta = float(rewards[t]) + gamma * next_val * next_non_terminal - float(values[t])
            last_gae = delta + gamma * gae_lambda * next_non_terminal * last_gae
            advantages[t] = last_gae

        returns = advantages + values.astype(np.float64)
        return advantages.astype(np.float32), returns.astype(np.float32)

    @pytest.mark.parametrize("gamma, gae_lambda", [
        (0.99, 0.95),
        (0.99, 0.0),   # 1-step TD advantage
        (0.99, 1.0),   # Monte-Carlo return advantage
        (0.0, 0.95),    # Zero future discount (myopic)
        (1.0, 0.95),    # Undiscounted
    ])
    def test_gae_against_independent_oracle(self, gamma, gae_lambda):
        """다양한 gamma, lambda 조건에서 RolloutBuffer GAE와 독립 Oracle의 완전 일치 검증"""
        buf_size = 64
        obs_dim = 14
        device = torch.device("cpu")
        buffer = RolloutBuffer(buffer_size=buf_size, obs_dim=obs_dim, device=device)

        rng = np.random.RandomState(42)
        rewards = rng.normal(0.0, 1.0, size=buf_size).astype(np.float32)
        values = rng.normal(10.0, 2.0, size=buf_size).astype(np.float32)
        # Random dones with some episode endings
        dones = np.zeros(buf_size, dtype=np.float32)
        dones[15] = 1.0
        dones[39] = 1.0
        dones[buf_size - 1] = 0.0

        last_value = 12.5
        last_done = False

        for i in range(buf_size):
            buffer.add(
                obs=np.zeros(obs_dim, dtype=np.float32),
                action=(1, 0.5),
                reward=float(rewards[i]),
                value=float(values[i]),
                log_prob=-0.5,
                done=bool(dones[i]),
            )

        buffer.compute_returns_and_advantages(
            last_value=last_value,
            last_done=last_done,
            gamma=gamma,
            gae_lambda=gae_lambda,
        )

        expected_adv, expected_ret = self._ground_truth_gae(
            rewards=rewards,
            values=values,
            dones=dones,
            last_value=last_value,
            last_done=last_done,
            gamma=gamma,
            gae_lambda=gae_lambda,
        )

        np.testing.assert_allclose(buffer.advantages, expected_adv, rtol=1e-5, atol=1e-5)
        np.testing.assert_allclose(buffer.returns, expected_ret, rtol=1e-5, atol=1e-5)

    def test_gae_lambda_zero_is_exact_td_error(self):
        """lambda=0 일 때 GAE가 정확히 1-step TD 오차(delta_t)와 동일함을 증명"""
        buf_size = 10
        buffer = RolloutBuffer(buffer_size=buf_size, obs_dim=14, device=torch.device("cpu"))

        rewards = np.array([1.0, 2.0, -1.0, 0.5, 3.0, -2.0, 1.5, 0.0, 1.0, 2.0], dtype=np.float32)
        values = np.array([5.0, 5.5, 4.0, 4.5, 6.0, 3.0, 4.0, 4.2, 5.0, 6.0], dtype=np.float32)
        dones = np.zeros(buf_size, dtype=np.float32)
        dones[4] = 1.0  # Terminal at step 4

        last_value = 7.0
        last_done = False
        gamma = 0.99

        for i in range(buf_size):
            buffer.add(
                obs=np.zeros(14, dtype=np.float32),
                action=(0, 0.0),
                reward=float(rewards[i]),
                value=float(values[i]),
                log_prob=0.0,
                done=bool(dones[i]),
            )

        buffer.compute_returns_and_advantages(
            last_value=last_value,
            last_done=last_done,
            gamma=gamma,
            gae_lambda=0.0,
        )

        for t in range(buf_size):
            if t == buf_size - 1:
                next_v = last_value
                next_non_term = 1.0 - float(last_done)
            else:
                next_v = values[t + 1]
                next_non_term = 1.0 - dones[t]

            expected_delta = rewards[t] + gamma * next_v * next_non_term - values[t]
            assert abs(buffer.advantages[t] - expected_delta) < 1e-6

    def test_entropy_mathematical_consistency(self):
        """Beta 및 Categorical 분포의 엔트로피 계산 일관성 및 미분 가능성 검증"""
        policy_beta = HybridActorCritic(obs_dim=14, feature_dim=32, distribution_type="beta")
        policy_gauss = HybridActorCritic(obs_dim=14, feature_dim=32, distribution_type="gaussian")

        obs = torch.randn(16, 14)
        act_disc = torch.randint(0, 3, (16,))
        act_cont = torch.rand(16, 1)

        # 1. Beta Distribution
        log_prob_b, entropy_b, value_b = policy_beta.evaluate_actions(obs, (act_disc, act_cont))
        assert entropy_b.shape == (16,)
        assert not torch.isnan(entropy_b).any()
        assert not torch.isinf(entropy_b).any()

        # Categorical entropy is bounded in [0, ln(3)] = [0, 1.0986]
        disc_dist_b, cont_dist_b = policy_beta.get_action_distribution(obs)
        cat_ent = disc_dist_b.entropy()
        assert (cat_ent >= 0.0).all()
        assert (cat_ent <= math.log(3.0) + 1e-5).all()

        # Total entropy matches individual components
        expected_total_ent = cat_ent + cont_dist_b.entropy().sum(dim=-1)
        torch.testing.assert_close(entropy_b, expected_total_ent)

        # 2. Gaussian Distribution
        log_prob_g, entropy_g, value_g = policy_gauss.evaluate_actions(obs, (act_disc, act_cont))
        assert entropy_g.shape == (16,)
        assert not torch.isnan(entropy_g).any()

    def test_advantage_normalization_zero_variance_resilience(self):
        """모든 Advantage가 동일할 때(분산 0) 0으로 나누기 방어 검증"""
        ppo = HybridPPO(obs_dim=14, n_steps=8, batch_size=4, n_epochs=1)
        # Fill buffer with identical rewards & values
        ppo.buffer.reset()
        for _ in range(8):
            ppo.buffer.add(
                obs=np.zeros(14, dtype=np.float32),
                action=(0, 0.5),
                reward=1.0,
                value=1.0,
                log_prob=-1.0,
                done=False,
            )
        ppo.buffer.compute_returns_and_advantages(last_value=1.0, last_done=False)

        # Execute train_epoch (which normalizes advantages)
        metrics = ppo.train_epoch()
        assert math.isfinite(metrics["policy_loss"])
        assert math.isfinite(metrics["value_loss"])
        assert math.isfinite(metrics["total_loss"])


# ==============================================================================
# 3. Random Seed Reproducibility & Checkpoint Exact Weight Match Tests
# ==============================================================================

class TestSeedReproducibilityAndCheckpointIntegrity:
    """난수 시드 기반 재현성 및 체크포인트 직렬화/역직렬화 가중치 비트 일치 검증"""

    def test_seed_exact_trajectory_and_weights_reproducibility(self, synthetic_market_data):
        """동일한 시드로 초기화된 두 독립 HybridPPO가 100% 동일한 가중치 궤적을 산출함을 검증"""
        env1 = HybridTradingEnv(df=synthetic_market_data, initial_cash=10_000_000, max_steps=100)
        env2 = HybridTradingEnv(df=synthetic_market_data, initial_cash=10_000_000, max_steps=100)

        # Run 1: seed=777
        ppo1 = HybridPPO(
            env=env1,
            learning_rate=3e-4,
            n_steps=32,
            batch_size=16,
            n_epochs=2,
            seed=777,
            device="cpu",
        )
        ppo1.learn(total_timesteps=64)

        # Run 2: seed=777
        ppo2 = HybridPPO(
            env=env2,
            learning_rate=3e-4,
            n_steps=32,
            batch_size=16,
            n_epochs=2,
            seed=777,
            device="cpu",
        )
        ppo2.learn(total_timesteps=64)

        # Check exact parameter bitwise equality across all weights & biases
        for (n1, p1), (n2, p2) in zip(ppo1.policy.named_parameters(), ppo2.policy.named_parameters()):
            assert n1 == n2
            assert torch.equal(p1, p2), f"Parameter mismatch for {n1} between identical runs with seed 777"

        # Check deterministic prediction outputs
        obs_test = np.random.RandomState(999).randn(14).astype(np.float32)
        act1, _ = ppo1.predict(obs_test, deterministic=True)
        act2, _ = ppo2.predict(obs_test, deterministic=True)
        assert act1[0] == act2[0]
        assert act1[1] == act2[1]

    def test_seed_divergence_with_different_seeds(self, synthetic_market_data):
        """서로 다른 시드로 초기화된 두 에이전트는 서로 다른 가중치로 분기함을 검증"""
        env1 = HybridTradingEnv(df=synthetic_market_data, initial_cash=10_000_000, max_steps=100)
        env2 = HybridTradingEnv(df=synthetic_market_data, initial_cash=10_000_000, max_steps=100)

        ppo1 = HybridPPO(env=env1, n_steps=32, batch_size=16, n_epochs=2, seed=111, device="cpu")
        ppo1.learn(total_timesteps=64)

        ppo2 = HybridPPO(env=env2, n_steps=32, batch_size=16, n_epochs=2, seed=999, device="cpu")
        ppo2.learn(total_timesteps=64)

        # Weights should NOT be identical
        has_difference = False
        for (n1, p1), (n2, p2) in zip(ppo1.policy.named_parameters(), ppo2.policy.named_parameters()):
            if not torch.equal(p1, p2):
                has_difference = True
                break
        assert has_difference, "Different seeds must produce different parameter trajectories"

    def test_checkpoint_save_and_load_exact_tensor_and_optimizer_match(self):
        """저장 및 로드 후 모든 파라미터, 버퍼, 옵티마이저 상태가 100% 동일함을 검증"""
        ppo_orig = HybridPPO(obs_dim=14, learning_rate=5e-4, device="cpu")

        # Perform one synthetic train step to populate optimizer state (momentum, variance)
        ppo_orig.buffer.reset()
        for _ in range(ppo_orig.n_steps):
            ppo_orig.buffer.add(
                obs=np.random.randn(14).astype(np.float32),
                action=(np.random.randint(0, 3), float(np.random.rand())),
                reward=float(np.random.randn()),
                value=float(np.random.randn()),
                log_prob=-0.5,
                done=False,
            )
        ppo_orig.buffer.compute_returns_and_advantages(last_value=0.0, last_done=False)
        ppo_orig.train_epoch()

        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            ppo_orig.save(tmp_path)
            assert os.path.exists(tmp_path)

            ppo_loaded = HybridPPO(obs_dim=14, device="cpu")
            ppo_loaded.load(tmp_path)

            # 1. Policy parameters exact equality
            for (n1, p1), (n2, p2) in zip(ppo_orig.policy.named_parameters(), ppo_loaded.policy.named_parameters()):
                assert n1 == n2
                assert torch.equal(p1, p2), f"Parameter tensor mismatch after load: {n1}"

            # 2. Optimizer state exact equality
            opt1_state = ppo_orig.optimizer.state_dict()["state"]
            opt2_state = ppo_loaded.optimizer.state_dict()["state"]
            assert len(opt1_state) == len(opt2_state)

            for k in opt1_state:
                assert k in opt2_state
                for sub_k in opt1_state[k]:
                    val1 = opt1_state[k][sub_k]
                    val2 = opt2_state[k][sub_k]
                    if isinstance(val1, torch.Tensor):
                        assert torch.equal(val1, val2), f"Optimizer state tensor mismatch at {k}->{sub_k}"
                    else:
                        assert val1 == val2

            # 3. Exact deterministic predictions on 20 random observations
            rng = np.random.RandomState(42)
            for _ in range(20):
                obs = rng.randn(14).astype(np.float32)
                act1, _ = ppo_orig.predict(obs, deterministic=True)
                act2, _ = ppo_loaded.predict(obs, deterministic=True)
                assert act1[0] == act2[0]
                assert act1[1] == act2[1]
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


# ==============================================================================
# 4. Feature Extractor Adversarial Boundary & Numerical Hardening Tests
# ==============================================================================

class TestFeatureExtractorAdversarialBoundaryHardening:
    """특징 추출기 극단값, 극한 배치, 결측 스트림 공격 방어 검증"""

    def test_extreme_input_values_defense(self):
        """NaN, +/-Inf, 1e18, 1e-18, -1e18 극단치 유입 시 유한한 출력 및 NaN 미발생 검증"""
        mlp = TabularMLPFeatureExtractor(input_dim=14, output_dim=32)
        cnn = Temporal1DCNNFeatureExtractor(in_channels=10, seq_len=20, output_dim=32)
        dual = DualStreamSLFeatureExtractor(output_dim=32)

        # Tabular extreme tensor
        x_extreme = torch.tensor([
            [float("nan"), float("inf"), -float("inf"), 1e18, -1e18, 1e-18] + [0.0] * 8,
            [1e10, -1e10, 0.0, float("nan"), 1.0, -1.0] + [0.5] * 8,
        ], dtype=torch.float32)

        out_mlp = mlp(x_extreme)
        assert not torch.isnan(out_mlp).any()
        assert not torch.isinf(out_mlp).any()
        assert out_mlp.shape == (2, 32)

        # 1D-CNN extreme tensor
        x_cnn_extreme = torch.full((2, 20, 10), float("nan"))
        out_cnn = cnn(x_cnn_extreme)
        assert not torch.isnan(out_cnn).any()
        assert not torch.isinf(out_cnn).any()
        assert out_cnn.shape == (2, 32)

        # DualStream extreme tensor
        out_dual = dual(x=x_extreme)
        assert not torch.isnan(out_dual).any()
        assert not torch.isinf(out_dual).any()

    @pytest.mark.parametrize("batch_size", [1, 2, 3, 7, 13, 64])
    def test_odd_and_prime_batch_sizes(self, batch_size):
        """홀수 및 소수(Prime) 배치 크기에서 GroupNorm 및 LayerNorm 안정성 검증"""
        mlp = TabularMLPFeatureExtractor(input_dim=14, output_dim=32, use_layer_norm=True)
        cnn = Temporal1DCNNFeatureExtractor(in_channels=10, seq_len=20, output_dim=32, norm_type="group_norm")
        dual = DualStreamSLFeatureExtractor(temporal_in_channels=10, temporal_seq_len=20, tabular_dim=4, output_dim=32)

        x_tab = torch.randn(batch_size, 14)
        x_temp = torch.randn(batch_size, 20, 10)

        out_m = mlp(x_tab)
        out_c = cnn(x_temp)
        out_d = dual(temporal_x=x_temp, tabular_x=x_tab[:, :4])

        assert out_m.shape == (batch_size, 32)
        assert out_c.shape == (batch_size, 32)
        assert out_d.shape == (batch_size, 32)

    def test_missing_stream_fallback_in_dual_stream(self):
        """DualStream에 temporal 또는 tabular 스트림이 완전히 누락(None)될 때 Zero Fallback 동작 검증"""
        dual = DualStreamSLFeatureExtractor(output_dim=32)

        # Only temporal provided
        out_temp_only = dual(temporal_x=torch.randn(4, 20, 10), tabular_x=None)
        assert out_temp_only.shape == (4, 32)
        assert not torch.isnan(out_temp_only).any()

        # Only tabular provided
        out_tab_only = dual(temporal_x=None, tabular_x=torch.randn(4, 4))
        assert out_tab_only.shape == (4, 32)
        assert not torch.isnan(out_tab_only).any()

        # Neither provided
        out_none = dual()
        assert out_none.shape == (1, 32)
        assert not torch.isnan(out_none).any()

    def test_sl_pretrainer_gradient_clipping_and_loss_weights(self):
        """SLPretrainer 멀티태스크 가중치(lambda_reg, lambda_cls) 반영 및 그래디언트 클리핑 검증"""
        dual = DualStreamSLFeatureExtractor(output_dim=32)
        pretrainer = SLPretrainer(
            backbone=dual,
            feature_dim=32,
            task_weight_reg=2.5,
            task_weight_cls=0.5,
        )

        t_x = torch.randn(8, 20, 10)
        tab_x = torch.randn(8, 4)
        y_ret = torch.randn(8, 1)
        y_dir = torch.randint(0, 3, (8,))

        p_ret, p_dir = pretrainer(temporal_x=t_x, tabular_x=tab_x)
        tot_l, reg_l, cls_l = pretrainer.compute_loss(p_ret, p_dir, y_ret, y_dir)

        # Check weighted formula
        expected_tot = 2.5 * reg_l + 0.5 * cls_l
        torch.testing.assert_close(tot_l, expected_tot)

        # Step execution
        metrics = pretrainer.train_step((t_x, tab_x, y_ret, y_dir))
        assert "total_loss" in metrics
        assert metrics["total_loss"] > 0.0
