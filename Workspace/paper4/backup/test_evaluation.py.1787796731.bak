# tests/test_evaluation.py
# ============================================================================
# Unit and Integration Tests for Milestone 5 (Evaluation Harness & Benchmark)
#
# Verifies:
# 1. Model Loading & Instantiation from HPO optimal hyperparameters.
# 2. Evaluation execution for all 10 candidate models (Heuristic + 9 RL baselines).
# 3. IEEE TWC 6 metrics mathematical invariants & boundary properties.
# 4. Deterministic multi-seed reproducibility.
# 5. Density scaling & wireless contention behavior.
# 6. CSV output generation, schema integrity, and absence of NaN/Inf values.
# ============================================================================

import os
import numpy as np
import pandas as pd
import pytest
import torch

from src.evaluate import (
    CANONICAL_EVAL_MODELS,
    calculate_jains_fairness,
    evaluate_single_run,
    instantiate_model,
    load_optimal_hparams,
    normalize_model_name,
    run_full_benchmark,
)
from src.heuristic_scheduler import HeuristicScheduler
from src.baselines import BaseRLModel


class TestEvaluationHarness:
    """Comprehensive test suite for evaluation harness and benchmark verification."""

    def test_01_canonical_models_and_name_normalization(self):
        """Verify all 10 canonical evaluation models and alias normalization."""
        assert len(CANONICAL_EVAL_MODELS) == 10
        assert "HeuristicScheduler" in CANONICAL_EVAL_MODELS

        alias_cases = {
            "Heuristic": "HeuristicScheduler",
            "heuristic-dynamic": "HeuristicScheduler",
            "H-PPO": "HybridPPO",
            "h_sac": "HybridSAC",
            "htd3": "HybridTD3",
            "MAPPO": "MAPPO",
            "hyar_ppo": "HyARPPO",
            "pdqn": "MPDQN",
            "Pure-AoI": "PureAoI",
            "dueling_q_aoi": "DuelingQAoI",
            "SAC-AoI": "SACAoI",
        }
        for alias, expected in alias_cases.items():
            assert normalize_model_name(alias) == expected

    def test_02_load_optimal_hparams_from_csv(self, tmp_path):
        """Verify loading and parsing of optimal hyperparameters from CSV."""
        hparams_csv = tmp_path / "test_best_params.csv"
        csv_content = (
            'model_name,category,best_value,best_trial_number,hparams_json,hidden_dim,lr,urgency_threshold\n'
            'HybridPPO,Category 1 (Basic),4.75,14,"{""lr"": 0.0003, ""hidden_dim"": 64, ""gamma"": 0.98}",64.0,0.0003,\n'
            'PureAoI,Category 3 (SOTA AoI),15.9,6,"{""urgency_threshold"": 0.25}",,,0.25\n'
        )
        hparams_csv.write_text(csv_content)

        loaded = load_optimal_hparams(str(hparams_csv))
        assert "HybridPPO" in loaded
        assert "PureAoI" in loaded
        assert loaded["HybridPPO"]["hidden_dim"] == 64
        assert isinstance(loaded["HybridPPO"]["hidden_dim"], int)
        assert pytest.approx(loaded["HybridPPO"]["lr"], 1e-5) == 0.0003
        assert pytest.approx(loaded["PureAoI"]["urgency_threshold"], 1e-4) == 0.25

    def test_03_load_optimal_hparams_missing_file_fallback(self):
        """Verify fallback behavior when hyperparameter file does not exist."""
        loaded = load_optimal_hparams("/non/existent/path.csv")
        assert isinstance(loaded, dict)
        assert len(loaded) == 0

    @pytest.mark.parametrize("model_name", CANONICAL_EVAL_MODELS)
    def test_04_instantiate_all_10_models(self, model_name):
        """Verify clean instantiation of all 10 candidate models."""
        model = instantiate_model(model_name)
        if model_name == "HeuristicScheduler":
            assert isinstance(model, HeuristicScheduler)
        else:
            assert isinstance(model, BaseRLModel)
            assert model.state_dim == 16
            assert model.num_channels == 4

    def test_05_jains_fairness_index_properties(self):
        """Verify mathematical invariants of Jain's Fairness Index."""
        # 1. Perfectly equal distribution -> 1.0
        assert pytest.approx(calculate_jains_fairness([5.0, 5.0, 5.0, 5.0]), 1e-4) == 1.0

        # 2. Completely skewed distribution (1 active, N-1 zero) -> 1/N
        skewed = [10.0, 0.0, 0.0, 0.0]
        assert pytest.approx(calculate_jains_fairness(skewed), 1e-4) == 0.25

        # 3. Empty or all zero -> 1.0
        assert calculate_jains_fairness([]) == 1.0
        assert calculate_jains_fairness([0.0, 0.0, 0.0]) == 1.0

        # 4. Invariant: 0 < J(x) <= 1.0 for non-zero inputs
        random_vals = list(np.random.exponential(scale=2.0, size=20))
        j_val = calculate_jains_fairness(random_vals)
        assert 0.0 < j_val <= 1.0

    @pytest.mark.parametrize("model_name", ["HeuristicScheduler", "HybridPPO", "PureAoI"])
    def test_06_single_evaluation_run_metrics(self, model_name):
        """Verify execution of single evaluation run and validity of all 6 IEEE TWC metrics."""
        model = instantiate_model(model_name)
        res = evaluate_single_run(model, density=25.0, seed=42, n_steps=30)

        # Check required fields
        required_keys = [
            "density", "seed", "mean_aoi", "peak_aoi", "packet_loss_rate",
            "mean_error", "max_error", "low_speed_error", "high_speed_error",
            "avg_tx_power_dbm", "total_energy_joules", "jains_fairness_aoi",
            "jains_fairness_err", "tx_attempts", "tx_fails",
        ]
        for k in required_keys:
            assert k in res, f"Missing key '{k}' in evaluation results"

        # Check mathematical invariants
        assert res["peak_aoi"] >= res["mean_aoi"], "Invariant failed: peak_aoi < mean_aoi"
        assert 0.0 <= res["packet_loss_rate"] <= 1.0, "Outage rate out of [0, 1]"
        assert res["mean_error"] >= 0.0, "Mean error must be non-negative"
        assert res["max_error"] >= res["mean_error"], "Max error must be >= mean error"
        assert 20.0 <= res["avg_tx_power_dbm"] <= 30.0, "Tx power out of bounds [20, 30] dBm"
        assert res["total_energy_joules"] >= 0.0, "Energy must be non-negative"
        assert 0.0 < res["jains_fairness_aoi"] <= 1.0, "Jain's AoI fairness out of (0, 1]"
        assert 0.0 < res["jains_fairness_err"] <= 1.0, "Jain's error fairness out of (0, 1]"

    def test_07_deterministic_multi_seed_reproducibility(self):
        """Verify that identical seed produces identical metric results."""
        torch.manual_seed(42)
        model1 = instantiate_model("HybridPPO")
        model2 = instantiate_model("HybridPPO")
        model2.load_state_dict(model1.state_dict())

        run1 = evaluate_single_run(model1, density=25.0, seed=101, n_steps=25)
        run2 = evaluate_single_run(model2, density=25.0, seed=101, n_steps=25)

        for k in ["mean_aoi", "peak_aoi", "packet_loss_rate", "mean_error", "total_energy_joules"]:
            assert pytest.approx(run1[k], rel=1e-3) == run2[k], f"Mismatch for metric {k}"

    def test_08_density_scaling_contention_effect(self):
        """Verify that higher vehicle density increases co-channel contention and packet loss rate."""
        model = instantiate_model("HeuristicScheduler")

        low_density_run = evaluate_single_run(model, density=15.0, seed=42, n_steps=40)
        high_density_run = evaluate_single_run(model, density=55.0, seed=42, n_steps=40)

        # In high density, contention increases so tx_attempts and packet loss rate are higher
        assert high_density_run["tx_attempts"] > low_density_run["tx_attempts"]
        assert high_density_run["packet_loss_rate"] >= low_density_run["packet_loss_rate"]

    def test_09_run_full_benchmark_end_to_end(self, tmp_path):
        """Verify full benchmark execution on subset of models and export of all 3 CSV files."""
        output_dir = str(tmp_path / "eval_out")
        subset_models = ["HeuristicScheduler", "HybridPPO"]
        subset_densities = [15.0, 35.0]
        subset_seeds = [42, 101]

        df_raw, df_summary, df_leaderboard = run_full_benchmark(
            models=subset_models,
            densities=subset_densities,
            seeds=subset_seeds,
            output_dir=output_dir,
            n_steps=20,
        )

        expected_raw_rows = len(subset_models) * len(subset_densities) * len(subset_seeds)  # 2 * 2 * 2 = 8
        assert len(df_raw) == expected_raw_rows
        assert len(df_summary) == len(subset_models) * len(subset_densities)  # 4
        assert len(df_leaderboard) == len(subset_models)  # 2

        # Check CSV files on disk
        raw_csv = os.path.join(output_dir, "eval_raw_runs.csv")
        summary_csv = os.path.join(output_dir, "eval_summary_by_density.csv")
        leaderboard_csv = os.path.join(output_dir, "eval_leaderboard.csv")

        assert os.path.exists(raw_csv)
        assert os.path.exists(summary_csv)
        assert os.path.exists(leaderboard_csv)

        # Check no NaN values
        assert not df_raw.isnull().any().any(), "Raw runs contain NaN"
        assert not df_summary.isnull().any().any(), "Summary contains NaN"
        assert not df_leaderboard.isnull().any().any(), "Leaderboard contains NaN"

        # Check leaderboard ordering
        assert df_leaderboard.iloc[0]["rank"] == 1
        assert df_leaderboard.iloc[1]["rank"] == 2
        assert df_leaderboard.iloc[0]["composite_score"] <= df_leaderboard.iloc[1]["composite_score"]

    def test_10_production_csv_files_exist_and_valid(self):
        """Verify that the production evaluation results generated in results/eval/ are valid."""
        prod_eval_dir = "/home/imnyj/Workspace/paper4/coder/results/eval"
        raw_csv = os.path.join(prod_eval_dir, "eval_raw_runs.csv")
        summary_csv = os.path.join(prod_eval_dir, "eval_summary_by_density.csv")
        leaderboard_csv = os.path.join(prod_eval_dir, "eval_leaderboard.csv")

        assert os.path.exists(raw_csv), f"Missing {raw_csv}"
        assert os.path.exists(summary_csv), f"Missing {summary_csv}"
        assert os.path.exists(leaderboard_csv), f"Missing {leaderboard_csv}"

        df_raw = pd.read_csv(raw_csv)
        df_summary = pd.read_csv(summary_csv)
        df_leaderboard = pd.read_csv(leaderboard_csv)

        assert len(df_raw) == 250, f"Expected 250 raw runs, got {len(df_raw)}"
        assert len(df_summary) == 50, f"Expected 50 summary rows, got {len(df_summary)}"
        assert len(df_leaderboard) == 10, f"Expected 10 leaderboard models, got {len(df_leaderboard)}"

        # Verify all 10 canonical models are represented
        assert set(df_leaderboard["model_name"]).issubset(set(CANONICAL_EVAL_MODELS))
        assert not df_raw.isnull().any().any(), "Production raw runs contain NaN values"
        assert not df_summary.isnull().any().any(), "Production summary contains NaN values"
        assert not df_leaderboard.isnull().any().any(), "Production leaderboard contains NaN values"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
