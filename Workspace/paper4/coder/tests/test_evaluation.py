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

from src.baselines import get_baseline
from src.evaluate import (
    CANONICAL_EVAL_MODELS,
    LEGACY_OUTAGE_METRIC_KEY,
    OUTAGE_METRIC_KEY,
    build_evaluated_model,
    calculate_jains_fairness,
    checkpoint_stem,
    constructor_hparams,
    evaluate_single_run,
    find_checkpoint,
    instantiate_model,
    load_optimal_hparams,
    normalize_model_name,
    normalize_power_dbm,
    run_full_benchmark,
)
from src.heuristic_scheduler import HeuristicScheduler
from tests.contract_adapters import DummyPolicy
from src.rl_interface import P_MAX, P_MIN, STATE_DIM


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
        """The CSV loader keys on current model names and never leaks env-only keys.

        This test used to feed the loader `HybridPPO` and `PureAoI` and assert
        those exact strings came back. Both baselines were discarded on
        2026-08-28, and `normalize_model_name` returns an unrecognised string
        unchanged, so what the test actually pinned down was "the loader accepts
        any garbage name" -- and it sat directly on top of the w1..w4 leak
        (C3) without noticing it. The contract asserted here instead is:
        a retired alias resolves to its replacement, and reward weights never
        survive into a model's hyperparameters.
        """
        from src.hot_swap_trainer import ENV_ONLY_HPARAM_KEYS

        hparams_csv = tmp_path / "test_best_params.csv"
        csv_content = (
            "model_name,category,best_value,best_trial_number,hparams_json,"
            "hidden_dim,lr,w1,w2,w3,w4,w1_raw,reward_weights_json\n"
            'HybridPPO,Category 1 (Basic),4.75,14,'
            '"{""lr"": 0.0003, ""hidden_dim"": 64, ""gamma"": 0.98, ""w1"": 0.079}",'
            '64.0,0.0003,0.079,0.2,0.2,0.1,0.116,"{""w1"": 0.079}"\n'
            'CARLTON,Category 3 (Similar),1.20,6,'
            '"{""omega"": 0.25, ""hidden_dim"": 128}",128.0,,0.5,0.2,0.2,0.1,0.6,"{}"\n'
        )
        hparams_csv.write_text(csv_content)

        loaded = load_optimal_hparams(str(hparams_csv))

        # A retired alias resolves to the baseline that replaced it.
        assert "PPO" in loaded, loaded
        assert "HybridPPO" not in loaded
        assert "CARLTON" in loaded

        assert loaded["PPO"]["hidden_dim"] == 64
        assert isinstance(loaded["PPO"]["hidden_dim"], int)
        assert pytest.approx(loaded["PPO"]["lr"], 1e-5) == 0.0003
        assert pytest.approx(loaded["CARLTON"]["omega"], 1e-4) == 0.25

        # C3: w1..w4, their raw samples and reward_weights_json are AoiV2IEnv
        # arguments. They must not appear in a dict destined for a constructor,
        # whether they arrived as a column or inside hparams_json.
        for name, hp in loaded.items():
            assert not (set(hp) & set(ENV_ONLY_HPARAM_KEYS)), (name, sorted(hp))
            assert "reward_weights_json" not in hp, name

    def test_02b_project_hpo_csv_carries_no_env_only_keys(self):
        """The real committed CSV, loaded through the real loader.

        Mirrors `tests/test_run_all.py::test_26`; the evaluation path had no such
        guard, which is why the leak survived there after run_all.py was fixed.
        """
        from src.hot_swap_trainer import ENV_ONLY_HPARAM_KEYS
        from src.evaluate import DEFAULT_HPARAMS_CSV

        if not os.path.exists(DEFAULT_HPARAMS_CSV):
            pytest.skip("project HPO CSV not present")

        loaded = load_optimal_hparams(DEFAULT_HPARAMS_CSV)
        assert loaded, "project HPO CSV loaded to an empty mapping"
        for name, hp in loaded.items():
            leaked = sorted(set(hp) & set(ENV_ONLY_HPARAM_KEYS))
            assert not leaked, f"{name} still carries env-only keys {leaked}"
            assert "reward_weights_json" not in hp, name

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

        # The emptiness signal survives aggregation. It used to be dropped from
        # both summary tables, so a run that measured nothing looked healthy.
        assert "n_observations" in df_summary.columns
        assert "n_observations" in df_leaderboard.columns
        assert (df_summary["n_observations"] > 0).all()

        # Every table states which outage definition scored it. AoiV2IEnv now
        # exports `coverage_outage_rate`, so the composite must be scored on the
        # coverage definition and never fall back to the frame error rate.
        assert set(df_leaderboard["outage_metric"]) == {OUTAGE_METRIC_KEY}
        assert LEGACY_OUTAGE_METRIC_KEY not in set(df_leaderboard["outage_metric"])


