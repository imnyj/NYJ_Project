#!/usr/bin/env python3
"""
etc/scripts/test_m1_models_comprehensive.py
============================================
Auto Stock ML/RL Trader — Phase 6 Milestone 1
3종 SL 모델(ResNet, Transformer, CVAE) 심층 종합 검증 스크립트.
"""

import math
import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from modules.models import (
    BaseSLFeatureExtractor,
    ResNet1DBlock,
    TemporalResNetFeatureExtractor,
    SinusoidalPositionalEncoding,
    AttentionPooling1D,
    CrossTimeframeAttention,
    TemporalTransformerFeatureExtractor,
    TemporalCVAEFeatureExtractor,
    DualStreamSLFeatureExtractor,
    SLPretrainer,
    HybridActorCritic,
)


def test_resnet_comprehensive():
    print("--- [1/5] Testing TemporalResNetFeatureExtractor ---")
    model = TemporalResNetFeatureExtractor(
        daily_in_channels=10,
        daily_seq_len=20,
        minute_in_channels=10,
        minute_seq_len=60,
        tabular_dim=4,
        output_dim=64,
        num_blocks=2,
        base_filters=64,
        kernel_size=3,
        dropout=0.1,
    )

    B = 8
    # 1. Explicit multi-timeframe tensors
    d_x = torch.randn(B, 20, 10)
    m_x = torch.randn(B, 60, 10)
    tab_x = torch.randn(B, 4)

    feats, ret, dire = model(daily_x=d_x, minute_x=m_x, tabular_x=tab_x)
    assert feats.shape == (B, 64)
    assert ret.shape == (B, 1)
    assert dire.shape == (B, 3)

    # 2. Polymorphic inputs: Dict
    f_dict, r_dict, d_dict = model(x={"daily": d_x, "minute": m_x, "tabular": tab_x})
    assert f_dict.shape == (B, 64)

    # 3. Polymorphic inputs: Tuple (3 elements)
    f_tup3, _, _ = model(x=(d_x, m_x, tab_x))
    assert f_tup3.shape == (B, 64)

    # 4. Polymorphic inputs: Tuple (2 elements - daily, tabular)
    f_tup2, _, _ = model(x=(d_x, tab_x))
    assert f_tup2.shape == (B, 64)

    # 5. Polymorphic inputs: Single 3D tensor (daily only)
    f_3d, _, _ = model(d_x)
    assert f_3d.shape == (B, 64)

    # 6. Polymorphic inputs: Single 2D observation tensor (14 dims)
    obs_14d = torch.randn(B, 14)
    f_14d, r_14d, d_14d = model(obs_14d)
    assert f_14d.shape == (B, 64)
    assert r_14d.shape == (B, 1)
    assert d_14d.shape == (B, 3)

    # 7. Polymorphic inputs: Single 1D unbatched vector (14 dims)
    obs_1d = torch.randn(14)
    f_1d, r_1d, d_1d = model(obs_1d)
    assert f_1d.shape == (64,)
    assert r_1d.shape == (1,)
    assert d_1d.shape == (3,)

    # 8. Unbatched extract_features
    f_ext_1d = model.extract_features(obs_1d)
    assert f_ext_1d.shape == (64,)

    # 9. Numpy array support
    np_obs = np.random.randn(B, 14).astype(np.float32)
    f_np, _, _ = model(np_obs)
    assert f_np.shape == (B, 64)

    # 10. NaN/Inf numerical robustness
    nan_tensor = torch.randn(B, 20, 10)
    nan_tensor[0, 0, 0] = float("nan")
    nan_tensor[1, 1, 1] = float("inf")
    nan_tensor[2, 2, 2] = float("-inf")
    f_nan, r_nan, d_nan = model(daily_x=nan_tensor, minute_x=m_x, tabular_x=tab_x)
    assert not torch.isnan(f_nan).any()
    assert not torch.isinf(f_nan).any()

    # 11. predict_targets
    targets = model.predict_targets(obs_14d)
    assert targets["pred_return"].shape == (B, 1)
    assert targets["trend_probs"].shape == (B, 3)
    assert targets["anomaly_score"].shape == (B, 1)
    prob_sums = targets["trend_probs"].sum(dim=-1)
    assert torch.allclose(prob_sums, torch.ones_like(prob_sums), atol=1e-5)

    # 12. compute_anomaly_score
    ano_score = model.compute_anomaly_score(obs_14d)
    assert ano_score.shape == (B, 1)
    assert torch.all(ano_score >= 0.0)

    # 13. Gradient flow & backward
    model.train()
    loss = r_14d.sum() + d_14d.sum() + ano_score.sum()
    loss.backward()
    for name, param in model.named_parameters():
        assert param.grad is not None, f"ResNet parameter {name} has None grad"

    print("  ✓ TemporalResNetFeatureExtractor passed all 13 checks!")


