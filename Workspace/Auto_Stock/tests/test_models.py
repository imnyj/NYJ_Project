"""
tests/test_models.py
====================
Milestone 2 단위 및 통합 테스트 스위트:
1. Supervised Learning Feature Extractors (TabularMLP, Temporal1DCNN, DualStream, SLPretrainer)
2. Hybrid RL Policies & PPO Agent (HybridActorCritic, HybridPPO, RolloutBuffer)
3. Stable-Baselines3 Compatibility & Integration (SB3CustomFeaturesExtractor, SB3HybridPolicyAdapter)
"""

import os
import tempfile
import numpy as np
import pytest
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from modules.engine.hybrid_trading_env import (
    ContinuousToHybridActionWrapper,
    HybridTradingEnv,
)
from modules.models.feature_extractor import (
    DualStreamSLFeatureExtractor,
    SLPretrainer,
    TabularMLPFeatureExtractor,
    Temporal1DCNNFeatureExtractor,
    get_activation_fn,
)
from modules.models.hybrid_policy import (
    HybridActorCritic,
    HybridPPO,
    RolloutBuffer,
    SB3CustomFeaturesExtractor,
    SB3HybridPolicyAdapter,
)


# ============================================================================
# Tier 1: SL Feature Extractor Tests
# ============================================================================