def _save_fake_checkpoint(path, model, hparams, training_steps=12345):
    """Write a bundle in exactly the shape `HotSwapTrainer.save_checkpoint` writes."""
    torch.save(
        {
            "model_name": "CARLTON",
            "hparams": dict(hparams),
            "rest_state_dict": model.state_dict(),
            "act_state_dict": model.state_dict(),
            "training_steps": training_steps,
            "swap_count": 7,
            "best_reward": -1.5,
        },
        str(path),
    )


class TestCheckpointsAreActuallyLoaded:
    """C1. The benchmark used to score randomly initialised networks.

    `src/evaluate.py` contained no `torch.load`, no `load_state_dict` and not
    even the word "checkpoint". `run_all.py` wrote 200,000 steps of training into
    `checkpoints/` and this harness never looked at the directory, so every
    number destined for the paper table came from the weights `__init__` happened
    to draw. The whole 144-test suite passed throughout.
    """

    def test_10_missing_checkpoint_is_fatal_not_silent(self, tmp_path):
        """The failure this defect needed in order to be noticed."""
        empty_dir = tmp_path / "checkpoints"
        empty_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="No checkpoint"):
            build_evaluated_model("CARLTON", {}, checkpoint_dir=str(empty_dir))

        # ... and the whole benchmark refuses to produce a table from it.
        with pytest.raises(FileNotFoundError, match="No checkpoint"):
            run_full_benchmark(
                models=["CARLTON"],
                densities=[25.0],
                seeds=[42],
                output_dir=str(tmp_path / "out"),
                n_steps=10,
                checkpoint_dir=str(empty_dir),
                hparams_csv=str(tmp_path / "nonexistent.csv"),
            )

    def test_11_trained_weights_reach_the_evaluated_model(self, tmp_path):
        """Loading must change the weights; otherwise it is not loading."""
        ckpt_dir = tmp_path / "checkpoints"
        ckpt_dir.mkdir()

        trained = get_baseline("CARLTON")(state_dim=STATE_DIM, num_channels=4, hidden_dim=64)
        with torch.no_grad():
            for p in trained.parameters():
                p.add_(1.25)  # a signature no fresh initialisation would produce
        _save_fake_checkpoint(ckpt_dir / "CARLTON_best.pt", trained, {"hidden_dim": 64})

        loaded, prov = build_evaluated_model("CARLTON", {}, checkpoint_dir=str(ckpt_dir))

        assert prov["checkpoint_loaded"] is True
        assert prov["checkpoint_file"] == "CARLTON_best.pt"
        assert prov["checkpoint_training_steps"] == 12345
        assert prov["checkpoint_weights"] == "act_state_dict"

        expected = trained.state_dict()
        got = loaded.state_dict()
        assert set(expected) == set(got)
        for k in expected:
            assert torch.equal(expected[k].cpu(), got[k].cpu()), k

        # Guard against a vacuous comparison: a fresh model must NOT match.
        fresh = get_baseline("CARLTON")(state_dim=STATE_DIM, num_channels=4, hidden_dim=64)
        assert any(
            not torch.equal(fresh.state_dict()[k].cpu(), expected[k].cpu())
            for k in expected
            if expected[k].is_floating_point() and expected[k].numel()
        ), "fresh weights already equal the trained ones; the test proves nothing"

    def test_12_checkpoint_filenames_use_class_names_not_table_names(self, tmp_path):
        """`run_all.py` injects classes, so files are IHAMAPPO_best.pt, not I-HAMAPPO."""
        ckpt_dir = tmp_path / "checkpoints"
        ckpt_dir.mkdir()
        for fname in ["IHAMAPPO_best.pt", "MADDPGMT_ep003.pt", "MADDPGMT_ep011.pt",
                      "SPAMD3QN_best.pt", "SPAMD3QN_ep002.pt"]:
            (ckpt_dir / fname).write_bytes(b"")

        assert checkpoint_stem("I-HAMAPPO") == "IHAMAPPO"
        assert checkpoint_stem("MADDPG-MT") == "MADDPGMT"

        assert find_checkpoint(str(ckpt_dir), "I-HAMAPPO").endswith("IHAMAPPO_best.pt")
        # No _best.pt for MADDPG-MT, so the highest episode is used -- and 11 > 3
        # must be compared numerically, not as strings.
        assert find_checkpoint(str(ckpt_dir), "MADDPG-MT").endswith("MADDPGMT_ep011.pt")
        assert find_checkpoint(str(ckpt_dir), "SPAM-D3QN").endswith("SPAMD3QN_best.pt")
        assert find_checkpoint(str(ckpt_dir), "SPAM-D3QN", select="last").endswith("SPAMD3QN_ep002.pt")
        assert find_checkpoint(str(ckpt_dir), "CARLTON") is None

    def test_13_checkpoint_hparams_win_over_the_csv(self, tmp_path):
        """The saved tensors were shaped by the checkpoint's hparams, not the CSV's."""
        ckpt_dir = tmp_path / "checkpoints"
        ckpt_dir.mkdir()
        trained = get_baseline("CARLTON")(state_dim=STATE_DIM, num_channels=4, hidden_dim=64)
        _save_fake_checkpoint(ckpt_dir / "CARLTON_best.pt", trained, {"hidden_dim": 64})

        # A stale CSV claims a different width. Trusting it would raise a size
        # mismatch in load_state_dict, or silently load a partial network.
        loaded, prov = build_evaluated_model(
            "CARLTON", {"hidden_dim": 256}, checkpoint_dir=str(ckpt_dir)
        )
        assert prov["checkpoint_loaded"] is True
        for k, v in trained.state_dict().items():
            assert loaded.state_dict()[k].shape == v.shape

    def test_14_opt_out_records_the_row_as_untrained(self, tmp_path):
        """If the abort is waived, the output must still say the weights are random."""
        empty_dir = tmp_path / "checkpoints"
        empty_dir.mkdir()
        model, prov = build_evaluated_model(
            "CARLTON", {}, checkpoint_dir=str(empty_dir), require_checkpoint=False
        )
        assert model is not None
        assert prov["checkpoint_loaded"] is False
        assert prov["checkpoint_file"] == ""

    def test_15_heuristic_needs_no_checkpoint(self, tmp_path):
        """The rule-based reference has no learned weights and must not be blocked."""
        empty_dir = tmp_path / "checkpoints"
        empty_dir.mkdir()
        model, prov = build_evaluated_model(
            "HeuristicScheduler", {}, checkpoint_dir=str(empty_dir), require_checkpoint=True
        )
        assert isinstance(model, HeuristicScheduler)
        assert prov["checkpoint_loaded"] is False

    def test_16_provenance_columns_reach_the_raw_csv(self, tmp_path):
        """Each row of the paper's raw table names the file its numbers came from."""
        out_dir = tmp_path / "out"
        df_raw, _, _ = run_full_benchmark(
            models=["HeuristicScheduler"],
            densities=[25.0],
            seeds=[42],
            output_dir=str(out_dir),
            n_steps=20,
            checkpoint_dir=str(tmp_path / "checkpoints"),
            hparams_csv=str(tmp_path / "nonexistent.csv"),
        )
        for col in ["checkpoint_loaded", "checkpoint_file", "checkpoint_episode",
                    "checkpoint_training_steps", "checkpoint_weights"]:
            assert col in df_raw.columns, col
        written = pd.read_csv(os.path.join(str(out_dir), "eval_raw_runs.csv"))
        assert "checkpoint_loaded" in written.columns