def test_transformer_comprehensive():
    print("--- [2/5] Testing TemporalTransformerFeatureExtractor ---")
    model = TemporalTransformerFeatureExtractor(
        daily_in_channels=10,
        daily_seq_len=20,
        minute_in_channels=10,
        minute_seq_len=60,
        tabular_dim=4,
        d_model=64,
        nhead=4,
        num_layers=2,
        dim_feedforward=128,
        dropout=0.1,
        output_dim=64,
        use_cross_attention=True,
    )

    B = 6
    d_x = torch.randn(B, 20, 10)
    m_x = torch.randn(B, 60, 10)
    tab_x = torch.randn(B, 4)

    # 1. Forward pass
    feats, ret, dire = model(daily_x=d_x, minute_x=m_x, tabular_x=tab_x)
    assert feats.shape == (B, 64)
    assert ret.shape == (B, 1)
    assert dire.shape == (B, 3)

    # 2. Polymorphic inputs
    f_dict, _, _ = model(x={"daily": d_x, "minute": m_x, "tabular": tab_x})
    assert f_dict.shape == (B, 64)

    f_tup, _, _ = model(x=(d_x, m_x, tab_x))
    assert f_tup.shape == (B, 64)

    obs_14d = torch.randn(B, 14)
    f_14, r_14, d_14 = model(obs_14d)
    assert f_14.shape == (B, 64)
    assert r_14.shape == (B, 1)
    assert d_14.shape == (B, 3)

    obs_1d = torch.randn(14)
    f_1d, r_1d, d_1d = model(obs_1d)
    assert f_1d.shape == (64,)
    assert r_1d.shape == (1,)
    assert d_1d.shape == (3,)

    # 3. XAI Attention Weights
    attn_dict = model.get_attention_weights(daily_x=d_x, minute_x=m_x, tabular_x=tab_x)
    assert "daily_weights" in attn_dict
    assert "minute_weights" in attn_dict
    assert attn_dict["daily_weights"].shape == (B, 20)
    assert attn_dict["minute_weights"].shape == (B, 60)
    # Check that attention weights sum to 1.0 along time dimension
    d_sums = attn_dict["daily_weights"].sum(dim=-1)
    m_sums = attn_dict["minute_weights"].sum(dim=-1)
    assert torch.allclose(d_sums, torch.ones_like(d_sums), atol=1e-5)
    assert torch.allclose(m_sums, torch.ones_like(m_sums), atol=1e-5)

    # 4. predict_targets & anomaly_score
    targets = model.predict_targets(obs_14d)
    assert targets["pred_return"].shape == (B, 1)
    assert targets["trend_probs"].shape == (B, 3)
    assert targets["anomaly_score"].shape == (B, 1)

    # 5. Gradient flow
    model.train()
    loss = r_14.sum() + d_14.sum() + targets["anomaly_score"].sum()
    loss.backward()
    for name, param in model.named_parameters():
        assert param.grad is not None, f"Transformer parameter {name} has None grad"

    print("  ✓ TemporalTransformerFeatureExtractor passed all checks!")


def test_cvae_comprehensive():
    print("--- [3/5] Testing TemporalCVAEFeatureExtractor ---")
    model = TemporalCVAEFeatureExtractor(
        daily_in_channels=10,
        daily_seq_len=20,
        minute_in_channels=10,
        minute_seq_len=60,
        tabular_dim=4,
        latent_dim=16,
        hidden_dim=64,
        c_dim=32,
        output_dim=64,
        kl_weight=1e-3,
        dropout=0.1,
    )

    B = 6
    d_x = torch.randn(B, 20, 10)
    m_x = torch.randn(B, 60, 10)
    tab_x = torch.randn(B, 4)

    # 1. Forward pass
    feats, ret, dire = model(daily_x=d_x, minute_x=m_x, tabular_x=tab_x)
    assert feats.shape == (B, 64)
    assert ret.shape == (B, 1)
    assert dire.shape == (B, 3)

    # 2. Forward with return_aux=True
    f_aux, r_aux, d_aux, aux = model(daily_x=d_x, minute_x=m_x, tabular_x=tab_x, return_aux=True)
    assert f_aux.shape == (B, 64)
    assert aux["reconstructed_daily"].shape == (B, 20, 10)
    assert aux["reconstructed_minute"].shape == (B, 60, 10)
    assert aux["latent_mu"].shape == (B, 16)
    assert aux["latent_logvar"].shape == (B, 16)
    assert aux["latent_z"].shape == (B, 16)
    assert aux["anomaly_score"].shape == (B, 1)

    # 3. Anomaly score method
    ano_score = model.compute_anomaly_score(daily_x=d_x, minute_x=m_x, tabular_x=tab_x)
    assert ano_score.shape == (B, 1)
    assert torch.all(ano_score >= 0.0)

    # 4. Polymorphic inputs
    obs_14d = torch.randn(B, 14)
    f_14, r_14, d_14 = model(obs_14d)
    assert f_14.shape == (B, 64)

    obs_1d = torch.randn(14)
    f_1d, r_1d, d_1d = model(obs_1d)
    assert f_1d.shape == (64,)
    assert r_1d.shape == (1,)
    assert d_1d.shape == (3,)

    # 5. predict_targets
    targets = model.predict_targets(obs_14d)
    assert targets["pred_return"].shape == (B, 1)
    assert targets["trend_probs"].shape == (B, 3)
    assert targets["anomaly_score"].shape == (B, 1)
    assert targets["latent_mu"].shape == (B, 16)

    # 6. compute_cvae_loss
    y_ret = torch.randn(B, 1)
    y_dir = torch.randint(0, 3, (B,))
    losses = model.compute_cvae_loss(
        daily_x=d_x,
        minute_x=m_x,
        tabular_x=tab_x,
        target_return=y_ret,
        target_direction=y_dir,
    )
    assert "total_loss" in losses
    assert "rec_loss" in losses
    assert "kl_loss" in losses
    assert "reg_loss" in losses
    assert "cls_loss" in losses

    # 7. Gradient flow
    model.train()
    losses["total_loss"].backward()
    for name, param in model.named_parameters():
        assert param.grad is not None, f"CVAE parameter {name} has None grad"

    print("  ✓ TemporalCVAEFeatureExtractor passed all checks!")