class TestSLFeatureExtractors:
    """지도학습 특징 추출기 단위 테스트"""

    def test_activation_function_factory(self):
        """지원되는 모든 활성화 함수 팩토리 테스트"""
        for act in ["relu", "gelu", "tanh", "elu", "leaky_relu", "silu", "swish"]:
            fn = get_activation_fn(act)
            assert isinstance(fn, nn.Module)

        with pytest.raises(ValueError, match="지원하지 않는 활성화 함수"):
            get_activation_fn("unsupported_act_123")

    def test_tabular_mlp_forward_backward_and_residuals(self):
        """TabularMLPFeatureExtractor 순전파, 역전파 및 잔차 연결 검증"""
        input_dim = 14
        output_dim = 64
        batch_size = 16

        # Standard MLP
        mlp = TabularMLPFeatureExtractor(
            input_dim=input_dim,
            hidden_dims=[128, 64],
            output_dim=output_dim,
            activation="gelu",
            dropout=0.1,
            use_layer_norm=True,
            use_residual=True,
        )

        # 2D Batched Tensor
        x = torch.randn(batch_size, input_dim, requires_grad=True)
        out = mlp(x)
        assert out.shape == (batch_size, output_dim)
        loss = out.sum()
        loss.backward()
        assert x.grad is not None
        assert not torch.isnan(x.grad).any()

        # 1D Unbatched Tensor
        x_unb = torch.randn(input_dim)
        out_unb = mlp(x_unb)
        assert out_unb.shape == (output_dim,)

        # NumPy input
        x_np = np.random.randn(batch_size, input_dim).astype(np.float32)
        out_np = mlp(x_np)
        assert out_np.shape == (batch_size, output_dim)

        # NaN & Inf Resilience
        x_nan = torch.tensor([[float('nan'), float('inf'), -float('inf')] + [0.0] * 11])
        out_nan = mlp(x_nan)
        assert not torch.isnan(out_nan).any()
        assert not torch.isinf(out_nan).any()

    def test_temporal_1dcnn_various_shapes_and_pooling(self):
        """Temporal1DCNNFeatureExtractor 다양한 입력 형상 및 풀링 방식 검증"""
        in_channels = 10
        seq_len = 20
        output_dim = 48
        batch_size = 8

        for pooling in ["adaptive_avg", "adaptive_max", "flatten"]:
            cnn = Temporal1DCNNFeatureExtractor(
                in_channels=in_channels,
                seq_len=seq_len,
                num_filters=[32, 64],
                kernel_sizes=[3, 3],
                output_dim=output_dim,
                dropout=0.1,
                pooling=pooling,
            )

            # Shape 1: (B, seq_len, in_channels)
            x1 = torch.randn(batch_size, seq_len, in_channels, requires_grad=True)
            out1 = cnn(x1)
            assert out1.shape == (batch_size, output_dim)
            out1.sum().backward()
            assert x1.grad is not None

            # Shape 2: (B, in_channels, seq_len)
            x2 = torch.randn(batch_size, in_channels, seq_len)
            out2 = cnn(x2)
            assert out2.shape == (batch_size, output_dim)

            # Shape 3: Single time step (B, in_channels)
            x3 = torch.randn(batch_size, in_channels)
            out3 = cnn(x3)
            assert out3.shape == (batch_size, output_dim)

            # Shape 4: Unbatched (seq_len, in_channels)
            x4 = torch.randn(seq_len, in_channels)
            out4 = cnn(x4)
            assert out4.shape == (output_dim,)

    def test_dual_stream_sl_feature_extractor_fusion(self):
        """DualStreamSLFeatureExtractor 멀티모달 퓨전 검증"""
        temp_c = 10
        seq_l = 20
        tab_dim = 4
        out_dim = 64
        b_size = 8

        dual = DualStreamSLFeatureExtractor(
            temporal_in_channels=temp_c,
            temporal_seq_len=seq_l,
            tabular_dim=tab_dim,
            output_dim=out_dim,
        )

        # 1. Dual stream explicit inputs
        t_x = torch.randn(b_size, seq_l, temp_c)
        tab_x = torch.randn(b_size, tab_dim)
        out_dual = dual(temporal_x=t_x, tabular_x=tab_x)
        assert out_dual.shape == (b_size, out_dim)

        # 2. Dictionary input
        dict_inp = {"temporal": t_x, "tabular": tab_x}
        out_dict = dual(x=dict_inp)
        assert out_dict.shape == (b_size, out_dim)

        # 3. Tuple input
        tuple_inp = (t_x, tab_x)
        out_tuple = dual(x=tuple_inp)
        assert out_tuple.shape == (b_size, out_dim)

        # 4. Flat observation input (B, temp_c + tab_dim)
        flat_inp = torch.randn(b_size, temp_c + tab_dim)
        out_flat = dual(x=flat_inp)
        assert out_flat.shape == (b_size, out_dim)

        # 5. Unbatched flat obs
        unb_flat = torch.randn(temp_c + tab_dim)
        out_unb = dual(x=unb_flat)
        assert out_unb.shape == (out_dim,)

    def test_sl_pretrainer_multitask_training_and_serialization(self):
        """SLPretrainer 멀티태스크 학습, 손실 감소, 평가 및 저장/로드 검증"""
        dual = DualStreamSLFeatureExtractor(
            temporal_in_channels=10,
            temporal_seq_len=20,
            tabular_dim=4,
            output_dim=64,
        )
        pretrainer = SLPretrainer(
            backbone=dual,
            feature_dim=64,
            num_classes=3,
            task_weight_cls=1.0,
            task_weight_reg=1.0,
            regression_loss_type="smooth_l1",
            lr=1e-3,
        )

        n_samples = 64
        t_data = torch.randn(n_samples, 20, 10)
        tab_data = torch.randn(n_samples, 4)
        target_ret = torch.randn(n_samples, 1) * 0.02
        target_dir = torch.randint(0, 3, (n_samples,))

        # Train 3 epochs
        history = pretrainer.fit(
            train_data=(t_data, tab_data, target_ret, target_dir),
            val_data=(t_data[:16], tab_data[:16], target_ret[:16], target_dir[:16]),
            epochs=3,
            batch_size=16,
        )

        assert len(history["train_total_loss"]) == 3
        assert len(history["val_total_loss"]) == 3
        assert history["train_total_loss"][-1] >= 0.0

        # Evaluate
        eval_metrics = pretrainer.evaluate((t_data[:16], tab_data[:16], target_ret[:16], target_dir[:16]))
        assert "total_loss" in eval_metrics
        assert "accuracy" in eval_metrics
        assert 0.0 <= eval_metrics["accuracy"] <= 1.0

        # Save & Load Checkpoint
        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            pretrainer.save_pretrained(tmp_path)
            assert os.path.exists(tmp_path)

            new_pretrainer = SLPretrainer(feature_dim=64)
            new_pretrainer.load_pretrained(tmp_path)

            # Compare predictions in eval mode (disabling dropout)
            pretrainer.eval()
            new_pretrainer.eval()
            with torch.no_grad():
                pred1_r, pred1_d = pretrainer(temporal_x=t_data[:4], tabular_x=tab_data[:4])
                pred2_r, pred2_d = new_pretrainer(temporal_x=t_data[:4], tabular_x=tab_data[:4])
            torch.testing.assert_close(pred1_r, pred2_r)
            torch.testing.assert_close(pred1_d, pred2_d)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


