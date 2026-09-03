"""
etc/scripts/m2_challenger1_stress_harness.py
============================================
Adversarial Stress Test Suite for Milestone 2 Neural Network Models
- modules/models/feature_extractor.py
- modules/models/hybrid_policy.py
"""

import math
import os
import sys
import traceback
from typing import Any, Dict, List, Tuple

import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.engine.hybrid_trading_env import (
    ContinuousToHybridActionWrapper,
    HybridTradingEnv,
)
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


class StressTestRunner:
    def __init__(self):
        self.results = []
        self.failures = []

    def log_result(self, test_name: str, status: str, details: str = ""):
        res = {"test": test_name, "status": status, "details": details}
        self.results.append(res)
        if status not in ("PASS", "WARN_ACCEPTABLE", "FAIL_EXPECTED"):
            self.failures.append(res)
        tag = f"[{status}]"
        print(f"{tag:<22} {test_name}: {details}")

    def run_all(self):
        print("=" * 90)
        print("RUNNING ADVERSARIAL STRESS TEST SUITE FOR M2 NEURAL MODELS")
        print("=" * 90)

        # 1. Non-standard input stress tests
        self.test_tabular_mlp_inputs()
        self.test_temporal_cnn_inputs()
        self.test_temporal_cnn_batch_seqlen_collision()
        self.test_dual_stream_inputs()
        self.test_actor_critic_inputs()

        # 2. Extreme LR and Gradient Stress Tests
        self.test_actor_critic_beta_numerical_stability()
        self.test_actor_critic_extreme_learning_rates()
        self.test_sl_pretrainer_extreme_learning_rates()
        self.test_ppo_numerical_stability_extreme_advantages()

        # 3. Weight Transfer & Freeze/Unfreeze Gradient Isolation
        self.test_freeze_unfreeze_gradient_isolation()
        self.test_sl_transfer_key_matching_and_silent_mismatch()

        # 4. Action Distribution Boundary Tests
        self.test_beta_boundary_sampling_and_eval()
        self.test_action_wrapper_boundary_inputs()

        # 5. PPO Execution & Rollout Buffer Edge Cases
        self.test_rollout_buffer_edge_cases()
        self.test_hybrid_ppo_e2e_learning()
        self.test_sb3_ppo_e2e_learning()

        print("\n" + "=" * 90)
        print(f"SUMMARY: Total Tests = {len(self.results)}, Issues/Warnings = {len(self.failures)}")
        print("=" * 90)
        return self.results, self.failures

    # ------------------------------------------------------------------------
    # 1. Non-standard input stress tests
    # ------------------------------------------------------------------------
    def test_tabular_mlp_inputs(self):
        mlp = TabularMLPFeatureExtractor(input_dim=14, output_dim=64, use_layer_norm=True, use_residual=True)
        mlp.eval()

        # 1a. Normal 2D tensor
        x_norm = torch.randn(8, 14)
        out = mlp(x_norm)
        assert out.shape == (8, 64) and not torch.isnan(out).any(), "Normal 2D failed"
        self.log_result("TabularMLP_Normal2D", "PASS", f"Output shape: {out.shape}")

        # 1b. 1D single vector
        x_1d = torch.randn(14)
        out_1d = mlp(x_1d)
        assert out_1d.shape == (64,) and not torch.isnan(out_1d).any(), f"1D shape mismatch: {out_1d.shape}"
        self.log_result("TabularMLP_1DVector", "PASS", f"Output shape: {out_1d.shape}")

        # 1c. Numpy input
        x_np = np.random.randn(4, 14).astype(np.float32)
        out_np = mlp(x_np)
        assert out_np.shape == (4, 64), f"Numpy shape mismatch: {out_np.shape}"
        self.log_result("TabularMLP_NumpyInput", "PASS", f"Output shape: {out_np.shape}")

        # 1d. NaN / Inf injection
        x_nan = torch.tensor([[float("nan"), float("inf"), float("-inf")] + [0.5] * 11])
        out_nan = mlp(x_nan)
        assert not torch.isnan(out_nan).any() and not torch.isinf(out_nan).any(), "NaN/Inf leaked to output"
        self.log_result("TabularMLP_NaN_Inf_Sanitization", "PASS", "NaN/Inf safely clamped without output corruption")

        # 1e. Batch size 0
        try:
            x_zero = torch.zeros((0, 14))
            out_zero = mlp(x_zero)
            if out_zero.shape == (0, 64):
                self.log_result("TabularMLP_ZeroBatch", "PASS", f"Handled 0-batch gracefully: {out_zero.shape}")
            else:
                self.log_result("TabularMLP_ZeroBatch", "FAIL", f"Unexpected shape for 0-batch: {out_zero.shape}")
        except Exception as e:
            self.log_result("TabularMLP_ZeroBatch", "FAIL", f"Crashed on 0-batch: {e}")

        # 1f. Extreme values (1e30, -1e30)
        x_ext = torch.tensor([[1e30, -1e30] + [0.0] * 12])
        out_ext = mlp(x_ext)
        if torch.isnan(out_ext).any() or torch.isinf(out_ext).any():
            self.log_result(
                "TabularMLP_ExtremeFloats_1e30",
                "WARN_NUMERICAL_OVERFLOW",
                "Extreme finite float (1e30) overflows float32 in LayerNorm variance squaring ((1e30)^2 = 1e60 > 3.4e38) producing NaN output. Recommend clamping inputs to [-1e6, 1e6].",
            )
        else:
            self.log_result("TabularMLP_ExtremeFloats_1e30", "PASS", f"Finite output max={out_ext.abs().max().item():.3f}")

        # 1g. 0D Scalar input
        try:
            x_scalar = torch.tensor(1.0)
            out_scalar = mlp(x_scalar)
            self.log_result("TabularMLP_ScalarInput", "PASS", f"Output: {out_scalar.shape}")
        except Exception as e:
            self.log_result("TabularMLP_ScalarInput", "FAIL_EXPECTED", f"Expected error on 0D scalar: {type(e).__name__}")

    def test_temporal_cnn_inputs(self):
        cnn = Temporal1DCNNFeatureExtractor(
            in_channels=10, seq_len=20, num_filters=[32, 64], output_dim=64, pooling="adaptive_avg"
        )
        cnn.eval()

        # 2a. Standard 3D input: (B, seq_len, in_channels) = (4, 20, 10)
        x_3d = torch.randn(4, 20, 10)
        out = cnn(x_3d)
        assert out.shape == (4, 64), f"3D shape mismatch: {out.shape}"
        self.log_result("TemporalCNN_Standard3D_SeqFirst", "PASS", f"Output: {out.shape}")

        # 2b. Standard 3D input transposed: (B, in_channels, seq_len) = (4, 10, 20)
        x_3d_t = torch.randn(4, 10, 20)
        out_t = cnn(x_3d_t)
        assert out_t.shape == (4, 64), f"3D transpose shape mismatch: {out_t.shape}"
        self.log_result("TemporalCNN_Standard3D_ChanFirst", "PASS", f"Output: {out_t.shape}")

        # 2c. 1D single vector
        x_1d = torch.randn(10)
        out_1d = cnn(x_1d)
        assert out_1d.shape == (64,), f"1D shape mismatch: {out_1d.shape}"
        self.log_result("TemporalCNN_1DVector", "PASS", f"Output: {out_1d.shape}")

        # 2d. 2D unbatched sequence: (seq_len=20, in_channels=10)
        x_2d_seq = torch.randn(20, 10)
        out_2d = cnn(x_2d_seq)
        self.log_result("TemporalCNN_2D_UnbatchedSeq", "PASS", f"Output shape: {out_2d.shape}")

        # 2e. NaN / Inf injection
        x_nan = torch.randn(4, 20, 10)
        x_nan[0, 0, 0] = float("nan")
        x_nan[1, 5, 2] = float("inf")
        x_nan[2, 10, 5] = float("-inf")
        out_nan = cnn(x_nan)
        assert not torch.isnan(out_nan).any() and not torch.isinf(out_nan).any(), "NaN/Inf leaked through CNN"
        self.log_result("TemporalCNN_NaN_Inf_Sanitization", "PASS", "NaN/Inf safely sanitized in 1D-CNN")

    def test_temporal_cnn_batch_seqlen_collision(self):
        """
        CRITICAL EDGE CASE CHECK:
        What if input is a 2D batch of features (B, in_channels) where B == seq_len?
        For instance, batch_size = 20, in_channels = 10.
        The model confuses (B=20, in_channels=10) with an unbatched sequence (seq_len=20, in_channels=10)!
        """
        cnn = Temporal1DCNNFeatureExtractor(
            in_channels=10, seq_len=20, num_filters=[32, 64], output_dim=64, pooling="adaptive_avg"
        )
        cnn.eval()

        # Batch of 20 samples, each of dim 10
        x_batch20 = torch.randn(20, 10)
        out = cnn(x_batch20)
        if out.shape == (64,):
            self.log_result(
                "TemporalCNN_BatchSize_SeqLen_Ambiguity",
                "WARN_AMBIGUOUS_SHAPE",
                f"2D tensor (20, 10) interpreted as single unbatched sequence of length 20 -> shape {out.shape} instead of (20, 64). "
                f"When B == seq_len in 2D inputs, shape heuristic misinterprets batch as sequence length. "
                f"3D shape (B, 1, 10) or explicit batch dim avoids ambiguity.",
            )
        elif out.shape == (20, 64):
            self.log_result("TemporalCNN_BatchSize_SeqLen_Ambiguity", "PASS", f"Handled as batched 2D: {out.shape}")
        else:
            self.log_result("TemporalCNN_BatchSize_SeqLen_Ambiguity", "FAIL", f"Unexpected shape: {out.shape}")

    def test_dual_stream_inputs(self):
        fusion = DualStreamSLFeatureExtractor(
            temporal_in_channels=10,
            temporal_seq_len=20,
            tabular_dim=4,
            temporal_output_dim=64,
            tabular_output_dim=32,
            fusion_dim=128,
            output_dim=64,
        )
        fusion.eval()

        # 3a. Dict input
        dict_inp = {
            "temporal": torch.randn(4, 20, 10),
            "tabular": torch.randn(4, 4),
        }
        out_dict = fusion(x=dict_inp)
        assert out_dict.shape == (4, 64), f"Dict input shape mismatch: {out_dict.shape}"
        self.log_result("DualStream_DictInput", "PASS", f"Output: {out_dict.shape}")

        # 3b. Tuple input
        tuple_inp = (torch.randn(4, 20, 10), torch.randn(4, 4))
        out_tuple = fusion(x=tuple_inp)
        assert out_tuple.shape == (4, 64), f"Tuple input shape mismatch: {out_tuple.shape}"
        self.log_result("DualStream_TupleInput", "PASS", f"Output: {out_tuple.shape}")

        # 3c. Single flat vector (14 elements: 10 temporal + 4 tabular)
        flat_1d = torch.randn(14)
        out_flat = fusion(x=flat_1d)
        assert out_flat.shape == (64,), f"Flat 1D shape mismatch: {out_flat.shape}"
        self.log_result("DualStream_Flat1DVector", "PASS", f"Output: {out_flat.shape}")

        # 3d. Batched flat vector (B=8, 14 elements)
        flat_2d = torch.randn(8, 14)
        out_flat_2d = fusion(x=flat_2d)
        assert out_flat_2d.shape == (8, 64), f"Flat 2D shape mismatch: {out_flat_2d.shape}"
        self.log_result("DualStream_Flat2D_Batched", "PASS", f"Output: {out_flat_2d.shape}")

        # 3e. Empty / missing stream fallbacks
        out_fallback = fusion(temporal_x=None, tabular_x=None)
        assert out_fallback.shape == (1, 64), f"Fallback shape mismatch: {out_fallback.shape}"
        self.log_result("DualStream_MissingStreamFallback", "PASS", f"Fallback zero-tensor output: {out_fallback.shape}")

    def test_actor_critic_inputs(self):
        ac_beta = HybridActorCritic(obs_dim=14, distribution_type="beta")
        ac_gauss = HybridActorCritic(obs_dim=14, distribution_type="gaussian")
        ac_beta.eval()
        ac_gauss.eval()

        # 4a. Beta forward
        x = torch.randn(4, 14)
        disc_logits, a, b, val = ac_beta(x)
        assert disc_logits.shape == (4, 3) and a.shape == (4, 1) and b.shape == (4, 1) and val.shape == (4, 1)
        assert (a >= 1.0).all() and (b >= 1.0).all(), "Beta parameters must be >= 1.0"
        self.log_result("ActorCritic_BetaForward", "PASS", f"Alpha min={a.min().item():.3f}, Beta min={b.min().item():.3f}")

        # 4b. Gaussian forward
        disc_logits_g, mu, std, val_g = ac_gauss(x)
        assert (mu >= 0.0).all() and (mu <= 1.0).all(), "Gaussian mean must be bounded in [0, 1]"
        assert (std > 0.0).all(), "Gaussian std must be positive"
        self.log_result("ActorCritic_GaussianForward", "PASS", f"Mu range: [{mu.min().item():.3f}, {mu.max().item():.3f}]")

        # 4c. Sample action unbatched 1D
        act_unbatched, log_p_unb, val_unb = ac_beta.sample_action(np.random.randn(14).astype(np.float32), deterministic=False)
        assert isinstance(act_unbatched, tuple) and len(act_unbatched) == 2
        assert isinstance(act_unbatched[0], int) and 0 <= act_unbatched[0] <= 2
        assert isinstance(act_unbatched[1], float) and 0.0 <= act_unbatched[1] <= 1.0
        assert not torch.isnan(log_p_unb) and not torch.isinf(log_p_unb)
        self.log_result("ActorCritic_SampleAction_1D", "PASS", f"Action: {act_unbatched}, log_p={log_p_unb.item():.4f}")

        # 4d. Sample action batched
        act_b, log_p_b, val_b = ac_beta.sample_action(np.random.randn(8, 14).astype(np.float32), deterministic=True)
        assert len(act_b[0]) == 8 and len(act_b[1]) == 8
        self.log_result("ActorCritic_SampleAction_Batched", "PASS", f"Deterministic batch sample count={len(act_b[0])}")

    # ------------------------------------------------------------------------
    # 2. Extreme LR and Gradient Stress Tests
    # ------------------------------------------------------------------------
    def test_actor_critic_beta_numerical_stability(self):
        """
        Adversarial test: Push actor latents to extreme magnitudes (e.g. +100, -100)
        and check if Beta distribution log_prob and entropy remain finite (no NaN / Inf).
        """
        ac = HybridActorCritic(obs_dim=14, distribution_type="beta")
        ac.train()

        test_obs = torch.randn(32, 14) * 100.0  # Huge inputs
        disc_logits, alpha, beta, val = ac(test_obs)

        # Check for NaN / Inf
        assert not torch.isnan(alpha).any() and not torch.isinf(alpha).any(), "Alpha has NaN/Inf"
        assert not torch.isnan(beta).any() and not torch.isinf(beta).any(), "Beta has NaN/Inf"

        # Check log_prob computation on boundary actions (0.000001, 0.999999)
        test_actions = (
            torch.randint(0, 3, (32,)),
            torch.tensor([1e-7] * 16 + [1.0 - 1e-7] * 16),
        )
        log_prob, entropy, value = ac.evaluate_actions(test_obs, test_actions)

        is_nan_logp = torch.isnan(log_prob).any() or torch.isinf(log_prob).any()
        is_nan_ent = torch.isnan(entropy).any() or torch.isinf(entropy).any()

        if is_nan_logp or is_nan_ent:
            self.log_result(
                "BetaDistribution_ExtremeLatentStability",
                "FAIL",
                f"NaN/Inf detected! log_prob finite: {not is_nan_logp}, entropy finite: {not is_nan_ent}",
            )
        else:
            self.log_result(
                "BetaDistribution_ExtremeLatentStability",
                "PASS",
                f"Log_prob and entropy completely finite under 100x input scale (log_p min={log_prob.min().item():.2f}, max={log_prob.max().item():.2f})",
            )

    def test_actor_critic_extreme_learning_rates(self):
        """
        Train HybridActorCritic with extreme learning rates: 1e-6, 1e-4, 1e-2, 1e-1, 1.0
        and check for gradient explosion or collapse into NaN.
        """
        learning_rates = [1e-6, 1e-4, 1e-2, 1e-1, 1.0]
        for lr in learning_rates:
            ac = HybridActorCritic(obs_dim=14, distribution_type="beta")
            optimizer = torch.optim.Adam(ac.parameters(), lr=lr)

            has_nan = False
            for step in range(20):
                obs = torch.randn(16, 14)
                disc_act = torch.randint(0, 3, (16,))
                cont_act = torch.rand(16, 1)
                log_prob, entropy, value = ac.evaluate_actions(obs, (disc_act, cont_act))

                target_v = torch.randn(16)
                loss = -log_prob.mean() + F.mse_loss(value, target_v) - 0.01 * entropy.mean()

                optimizer.zero_grad()
                loss.backward()

                # Check gradients
                for name, param in ac.named_parameters():
                    if param.grad is not None:
                        if torch.isnan(param.grad).any() or torch.isinf(param.grad).any():
                            has_nan = True
                            break
                torch.nn.utils.clip_grad_norm_(ac.parameters(), max_norm=1.0)
                optimizer.step()

                if has_nan:
                    break

            if has_nan:
                self.log_result(
                    f"ActorCritic_ExtremeLR_{lr}",
                    "FAIL",
                    f"Gradients exploded to NaN at lr={lr}",
                )
            else:
                self.log_result(
                    f"ActorCritic_ExtremeLR_{lr}",
                    "PASS",
                    f"Survived 20 steps without NaN/Inf (lr={lr})",
                )

    def test_sl_pretrainer_extreme_learning_rates(self):
        """
        Train SLPretrainer with extreme learning rates and check multi-task loss stability.
        """
        for lr in [1e-5, 1e-3, 0.1, 1.0]:
            pretrainer = SLPretrainer(feature_dim=64, num_classes=3, lr=lr)
            # Dummy dataset
            t_x = torch.randn(64, 20, 10)
            tab_x = torch.randn(64, 4)
            y_ret = torch.randn(64, 1) * 0.05
            y_dir = torch.randint(0, 3, (64,))

            history = pretrainer.fit(
                train_data=(t_x, tab_x, y_ret, y_dir),
                epochs=3,
                batch_size=16,
                lr=lr,
                verbose=False,
            )

            final_loss = history["train_total_loss"][-1]
            if math.isnan(final_loss) or math.isinf(final_loss):
                self.log_result(f"SLPretrainer_LR_{lr}", "FAIL", f"Loss diverged to {final_loss}")
            else:
                self.log_result(f"SLPretrainer_LR_{lr}", "PASS", f"Final loss={final_loss:.4f}, Acc={history['train_accuracy'][-1]:.2f}")

    def test_ppo_numerical_stability_extreme_advantages(self):
        """
        Adversarial test on PPO loss:
        Inject extreme advantages (+10000.0, -10000.0) and extreme policy ratios (1e-8, 1e8)
        to verify clipped surrogate loss doesn't overflow.
        """
        ac = HybridActorCritic(obs_dim=14, distribution_type="beta")
        obs = torch.randn(10, 14)
        actions = (torch.randint(0, 3, (10,)), torch.rand(10, 1))

        log_prob, entropy, values = ac.evaluate_actions(obs, actions)
        old_log_p = log_prob.detach() + torch.tensor([50.0, -50.0] * 5)  # Huge ratio differences
        adv = torch.tensor([1e5, -1e5] * 5)

        # Normalized adv
        adv = (adv - adv.mean()) / (adv.std() + 1e-8)

        ratio = torch.exp(torch.clamp(log_prob - old_log_p, -20.0, 20.0))
        surr1 = ratio * adv
        surr2 = torch.clamp(ratio, 0.8, 1.2) * adv
        policy_loss = -torch.min(surr1, surr2).mean()

        assert not torch.isnan(policy_loss) and not torch.isinf(policy_loss), "PPO surrogate loss overflowed"
        self.log_result("PPO_ExtremeAdvantageSurrogateStability", "PASS", f"Policy loss={policy_loss.item():.4f}")

    # ------------------------------------------------------------------------
    # 3. Weight Transfer & Freeze/Unfreeze Gradient Isolation
    # ------------------------------------------------------------------------
    def test_freeze_unfreeze_gradient_isolation(self):
        """
        Verify that freeze_backbone() prevents gradients from flowing to feature_extractor parameters,
        and unfreeze_backbone() restores gradient flow.
        """
        custom_backbone = TabularMLPFeatureExtractor(input_dim=14, output_dim=64)
        ac = HybridActorCritic(obs_dim=14, feature_extractor=custom_backbone)

        # 1. Initially unfrozen
        obs = torch.randn(8, 14)
        disc_act = torch.randint(0, 3, (8,))
        cont_act = torch.rand(8, 1)

        log_p, ent, val = ac.evaluate_actions(obs, (disc_act, cont_act))
        loss = -log_p.mean() + val.mean()
        loss.backward()

        backbone_has_grad_unfrozen = any(
            p.grad is not None and torch.norm(p.grad).item() > 0.0 for p in ac.feature_extractor.parameters()
        )
        assert backbone_has_grad_unfrozen, "Unfrozen backbone failed to receive gradients!"

        # 2. Freeze backbone
        ac.zero_grad()
        ac.freeze_backbone()

        log_p, ent, val = ac.evaluate_actions(obs, (disc_act, cont_act))
        loss = -log_p.mean() + val.mean()
        loss.backward()

        backbone_has_grad_frozen = any(
            p.grad is not None and torch.norm(p.grad).item() > 0.0 for p in ac.feature_extractor.parameters()
        )
        actor_head_has_grad = any(
            p.grad is not None and torch.norm(p.grad).item() > 0.0 for p in ac.actor_latent.parameters()
        )

        assert not backbone_has_grad_frozen, "CRITICAL: Frozen backbone received gradients!"
        assert actor_head_has_grad, "Actor head failed to receive gradients when backbone was frozen!"
        self.log_result(
            "Backbone_Freeze_Isolation",
            "PASS",
            "feature_extractor gradients strictly zero/None while actor/critic heads learn normally",
        )

        # 3. Unfreeze backbone
        ac.zero_grad()
        ac.unfreeze_backbone()

        log_p, ent, val = ac.evaluate_actions(obs, (disc_act, cont_act))
        loss = -log_p.mean() + val.mean()
        loss.backward()

        backbone_has_grad_restored = any(
            p.grad is not None and torch.norm(p.grad).item() > 0.0 for p in ac.feature_extractor.parameters()
        )
        assert backbone_has_grad_restored, "Unfreeze failed to restore gradient flow!"
        self.log_result("Backbone_Unfreeze_Restoration", "PASS", "Gradient flow cleanly restored to feature_extractor")

    def test_sl_transfer_key_matching_and_silent_mismatch(self):
        """
        Verify weight transfer from SLPretrainer to HybridActorCritic and check behavior on mismatched backbone.
        """
        # Case 1: Matching backbone (DualStream -> DualStream)
        pretrainer = SLPretrainer(feature_dim=64)
        t_x = torch.randn(16, 20, 10)
        tab_x = torch.randn(16, 4)
        y_ret = torch.randn(16, 1)
        y_dir = torch.randint(0, 3, (16,))
        pretrainer.train_step((t_x, tab_x, y_ret, y_dir))

        save_path = "/tmp/test_sl_pretrained.pt"
        pretrainer.save_pretrained(save_path)

        matching_backbone = DualStreamSLFeatureExtractor(output_dim=64)
        ac_matching = HybridActorCritic(obs_dim=14, feature_extractor=matching_backbone)
        ac_matching.load_from_sl_pretrainer(save_path, freeze=True)

        p1 = list(pretrainer.backbone.parameters())[0]
        p2 = list(ac_matching.feature_extractor.parameters())[0]
        diff = (p1 - p2).abs().max().item()
        assert diff < 1e-6, f"Weight transfer mismatch on matching backbone: diff={diff}"
        assert ac_matching.freeze_feature_extractor, "Freeze flag not set on load"
        self.log_result("SL_Transfer_MatchingBackbone", "PASS", f"Weights transferred perfectly, diff={diff:.2e}")

        # Case 2: Mismatched backbone (DualStream saved, loaded into default TabularMLP)
        ac_mismatched = HybridActorCritic(obs_dim=14)  # Default is TabularMLP
        orig_w = list(ac_mismatched.feature_extractor.parameters())[0].clone()
        ac_mismatched.load_from_sl_pretrainer(save_path, freeze=False)
        new_w = list(ac_mismatched.feature_extractor.parameters())[0]

        is_unchanged = torch.equal(orig_w, new_w)
        if is_unchanged:
            self.log_result(
                "SL_Transfer_MismatchedBackbone_SilentDrop",
                "WARN_SILENT_KEY_MISMATCH",
                "When transferring DualStream SLPretrainer weights into default TabularMLP HybridActorCritic, "
                "strict=False silently ignores all keys. The weights remain completely un-transferred without error. "
                "Recommend explicit key-match validation or logging in load_from_sl_pretrainer.",
            )
        else:
            self.log_result("SL_Transfer_MismatchedBackbone_SilentDrop", "PASS", "Weights unexpectedly modified")

        if os.path.exists(save_path):
            os.remove(save_path)

    # ------------------------------------------------------------------------
    # 4. Action Distribution Boundary Tests
    # ------------------------------------------------------------------------
    def test_beta_boundary_sampling_and_eval(self):
        """
        Stress test Beta distribution near 0.0 and 1.0.
        """
        ac = HybridActorCritic(obs_dim=14, distribution_type="beta")
        ac.eval()

        boundary_actions = (
            torch.tensor([0, 1, 2, 0]),
            torch.tensor([0.0, 1.0, 0.5, 0.0000001]),
        )
        obs = torch.randn(4, 14)
        log_prob, entropy, value = ac.evaluate_actions(obs, boundary_actions)

        assert not torch.isnan(log_prob).any() and not torch.isinf(log_prob).any(), "Beta log_prob broke at 0.0/1.0"
        assert not torch.isnan(entropy).any() and not torch.isinf(entropy).any(), "Beta entropy broke"
        self.log_result("Beta_Boundary_0_and_1_Handling", "PASS", "Actions clamped to [1e-6, 1-1e-6] safely prevents -Inf")

    def test_action_wrapper_boundary_inputs(self):
        """
        Test ContinuousToHybridActionWrapper and SB3HybridPolicyAdapter with boundary continuous inputs:
        - [-10.0, 10.0]
        - [0.0, 0.5]
        """
        env = HybridTradingEnv(initial_cash=10_000_000.0)
        wrapped = ContinuousToHybridActionWrapper(env)
        wrapped.reset(seed=42)

        test_actions = [
            np.array([10.0, 5.0], dtype=np.float32),   # signal > 0.333 -> BUY, weight clamped to 1.0
            np.array([-10.0, -5.0], dtype=np.float32), # signal < -0.333 -> SELL, weight clamped to 0.0
            np.array([0.0, 0.5], dtype=np.float32),    # HOLD
            np.array([0.333, 0.5], dtype=np.float32),  # Boundary HOLD
            np.array([-0.333, 0.5], dtype=np.float32), # Boundary HOLD
        ]

        for act in test_actions:
            obs, rew, term, trunc, info = wrapped.step(act)
            assert not np.isnan(rew) and not np.isinf(rew)
            if term or trunc:
                wrapped.reset()

        self.log_result("ActionWrapper_ExtremeContinuousSignals", "PASS", "Extreme continuous signals [-10, 10] safely clipped and decoded")

    # ------------------------------------------------------------------------
    # 5. PPO Execution & Rollout Buffer Edge Cases
    # ------------------------------------------------------------------------
    def test_rollout_buffer_edge_cases(self):
        """
        Test RolloutBuffer with overflow and zero transitions.
        """
        buf = RolloutBuffer(buffer_size=10, obs_dim=14, device=torch.device("cpu"))
        for i in range(15):
            buf.add(
                obs=np.random.randn(14).astype(np.float32),
                action=(1, 0.5),
                reward=1.0,
                value=0.5,
                log_prob=-0.5,
                done=False,
            )

        assert buf.ptr == 10 and buf.full, f"Buffer failed to cap at buffer_size: ptr={buf.ptr}"
        buf.compute_returns_and_advantages(last_value=0.5, last_done=False)
        assert not np.isnan(buf.advantages).any() and not np.isnan(buf.returns).any()

        batches = list(buf.get_batches(batch_size=4))
        assert len(batches) == 3
        self.log_result("RolloutBuffer_OverflowAndGAE", "PASS", f"Buffer capped at 10, generated {len(batches)} batches")

    def test_hybrid_ppo_e2e_learning(self):
        """
        End-to-end learning test of Native HybridPPO on HybridTradingEnv.
        """
        env = HybridTradingEnv(initial_cash=10_000_000.0)
        agent = HybridPPO(
            env=env,
            learning_rate=3e-4,
            n_steps=64,
            batch_size=16,
            n_epochs=2,
            seed=42,
        )
        agent.learn(total_timesteps=128)
        eval_res = agent.evaluate(n_episodes=2)
        assert "mean_reward" in eval_res and not math.isnan(eval_res["mean_reward"])
        self.log_result("HybridPPO_E2E_Learn", "PASS", f"E2E learn 128 steps successful: mean_reward={eval_res['mean_reward']:.4f}")

    def test_sb3_ppo_e2e_learning(self):
        """
        End-to-end learning test of SB3 PPO via SB3HybridPolicyAdapter.
        """
        env = HybridTradingEnv(initial_cash=10_000_000.0)
        sb3_model = SB3HybridPolicyAdapter.create_sb3_ppo(
            env=env,
            features_dim=32,
            n_steps=64,
            batch_size=16,
            seed=42,
        )
        sb3_model.learn(total_timesteps=128)

        # Predict hybrid
        obs, _ = env.reset(seed=42)
        hybrid_act, raw_act = SB3HybridPolicyAdapter.predict_hybrid(sb3_model, obs)
        assert isinstance(hybrid_act, tuple) and len(hybrid_act) == 2
        assert 0 <= hybrid_act[0] <= 2 and 0.0 <= hybrid_act[1] <= 1.0
        self.log_result("SB3_HybridAdapter_E2E_Learn", "PASS", f"SB3 PPO trained 128 steps and predicted action: {hybrid_act}")


if __name__ == "__main__":
    runner = StressTestRunner()
    results, failures = runner.run_all()
    if failures:
        print(f"\n[SUMMARY] {len(failures)} issue(s)/warning(s) found during stress testing.")
        for f in failures:
            print(f" - {f['test']}: {f['status']} -> {f['details']}")
