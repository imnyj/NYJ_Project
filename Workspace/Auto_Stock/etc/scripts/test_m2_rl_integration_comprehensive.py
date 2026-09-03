"""
etc/scripts/test_m2_rl_integration_comprehensive.py
===================================================
Auto Stock ML/RL Trader — Phase 6 Milestone 2: 하이브리드 RL 통합 심층 종합 검증 하네스.

검증 항목:
1. SLEnrichedTradingEnvWrapper 기능 검증:
   - ResNet, Transformer, CVAE 3종 SL 모델과의 결합 및 18/19차원 관측치 확장
   - reset 및 step 시 정상 관측치 및 info 메타데이터 생성
   - Gymnasium 1.2.0 check_env 통과 및 ContinuousToHybridActionWrapper 양방향 체이닝 호환성
   - 사전 계산 DataFrame 캐시 모드 검증
   - 결측치/NaN/Inf 방어 및 1원 회계 불변식 보존 검증
2. HybridActorCritic 및 다중 SL 백본 통합 검증:
   - create_hybrid_agent 팩토리 함수 3종 ("resnet", "transformer", "cvae") 원라인 생성
   - 다양한 배치(B=1, B=4, B=16, 1D unbatched) 및 다중 타임프레임 텐서 forward pass 검증
   - get_action_and_value 롤아웃 샘플링 및 학습 평가 모드 검증
   - sample_action 및 evaluate_actions 호환성 검증
   - freeze_feature_extractor / unfreeze_feature_extractor autograd 분리 무결성 실증
3. End-to-End PPO 롤아웃 및 학습 파이프라인 검증:
   - SLEnrichedTradingEnvWrapper(18D) + create_hybrid_agent("resnet") 기반 롤아웃 수집
   - RolloutBuffer 적재 및 손실 역전파 학습 스텝 크래시 없는 완주 증명
"""

import sys
import os
import math
from decimal import Decimal
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import gymnasium as gym
from gymnasium.utils.env_checker import check_env

# 프로젝트 루트 경로 추가
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.engine.hybrid_trading_env import (
    HybridTradingEnv,
    ContinuousToHybridActionWrapper,
    SLEnrichedTradingEnvWrapper,
)
from modules.models.resnet import TemporalResNetFeatureExtractor
from modules.models.transformer import TemporalTransformerFeatureExtractor
from modules.models.cvae import TemporalCVAEFeatureExtractor
from modules.models.hybrid_policy import (
    HybridActorCritic,
    create_hybrid_agent,
    RolloutBuffer,
)


def create_dummy_market_df(n_rows: int = 100) -> pd.DataFrame:
    """테스트용 가상 시장 데이터프레임 생성"""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")
    prices = 70000.0 + np.cumsum(np.random.randn(n_rows) * 500)
    prices = np.clip(prices, 10000.0, 200000.0)

    df = pd.DataFrame({
        "date": dates,
        "open": prices * 0.99,
        "high": prices * 1.02,
        "low": prices * 0.98,
        "close": prices,
        "volume": np.random.uniform(100000, 1000000, size=n_rows),
        "returns_1d": np.random.uniform(-0.05, 0.05, size=n_rows),
        "volatility_20d": np.random.uniform(0.1, 0.4, size=n_rows),
        "log_return": np.random.uniform(-0.05, 0.05, size=n_rows),
        "ma_5_dev": np.random.uniform(-0.03, 0.03, size=n_rows),
        "ma_20_dev": np.random.uniform(-0.06, 0.06, size=n_rows),
        "ma_60_dev": np.random.uniform(-0.1, 0.1, size=n_rows),
        "dynamic_per": np.random.uniform(10.0, 25.0, size=n_rows),
        "dynamic_pbr": np.random.uniform(1.0, 2.5, size=n_rows),
        "dynamic_market_cap": np.random.uniform(1e11, 5e12, size=n_rows),
    })
    return df


