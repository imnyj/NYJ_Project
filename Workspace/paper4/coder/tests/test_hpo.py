# tests/test_hpo.py
# ============================================================================
# Unit and Integration Tests for Hyperparameter Optimization (Optuna HPO - R3)
# ============================================================================

import json
import math
import os
import optuna
import pandas as pd
import pytest

from src.hpo import (
    CANONICAL_MODEL_NAMES,
    compute_composite_objective,
    evaluate_model_in_env,
    evaluate_trial_multiseed,
    normalize_model_name,
    run_hpo_study,
    sample_hparams,
    sample_reward_weights,
    save_study_results,
)
from tests.contract_adapters import DummyPolicy


class TestHyperparameterOptimization:
    """Test suite verifying all aspects of Optuna HPO."""

    @pytest.mark.parametrize("model_name", CANONICAL_MODEL_NAMES)
    def test_01_search_space_definitions(self, model_name):
        """Verify tailored search space is correctly defined for model names."""
        study = optuna.create_study(direction="minimize")
        trial = study.ask()
        
        params = sample_hparams(trial, model_name)
        assert isinstance(params, dict), f"{model_name}: hparams must be a dict"
        assert len(params) > 0, f"{model_name}: search space must not be empty"

        # Model-specific signature checks
        if model_name in ["HybridPPO", "MAPPO", "HyARPPO"]:
            assert "clip_ratio" in params
            assert "entropy_coef" in params
            assert "value_coef" in params
            assert 0.1 <= params["clip_ratio"] <= 0.3
            assert 1e-4 <= params["entropy_coef"] <= 0.05
        elif model_name == "HybridSAC":
            assert "tau" in params
            assert "lr" in params
            assert "hidden_dim" in params
        elif model_name == "HybridTD3":
            assert "tau" in params
            assert "policy_noise" in params
            assert "noise_clip" in params
            assert "policy_freq" in params
        elif model_name == "MPDQN":
            assert "lr_actor" in params
            assert "lr_critic" in params
            assert "epsilon_initial" in params
            assert "epsilon_decay" in params
        elif model_name == "PureAoI":
            assert "urgency_threshold" in params
            assert 0.1 <= params["urgency_threshold"] <= 0.7
        elif model_name == "DuelingQAoI":
            assert "lr" in params
            assert "epsilon_initial" in params
        elif model_name == "SACAoI":
            assert "lyapunov_v" in params
            assert "aoi_thresh" in params

    def test_02_model_name_normalization_and_aliases(self):
        """Verify alias resolution maps to canonical model names."""
        assert normalize_model_name("H-PPO") == "HybridPPO"
        assert normalize_model_name("H-SAC") == "HybridSAC"
        assert normalize_model_name("H-TD3") == "HybridTD3"
        assert normalize_model_name("HyAR-PPO") == "HyARPPO"
        assert normalize_model_name("MP-DQN") == "MPDQN"
        assert normalize_model_name("PDQN") == "MPDQN"
        assert normalize_model_name("Pure-AoI") == "PureAoI"
        assert normalize_model_name("Dueling-Q-AoI") == "DuelingQAoI"
        assert normalize_model_name("SAC-AoI") == "SACAoI"

    def test_03_composite_objective_monotonicity_and_bounds(self):
        """Verify composite objective penalty increases monotonically with error, AoI, outage, and power."""
        base_metrics = {
            "mean_error": 1.0,
            "mean_aoi": 2.0,
            "outage_rate": 0.05,
            "avg_power_norm": 0.5,
        }
        base_score = compute_composite_objective(base_metrics)

        # 1. Error increase -> Score increase
        err_up = dict(base_metrics, mean_error=2.0)
        assert compute_composite_objective(err_up) > base_score

        # 2. AoI increase -> Score increase
        aoi_up = dict(base_metrics, mean_aoi=4.0)
        assert compute_composite_objective(aoi_up) > base_score

        # 3. Outage rate increase -> Score increase
        outage_up = dict(base_metrics, outage_rate=0.20)
        assert compute_composite_objective(outage_up) > base_score

        # 4. Power increase -> Score increase
        power_up = dict(base_metrics, avg_power_norm=1.0)
        assert compute_composite_objective(power_up) > base_score

    def test_04_env_evaluation_single_seed(self):
        """Verify environment evaluation produces valid IEEE TWC metrics."""
        model = DummyPolicy(state_dim=18, num_channels=4, hidden_dim=32)
        
        metrics = evaluate_model_in_env(
            model=model,
            seed=42,
            n_steps=20,
            n_vehicles=10,
            train_steps_during_rollout=1,
        )

        assert "mean_error" in metrics
        assert "mean_aoi" in metrics
        assert "outage_rate" in metrics
        assert "avg_power_dbm" in metrics
        assert "avg_power_norm" in metrics
        assert "tx_attempts" in metrics

        assert metrics["mean_error"] >= 0.0
        assert metrics["mean_aoi"] > 0.0
        assert 0.0 <= metrics["outage_rate"] <= 1.0
        assert 10.0 <= metrics["avg_power_dbm"] <= 23.0
        assert 0.0 <= metrics["avg_power_norm"] <= 1.0
        assert metrics["tx_attempts"] >= 0

    def test_05_evaluate_trial_multiseed(self):
        """Verify multi-seed evaluation computes averaged composite score and metrics."""
        hparams = {"lr": 1e-3, "hidden_dim": 32, "gamma": 0.98}
        
        score, avg_metrics = evaluate_trial_multiseed(
            model_cls=DummyPolicy,
            hparams=hparams,
            seeds=[42, 101],
            n_steps=15,
            n_vehicles=8,
        )

        assert isinstance(score, float)
        assert not math.isnan(score) and not math.isinf(score)
        assert score > 0.0
        assert "mean_error" in avg_metrics
        assert "mean_aoi" in avg_metrics

    def test_06_optuna_study_single_model_optimization(self):
        """Verify run_hpo_study successfully executes trials and selects optimal parameters."""
        study = run_hpo_study(
            model_name="DummyPolicy",
            model_cls=DummyPolicy,
            n_trials=4,
            seeds=[42],
            n_steps=10,
        )

        assert len(study.trials) == 4
        assert study.best_value is not None
        assert not math.isnan(study.best_value)
        assert study.best_trial.number in [0, 1, 2, 3]

        best_params = study.best_params
        assert len(best_params) > 0

    def test_07_save_study_results_and_csv_generation(self, tmp_path):
        """Verify save_study_results exports trial dataframe and summary record."""
        study = run_hpo_study(
            model_name="DummyPolicy",
            model_cls=DummyPolicy,
            n_trials=3,
            seeds=[42],
            n_steps=10,
        )
        csv_path, record = save_study_results(study, model_name="DummyPolicy", output_dir=str(tmp_path))

        assert os.path.exists(csv_path)
        assert csv_path.endswith("optuna_trials_DummyPolicy.csv")

        df = pd.read_csv(csv_path)
        assert len(df) == 3
        assert "value" in df.columns
        assert "number" in df.columns
        assert "state" in df.columns

        assert record["model_name"] == "DummyPolicy"
        assert len(record["best_params"]) > 0

    def test_08_sample_reward_weights_normalization(self):
        """Verify sample_reward_weights samples w1-w4 normalized to sum to 1.0."""
        study = optuna.create_study(direction="minimize")
        trial = study.ask()
        weights = sample_reward_weights(trial)
        assert "w1" in weights
        assert "w2" in weights
        assert "w3" in weights
        assert "w4" in weights
        total_w = sum(weights.values())
        assert math.isclose(total_w, 1.0, abs_tol=1e-5)

    def test_09_scraped_baseline_raises_error(self):
        """Verify attempting to run HPO for string model without model_cls raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Baseline models scraped"):
            run_hpo_study(model_name="HybridPPO", n_trials=1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