def test_sl_pretrainer_and_hybrid_actor_critic_interop():
    print("--- [4/5] Testing Interoperability with SLPretrainer & HybridActorCritic ---")
    # 1. Test using ResNet as backbone in SLPretrainer
    resnet_backbone = TemporalResNetFeatureExtractor(output_dim=64)
    pretrainer = SLPretrainer(backbone=resnet_backbone, feature_dim=64)
    assert pretrainer.feature_dim == 64

    # Dummy batch for pretrainer
    t_x = torch.randn(4, 20, 10)
    tab_x = torch.randn(4, 4)
    y_ret = torch.randn(4, 1)
    y_dir = torch.randint(0, 3, (4,))
    batch = (t_x, tab_x, y_ret, y_dir)

    metrics = pretrainer.train_step(batch)
    assert "total_loss" in metrics
    print("  ✓ SLPretrainer with TemporalResNetFeatureExtractor works!")

    # 2. Test using Transformer in HybridActorCritic
    trans_backbone = TemporalTransformerFeatureExtractor(output_dim=64)
    policy_trans = HybridActorCritic(
        obs_dim=14,
        feature_extractor=trans_backbone,
        feature_dim=64,
        distribution_type="beta",
    )
    obs = torch.randn(4, 14)
    disc_logits, p1, p2, val = policy_trans(obs)
    assert disc_logits.shape == (4, 3)
    assert p1.shape == (4, 1)
    assert p2.shape == (4, 1)
    assert val.shape == (4, 1)
    print("  ✓ HybridActorCritic with TemporalTransformerFeatureExtractor works!")

    # 3. Test using CVAE in HybridActorCritic
    cvae_backbone = TemporalCVAEFeatureExtractor(output_dim=64)
    policy_cvae = HybridActorCritic(
        obs_dim=14,
        feature_extractor=cvae_backbone,
        feature_dim=64,
        distribution_type="beta",
    )
    disc_logits_c, p1_c, p2_c, val_c = policy_cvae(obs)
    assert disc_logits_c.shape == (4, 3)
    assert p1_c.shape == (4, 1)
    assert p2_c.shape == (4, 1)
    assert val_c.shape == (4, 1)
    print("  ✓ HybridActorCritic with TemporalCVAEFeatureExtractor works!")

    # 4. Test weight freezing
    policy_cvae.freeze_backbone()
    for p in cvae_backbone.parameters():
        assert not p.requires_grad
    policy_cvae.unfreeze_backbone()
    for p in cvae_backbone.parameters():
        assert p.requires_grad
    print("  ✓ Backbone freeze / unfreeze works on Phase 6 models!")


def test_cuda_device_safety():
    print("--- [5/5] Testing GPU / CPU device auto-detection & migration ---")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Target device: {device}")

    models = [
        TemporalResNetFeatureExtractor(),
        TemporalTransformerFeatureExtractor(),
        TemporalCVAEFeatureExtractor(),
    ]

    for m in models:
        m = m.to(device)
        d_x = torch.randn(2, 20, 10, device=device)
        m_x = torch.randn(2, 60, 10, device=device)
        tab_x = torch.randn(2, 4, device=device)

        f, r, d = m(daily_x=d_x, minute_x=m_x, tabular_x=tab_x)
        assert f.device.type == device.type
        assert r.device.type == device.type
        assert d.device.type == device.type
    print("  ✓ Device placement verified for all 3 models!")


if __name__ == "__main__":
    test_resnet_comprehensive()
    test_transformer_comprehensive()
    test_cvae_comprehensive()
    test_sl_pretrainer_and_hybrid_actor_critic_interop()
    test_cuda_device_safety()
    print("\n==================================================")
    print("🎉 ALL PHASE 6 MILESTONE 1 ARCHITECTURES FULLY VERIFIED! 🎉")
    print("==================================================")