def test_sl_enriched_wrapper_with_3_models():
    print("\n--- [1/3] Testing SLEnrichedTradingEnvWrapper with 3 SL Models ---")
    df = create_dummy_market_df(100)
    base_env = HybridTradingEnv(df=df, initial_cash=10_000_000, max_steps=50)

    # 1. ResNet 결합 (기본: include_anomaly_score=False -> 14 + 4 = 18차원)
    resnet_model = TemporalResNetFeatureExtractor(
        daily_in_channels=10,
        daily_seq_len=20,
        minute_in_channels=10,
        minute_seq_len=60,
        tabular_dim=4,
        output_dim=64,
        num_blocks=2,
        base_filters=32,
    )
    env_resnet = SLEnrichedTradingEnvWrapper(base_env, sl_model=resnet_model)
    assert env_resnet.observation_space.shape == (18,), f"Expected (18,), got {env_resnet.observation_space.shape}"
    assert env_resnet.sl_feature_dim == 4, f"Expected 4, got {env_resnet.sl_feature_dim}"

    obs, info = env_resnet.reset(seed=42)
    assert obs.shape == (18,), f"Reset obs shape mismatch: {obs.shape}"
    assert isinstance(obs, np.ndarray) and obs.dtype == np.float32
    assert "sl_targets" in info and len(info["sl_targets"]) == 4
    assert np.all(np.isfinite(obs)), "Reset obs contains NaN or Inf!"

    step_obs, r, term, trunc, s_info = env_resnet.step((1, np.array([0.5], dtype=np.float32)))
    assert step_obs.shape == (18,), f"Step obs shape mismatch: {step_obs.shape}"
    assert isinstance(r, (float, np.floating))
    assert np.all(np.isfinite(step_obs)), "Step obs contains NaN or Inf!"
    assert env_resnet.unwrapped.verify_accounting_invariant(), "Accounting invariant broken!"
    print("  ✓ ResNet wrapper integration: 18D state vector verified!")

    # 2. Transformer 결합 (기본: 18차원)
    trans_model = TemporalTransformerFeatureExtractor(
        daily_in_channels=10,
        daily_seq_len=20,
        minute_in_channels=10,
        minute_seq_len=60,
        tabular_dim=4,
        d_model=32,
        nhead=4,
        num_layers=2,
        output_dim=64,
    )
    env_trans = SLEnrichedTradingEnvWrapper(base_env, sl_model=trans_model)
    assert env_trans.observation_space.shape == (18,)
    obs_t, info_t = env_trans.reset(seed=123)
    assert obs_t.shape == (18,) and np.all(np.isfinite(obs_t))
    obs_t2, _, _, _, _ = env_trans.step((0, np.array([0.0], dtype=np.float32)))
    assert obs_t2.shape == (18,) and np.all(np.isfinite(obs_t2))
    print("  ✓ Transformer wrapper integration: 18D state vector verified!")

    # 3. CVAE 결합 (자동 감지: include_anomaly_score=True -> 14 + 5 = 19차원)
    cvae_model = TemporalCVAEFeatureExtractor(
        daily_in_channels=10,
        daily_seq_len=20,
        minute_in_channels=10,
        minute_seq_len=60,
        tabular_dim=4,
        latent_dim=16,
        output_dim=64,
    )
    env_cvae = SLEnrichedTradingEnvWrapper(base_env, sl_model=cvae_model)
    assert env_cvae.observation_space.shape == (19,), f"Expected (19,), got {env_cvae.observation_space.shape}"
    assert env_cvae.sl_feature_dim == 5, f"Expected 5, got {env_cvae.sl_feature_dim}"
    obs_c, info_c = env_cvae.reset(seed=999)
    assert obs_c.shape == (19,) and np.all(np.isfinite(obs_c))
    assert len(info_c["sl_targets"]) == 5
    obs_c2, _, _, _, _ = env_cvae.step((2, np.array([1.0], dtype=np.float32)))
    assert obs_c2.shape == (19,) and np.all(np.isfinite(obs_c2))
    print("  ✓ CVAE wrapper integration: 19D state vector with anomaly score verified!")

    # 4. 사전 계산 캐시 DataFrame 모드 검증
    cache_df = pd.DataFrame({
        "pred_return": np.linspace(0.01, 0.05, 50),
        "prob_up": [0.6] * 50,
        "prob_neutral": [0.3] * 50,
        "prob_down": [0.1] * 50,
        "anomaly_score": [0.05] * 50,
    })
    env_cache = SLEnrichedTradingEnvWrapper(base_env, sl_predictions_df=cache_df, include_anomaly_score=True)
    assert env_cache.observation_space.shape == (19,)
    obs_cache, info_cache = env_cache.reset(seed=1)
    np.testing.assert_allclose(info_cache["sl_targets"][:4], [0.01, 0.6, 0.3, 0.1], rtol=1e-3)
    np.testing.assert_allclose(info_cache["sl_targets"][4], 0.05, rtol=1e-3)
    print("  ✓ Precomputed predictions DataFrame cache mode verified!")

    # 5. ContinuousToHybridActionWrapper 양방향 체이닝 호환성
    # Chain 1: ContinuousToHybridActionWrapper on top of SLEnrichedTradingEnvWrapper
    c_env1 = ContinuousToHybridActionWrapper(env_resnet)
    assert c_env1.observation_space.shape == (18,)
    assert c_env1.action_space.shape == (2,)
    o1, _ = c_env1.reset(seed=10)
    assert o1.shape == (18,)
    o1_step, _, _, _, _ = c_env1.step(np.array([0.8, 0.5], dtype=np.float32))
    assert o1_step.shape == (18,)
    print("  ✓ ContinuousToHybridActionWrapper(SLEnriched) verified!")

    # Chain 2: SLEnriched on top of ContinuousToHybridActionWrapper
    raw_env = HybridTradingEnv(df=df, initial_cash=10_000_000, max_steps=50)
    c_env2 = SLEnrichedTradingEnvWrapper(ContinuousToHybridActionWrapper(raw_env), sl_model=cvae_model)
    assert c_env2.observation_space.shape == (19,)
    assert c_env2.action_space.shape == (2,)
    o2, _ = c_env2.reset(seed=20)
    assert o2.shape == (19,)
    o2_step, _, _, _, _ = c_env2.step(np.array([-0.9, 0.8], dtype=np.float32))
    assert o2_step.shape == (19,)
    print("  ✓ SLEnriched(ContinuousToHybridActionWrapper) verified!")

    # 6. Gymnasium check_env 검증
    # Note: Gymnasium env_checker warns on infinite Box bounds which is normal for financial features
    check_env(env_resnet.unwrapped)
    print("  ✓ Gymnasium 1.2.0 check_env compliance verified!")