class TestBenchmarkInvariants:
    """The guards that would have caught C3, H5, H6 and L3."""

    def test_17_env_only_and_unknown_keys_never_reach_a_constructor(self):
        """C3, generalised: a whitelist off the signature, not a blacklist.

        Every baseline ends in `**hparams` and hands the remainder to
        `BaseRLModel.__init__`, which only stores it. So a key that is not a
        named argument has no effect at all -- and `density`, `warmup_steps` and
        `rsu_range` would leak exactly the way w1..w4 did the moment such a
        column appears in the CSV.
        """
        from src.hot_swap_trainer import ENV_ONLY_HPARAM_KEYS

        polluted = {
            "hidden_dim": 64, "omega": 0.3,
            "w1": 0.5, "w2": 0.2, "w3": 0.2, "w4": 0.1, "w1_raw": 0.116,
            "density": 25.0, "warmup_steps": 350, "rsu_range": 300.0,
            "reward_weights_json": "{}",
        }
        kept = constructor_hparams(get_baseline("CARLTON"), polluted)
        assert set(kept) == {"hidden_dim", "omega"}
        assert not (set(kept) & set(ENV_ONLY_HPARAM_KEYS))

        # And the model builds. Without the filter, BaseRLModel raises TypeError
        # on w1..w4 while `density` and `warmup_steps` are swallowed in silence.
        model = instantiate_model("CARLTON", polluted)
        assert model.hparams == {}

    def test_18_power_normalisation_uses_the_decoder_bounds(self):
        """L3 / H5. The leaderboard mapped [20, 30] dBm, HPO mapped [10, 23]."""
        from src.rl_interface import P_MAX, P_MIN

        assert (P_MIN, P_MAX) == (10.0, 23.0)
        assert normalize_power_dbm(P_MIN) == pytest.approx(0.0)
        assert normalize_power_dbm(P_MAX) == pytest.approx(1.0)
        # The discarded window collapsed everything below 20 dBm to zero, so the
        # power term was inert over most of the real range.
        assert normalize_power_dbm(16.5) == pytest.approx(0.5)
        assert normalize_power_dbm(12.0) > 0.0

        # HPO must score the identical function; it imports this one.
        import src.hpo as hpo
        assert hpo.normalize_power_dbm is normalize_power_dbm

    def test_19_empty_runs_abort_the_benchmark(self, tmp_path, monkeypatch):
        """H6. A run that measured nothing must not reach the leaderboard."""
        import src.evaluate as ev

        def _empty_run(**kwargs):
            return {
                "density": kwargs["density"], "seed": kwargs["seed"],
                "mean_aoi": 0.0, "peak_aoi": 0.0, "packet_loss_rate": 0.0,
                "mean_error": 0.0, "max_error": 0.0, "low_speed_error": 0.0,
                "high_speed_error": 0.0, "avg_tx_power_dbm": 10.0,
                "total_energy_joules": 0.0, "jains_fairness_aoi": 1.0,
                "jains_fairness_err": 1.0, "tx_attempts": 0, "tx_fails": 0,
                "tx_abandoned": 0, "n_observations": 0, "n_vehicles_seen": 0,
            }

        monkeypatch.setattr(ev, "evaluate_single_run", _empty_run)
        with pytest.raises(RuntimeError, match="No AoI observation"):
            ev.run_full_benchmark(
                models=["HeuristicScheduler"], densities=[25.0], seeds=[42],
                output_dir=str(tmp_path / "out"), n_steps=10,
                checkpoint_dir=str(tmp_path / "ckpt"),
                hparams_csv=str(tmp_path / "none.csv"),
                require_outage_metric=False,
            )

    def test_20_outage_is_coverage_outage(self, tmp_path, monkeypatch):
        """H4, resolved by the user on 2026-08-31: outage is a coverage notion.

        `packet_loss_rate` is the link-layer frame error rate and is a different
        quantity. The benchmark must refuse to build a table under the old
        definition unless the caller says so explicitly, and must score the
        coverage metric when the environment provides it.
        """
        import src.evaluate as ev

        assert ev.OUTAGE_METRIC_KEY == "coverage_outage_rate"

        base = {
            "mean_aoi": 1.0, "peak_aoi": 2.0, "packet_loss_rate": 0.9,
            "mean_error": 0.5, "max_error": 1.0, "low_speed_error": 0.4,
            "high_speed_error": 0.6, "avg_tx_power_dbm": 16.5,
            "total_energy_joules": 0.1, "jains_fairness_aoi": 1.0,
            "jains_fairness_err": 1.0, "tx_attempts": 10, "tx_fails": 1,
            "tx_abandoned": 0, "n_observations": 100, "n_vehicles_seen": 3,
        }

        def _run(**kwargs):
            return {"density": kwargs["density"], "seed": kwargs["seed"], **base}

        monkeypatch.setattr(ev, "evaluate_single_run", _run)
        kwargs = dict(
            models=["HeuristicScheduler"], densities=[25.0], seeds=[42],
            output_dir=str(tmp_path / "out"), n_steps=10,
            checkpoint_dir=str(tmp_path / "ckpt"),
            hparams_csv=str(tmp_path / "none.csv"),
        )

        # The environment does not export the coverage metric yet -> refuse.
        with pytest.raises(RuntimeError, match=ev.OUTAGE_METRIC_KEY):
            ev.run_full_benchmark(**kwargs)

        # Once it does, that is the term the composite scores.
        def _run_with_coverage(**kw):
            return {"density": kw["density"], "seed": kw["seed"],
                    **base, ev.OUTAGE_METRIC_KEY: 0.25}

        monkeypatch.setattr(ev, "evaluate_single_run", _run_with_coverage)
        _, df_summary, df_lb = ev.run_full_benchmark(**kwargs)
        assert set(df_lb["outage_metric"]) == {ev.OUTAGE_METRIC_KEY}
        assert ev.OUTAGE_METRIC_KEY in df_summary.columns
        expected = (
            ev.COMPOSITE_WEIGHTS["error"] * base["mean_error"]
            + ev.COMPOSITE_WEIGHTS["aoi"] * base["mean_aoi"]
            + ev.COMPOSITE_WEIGHTS["outage"] * 0.25
            + ev.COMPOSITE_WEIGHTS["power"] * normalize_power_dbm(base["avg_tx_power_dbm"])
        )
        assert df_lb.iloc[0]["composite_score"] == pytest.approx(round(expected, 4))

    def test_21_heuristic_shares_the_rl_action_bounds(self):
        """H1. The rule-based baseline was confined to a quarter of the Delta range."""

        h = instantiate_model("HeuristicScheduler")

        # The scheduler resolves its own bounds from the ActionDecoder that every
        # RL baseline also uses. This harness must not name them at all: the
        # literals delta_min=0.5 / delta_max=10.0 that used to sit here confined
        # the rule-based reference to about a quarter of the interval range the
        # RL models could use, which disabled the red-phase backoff rule that is
        # this baseline's entire design premise.
        assert h.delta_min == pytest.approx(h.decoder.delta_min)
        assert h.delta_max == pytest.approx(h.decoder.delta_max)
        assert h.p_low == pytest.approx(h.decoder.p_min)
        assert h.p_high == pytest.approx(h.decoder.p_max)
        assert h.delta_max > 10.0, "the discarded literal 10.0 disabled the red-phase backoff"
        assert h.p_low == pytest.approx(P_MIN)
        assert h.p_high == pytest.approx(P_MAX)

        # The scheduler's own fairness flag must be clear, or the benchmark is
        # comparing a deliberately weakened baseline against the RL models.
        assert h.action_space_handicapped is False, (
            "evaluate.py narrowed the heuristic's action space relative to the decoder"
        )

    def test_22_evaluation_reseeds_the_global_random_stream(self):
        """L4. The uplink draw is `random.random()`, seeded nowhere in this file."""
        import random as _random

        model = instantiate_model("HeuristicScheduler")
        _random.seed(999999)  # a stream position no run would land on by itself
        run1 = evaluate_single_run(model, density=25.0, seed=101, n_steps=25)
        _random.seed(1)
        run2 = evaluate_single_run(model, density=25.0, seed=101, n_steps=25)

        for k in ["mean_aoi", "mean_error", "packet_loss_rate", "tx_attempts"]:
            assert run1[k] == pytest.approx(run2[k]), (
                f"{k} depends on the caller's random stream position"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestOpenIntervalsAreClosed:
    """The step budget running out must not silently discard in-flight intervals.

    `AoiV2IEnv.close()` used to drop every SMDP interval that was still open when
    the loop ended, so their accrued dead-reckoning error never reached
    `get_metrics()`. The loss is length-biased -- an interval is likelier to be
    open the longer its Delta -- so what went missing was disproportionately the
    long-Delta decisions carrying the largest accumulated penalty, which is
    exactly the decision variable this paper contributes.
    """

    def test_23_evaluate_single_run_finalises_before_close(self, monkeypatch, caplog):
        import logging as _logging
        import src.evaluate as ev

        seen = {"finalized": 0, "instances": []}
        real_cls = ev.AoiV2IEnv

        class _SpyEnv(real_cls):
            def finalize_open_intervals(self):
                recs = super().finalize_open_intervals()
                seen["finalized"] += len(recs)
                return recs

        def _factory(*a, **k):
            env = _SpyEnv(*a, **k)
            seen["instances"].append(env)
            return env

        monkeypatch.setattr(ev, "AoiV2IEnv", _factory)

        model = ev.instantiate_model("HeuristicScheduler")
        with caplog.at_level(_logging.WARNING):
            ev.evaluate_single_run(model, density=25.0, seed=42, n_steps=60)

        assert seen["instances"], "the spy env was never constructed"
        env = seen["instances"][0]
        assert not env.interval_start_t, "intervals were still open at close()"
        # Guard against a vacuous pass: there must have been something to close.
        assert seen["finalized"] > 0, "no interval was in flight; the test proves nothing"
        assert not [r for r in caplog.records if "discarding" in r.getMessage()], (
            "close() reported discarded SMDP intervals"
        )
