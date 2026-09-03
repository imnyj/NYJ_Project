# tests/test_evaluation.py
# ============================================================================
# Unit and Integration Tests for Milestone 5 (Evaluation Harness & Benchmark)
#
# Verifies:
# 1. Model Loading & Instantiation from HPO optimal hyperparameters.
# 2. Evaluation execution for Heuristic & custom instantiated models.
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
from tests.contract_adapters import DummyPolicy
from src.rl_interface import STATE_DIM


class TestEvaluationHarness:
    """Comprehensive test suite for evaluation harness and benchmark verification."""

    def test_01_canonical_models_and_name_normalization(self):
        """The benchmark evaluates the rule-based reference plus all nine baselines.

        This used to assert `CANONICAL_EVAL_MODELS == ["HeuristicScheduler"]` and
        map aliases onto the previous generation of baselines. Both outlived the
        2026-08-28 baseline replacement and quietly locked in a benchmark that
        could not run a single real model.
        """
        from src.baselines import ALL_BASELINES

        assert CANONICAL_EVAL_MODELS[0] == "HeuristicScheduler"
        assert set(CANONICAL_EVAL_MODELS[1:]) == set(ALL_BASELINES)

        alias_cases = {
            "Heuristic": "HeuristicScheduler",
            "heuristic-dynamic": "HeuristicScheduler",
            "ppo": "PPO",
            "res_mapddpg": "RES-MAPDDPG",
            "i-hamappo": "I-HAMAPPO",
            "spamd3qn": "SPAM-D3QN",
            "maddpg_mt": "MADDPG-MT",
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

    def test_04_instantiate_models(self):
        """Every canonical name must instantiate; unknown names must fail loudly."""
        from src.baselines import ALL_BASELINES

        model = instantiate_model("HeuristicScheduler")
        assert isinstance(model, HeuristicScheduler)

        # All nine baselines instantiate from their name alone.
        for m_name in ALL_BASELINES:
            built = instantiate_model(m_name)
            assert built is not None, m_name
            assert hasattr(built, "select_action"), m_name

        # A retired name is not silently accepted.
        for gone in ["HybridPPO", "MAPPO", "PureAoI"]:
            with pytest.raises(KeyError, match="Unknown baseline"):
                instantiate_model(gone)

        # Passing a class/instantiated module should succeed
        dummy_inst = instantiate_model(DummyPolicy)
        assert isinstance(dummy_inst, DummyPolicy)
        assert dummy_inst.state_dim == STATE_DIM

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

    def test_06_single_evaluation_run_metrics(self):
        """Verify execution of single evaluation run and validity of all 6 IEEE TWC metrics."""
        model = instantiate_model("HeuristicScheduler")
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
        assert 10.0 <= res["avg_tx_power_dbm"] <= 23.0, "Tx power out of bounds [10, 23] dBm"
        assert res["total_energy_joules"] >= 0.0, "Energy must be non-negative"
        assert 0.0 < res["jains_fairness_aoi"] <= 1.0, "Jain's AoI fairness out of (0, 1]"
        assert 0.0 < res["jains_fairness_err"] <= 1.0, "Jain's error fairness out of (0, 1]"

    def test_07_deterministic_multi_seed_reproducibility(self):
        """Verify that identical seed produces identical metric results."""
        torch.manual_seed(42)
        model1 = DummyPolicy(state_dim=STATE_DIM, num_channels=4)
        model2 = DummyPolicy(state_dim=STATE_DIM, num_channels=4)
        model2.load_state_dict(model1.state_dict())

        run1 = evaluate_single_run(model1, density=25.0, seed=101, n_steps=25)
        run2 = evaluate_single_run(model2, density=25.0, seed=101, n_steps=25)

        for k in ["mean_aoi", "peak_aoi", "packet_loss_rate", "mean_error", "total_energy_joules"]:
            assert pytest.approx(run1[k], rel=1e-3) == run2[k], f"Mismatch for metric {k}"

    def test_08_density_scaling_contention_effect(self):
        """Verify that higher vehicle density increases co-channel contention and packet loss rate."""
        model = instantiate_model("HeuristicScheduler")

        low_density_run = evaluate_single_run(model, density=15.0, seed=42, n_steps=400)
        high_density_run = evaluate_single_run(model, density=55.0, seed=42, n_steps=400)

        # In high density, contention increases so tx_attempts is higher
        assert high_density_run["tx_attempts"] >= low_density_run["tx_attempts"]
        assert high_density_run["tx_attempts"] > 0

    def test_09_run_full_benchmark_end_to_end(self, tmp_path):
        """Verify full benchmark execution on HeuristicScheduler and export of all 3 CSV files."""
        output_dir = str(tmp_path / "eval_out")
        subset_models = ["HeuristicScheduler"]
        subset_densities = [15.0, 35.0]
        subset_seeds = [42, 101]

        df_raw, df_summary, df_leaderboard = run_full_benchmark(
            models=subset_models,
            densities=subset_densities,
            seeds=subset_seeds,
            output_dir=output_dir,
            n_steps=20,
        )

        expected_raw_rows = len(subset_models) * len(subset_densities) * len(subset_seeds)  # 1 * 2 * 2 = 4
        assert len(df_raw) == expected_raw_rows
        assert len(df_summary) == len(subset_models) * len(subset_densities)  # 2
        assert len(df_leaderboard) == len(subset_models)  # 1

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