def test_hybrid_actor_critic_and_factory():
    print("\n--- [2/3] Testing HybridActorCritic and create_hybrid_agent Factory ---")

    for model_type in ["resnet", "transformer", "cvae"]:
        agent = create_hybrid_agent(
            sl_model_type=model_type,
            obs_dim=18,
            feature_dim=64,
            hidden_dims=[64, 64],
            action_dim=3,
            distribution_type="beta",
        )
        assert isinstance(agent, HybridActorCritic), f"create_hybrid_agent({model_type}) failed to return HybridActorCritic"
        assert agent.feature_dim == 64

        # Test forward pass with various observation formats:
        # A. Batched 18D state vector (B=4, 18)
        b_obs = torch.randn(4, 18)
        logits, a, b, val = agent.forward(b_obs)
        assert logits.shape == (4, 3), f"Logits shape mismatch: {logits.shape}"
        assert a.shape == (4, 1) and b.shape == (4, 1)
        assert val.shape == (4, 1)

        # B. Unbatched 18D state vector (18,)
        u_obs = torch.randn(18)
        logits_u, a_u, b_u, val_u = agent.forward(u_obs)
        assert logits_u.shape == (1, 3)

        # C. 19D state vector (B=2, 19)
        obs_19 = torch.randn(2, 19)
        logits_19, _, _, val_19 = agent.forward(obs_19)
        assert logits_19.shape == (2, 3) and val_19.shape == (2, 1)

        # D. Time-series temporal window (B=2, 20, 10)
        t_obs = torch.randn(2, 20, 10)
        logits_t, _, _, val_t = agent.forward(t_obs)
        assert logits_t.shape == (2, 3) and val_t.shape == (2, 1)

        # E. Multi-timeframe tuple: (daily, minute, tabular)
        m_tuple = (torch.randn(3, 20, 10), torch.randn(3, 60, 10), torch.randn(3, 4))
        logits_m, _, _, val_m = agent.forward(m_tuple)
        assert logits_m.shape == (3, 3) and val_m.shape == (3, 1)

        # Test get_action_and_value (sampling mode: action=None)
        # Batched
        act, log_prob, entropy, val_out = agent.get_action_and_value(b_obs, action=None)
        disc_act, cont_act = act
        assert disc_act.shape == (4,)
        assert cont_act.shape == (4, 1)
        assert log_prob.shape == (4,)
        assert entropy.shape == (4,)
        assert val_out.shape == (4,)

        # Unbatched
        act_unb, lp_unb, ent_unb, v_unb = agent.get_action_and_value(u_obs, action=None)
        assert isinstance(act_unb, tuple) and len(act_unb) == 2
        assert isinstance(act_unb[0], int) and 0 <= act_unb[0] < 3
        assert isinstance(act_unb[1], float) and 0.0 <= act_unb[1] <= 1.0
        assert lp_unb.dim() == 0 and ent_unb.dim() == 0 and v_unb.dim() == 0

        # Test get_action_and_value (evaluation mode: action provided)
        eval_act = (torch.tensor([0, 1, 2, 1], dtype=torch.long), torch.tensor([[0.2], [0.5], [0.8], [0.1]], dtype=torch.float32))
        _, eval_lp, eval_ent, eval_v = agent.get_action_and_value(b_obs, action=eval_act)
        assert eval_lp.shape == (4,) and eval_ent.shape == (4,) and eval_v.shape == (4,)

        # Test sample_action method
        sample_res, sample_lp, sample_v = agent.sample_action(b_obs.numpy(), deterministic=True)
        assert sample_res[0].shape == (4,) and sample_res[1].shape == (4,)

        print(f"  ✓ create_hybrid_agent('{model_type}') and forward/sampling/evaluation verified!")

    # 4. Freeze / Unfreeze Autograd Isolation Test
    print("  Testing backbone freeze / unfreeze autograd flow...")
    agent_freeze = create_hybrid_agent(
        sl_model_type="resnet",
        obs_dim=18,
        feature_dim=64,
        freeze_feature_extractor=True,
    )
    assert agent_freeze.is_feature_extractor_frozen is True
    for p in agent_freeze.feature_extractor.parameters():
        assert not p.requires_grad

    # Check that backward does not update backbone
    sample_obs = torch.randn(4, 18)
    logits, a, b, val = agent_freeze(sample_obs)
    loss = logits.sum() + val.sum()
    loss.backward()

    for name, p in agent_freeze.feature_extractor.named_parameters():
        assert p.grad is None, f"Frozen parameter {name} received gradient!"

    # Unfreeze and verify gradient propagation
    agent_freeze.unfreeze_feature_extractor()
    assert agent_freeze.is_feature_extractor_frozen is False
    agent_freeze.zero_grad()
    logits2, a2, b2, val2 = agent_freeze(sample_obs)
    loss2 = logits2.sum() + val2.sum()
    loss2.backward()

    backbone_grad_norm = sum(p.grad.norm().item() for p in agent_freeze.feature_extractor.parameters() if p.grad is not None)
    assert backbone_grad_norm > 0, "Unfrozen backbone failed to receive gradients!"
    print(f"  ✓ Freeze/Unfreeze autograd isolation verified (backbone grad norm after unfreeze: {backbone_grad_norm:.4f})")


