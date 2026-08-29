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

from src.baselines import BASELINE_REGISTRY
from src.hpo import (
    CANONICAL_MODEL_NAMES,
    compute_composite_objective,
    evaluate_model_in_env,
    evaluate_trial_multiseed,
    normalize_model_name,
    run_all_baselines_hpo,
    run_hpo_study,
    sample_hparams,
    save_study_results,
)


class TestHyperparameterOptimization:
    """Test suite verifying all aspects of Optuna HPO for 9 baselines."""

    @pytest.mark.parametrize("model_name", CANONICAL_MODEL_NAMES)
    def test_01_search_space_definitions_for_all_9_baselines(self, model_name):
        """Verify tailored search space is correctly defined for all 9 baseline models."""
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

        # Verify model can actually be initialized with these sampled parameters
        model_cls = BASELINE_REGISTRY[model_name]
        instance = model_cls(state_dim=16, num_channels=4, **params)
        assert instance is not None
        assert instance.state_dim == 16
        assert instance.num_channels == 4

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
        model_cls = BASELINE_REGISTRY["HybridPPO"]
        model = model_cls(state_dim=16, num_channels=4, hidden_dim=32)
        
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
        assert 20.0 <= metrics["avg_power_dbm"] <= 30.0
        assert 0.0 <= metrics["avg_power_norm"] <= 1.0
        assert metrics["tx_attempts"] > 0

    def test_05_evaluate_trial_multiseed(self):
        """Verify multi-seed evaluation computes averaged composite score and metrics."""
        model_cls = BASELINE_REGISTRY["HybridSAC"]
        hparams = {"lr": 1e-3, "hidden_dim": 32, "gamma": 0.98, "tau": 0.01}
        
        score, avg_metrics = evaluate_trial_multiseed(
            model_cls=model_cls,
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
            model_name="HybridTD3",
            n_trials=4,
            seeds=[42],
            n_steps=10,
        )

        assert len(study.trials) == 4
        assert study.best_value is not None
        assert not math.isnan(study.best_value)
        assert study.best_trial.number in [0, 1, 2, 3]

        best_params = study.best_params
        assert "lr" in best_params
        assert "hidden_dim" in best_params
        assert "gamma" in best_params
        assert "tau" in best_params
        assert "policy_noise" in best_params

    def test_07_save_study_results_and_csv_generation(self, tmp_path):
        """Verify save_study_results exports trial dataframe and summary record."""
        study = run_hpo_study(
            model_name="PureAoI",
            n_trials=3,
            seeds=[42],
            n_steps=10,
        )
        csv_path, record = save_study_results(study, model_name="PureAoI", output_dir=str(tmp_path))

        assert os.path.exists(csv_path)
        assert csv_path.endswith("optuna_trials_PureAoI.csv")

        df = pd.read_csv(csv_path)
        assert len(df) == 3
        assert "value" in df.columns
        assert "number" in df.columns
        assert "state" in df.columns
        assert "params_urgency_threshold" in df.columns

        assert record["model_name"] == "PureAoI"
        assert record["category"] == "Category 3 (SOTA AoI)"
        assert "urgency_threshold" in record["best_params"]

    def test_08_run_all_baselines_hpo_pipeline(self, tmp_path):
        """Verify full HPO pipeline for multiple models with master summary CSV generation."""
        test_models = ["HybridPPO", "PureAoI"]
        master_csv, df_best = run_all_baselines_hpo(
            n_trials=2,
            output_dir=str(tmp_path),
            models=test_models,
            seeds=[42],
            n_steps=10,
        )

        assert os.path.exists(master_csv)
        assert master_csv.endswith("optuna_best_params.csv")

        # Master CSV validation
        loaded_df = pd.read_csv(master_csv)
        assert len(loaded_df) == 2
        assert set(loaded_df["model_name"]).issubset(set(test_models))
        assert "best_value" in loaded_df.columns
        assert "best_trial_number" in loaded_df.columns
        assert "hparams_json" in loaded_df.columns

        # Verify json deserialization
        for _, row in loaded_df.iterrows():
            params_dict = json.loads(row["hparams_json"])
            assert isinstance(params_dict, dict)
            assert len(params_dict) > 0

        # Verify per-model trials CSVs also exist
        for m in test_models:
            trial_csv = os.path.join(str(tmp_path), f"optuna_trials_{m}.csv")
            assert os.path.exists(trial_csv)

    def test_09_unknown_model_raises_error(self):
        """Verify attempting to run HPO with an unknown model raises ValueError."""
        with pytest.raises(ValueError, match="Unknown baseline model"):
            run_hpo_study(model_name="NonExistentModel", n_trials=1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