# ============================================================================
# Tier 2: Hybrid RL Policy & Agent Tests
# ============================================================================

class TestHybridActorCriticAndPolicy:
    """하이브리드 액션 정책 및 가치망 단위 테스트"""

    def test_hybrid_actor_critic_beta_distribution(self):
        """Beta 분포 기반 HybridActorCritic 샘플링 및 log_prob 검증"""
        policy = HybridActorCritic(obs_dim=14, feature_dim=64, distribution_type="beta")
        obs = np.random.randn(14).astype(np.float32)

        # 1. Stochastic sampling (unbatched)
        action, log_prob, value = policy.sample_action(obs, deterministic=False)
        act_type, weight = action
        assert act_type in (0, 1, 2)
        assert 0.0 <= weight <= 1.0
        assert isinstance(log_prob, torch.Tensor)
        assert isinstance(value, torch.Tensor)
        assert not torch.isnan(log_prob)
        assert not torch.isnan(value)

        # 2. Deterministic sampling (unbatched)
        action_det, _, _ = policy.sample_action(obs, deterministic=True)
        act_type_det, weight_det = action_det
        assert act_type_det in (0, 1, 2)
        assert 0.0 <= weight_det <= 1.0

        # 3. Batched sampling
        obs_batch = np.random.randn(8, 14).astype(np.float32)
        (act_types, weights), log_probs, values = policy.sample_action(obs_batch, deterministic=False)
        assert len(act_types) == 8
        assert len(weights) == 8
        assert log_probs.shape == (8,)
        assert values.shape == (8,)

    def test_hybrid_actor_critic_gaussian_distribution(self):
        """Gaussian 분포 기반 HybridActorCritic 샘플링 및 log_prob 검증"""
        policy = HybridActorCritic(obs_dim=14, feature_dim=64, distribution_type="gaussian")
        obs = np.random.randn(14).astype(np.float32)

        action, log_prob, value = policy.sample_action(obs, deterministic=False)
        act_type, weight = action
        assert act_type in (0, 1, 2)
        assert 0.0 <= weight <= 1.0

    def test_hybrid_actor_critic_evaluate_actions_and_entropy(self):
        """PPO 손실 계산용 evaluate_actions 무결성 검증"""
        policy = HybridActorCritic(obs_dim=14, feature_dim=64, distribution_type="beta")
        batch_size = 16

        obs = torch.randn(batch_size, 14)
        act_disc = torch.randint(0, 3, (batch_size,))
        act_cont = torch.rand(batch_size, 1)

        log_prob, entropy, value = policy.evaluate_actions(obs, (act_disc, act_cont))

        assert log_prob.shape == (batch_size,)
        assert entropy.shape == (batch_size,)
        assert value.shape == (batch_size,)

        # Log prob and entropy should be non-NaN
        assert not torch.isnan(log_prob).any()
        assert not torch.isnan(entropy).any()
        assert not torch.isnan(value).any()

        # Differentiability check
        loss = -log_prob.mean() - 0.01 * entropy.mean() + value.mean()
        loss.backward()

        for name, param in policy.named_parameters():
            if param.requires_grad:
                assert param.grad is not None, f"Gradient missing for {name}"

    def test_sl_to_rl_weight_transfer_and_freezing(self):
        """사전학습된 SL 가중치의 RL 정책망 전이 및 Freeze/Unfreeze 검증"""
        dual = DualStreamSLFeatureExtractor(output_dim=64)
        pretrainer = SLPretrainer(backbone=dual, feature_dim=64)

        # Train a bit to have distinct weights
        pretrainer.fit(
            train_data=(torch.randn(16, 20, 10), torch.randn(16, 4), torch.randn(16, 1), torch.randint(0, 3, (16,))),
            epochs=1,
            batch_size=8,
        )

        rl_policy = HybridActorCritic(obs_dim=14, feature_dim=64)
        rl_policy.load_from_sl_pretrainer(pretrainer, freeze=True)

        # Verify frozen parameters
        for param in rl_policy.feature_extractor.parameters():
            assert not param.requires_grad

        # Unfreeze
        rl_policy.unfreeze_backbone()
        for param in rl_policy.feature_extractor.parameters():
            assert param.requires_grad


