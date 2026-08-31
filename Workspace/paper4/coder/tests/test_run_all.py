# tests/test_run_all.py
# ============================================================================
# Unit and Integration Tests for run_all.py HPO Parameter Loading and Training
# ============================================================================

import glob
import json
import logging
import os
import subprocess
import sys
import tempfile
import uuid

import pandas as pd
import pytest
import torch

from run_all import (
    get_hparams_for_model,
    load_hparams_from_csv,
    main,
    normalize_model_name,
)
from src.baselines import ALL_BASELINES
from src.hot_swap_trainer import (
    DEFAULT_REWARD_WEIGHTS,
    ENV_ONLY_HPARAM_KEYS,
    AoiV2IEnv,
    split_env_hparams,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write_csv(rows):
    """Write `rows` to a throwaway CSV and return its path."""
    path = os.path.join(tempfile.gettempdir(), f"hparams_{uuid.uuid4().hex}.csv")
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


class TestRunAllHparamsLoading:
    """Unit test suite verifying HPO CSV parsing and model matching."""

    def test_01_load_hparams_from_valid_csv(self, tmp_path):
        csv_file = tmp_path / "test_hparams.csv"
        df = pd.DataFrame([
            {
                "model_name": "PPO",
                "category": "basic",
                "hparams_json": json.dumps({"learning_rate": 0.0005, "gamma": 0.98, "clip_range": 0.25, "n_epochs": 10.0}),
            },
            {
                "model_name": "RES-MAPDDPG",
                "category": "latest",
                "hparams_json": json.dumps({"lr_actor": 0.0001, "hidden_dim": 128.0, "num_res_blocks": 2.0}),
            },
            {
                "model_name": "SPAM-D3QN",
                "category": "similar",
                "hparams_json": json.dumps({"hidden_dim": 256.0, "target_update_freq": 500.0, "num_delta_levels": 8.0}),
            },
        ])
        df.to_csv(csv_file, index=False)

        hparams_map = load_hparams_from_csv(str(csv_file))
        assert "PPO" in hparams_map
        assert hparams_map["PPO"]["learning_rate"] == 0.0005
        assert hparams_map["PPO"]["gamma"] == 0.98
        assert hparams_map["PPO"]["n_epochs"] == 10
        assert isinstance(hparams_map["PPO"]["n_epochs"], int)

        assert "RES-MAPDDPG" in hparams_map
        assert hparams_map["RES-MAPDDPG"]["hidden_dim"] == 128
        assert isinstance(hparams_map["RES-MAPDDPG"]["hidden_dim"], int)
        assert hparams_map["RES-MAPDDPG"]["num_res_blocks"] == 2
        assert isinstance(hparams_map["RES-MAPDDPG"]["num_res_blocks"], int)

        assert "SPAM-D3QN" in hparams_map
        assert hparams_map["SPAM-D3QN"]["hidden_dim"] == 256
        assert isinstance(hparams_map["SPAM-D3QN"]["hidden_dim"], int)
        assert hparams_map["SPAM-D3QN"]["target_update_freq"] == 500
        assert isinstance(hparams_map["SPAM-D3QN"]["target_update_freq"], int)
        assert hparams_map["SPAM-D3QN"]["num_delta_levels"] == 8
        assert isinstance(hparams_map["SPAM-D3QN"]["num_delta_levels"], int)

    def test_02_load_hparams_missing_csv_file(self, caplog):
        with caplog.at_level(logging.WARNING):
            hparams_map = load_hparams_from_csv("/path/to/non_existent_file.csv")
        assert hparams_map == {}
        assert any("not found" in rec.message for rec in caplog.records)

    def test_03_load_hparams_none_or_empty_path(self, caplog):
        with caplog.at_level(logging.WARNING):
            hparams_map = load_hparams_from_csv(None)
        assert hparams_map == {}

        with caplog.at_level(logging.WARNING):
            hparams_map_empty = load_hparams_from_csv("")
        assert hparams_map_empty == {}

    def test_04_load_hparams_empty_csv_file(self, tmp_path, caplog):
        empty_csv = tmp_path / "empty.csv"
        empty_csv.write_text("")
        with caplog.at_level(logging.WARNING):
            hparams_map = load_hparams_from_csv(str(empty_csv))
        assert hparams_map == {}
        assert any("Failed to read" in rec.message for rec in caplog.records)

    def test_05_load_hparams_malformed_json_fallback(self, tmp_path, caplog):
        csv_file = tmp_path / "malformed.csv"
        df = pd.DataFrame([
            {
                "model_name": "SAC",
                "learning_rate": 0.001,
                "gamma": 0.97,
                "hparams_json": "INVALID_JSON_STRING",
            }
        ])
        df.to_csv(csv_file, index=False)

        with caplog.at_level(logging.WARNING):
            hparams_map = load_hparams_from_csv(str(csv_file))
        assert "SAC" in hparams_map
        # Fallback to column values when hparams_json fails
        assert hparams_map["SAC"]["learning_rate"] == 0.001
        assert hparams_map["SAC"]["gamma"] == 0.97

    def test_06_model_name_normalization_and_legacy_aliases(self):
        # Canonical names
        assert normalize_model_name("PPO") == "PPO"
        assert normalize_model_name("RES-MAPDDPG") == "RES-MAPDDPG"
        assert normalize_model_name("I-HAMAPPO") == "I-HAMAPPO"

        # Case-insensitive / hyphen-free aliases
        assert normalize_model_name("ppo") == "PPO"
        assert normalize_model_name("resmapddpg") == "RES-MAPDDPG"
        assert normalize_model_name("res_mapddpg") == "RES-MAPDDPG"
        assert normalize_model_name("i-hamappo") == "I-HAMAPPO"
        assert normalize_model_name("ihamappo") == "I-HAMAPPO"
        assert normalize_model_name("spamd3qn") == "SPAM-D3QN"
        assert normalize_model_name("maddpg_mt") == "MADDPG-MT"

        # Legacy aliases
        assert normalize_model_name("HybridPPO") == "PPO"
        assert normalize_model_name("HybridSAC") == "SAC"
        assert normalize_model_name("HybridTD3") == "TD3"
        assert normalize_model_name("hybridppo") == "PPO"

    def test_07_get_hparams_for_model_matching(self):
        hparams_map = {
            "PPO": {"learning_rate": 0.0003},
            "RES-MAPDDPG": {"lr_actor": 0.0001},
        }

        # Exact match
        assert get_hparams_for_model(hparams_map, "PPO") == {"learning_rate": 0.0003}
        # Canonical/alias match
        assert get_hparams_for_model(hparams_map, "RESMAPDDPG") == {"lr_actor": 0.0001}
        assert get_hparams_for_model(hparams_map, "res-mapddpg") == {"lr_actor": 0.0001}
        assert get_hparams_for_model(hparams_map, "ppo") == {"learning_rate": 0.0003}
        # Not found
        assert get_hparams_for_model(hparams_map, "TD3") is None
        assert get_hparams_for_model({}, "PPO") is None

    def test_08_cli_argument_parsing(self):
        import argparse

        test_args = ["--hparams-csv", "custom/hparams.csv", "--episodes", "2", "--steps-per-episode", "50", "--models", "PPO", "SAC"]
        orig_argv = sys.argv
        try:
            sys.argv = ["run_all.py"] + test_args
            ap = argparse.ArgumentParser()
            ap.add_argument("--models", nargs="*", default=list(ALL_BASELINES))
            ap.add_argument("--episodes", type=int, default=100)
            ap.add_argument("--steps-per-episode", type=int, default=2000)
            ap.add_argument("--seed", type=int, default=42)
            ap.add_argument("--no-resume", action="store_true")
            ap.add_argument("--hparams-csv", type=str, default="results/hpo/optuna_best_params.csv")
            args = ap.parse_args(test_args)
            assert args.hparams_csv == "custom/hparams.csv"
            assert args.episodes == 2
            assert args.steps_per_episode == 50
            assert args.models == ["PPO", "SAC"]
        finally:
            sys.argv = orig_argv


class TestRunAllExecutionIntegration:
    """End-to-end integration tests running run_all.py as a subprocess."""

    def test_09_run_all_with_custom_hparams_csv(self, tmp_path):
        custom_csv = tmp_path / "custom_optuna_best.csv"
        df = pd.DataFrame([
            {
                "model_name": "PPO",
                "category": "Category 1 (Basic)",
                "hparams_json": json.dumps({"learning_rate": 0.0002, "clip_range": 0.15, "ent_coef": 0.001}),
            }
        ])
        df.to_csv(custom_csv, index=False)

        cmd = [
            sys.executable,
            "run_all.py",
            "--episodes", "1",
            "--steps-per-episode", "10",
            "--models", "PPO",
            "--hparams-csv", str(custom_csv),
            "--checkpoint-dir", str(tmp_path / "checkpoints"),
            "--tensorboard-dir", str(tmp_path / "tensorboard"),
        ]
        res = subprocess.run(cmd, cwd="/home/imnyj/Workspace/paper4/coder", capture_output=True, text=True)
        assert res.returncode == 0, f"run_all.py failed: {res.stderr}\nStdout: {res.stdout}"
        output = res.stderr + res.stdout
        assert "Applying HPO hyperparameters for PPO" in output
        assert "All 1 model(s) trained successfully." in output

    def test_10_run_all_with_missing_hparams_csv(self, tmp_path):
        missing_csv = "/tmp/non_existent_params_12345.csv"
        cmd = [
            sys.executable,
            "run_all.py",
            "--episodes", "1",
            "--steps-per-episode", "10",
            "--models", "PPO",
            "--hparams-csv", missing_csv,
            "--checkpoint-dir", str(tmp_path / "checkpoints"),
            "--tensorboard-dir", str(tmp_path / "tensorboard"),
        ]
        res = subprocess.run(cmd, cwd="/home/imnyj/Workspace/paper4/coder", capture_output=True, text=True)
        assert res.returncode == 0, f"run_all.py failed when CSV missing: {res.stderr}\nStdout: {res.stdout}"
        output = res.stderr + res.stdout
        assert "not found" in output or "falling back to default" in output
        assert "All 1 model(s) trained successfully." in output

    def test_11_run_all_with_lowercase_model_cli(self, tmp_path):
        cmd = [
            sys.executable,
            "run_all.py",
            "--episodes", "1",
            "--steps-per-episode", "10",
            "--models", "ppo",
            "--checkpoint-dir", str(tmp_path / "checkpoints"),
            "--tensorboard-dir", str(tmp_path / "tensorboard"),
        ]
        res = subprocess.run(cmd, cwd="/home/imnyj/Workspace/paper4/coder", capture_output=True, text=True)
        assert res.returncode == 0, f"run_all.py failed with lowercase model: {res.stderr}\nStdout: {res.stdout}"
        output = res.stderr + res.stdout
        assert "Starting training for PPO (PPO)" in output
        assert "All 1 model(s) trained successfully." in output

    def test_12_run_all_default_acceptance_criterion(self, tmp_path):
        """Verification acceptance criterion:
        Running python run_all.py --episodes 1 --steps-per-episode 10 --models PPO completes successfully without crashing.
        """
        cmd = [
            sys.executable,
            "run_all.py",
            "--episodes", "1",
            "--steps-per-episode", "10",
            "--models", "PPO",
            "--checkpoint-dir", str(tmp_path / "checkpoints"),
            "--tensorboard-dir", str(tmp_path / "tensorboard"),
        ]
        res = subprocess.run(cmd, cwd="/home/imnyj/Workspace/paper4/coder", capture_output=True, text=True)
        assert res.returncode == 0, f"Default run_all.py command failed: {res.stderr}\nStdout: {res.stdout}"
        output = res.stderr + res.stdout
        assert "All 1 model(s) trained successfully." in output


class TestRunAllAdversarialAndEdgeCases:
    """Adversarial and robustness tests probing edge cases in HPO loading and execution."""

    def test_13_load_hparams_nan_inf_none_sanitization(self, tmp_path):
        csv_file = tmp_path / "nan_hparams.csv"
        df = pd.DataFrame([
            {
                "model_name": "PPO",
                "hparams_json": json.dumps({
                    "learning_rate": 0.0003,
                    "clip_range": float("nan"),
                    "gamma": None,
                    "n_epochs": "NaN",
                }),
                "ent_coef": float("nan"),
                "vf_coef": 0.5,
            }
        ])
        df.to_csv(csv_file, index=False)

        hparams_map = load_hparams_from_csv(str(csv_file))
        assert "PPO" in hparams_map
        ppo_hparams = hparams_map["PPO"]
        assert ppo_hparams["learning_rate"] == 0.0003
        assert ppo_hparams["vf_coef"] == 0.5
        # Corrupted / NaN / None values must be stripped out so defaults can apply
        assert "clip_range" not in ppo_hparams
        assert "gamma" not in ppo_hparams
        assert "n_epochs" not in ppo_hparams
        assert "ent_coef" not in ppo_hparams

    def test_14_load_hparams_duplicate_models_best_score_selection(self, tmp_path):
        """`src/hpo.py` studies are created with direction="minimize", so across
        duplicate rows the better trial is the one with the LOWEST value."""
        csv_file = tmp_path / "multi_trials.csv"
        df = pd.DataFrame([
            {
                "model_name": "PPO",
                "value": 1.10,
                "hparams_json": json.dumps({"learning_rate": 0.001}),
            },
            {
                "model_name": "PPO",
                "value": 1.45,
                "hparams_json": json.dumps({"learning_rate": 0.0003}),
            },
            {
                "model_name": "PPO",
                "value": 0.95,  # lowest composite objective -> the best trial
                "hparams_json": json.dumps({"learning_rate": 0.005}),
            },
        ])
        df.to_csv(csv_file, index=False)

        hparams_map = load_hparams_from_csv(str(csv_file))
        assert "PPO" in hparams_map
        assert hparams_map["PPO"]["learning_rate"] == 0.005

    def test_15_load_hparams_reward_weights_are_not_merged(self, tmp_path):
        """w1..w4 configure AoiV2IEnv, so they must never enter model hparams."""
        csv_file = tmp_path / "rw_hparams.csv"
        df = pd.DataFrame([
            {
                "model_name": "CARLTON",
                "hparams_json": json.dumps({"lr": 0.0002, "hidden_dim": 64}),
                "reward_weights_json": json.dumps({"w1": 0.5, "w2": 0.1, "w3": 0.3, "w4": 0.1}),
            }
        ])
        df.to_csv(csv_file, index=False)

        hparams_map = load_hparams_from_csv(str(csv_file))
        assert "CARLTON" in hparams_map
        carlton_hp = hparams_map["CARLTON"]
        assert carlton_hp == {"lr": 0.0002, "hidden_dim": 64}

    def test_16_load_hparams_params_prefix_columns(self, tmp_path):
        csv_file = tmp_path / "optuna_raw_trial.csv"
        df = pd.DataFrame([
            {
                "model_name": "MA2HDQN",
                "params_hidden_dim": 128,
                "params_lr_q": 0.0005,
                "params_target_sync_interval": 200.0,
                "params_n_step": 3,
            }
        ])
        df.to_csv(csv_file, index=False)

        hparams_map = load_hparams_from_csv(str(csv_file))
        assert "MA2HDQN" in hparams_map
        ma_hp = hparams_map["MA2HDQN"]
        assert ma_hp["hidden_dim"] == 128
        assert isinstance(ma_hp["hidden_dim"], int)
        assert ma_hp["lr_q"] == 0.0005
        assert ma_hp["target_sync_interval"] == 200
        assert isinstance(ma_hp["target_sync_interval"], int)
        assert ma_hp["n_step"] == 3
        assert isinstance(ma_hp["n_step"], int)

    def test_17_load_hparams_user_path_expansion_and_spaces(self, tmp_path):
        # Path with spaces
        spaced_dir = tmp_path / "folder with spaces"
        spaced_dir.mkdir()
        csv_file = spaced_dir / "params.csv"
        df = pd.DataFrame([
            {"model_name": "TD3", "hparams_json": json.dumps({"learning_rate": 0.002})}
        ])
        df.to_csv(csv_file, index=False)

        hparams_map = load_hparams_from_csv(f"  {str(csv_file)}  ")
        assert "TD3" in hparams_map
        assert hparams_map["TD3"]["learning_rate"] == 0.002

    def test_18_load_hparams_boolean_and_integer_casting(self, tmp_path):
        csv_file = tmp_path / "types_cast.csv"
        df = pd.DataFrame([
            {
                "model_name": "CARLTON",
                "hparams_json": json.dumps({
                    "use_target_network": "true",
                    "hidden_dim": "64.0",
                    "num_delta_levels": 8.0,
                }),
            },
            {
                "model_name": "PPO",
                "hparams_json": json.dumps({
                    "normalize_advantage": "false",
                    "n_epochs": 10.0,
                    "rollout_n_steps": 64.0,
                }),
            },
        ])
        df.to_csv(csv_file, index=False)

        hparams_map = load_hparams_from_csv(str(csv_file))
        assert hparams_map["CARLTON"]["use_target_network"] is True
        assert hparams_map["CARLTON"]["hidden_dim"] == 64
        assert isinstance(hparams_map["CARLTON"]["hidden_dim"], int)
        assert hparams_map["CARLTON"]["num_delta_levels"] == 8
        assert isinstance(hparams_map["CARLTON"]["num_delta_levels"], int)

        assert hparams_map["PPO"]["normalize_advantage"] is False
        assert hparams_map["PPO"]["n_epochs"] == 10
        assert isinstance(hparams_map["PPO"]["n_epochs"], int)
        assert hparams_map["PPO"]["rollout_n_steps"] == 64
        assert isinstance(hparams_map["PPO"]["rollout_n_steps"], int)

    def test_19_load_hparams_alternative_model_column_headers(self, tmp_path):
        csv_file = tmp_path / "alt_columns.csv"
        df = pd.DataFrame([
            {
                "baseline": "MADDPG-MT",
                "hparams_json": json.dumps({"actor_lr": 0.0003, "hidden_dim": 128}),
            }
        ])
        df.to_csv(csv_file, index=False)

        hparams_map = load_hparams_from_csv(str(csv_file))
        assert "MADDPG-MT" in hparams_map
        assert hparams_map["MADDPG-MT"]["actor_lr"] == 0.0003
        assert hparams_map["MADDPG-MT"]["hidden_dim"] == 128

    def test_20_get_hparams_for_model_class_objects_and_whitespace(self):
        from src.baselines.sb3_ppo import PPO as PPOClass
        hparams_map = {
            "PPO": {"learning_rate": 0.0003},
            "RES-MAPDDPG": {"lr_actor": 0.0001},
        }

        # Class object lookup
        assert get_hparams_for_model(hparams_map, PPOClass) == {"learning_rate": 0.0003}
        # Whitespace padded lookup
        assert get_hparams_for_model(hparams_map, "  PPO  ") == {"learning_rate": 0.0003}
        assert get_hparams_for_model(hparams_map, "  res_mapddpg  ") == {"lr_actor": 0.0001}

    def test_21_models_cli_all_keyword_expansion(self):
        """Passing --models ALL or --models all should expand to all 9 baselines."""
        import argparse
        orig_argv = sys.argv
        try:
            for all_keyword in ("ALL", "all", "ALL_BASELINES", "*"):
                test_args = ["--models", all_keyword]
                ap = argparse.ArgumentParser()
                ap.add_argument("--models", nargs="*", default=list(ALL_BASELINES))
                ap.add_argument("--episodes", type=int, default=100)
                ap.add_argument("--steps-per-episode", type=int, default=2000)
                ap.add_argument("--seed", type=int, default=42)
                ap.add_argument("--no-resume", action="store_true")
                ap.add_argument("--hparams-csv", type=str, default="results/hpo/optuna_best_params.csv")
                args = ap.parse_args(test_args)
                raw_models = args.models if args.models else list(ALL_BASELINES)
                target_models = []
                for item in raw_models:
                    for token in str(item).replace(",", " ").split():
                        t = token.strip()
                        if not t:
                            continue
                        if t.upper() in ("ALL", "ALL_BASELINES", "*"):
                            target_models.extend(list(ALL_BASELINES))
                        else:
                            target_models.append(t)
                assert len(target_models) == 9
                assert set(target_models) == set(ALL_BASELINES)
        finally:
            sys.argv = orig_argv

    def test_22_models_cli_comma_separated_parsing(self):
        """Passing comma-separated model names like --models PPO,SAC,TD3 should parse accurately."""
        import argparse
        test_args = ["--models", "PPO,SAC,TD3", "RES-MAPDDPG"]
        ap = argparse.ArgumentParser()
        ap.add_argument("--models", nargs="*", default=list(ALL_BASELINES))
        args = ap.parse_args(test_args)
        target_models = []
        for item in args.models:
            for token in str(item).replace(",", " ").split():
                t = token.strip()
                if t:
                    target_models.append(t)
        assert target_models == ["PPO", "SAC", "TD3", "RES-MAPDDPG"]

    def test_23_load_hparams_directory_path_graceful_fallback(self, tmp_path, caplog):
        """Passing a directory path or whitespace-only path should not raise IsADirectoryError and should fallback gracefully."""
        with caplog.at_level(logging.WARNING):
            # Directory path
            hparams_dir = load_hparams_from_csv(str(tmp_path))
            assert hparams_dir == {}
            # Whitespace string
            hparams_ws = load_hparams_from_csv("   ")
            assert hparams_ws == {}
        assert any("not found or is not a regular file" in rec.message or "No HPO params CSV path provided" in rec.message for rec in caplog.records)

    def test_24_main_invalid_episodes_and_steps_exit_code(self, caplog):
        """main() should return exit code 1 when episodes or steps <= 0."""
        with caplog.at_level(logging.ERROR):
            code_0_ep = main(["--episodes", "0", "--steps-per-episode", "10", "--models", "PPO"])
            assert code_0_ep == 1
            code_neg_step = main(["--episodes", "1", "--steps-per-episode", "-5", "--models", "PPO"])
            assert code_neg_step == 1
        assert any("must both be positive integers" in rec.message for rec in caplog.records)

    def test_25_main_programmatic_invocation(self, tmp_path):
        """main() should execute cleanly when invoked programmatically with valid argv arguments."""
        exit_code = main([
            "--episodes", "1",
            "--steps-per-episode", "5",
            "--models", "PPO",
            "--no-resume",
            "--checkpoint-dir", str(tmp_path / "checkpoints"),
            "--tensorboard-dir", str(tmp_path / "tensorboard"),
        ])
        assert exit_code == 0


class TestRewardWeightSeparation:
    """Regression tests for the HPO-injection defects found in the 2026-08-31 audit.

    The reward weights w1..w4 are AoiV2IEnv constructor arguments, but every
    baseline constructor ends in `**hparams`. Before this suite existed, run_all.py
    put w1..w4 into the model hyperparameter dict, the model swallowed them without
    complaint, and the 200k-step runs trained under the default reward while the
    HPO CSV claimed otherwise. Nothing crashed, so all 25 pre-existing tests passed.
    """

    def test_26_project_csv_yields_no_reward_weights(self):
        """The real optuna_best_params.csv must not leak w1..w4 into model hparams."""
        csv_path = os.path.join(REPO_ROOT, "results", "hpo", "optuna_best_params.csv")
        if not os.path.isfile(csv_path):
            pytest.skip("project HPO CSV not present")
        loaded = load_hparams_from_csv(csv_path)
        assert loaded, "expected the project CSV to yield at least one model"
        for model, hp in loaded.items():
            leaked = set(hp) & ENV_ONLY_HPARAM_KEYS
            assert not leaked, f"{model} leaked environment-only keys {sorted(leaked)}"

    def test_27_reward_weight_columns_and_json_are_both_ignored(self):
        """w1..w4 must be stripped whether they arrive as columns or inside JSON."""
        loaded = load_hparams_from_csv(
            _write_csv([{
                "model_name": "PPO",
                "best_value": 1.0,
                "w1": 0.9, "w2": 0.05, "w3": 0.03, "w4": 0.02,
                "w1_raw": 0.7,
                "reward_weights_json": json.dumps({"w1": 0.9, "w2": 0.05}),
                "hparams_json": json.dumps({"learning_rate": 3e-4, "w1": 0.9, "w3": 0.03}),
            }])
        )
        assert loaded["PPO"] == {"learning_rate": 3e-4}

    def test_28_split_env_hparams_partitions_correctly(self):
        model_hp, env_hp = split_env_hparams(
            {"learning_rate": 1e-3, "hidden_dim": 64, "w1": 0.5, "w2_raw": 0.3}
        )
        assert model_hp == {"learning_rate": 1e-3, "hidden_dim": 64}
        assert env_hp == {"w1": 0.5, "w2_raw": 0.3}
        assert split_env_hparams(None) == ({}, {})

    def test_29_env_defaults_match_the_shared_benchmark_weights(self):
        """AoiV2IEnv, the trainer and evaluate.py must all read one constant."""
        env = AoiV2IEnv(density=25.0, seed=0, max_steps=10, warmup_steps=0)
        for key, expected in DEFAULT_REWARD_WEIGHTS.items():
            assert getattr(env, key) == pytest.approx(expected)
        assert sum(DEFAULT_REWARD_WEIGHTS.values()) == pytest.approx(1.0)

    def test_30_duplicate_rows_pick_the_minimising_trial(self):
        """src/hpo.py minimises, so the LOWER best_value is the better trial."""
        csv_path = _write_csv([
            {"model_name": "PPO", "best_value": 2.0,
             "hparams_json": json.dumps({"learning_rate": 0.111})},
            {"model_name": "PPO", "best_value": 1.0,
             "hparams_json": json.dumps({"learning_rate": 0.999})},
        ])
        assert load_hparams_from_csv(csv_path)["PPO"]["learning_rate"] == 0.999

        # ... and the ordering of the rows must not change the answer.
        csv_path_rev = _write_csv([
            {"model_name": "PPO", "best_value": 1.0,
             "hparams_json": json.dumps({"learning_rate": 0.999})},
            {"model_name": "PPO", "best_value": 2.0,
             "hparams_json": json.dumps({"learning_rate": 0.111})},
        ])
        assert load_hparams_from_csv(csv_path_rev)["PPO"]["learning_rate"] == 0.999

    def test_31_scoreless_row_never_displaces_a_scored_one(self):
        csv_path = _write_csv([
            {"model_name": "PPO", "best_value": 1.0,
             "hparams_json": json.dumps({"learning_rate": 0.999})},
            {"model_name": "PPO", "best_value": None,
             "hparams_json": json.dumps({"learning_rate": 0.111})},
        ])
        assert load_hparams_from_csv(csv_path)["PPO"]["learning_rate"] == 0.999

    def test_32_no_alias_duplicate_entries(self):
        """One entry per model, keyed canonically; aliases resolve on lookup."""
        loaded = load_hparams_from_csv(
            _write_csv([{"model_name": "hybridppo", "best_value": 1.0,
                         "hparams_json": json.dumps({"learning_rate": 1e-4})}])
        )
        assert list(loaded) == ["PPO"]
        assert get_hparams_for_model(loaded, "hybridppo") == {"learning_rate": 1e-4}
        assert get_hparams_for_model(loaded, "PPO") == {"learning_rate": 1e-4}

    def test_33_container_values_do_not_raise(self):
        """pd.isna returns an array for a list; `if <array>` used to blow up."""
        loaded = load_hparams_from_csv(
            _write_csv([{"model_name": "PPO", "best_value": 1.0,
                         "hparams_json": json.dumps({"learning_rate": 1e-4,
                                                     "net_arch": [64, 64]})}])
        )
        assert loaded["PPO"] == {"learning_rate": 1e-4}

    def test_34_checkpoints_are_written_where_told_and_carry_no_weights(self, tmp_path):
        """End-to-end: --checkpoint-dir is honoured and w1..w4 never reach the model.

        This is the test that would have caught the original defect. The evidence
        for it was `checkpoints/CARLTON_best.pt`, whose stored hparams contained
        'w1': 0.523336 -- a reward weight sitting inside a model's checkpoint.
        """
        ckpt_dir = tmp_path / "checkpoints"
        before = set(glob.glob(os.path.join(REPO_ROOT, "checkpoints", "*.pt")))

        csv_file = tmp_path / "params.csv"
        pd.DataFrame([{
            "model_name": "PPO",
            "best_value": 1.0,
            "w1": 0.9, "w2": 0.05, "w3": 0.03, "w4": 0.02,
            "hparams_json": json.dumps({"learning_rate": 0.0002}),
        }]).to_csv(csv_file, index=False)

        res = subprocess.run(
            [sys.executable, "run_all.py",
             "--episodes", "1", "--steps-per-episode", "10", "--models", "PPO",
             "--no-resume",
             "--hparams-csv", str(csv_file),
             "--checkpoint-dir", str(ckpt_dir),
             "--tensorboard-dir", str(tmp_path / "tensorboard")],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        assert res.returncode == 0, f"run_all.py failed: {res.stderr}"

        written = sorted(ckpt_dir.glob("*.pt"))
        assert written, "no checkpoint landed in the directory we asked for"

        after = set(glob.glob(os.path.join(REPO_ROOT, "checkpoints", "*.pt")))
        assert after == before, f"production checkpoints touched: {sorted(after - before)}"

        stored = torch.load(written[0], map_location="cpu", weights_only=False)
        leaked = set(stored.get("hparams", {})) & ENV_ONLY_HPARAM_KEYS
        assert not leaked, f"reward weights reached the model: {sorted(leaked)}"

