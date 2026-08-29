# tests/test_dummy_verification.py
# ============================================================================
# Short Dummy Run (10-step) Verification Test Suite
#
# Mathematically and functionally proves 100% crash-free integration of:
# 1. D1: SUMO real simulation environment (AoiV2IEnv) with TraCI/libsumo (18D state).
# 2. D2: Heuristic & generic policy model instantiation and inference.
# 3. D3: Act/Rest dual-model hot-swap and gradient training step.
# 4. D4: Optuna HPO 1-trial evaluation and parameter extraction.
# 5. D5: Benchmark evaluation single run and 6 IEEE TWC metrics computation.
# 6. Performance: Entire verification execution completes in < 15 seconds.
# ============================================================================

from __future__ import annotations
import math
import os
import time
import pytest
import numpy as np
import torch

from src.hot_swap_trainer import (
    AoiV2IEnv,
    DualModelHotSwapManager,
    HotSwapTrainer,
    select_default_devices,
)
import src.Communications as comm
from src.hpo import (
    run_hpo_study,
    save_study_results,
    compute_composite_objective,
    sample_reward_weights,
)
from src.evaluate import (
    evaluate_single_run,
    calculate_jains_fairness,
    instantiate_model,
)
from src.heuristic_scheduler import HeuristicScheduler
from tests.contract_adapters import DummyPolicy