class TestHybridPPOAgent:
    """하이브리드 PPO 에이전트 학습 및 평가 테스트"""

    def test_rollout_buffer_gae_computation(self):
        """RolloutBuffer GAE 및 어드밴티지 계산 검증"""
        buf_size = 32
        obs_dim = 14
        device = torch.device("cpu")
        buffer = RolloutBuffer(buffer_size=buf_size, obs_dim=obs_dim, device=device)

        for i in range(buf_size):
            buffer.add(
                obs=np.random.randn(obs_dim).astype(np.float32),
                action=(np.random.randint(0, 3), float(np.random.rand())),
                reward=float(np.random.randn() * 0.01),
                value=float(np.random.randn()),
                log_prob=float(-np.random.rand()),
                done=(i == buf_size - 1),
            )

        assert buffer.full
        buffer.compute_returns_and_advantages(last_value=0.0, last_done=True, gamma=0.99, gae_lambda=0.95)

        assert not np.isnan(buffer.advantages).any()
        assert not np.isnan(buffer.returns).any()

        # Check mini-batches
        batch_count = 0
        for obs_b, act_d_b, act_c_b, log_p_b, val_b, adv_b, ret_b in buffer.get_batches(batch_size=8):
            assert obs_b.shape == (8, obs_dim)
            assert act_d_b.shape == (8,)
            assert act_c_b.shape == (8,)
            assert log_p_b.shape == (8,)
            assert val_b.shape == (8,)
            assert adv_b.shape == (8,)
            assert ret_b.shape == (8,)
            batch_count += 1
        assert batch_count == 4

    def test_hybrid_ppo_training_loop_and_convergence(self):
        """HybridPPO 학습 루프(Rollout 수집 -> GAE -> PPO Update) 실행 검증"""
        env = HybridTradingEnv()
        ppo = HybridPPO(
            env=env,
            learning_rate=1e-3,
            n_steps=32,
            batch_size=16,
            n_epochs=2,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,
            vf_coef=0.5,
        )

        # Train for 64 steps (2 rollout cycles)
        ppo.learn(total_timesteps=64)

        # Prediction test
        obs, _ = env.reset()
        action, state = ppo.predict(obs, deterministic=True)
        assert action[0] in (0, 1, 2)
        assert 0.0 <= action[1] <= 1.0
        assert state is None

        # Evaluation test
        eval_metrics = ppo.evaluate(env=env, n_episodes=2, deterministic=True)
        assert "mean_reward" in eval_metrics
        assert "mean_final_equity" in eval_metrics
        assert eval_metrics["mean_final_equity"] > 0.0

    def test_hybrid_ppo_save_and_load(self):
        """HybridPPO 모델 직렬화 및 복원 검증"""
        env = HybridTradingEnv()
        ppo1 = HybridPPO(env=env, learning_rate=5e-4, n_steps=32)
        ppo1.learn(total_timesteps=32)

        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            ppo1.save(tmp_path)
            assert os.path.exists(tmp_path)

            ppo2 = HybridPPO(env=env)
            ppo2.load(tmp_path)

            obs, _ = env.reset()
            act1, _ = ppo1.predict(obs, deterministic=True)
            act2, _ = ppo2.predict(obs, deterministic=True)
            assert act1[0] == act2[0]
            np.testing.assert_almost_equal(act1[1], act2[1], decimal=4)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


# ============================================================================
# Tier 3: SB3 Integration & Adapter Tests
# ============================================================================

class TestSB3HybridAdapter:
    """Stable-Baselines3 호환성 및 어댑터 통합 테스트"""

    def test_sb3_custom_features_extractor_forward(self):
        """SB3CustomFeaturesExtractor의 SB3 내장 정책 순전파 검증"""
        env = ContinuousToHybridActionWrapper(HybridTradingEnv())
        extractor = SB3CustomFeaturesExtractor(
            observation_space=env.observation_space,
            features_dim=64,
        )
        obs = torch.randn(8, env.observation_space.shape[0])
        out = extractor(obs)
        assert out.shape == (8, 64)

    def test_sb3_hybrid_adapter_train_and_predict(self):
        """SB3HybridPolicyAdapter PPO 생성, 학습 및 하이브리드 액션 디코딩 검증"""
        env = HybridTradingEnv()
        model = SB3HybridPolicyAdapter.create_sb3_ppo(
            env=env,
            features_dim=32,
            n_steps=32,
            batch_size=16,
            learning_rate=3e-4,
        )

        # Train agent
        SB3HybridPolicyAdapter.train_sb3_agent(model, total_timesteps=64)

        # Test predict_hybrid
        obs, _ = env.reset()
        hybrid_act, raw_act = SB3HybridPolicyAdapter.predict_hybrid(model, obs, deterministic=True)

        assert hybrid_act[0] in (0, 1, 2)
        assert 0.0 <= hybrid_act[1] <= 1.0
        assert len(raw_act) == 2