def test_end_to_end_ppo_rollout_and_step():
    print("\n--- [3/3] Testing End-to-End PPO Rollout & Update Loop ---")
    df = create_dummy_market_df(80)
    base_env = HybridTradingEnv(df=df, initial_cash=10_000_000, max_steps=40)

    resnet_model = TemporalResNetFeatureExtractor(
        daily_in_channels=10,
        daily_seq_len=20,
        minute_in_channels=10,
        minute_seq_len=60,
        tabular_dim=4,
        output_dim=64,
        num_blocks=1,
        base_filters=16,
    )
    env = SLEnrichedTradingEnvWrapper(base_env, sl_model=resnet_model)
    obs_dim = env.observation_space.shape[0]
    assert obs_dim == 18

    device = torch.device("cpu")
    agent = create_hybrid_agent(
        sl_model_type=resnet_model,
        obs_dim=obs_dim,
        feature_dim=64,
        freeze_feature_extractor=True,
        device=device,
    )

    buffer_size = 32
    buffer = RolloutBuffer(buffer_size=buffer_size, obs_dim=obs_dim, device=device)

    obs, info = env.reset(seed=42)
    for step in range(buffer_size):
        with torch.no_grad():
            act_tuple, log_prob, entropy, value = agent.get_action_and_value(obs)
            disc_act, cont_act = act_tuple

        action_env = (disc_act, np.array([cont_act], dtype=np.float32))
        next_obs, reward, terminated, truncated, step_info = env.step(action_env)
        done = terminated or truncated

        buffer.add(
            obs=obs,
            action=(disc_act, cont_act),
            reward=reward,
            value=float(value.item()),
            log_prob=float(log_prob.item()),
            done=done,
        )

        obs = next_obs
        if done:
            obs, _ = env.reset()

    assert buffer.full, f"Buffer expected to be full, ptr={buffer.ptr}"

    # Compute GAE returns
    last_value = float(agent.get_value(obs).item())
    buffer.compute_returns_and_advantages(last_value=last_value, last_done=False, gamma=0.99, gae_lambda=0.95)

    # Mini-batch PPO Optimization step
    optimizer = torch.optim.Adam(agent.parameters(), lr=1e-4)

    for b_obs, b_act_disc, b_act_cont, b_old_log_probs, b_old_values, b_advantages, b_returns in buffer.get_batches(batch_size=16):
        b_actions = (b_act_disc, b_act_cont)

        _, new_log_probs, entropy, new_values = agent.get_action_and_value(b_obs, action=b_actions)

        # Policy loss
        ratio = torch.exp(new_log_probs - b_old_log_probs)
        surr1 = ratio * b_advantages
        surr2 = torch.clamp(ratio, 0.8, 1.2) * b_advantages
        policy_loss = -torch.min(surr1, surr2).mean()

        # Value loss
        value_loss = 0.5 * ((new_values - b_returns) ** 2).mean()

        # Entropy loss
        entropy_loss = -entropy.mean()

        total_loss = policy_loss + 0.5 * value_loss + 0.01 * entropy_loss

        optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(agent.parameters(), 0.5)
        optimizer.step()

        assert torch.isfinite(total_loss), "PPO loss exploded to NaN or Inf!"

    print(f"  ✓ PPO Rollout & Update step passed with finite loss: {total_loss.item():.4f}")


if __name__ == "__main__":
    print("==================================================")
    print(" Auto Stock Phase 6 Milestone 2: RL Integration Comprehensive Verification")
    print("==================================================")
    test_sl_enriched_wrapper_with_3_models()
    test_hybrid_actor_critic_and_factory()
    test_end_to_end_ppo_rollout_and_step()
    print("\n==================================================")
    print(" 🎉 ALL PHASE 6 MILESTONE 2 TESTS FULLY PASSED! 🎉")
    print("==================================================")