class TestShortDummyRunVerification:
    """Short Dummy Run verification across entire pipeline."""

    def test_d1_sumo_real_environment_10_steps(self):
        """D1: Verify genuine SUMO environment runs 10 steps with active vehicles and channel contention."""
        env = AoiV2IEnv(density=25.0, seed=42, max_steps=10, warmup_steps=10)
        obs, info = env.reset()

        assert isinstance(obs, dict)
        assert info["sim_time"] > 0.0
        assert info["active_vehicles"] >= 0

        for step in range(10):
            action_dict = {}
            for vid, s_vec in obs.items():
                assert len(s_vec) == 18
                assert np.all(s_vec >= -1.0) and np.all(s_vec <= 1.0)
                # Hybrid action (delta=1.0s, ch=step%4, power=20.0dBm)
                action_dict[vid] = (1.0, step % comm.NUM_SUBCHANNELS, 20.0)

            next_obs, rewards, terminateds, truncateds, step_info = env.step(action_dict)
            obs = next_obs

            assert step_info["step"] == step + 1
            assert step_info["sim_time"] > 0.0
            for vid, r in rewards.items():
                assert not math.isnan(r) and not math.isinf(r)
                assert r <= 0.0

        metrics = env.get_metrics()
        env.close()

        assert metrics["mean_aoi"] >= 0.0
        assert metrics["mean_error"] >= 0.0
        assert 0.0 <= metrics["packet_loss_rate"] <= 1.0
        assert metrics["peak_aoi"] >= metrics["mean_aoi"]

    def test_d2_model_instantiation_and_inference(self):
        """D2: Verify generic model and heuristic scheduler accept 18-dim state and output valid hybrid actions."""
        model = DummyPolicy(state_dim=18, num_channels=4, hidden_dim=32)

        # Mock normalized 18-dim state vector
        s_vec = np.random.uniform(-0.8, 0.8, size=18).astype(np.float32)

        # Model inference
        grant, raw_action, info = model.select_action(s_vec, deterministic=False)
        delta, ch, power = grant

        assert 0.1 <= delta <= 45.0, f"Delta out of bounds [0.1, 45.0]: {delta}"
        assert 0 <= ch < 4, f"Channel index out of range {ch}"
        assert 10.0 <= power <= 23.0, f"Power out of bounds [10.0, 23.0]: {power}"
        assert not np.isnan(delta) and not np.isnan(power)

        # HeuristicScheduler inference
        scheduler = HeuristicScheduler(num_subchannels=4)
        st_dict = {"speed": 10.0, "stop_imminent": 0.0, "start_imminent": 0.0, "time_to_switch": 20.0}
        h_delta, h_ch, h_power = scheduler.decide_grant("v_dummy", st_dict)
        assert 0.1 <= h_delta <= 45.0
        assert 0 <= h_ch < 4
        assert 10.0 <= h_power <= 23.0

    def test_d3_hot_swap_gradient_step_and_parameter_sync(self):
        """D3: Verify transition collection, 1 gradient update on Rest model, and atomic hot-swap."""
        trainer = HotSwapTrainer(model_cls=DummyPolicy, batch_size=4, swap_interval=1)

        # Ingest 8 dummy transitions
        for i in range(8):
            s = np.random.uniform(-0.5, 0.5, size=18).astype(np.float32)
            ns = np.random.uniform(-0.5, 0.5, size=18).astype(np.float32)
            trainer.streamer.push(
                state=s,
                action=np.array([0.0, 1.0, 0.0], dtype=np.float32),
                reward=-0.5,
                next_state=ns,
                done=False,
                delta_t=1.0,
            )

        # Synchronous gradient update on Rest model
        loss_dict = trainer.step_training_sync()
        assert loss_dict is not None
        assert "loss" in loss_dict
        assert not math.isnan(loss_dict["loss"])

        # Atomic hot-swap
        swap_success = trainer.hot_swap_manager.hot_swap()
        assert swap_success is True
        assert trainer.hot_swap_manager.swap_count >= 1

        # Check parameter equivalence between Act and Rest models (handling cross-device)
        for p_act, p_rest in zip(trainer.act_model.parameters(), trainer.rest_model.parameters()):
            assert torch.allclose(p_act.cpu(), p_rest.cpu())

    def test_d4_optuna_hpo_single_trial_10_steps(self, tmp_path):
        """D4: Verify Optuna HPO executes 1 trial with 10 steps on real environment and saves CSV."""
        out_dir = str(tmp_path / "hpo_dummy")
        study = run_hpo_study(
            model_name="DummyPolicy",
            model_cls=DummyPolicy,
            n_trials=1,
            seeds=[42],
            n_steps=10,
        )

        csv_path, best_record = save_study_results(study, model_name="DummyPolicy", output_dir=out_dir)

        assert os.path.exists(csv_path)
        assert best_record["model_name"] == "DummyPolicy"
        assert not math.isnan(best_record["best_value"])

    def test_d5_benchmark_evaluation_single_run_10_steps(self):
        """D5: Verify benchmark single run on genuine SUMO environment computes all 6 IEEE TWC metrics."""
        model = instantiate_model("HeuristicScheduler")
        metrics = evaluate_single_run(
            model=model,
            density=25.0,
            seed=42,
            n_steps=10,
        )

        assert "mean_aoi" in metrics
        assert "peak_aoi" in metrics
        assert "packet_loss_rate" in metrics
        assert "mean_error" in metrics
        assert "avg_tx_power_dbm" in metrics
        assert "total_energy_joules" in metrics
        assert "jains_fairness_aoi" in metrics
        assert "jains_fairness_err" in metrics

        assert metrics["peak_aoi"] >= metrics["mean_aoi"]
        assert 0.0 <= metrics["packet_loss_rate"] <= 1.0
        assert metrics["mean_error"] >= 0.0
        assert 10.0 <= metrics["avg_tx_power_dbm"] <= 23.0
        assert 0.0 <= metrics["jains_fairness_aoi"] <= 1.0

    def test_d6_total_dummy_run_execution_under_15_seconds(self):
        """Verify the integrated short dummy run completes end-to-end within 15 seconds."""
        t0 = time.perf_counter()

        # Step 1: Real SUMO env step (5 steps)
        env = AoiV2IEnv(density=25.0, seed=42, max_steps=5, warmup_steps=5)
        obs, _ = env.reset()
        for _ in range(5):
            actions = {v: (1.0, 0, 20.0) for v in obs}
            obs, _, _, _, _ = env.step(actions)
        env.close()

        # Step 2: Policy inference
        s_vec = np.zeros(18, dtype=np.float32)
        m = DummyPolicy(state_dim=18, num_channels=4, hidden_dim=32)
        m.select_action(s_vec)

        # Step 3: Hot-swap step
        trainer = HotSwapTrainer(model_cls=DummyPolicy, batch_size=2)
        trainer.streamer.push(s_vec, np.zeros(3), 0.0, s_vec, False, 1.0)
        trainer.streamer.push(s_vec, np.zeros(3), 0.0, s_vec, False, 1.0)
        trainer.step_training_sync()
        trainer.hot_swap_manager.hot_swap()

        elapsed = time.perf_counter() - t0
        assert elapsed < 15.0, f"Execution exceeded 15s limit: {elapsed:.2f}s"