# ============================================================================
# Tier 4: Edge Cases & Deep Hardening Tests
# ============================================================================

class TestModelsDeepHardeningAndEdgeCases:
    """경계값, 예외 처리 및 추가 커버리지 심층 검증"""

    def test_feature_extractor_exceptions_and_edge_paths(self):
        """특징 추출기 예외 및 경계 조건 검증"""
        # 1. Kernel size mismatch error
        with pytest.raises(ValueError, match="길이는 동일해야"):
            Temporal1DCNNFeatureExtractor(num_filters=[32, 64], kernel_sizes=[3])

        # 2. Unsupported pooling error
        with pytest.raises(ValueError, match="지원하지 않는 풀링"):
            Temporal1DCNNFeatureExtractor(pooling="unsupported_pool")

        # 3. BatchNorm option
        cnn_bn = Temporal1DCNNFeatureExtractor(norm_type="batch_norm")
        assert isinstance(cnn_bn, Temporal1DCNNFeatureExtractor)

        # 4. Custom feature extractors passed to DualStream
        custom_temp = Temporal1DCNNFeatureExtractor(in_channels=10, output_dim=32)
        custom_tab = TabularMLPFeatureExtractor(input_dim=4, output_dim=16)
        dual_custom = DualStreamSLFeatureExtractor(
            temporal_extractor=custom_temp,
            tabular_extractor=custom_tab,
            output_dim=48,
        )
        out_custom = dual_custom(torch.randn(4, 20, 10), torch.randn(4, 4))
        assert out_custom.shape == (4, 48)

    def test_sl_pretrainer_mse_and_dict_and_tuple_batch(self):
        """SLPretrainer MSE 손실, Dict 배치 및 3-튜플 배치 처리 검증"""
        pretrainer_mse = SLPretrainer(
            feature_dim=32,
            regression_loss_type="mse",
        )

        # 3-tuple batch (flat_x, target_return, target_direction)
        batch_3 = (torch.randn(8, 14), torch.randn(8, 1), torch.randint(0, 3, (8,)))
        res_3 = pretrainer_mse.train_step(batch_3)
        assert "total_loss" in res_3

        # Dict batch
        batch_dict = {
            "temporal": torch.randn(8, 20, 10),
            "tabular": torch.randn(8, 4),
            "target_return": torch.randn(8, 1),
            "target_direction": torch.randint(0, 3, (8,)),
        }
        res_dict = pretrainer_mse.train_step(batch_dict)
        assert "total_loss" in res_dict

        # Verbose fit
        train_ds = TensorDataset(torch.randn(16, 20, 10), torch.randn(16, 4), torch.randn(16, 1), torch.randint(0, 3, (16,)))
        train_loader = DataLoader(train_ds, batch_size=8)
        hist = pretrainer_mse.fit(train_loader, epochs=2, verbose=True)
        assert len(hist["train_total_loss"]) == 2

    def test_hybrid_policy_action_tensor_and_clip_vf_and_callbacks(self):
        """HybridActorCritic 텐서 액션 평가, VF Clipping 및 PPO 콜백 검증"""
        # 1. Invalid distribution type error
        with pytest.raises(ValueError, match="지원하지 않는 분포"):
            HybridActorCritic(distribution_type="invalid_dist")

        # 2. Evaluate actions using 2D Tensor
        policy = HybridActorCritic(obs_dim=14, feature_dim=32)
        obs = torch.randn(8, 14)
        act_tensor = torch.tensor([[1.0, 0.5]] * 8)
        log_p, ent, val = policy.evaluate_actions(obs, act_tensor)
        assert log_p.shape == (8,)

        # 3. HybridPPO with clip_range_vf and custom obs_dim
        env = HybridTradingEnv()
        callbacks_called = []
        def test_callback(local_vars, global_vars):
            callbacks_called.append(True)

        ppo_vf = HybridPPO(
            env=env,
            clip_range_vf=0.5,
            n_steps=16,
            batch_size=8,
            n_epochs=1,
        )
        ppo_vf.learn(total_timesteps=16, callback=test_callback)
        assert len(callbacks_called) >= 1

    def test_sb3_custom_extractor_loading_and_weights_sync(self):
        """SB3CustomFeaturesExtractor 가중치 로드 및 동기화 검증"""
        pretrainer = SLPretrainer(feature_dim=32)
        env = ContinuousToHybridActionWrapper(HybridTradingEnv())

        extractor = SB3CustomFeaturesExtractor(
            observation_space=env.observation_space,
            features_dim=32,
        )
        # Load from pretrainer instance
        extractor.load_pretrained_weights(pretrainer)

        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            pretrainer.save_pretrained(tmp_path)
            # Load from file path
            extractor.load_pretrained_weights(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


# ============================================================================
# Tier 5: Milestone 2 Gate Review Defect Fix & Regression Tests
# ============================================================================

class TestMilestone2GateDefectFixesAndRegression:
    """Milestone 2 게이트 리뷰 지적 결함 5종에 대한 전용 회귀 방지 테스트"""

    def test_gae_episode_boundary_isolation_and_no_leakage(self):
        """[Defect 1] GAE 계산 시 dones 인덱스 정합성 및 에피소드 경계 가치 누수 방지 검증"""
        buf = RolloutBuffer(buffer_size=4, obs_dim=2, device=torch.device("cpu"))
        buf.add(np.array([1.0, 1.0]), (0, 0.5), reward=1.0, value=10.0, log_prob=-1.0, done=False)
        buf.add(np.array([2.0, 2.0]), (1, 0.5), reward=2.0, value=20.0, log_prob=-1.0, done=True)
        buf.add(np.array([3.0, 3.0]), (2, 0.5), reward=3.0, value=30.0, log_prob=-1.0, done=False)
        buf.add(np.array([4.0, 4.0]), (0, 0.5), reward=4.0, value=40.0, log_prob=-1.0, done=False)

        # compute GAE
        buf.compute_returns_and_advantages(last_value=50.0, last_done=False, gamma=0.99, gae_lambda=0.95)

        # Step 3: delta = 4.0 + 0.99 * 50.0 * 1.0 - 40.0 = 13.5, last_gae = 13.5
        assert np.isclose(buf.advantages[3], 13.5, atol=1e-5)

        # Step 2: delta = 3.0 + 0.99 * 40.0 * 1.0 - 30.0 = 12.6, last_gae = 12.6 + 0.99 * 0.95 * 1.0 * 13.5 = 25.29675
        assert np.isclose(buf.advantages[2], 25.29675, atol=1e-5)

        # Step 1 (done=True): next_non_terminal = 0.0 -> delta = 2.0 + 0.99 * 30.0 * 0.0 - 20.0 = -18.0
        # last_gae = -18.0 + 0.0 = -18.0 (Future episode advantage MUST NOT leak into Step 1)
        assert np.isclose(buf.advantages[1], -18.0, atol=1e-5)

        # Step 0: next_non_terminal = 1.0 -> delta = 1.0 + 0.99 * 20.0 * 1.0 - 10.0 = 10.8
        # last_gae = 10.8 + 0.99 * 0.95 * 1.0 * (-18.0) = 10.8 - 16.929 = -6.129
        assert np.isclose(buf.advantages[0], -6.129, atol=1e-5)

        # Multi-episode stress test with multiple terminal boundaries
        buf_multi = RolloutBuffer(buffer_size=10, obs_dim=4, device=torch.device("cpu"))
        for i in range(10):
            buf_multi.add(
                obs=np.zeros(4, dtype=np.float32),
                action=(0, 0.5),
                reward=1.0,
                value=5.0,
                log_prob=-0.5,
                done=(i in (2, 5, 8)),
            )
        buf_multi.compute_returns_and_advantages(last_value=5.0, last_done=False, gamma=0.99, gae_lambda=0.95)
        assert not np.isnan(buf_multi.advantages).any()
        assert not np.isnan(buf_multi.returns).any()

    def test_dual_stream_batch_size_equals_seq_len_2d_tensor(self):
        """[Defect 2] 배치 크기가 seq_len(기본값 20)인 평탄화 2D 텐서 유입 시 차원 불일치 없이 정상 처리 검증"""
        seq_len = 20
        temp_channels = 10
        tab_dim = 4
        tot_dim = temp_channels + tab_dim
        out_dim = 64

        dual = DualStreamSLFeatureExtractor(
            temporal_in_channels=temp_channels,
            temporal_seq_len=seq_len,
            tabular_dim=tab_dim,
            output_dim=out_dim,
        )

        # Batch sizes equal to seq_len and multiples
        for b_size in [1, seq_len, seq_len * 2, 32]:
            x_batch = torch.randn(b_size, tot_dim)
            out = dual(x_batch)
            assert out.shape == (b_size, out_dim), f"Expected ({b_size}, {out_dim}), got {out.shape}"

            # Verify backward pass gradient flow
            loss = out.sum()
            loss.backward()

        # Direct Temporal1DCNNFeatureExtractor check with 2D tensor of B=seq_len
        cnn = Temporal1DCNNFeatureExtractor(in_channels=temp_channels, seq_len=seq_len, output_dim=32)
        # 3D batched (20, 10, 1) -> (20, 32)
        x_3d = torch.randn(20, temp_channels, 1)
        out_3d = cnn(x_3d)
        assert out_3d.shape == (20, 32)

        # Unbatched sequence (20, 10) -> (32,)
        x_unb_seq = torch.randn(seq_len, temp_channels)
        out_unb = cnn(x_unb_seq)
        assert out_unb.shape == (32,)

    def test_dual_stream_positional_arguments_and_dict_tuple_safety(self):
        """[Defect 3] DualStreamSLFeatureExtractor 단일 위치 인자(Tuple, Dict, Tensor) 전달 시 AttributeError 방어 검증"""
        temp_c = 10
        seq_l = 20
        tab_d = 4
        out_d = 64
        b_size = 4

        dual = DualStreamSLFeatureExtractor(
            temporal_in_channels=temp_c,
            temporal_seq_len=seq_l,
            tabular_dim=tab_d,
            output_dim=out_d,
        )

        t_x = torch.randn(b_size, seq_l, temp_c)
        tab_x = torch.randn(b_size, tab_d)

        # 1. Single positional tuple
        out_tup = dual((t_x, tab_x))
        assert out_tup.shape == (b_size, out_d)

        # 2. Single positional dict
        dict_obs = {"temporal": t_x, "tabular": tab_x}
        out_dict = dual(dict_obs)
        assert out_dict.shape == (b_size, out_d)

        # 3. Single positional flat 2D tensor
        flat_2d = torch.randn(b_size, temp_c + tab_d)
        out_flat = dual(flat_2d)
        assert out_flat.shape == (b_size, out_d)

        # 4. Single positional flat 1D numpy array
        flat_1d_np = np.random.randn(temp_c + tab_d).astype(np.float32)
        out_np = dual(flat_1d_np)
        assert out_np.shape == (out_d,)

    def test_hybrid_actor_critic_extract_features_polymorphism(self):
        """[Defect 4] HybridActorCritic.extract_features 다양한 관측값 포맷 및 예외 fallback 처리 검증"""
        policy = HybridActorCritic(obs_dim=14, feature_dim=64)

        # 1. Tuple obs (t_x, tab_x)
        t_x = torch.randn(4, 20, 10)
        tab_x = torch.randn(4, 4)
        feat_tup = policy.extract_features((t_x, tab_x))
        assert feat_tup.shape == (4, 64)

        # 2. Dict obs
        dict_obs = {"temporal": t_x, "tabular": tab_x}
        feat_dict = policy.extract_features(dict_obs)
        assert feat_dict.shape == (4, 64)

        # 3. 2D Tensor obs
        flat_obs = torch.randn(4, 14)
        feat_flat = policy.extract_features(flat_obs)
        assert feat_flat.shape == (4, 64)

        # 4. 1D Numpy obs
        flat_np = np.random.randn(14).astype(np.float32)
        feat_np = policy.extract_features(flat_np)
        assert feat_np.shape == (1, 64)

        # 5. Fallback check with dummy feature extractor raising ValueError/AttributeError
        class ErrorThrowingExtractor(nn.Module):
            def forward(self, *args, **kwargs):
                if len(args) == 1 and not kwargs:
                    raise AttributeError("Simulated parameter mismatch")
                return torch.zeros(4, 64)

        policy_err = HybridActorCritic(obs_dim=14, feature_dim=64, feature_extractor=ErrorThrowingExtractor())
        feat_fallback = policy_err.extract_features((t_x, tab_x))
        assert feat_fallback.shape == (4, 64)

    def test_sb3_predict_hybrid_2d_batch_and_1d_actions(self):
        """[Defect 5] SB3HybridPolicyAdapter.predict_hybrid 2D 배치 관측값 및 1D 단일 관측값 디코딩 검증"""
        env = HybridTradingEnv()
        sb3_model = SB3HybridPolicyAdapter.create_sb3_ppo(
            env=env,
            features_dim=32,
            n_steps=16,
            batch_size=8,
        )

        # 1. 1D Single observation
        obs_1d = np.random.randn(14).astype(np.float32)
        act_single, raw_single = SB3HybridPolicyAdapter.predict_hybrid(sb3_model, obs_1d, deterministic=True)
        assert isinstance(act_single, tuple)
        assert act_single[0] in (0, 1, 2)
        assert 0.0 <= act_single[1] <= 1.0
        assert raw_single.ndim == 1

        # 2. 2D Batched observation
        batch_size = 6
        obs_2d = np.random.randn(batch_size, 14).astype(np.float32)
        acts_batch, raw_batch = SB3HybridPolicyAdapter.predict_hybrid(sb3_model, obs_2d, deterministic=True)
        assert isinstance(acts_batch, list)
        assert len(acts_batch) == batch_size
        for act in acts_batch:
            assert isinstance(act, tuple)
            assert act[0] in (0, 1, 2)
            assert 0.0 <= act[1] <= 1.0
        assert raw_batch.shape == (batch_size, 2)

    def test_torch_tensor_device_auto_transfer_all_extractors_and_policy(self):
        """[BUG-RL03] PyTorch CPU Tensor가 입력되었을 때 모델 내부 device로의 자동 전환 및 forward 정상 연산 검증"""
        # Test TabularMLPFeatureExtractor
        mlp = TabularMLPFeatureExtractor(input_dim=14, output_dim=32)
        cpu_tensor_1d = torch.randn(14, dtype=torch.float32)
        cpu_tensor_2d = torch.randn(5, 14, dtype=torch.float32)
        out_mlp_1d = mlp(cpu_tensor_1d)
        assert out_mlp_1d.shape == (32,)
        out_mlp_2d = mlp(cpu_tensor_2d)
        assert out_mlp_2d.shape == (5, 32)

        # Test Temporal1DCNNFeatureExtractor
        cnn = Temporal1DCNNFeatureExtractor(in_channels=10, seq_len=20, output_dim=32)
        cnn_in_2d = torch.randn(5, 10, dtype=torch.float32)
        out_cnn = cnn(cnn_in_2d)
        assert out_cnn.shape == (5, 32)

        # Test DualStreamSLFeatureExtractor
        dual = DualStreamSLFeatureExtractor(temporal_in_channels=10, temporal_seq_len=20, tabular_dim=4, output_dim=64)
        t_x = torch.randn(3, 20, 10, dtype=torch.float32)
        tab_x = torch.randn(3, 4, dtype=torch.float32)
        out_dual_pos = dual(temporal_x=t_x, tabular_x=tab_x)
        assert out_dual_pos.shape == (3, 64)
        out_dual_tup = dual((t_x, tab_x))
        assert out_dual_tup.shape == (3, 64)
        out_dual_dict = dual({"temporal": t_x, "tabular": tab_x})
        assert out_dual_dict.shape == (3, 64)

        # Test HybridActorCritic
        policy = HybridActorCritic(obs_dim=14, feature_dim=64)
        out_pol_feats = policy.extract_features(cpu_tensor_2d)
        assert out_pol_feats.shape == (5, 64)
        disc_logits, p1, p2, val = policy(cpu_tensor_2d)
        assert disc_logits.shape == (5, 3)
        assert val.shape == (5, 1)


