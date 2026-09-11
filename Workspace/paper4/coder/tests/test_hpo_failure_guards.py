# tests/test_hpo_failure_guards.py
# ============================================================================
# Regressions for the three defects found in the parallel HPO re-search of
# 2026-09-04 (logs/hpo_parallel/g1.log).
#
# What happened. Two and a half hours into the run the g1 group lost its SUMO
# scenario directory, `results/hpo_parallel/g1/sumo/`. Every rollout after that
# raised FileNotFoundError while opening the generation lock, 62 of them. The
# SAC study lost all 15 of its trials and I-HAMAPPO lost 5 of 15 -- and the run
# reported success, exited 0, and wrote SAC into
# `results/hpo_parallel/g1/optuna_best_params.csv` with `best_value 100.0`, the
# failure penalty, as though it were a tuning result.
#
# Three separate things had to fail for that to reach a CSV:
#   1. the generation lock opened its file with O_CREAT, which creates a file but
#      not the directory holding it, so a vanished directory was fatal instead of
#      self-healing;
#   2. the penalty guard assumed at least one trial would score below the
#      penalty, but the study MINIMISES, so when every trial scores exactly
#      FAILED_RUN_PENALTY the penalty is the minimum and one of the failures is
#      returned as `best_trial`;
#   3. the merge step checked for missing and duplicated models but not for
#      penalty scores, so it would have passed the row through to training.
#
# The tests below cover each in turn. None of them runs a real rollout: the
# objective is stubbed, which is what makes them affordable in the ordinary
# suite.
# ============================================================================

from __future__ import annotations

import importlib.util
import os
import sys

import pandas as pd
import pytest

import src.hpo as hpo
import src.sumo.make_sumo_set as ss
from src.baselines import ALL_BASELINES, get_baseline
from src.hpo import (
    FAILED_RUN_PENALTY,
    AllTrialsFailedError,
    is_penalty_score,
    run_all_baselines_hpo,
    summarize_study_outcome,
)

CODER_DIR = "/home/imnyj/Workspace/paper4/coder"
MERGE_SCRIPT = os.path.join(CODER_DIR, "etc", "merge_hpo_results.py")


# ---------------------------------------------------------------------------
# Defect 1 -- the generation lock has to make the directory it locks in
# ---------------------------------------------------------------------------
class TestGenerationLockCreatesItsDirectory:
    """`os.open(..., O_CREAT)` creates a file, never the directory above it."""

    def test_an_explicit_missing_base_path_is_created(self, tmp_path):
        missing = tmp_path / "never_created" / "sumo"
        assert not missing.exists()

        with ss._generation_lock(str(missing)):
            pass

        assert missing.is_dir()
        assert (missing / ss.GENERATION_LOCK_FILE).exists()

    def test_a_missing_paper4_sumo_dir_is_created(self, tmp_path, monkeypatch):
        """`PAPER4_SUMO_DIR` is read into `BASE_PATH` at import time and the
        directory is made once, right there. A process that runs for hours has no
        guarantee it is still there when it next generates, which is precisely
        what g1 discovered."""
        missing = tmp_path / "group" / "sumo"
        monkeypatch.setattr(ss, "BASE_PATH", str(missing))
        assert not missing.exists()

        with ss._generation_lock():
            pass

        assert (missing / ss.GENERATION_LOCK_FILE).exists()

    def test_the_directory_vanishing_between_acquisitions_is_survived(self, tmp_path):
        """The g1 incident in miniature: the lock is taken once successfully, the
        directory disappears underneath the process, and the next acquisition has
        to work rather than raise FileNotFoundError."""
        import shutil

        base = tmp_path / "sumo"
        with ss._generation_lock(str(base)):
            pass
        shutil.rmtree(base)
        assert not base.exists()

        with ss._generation_lock(str(base)):
            pass

        assert (base / ss.GENERATION_LOCK_FILE).exists()


# ---------------------------------------------------------------------------
# Defect 2 -- a study in which everything failed is not a tuning result
# ---------------------------------------------------------------------------
def _stub_objective(monkeypatch, scores_by_class):
    """Replace the rollout entirely: each model class gets a fixed score.

    `evaluate_trial_multiseed` is the boundary between the search and the SUMO
    simulation, so stubbing it here means no environment is built, no model is
    constructed and no gradient step is taken, while `run_hpo_study`,
    `save_study_results` and `run_all_baselines_hpo` all run for real.
    """
    def fake(model_cls, hparams, seeds, **kwargs):
        score = scores_by_class[model_cls]
        return float(score), {
            "mean_error": 1.0,
            "mean_aoi": 1.0,
            "outage_rate": 0.1,
            "avg_power_norm": 0.5,
            "n_failed_seeds": 3 if is_penalty_score(score) else 0,
            "n_update_failures": 0,
            "n_diverged_seeds": 0,
            "diverged": False,
        }

    monkeypatch.setattr(hpo, "evaluate_trial_multiseed", fake)


class TestAStudyWhereEveryTrialFailed:
    """`direction="minimize"` makes the penalty the minimum once nothing beats it."""

    def test_the_summary_calls_it_failed(self, monkeypatch):
        _stub_objective(monkeypatch, {get_baseline("SAC"): FAILED_RUN_PENALTY})
        study = hpo.run_hpo_study(model_name="SAC", n_trials=3, seeds=[1], n_steps=10)

        summary = summarize_study_outcome(study)
        assert summary["all_trials_failed"] is True
        assert summary["n_usable_trials"] == 0
        assert summary["n_penalised_trials"] == 3
        assert summary["failed_fraction"] == 1.0
        # Optuna itself still reports a best; that is the whole problem.
        assert study.best_value == FAILED_RUN_PENALTY

    def test_a_partial_loss_is_counted_not_hidden(self, monkeypatch):
        """I-HAMAPPO lost 5 of 15 trials and looked healthy. The fraction is what
        makes that visible to a person reading the log or the CSV."""
        cls = get_baseline("I-HAMAPPO")
        values = [FAILED_RUN_PENALTY, 4.0, FAILED_RUN_PENALTY, 3.0]
        calls = {"n": 0}

        def fake(model_cls, hparams, seeds, **kwargs):
            score = values[calls["n"]]
            calls["n"] += 1
            return float(score), {"diverged": False, "n_diverged_seeds": 0}

        monkeypatch.setattr(hpo, "evaluate_trial_multiseed", fake)
        study = hpo.run_hpo_study(model_name="I-HAMAPPO", model_cls=cls,
                                  n_trials=4, seeds=[1], n_steps=10)

        summary = summarize_study_outcome(study)
        assert summary["all_trials_failed"] is False
        assert summary["n_penalised_trials"] == 2
        assert summary["n_usable_trials"] == 2
        assert summary["failed_fraction"] == 0.5
        assert study.best_value == 3.0

    def test_the_failed_model_is_kept_out_of_the_master_csv(self, monkeypatch, tmp_path):
        """The exact g1 shape: SAC failed on every trial, I-HAMAPPO did not."""
        _stub_objective(monkeypatch, {
            get_baseline("SAC"): FAILED_RUN_PENALTY,
            get_baseline("I-HAMAPPO"): 8.9292,
        })

        csv_path, df = run_all_baselines_hpo(
            n_trials=2, output_dir=str(tmp_path),
            models=["I-HAMAPPO", "SAC"], seeds=[1], n_steps=10,
        )

        written = pd.read_csv(csv_path)
        assert list(written["model_name"]) == ["I-HAMAPPO"], (
            "SAC scored nothing but the penalty and must not appear as a tuned model"
        )
        assert not any(is_penalty_score(v) for v in written["best_value"])

        failed = df.attrs["failed_models"]
        assert [f["model_name"] for f in failed] == ["SAC"]
        assert failed[0]["n_usable_trials"] == 0

        # The failure is on disk as well as in memory, because the process that
        # has to act on it is a shell script reading the output directory.
        failures = pd.read_csv(tmp_path / "hpo_failed_models.csv")
        assert list(failures["model_name"]) == ["SAC"]

    def test_the_trial_history_of_the_failed_model_is_still_written(self, monkeypatch, tmp_path):
        """Excluding the row must not throw away the evidence for the exclusion."""
        _stub_objective(monkeypatch, {get_baseline("SAC"): FAILED_RUN_PENALTY})
        run_all_baselines_hpo(n_trials=2, output_dir=str(tmp_path),
                              models=["SAC"], seeds=[1], n_steps=10)

        trials = pd.read_csv(tmp_path / "optuna_trials_SAC.csv")
        assert len(trials) == 2
        assert all(is_penalty_score(v) for v in trials["value"])

    def test_no_master_csv_at_all_when_every_model_failed(self, monkeypatch, tmp_path):
        _stub_objective(monkeypatch, {
            get_baseline("SAC"): FAILED_RUN_PENALTY,
            get_baseline("PPO"): FAILED_RUN_PENALTY,
        })
        csv_path, df = run_all_baselines_hpo(
            n_trials=2, output_dir=str(tmp_path),
            models=["SAC", "PPO"], seeds=[1], n_steps=10,
        )
        assert not os.path.exists(csv_path)
        assert len(df.attrs["failed_models"]) == 2

    def test_one_dead_study_does_not_stop_the_others(self, monkeypatch, tmp_path):
        """A study that raises outright is recorded and skipped; the models after
        it in the list are independent and must still be searched."""
        real_run = hpo.run_hpo_study

        def flaky(model_name, **kwargs):
            if model_name == "SAC":
                raise RuntimeError("scripted study failure")
            return real_run(model_name=model_name, **kwargs)

        _stub_objective(monkeypatch, {get_baseline("PPO"): 5.0})
        monkeypatch.setattr(hpo, "run_hpo_study", flaky)

        csv_path, df = run_all_baselines_hpo(
            n_trials=2, output_dir=str(tmp_path),
            models=["SAC", "PPO"], seeds=[1], n_steps=10,
        )
        assert list(pd.read_csv(csv_path)["model_name"]) == ["PPO"]
        assert [f["model_name"] for f in df.attrs["failed_models"]] == ["SAC"]

    def test_save_study_results_refuses_a_study_with_no_completed_trial(self, tmp_path):
        import optuna

        study = optuna.create_study(direction="minimize")
        study.add_trial(optuna.trial.create_trial(
            state=optuna.trial.TrialState.FAIL, params={}, distributions={},
        ))
        with pytest.raises(AllTrialsFailedError):
            hpo.save_study_results(study, model_name="SAC", output_dir=str(tmp_path))
        # The history is written before the refusal.
        assert (tmp_path / "optuna_trials_SAC.csv").exists()


class TestTheExitCodeReportsFailure:
    """A run that lost a model must not exit 0; the launcher reads the code."""

    def _run_main(self, monkeypatch, tmp_path, argv_models):
        monkeypatch.setattr(sys, "argv", [
            "hpo", "--n-trials", "2", "--seeds", "1",
            "--output-dir", str(tmp_path), "--models", *argv_models,
        ])
        return hpo.main()

    def test_nonzero_when_a_model_failed(self, monkeypatch, tmp_path):
        _stub_objective(monkeypatch, {
            get_baseline("SAC"): FAILED_RUN_PENALTY,
            get_baseline("PPO"): 5.0,
        })
        assert self._run_main(monkeypatch, tmp_path, ["PPO", "SAC"]) == 1

    def test_zero_when_every_model_produced_a_real_score(self, monkeypatch, tmp_path):
        _stub_objective(monkeypatch, {get_baseline("PPO"): 5.0})
        assert self._run_main(monkeypatch, tmp_path, ["PPO"]) == 0


class TestPenaltyPredicate:
    def test_the_penalty_and_anything_worse_is_a_failure(self):
        assert is_penalty_score(FAILED_RUN_PENALTY)
        assert is_penalty_score(FAILED_RUN_PENALTY + 1.0)
        assert is_penalty_score(float("nan"))
        assert is_penalty_score(float("inf"))
        assert is_penalty_score(None)

    def test_a_real_score_is_not(self):
        # 35.815 (PPO) is the worst real score in the nine committed studies.
        for value in (0.925, 8.9292, 35.815, 99.0):
            assert not is_penalty_score(value)


# ---------------------------------------------------------------------------
# Defect 3 -- the merge must not pass a penalty row through to training
# ---------------------------------------------------------------------------
def _load_merge_module():
    spec = importlib.util.spec_from_file_location("merge_hpo_results", MERGE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_group(root, group, rows):
    directory = os.path.join(root, group)
    os.makedirs(directory, exist_ok=True)
    pd.DataFrame(rows).to_csv(os.path.join(directory, "optuna_best_params.csv"), index=False)


def _all_nine(penalised=()):
    """One row per baseline, split into two groups, with `penalised` names failed."""
    rows = []
    for i, name in enumerate(ALL_BASELINES):
        rows.append({
            "model_name": name,
            "category": "Baseline",
            "best_value": FAILED_RUN_PENALTY if name in penalised else 1.0 + i,
            "best_trial_number": 0,
            "hparams_json": "{}",
        })
    return rows[:5], rows[5:]


class TestMergeRefusesPenaltyRows:
    @pytest.fixture
    def merge(self, tmp_path, monkeypatch):
        module = _load_merge_module()
        monkeypatch.setattr(module, "PARALLEL_ROOT", str(tmp_path / "hpo_parallel"))
        monkeypatch.setattr(module, "TARGET_DIR", str(tmp_path / "hpo"))
        monkeypatch.setattr(module, "BACKUP_ROOT", str(tmp_path / "backup"))
        monkeypatch.setattr(sys, "argv", ["merge_hpo_results.py"])
        return module

    def test_a_penalty_row_is_refused(self, merge, capsys):
        g0, g1 = _all_nine(penalised=("SAC",))
        _write_group(merge.PARALLEL_ROOT, "g0", g0)
        _write_group(merge.PARALLEL_ROOT, "g1", g1)

        assert merge.main() == 1
        err = capsys.readouterr().err
        assert "SAC" in err, "the refusal must name the offending model"
        assert not os.path.exists(os.path.join(merge.TARGET_DIR, "optuna_best_params.csv"))

    def test_a_missing_best_value_is_refused_too(self, merge):
        """An unscored row reads as NaN, which is no more mergeable than 100.0."""
        g0, g1 = _all_nine()
        g0[0]["best_value"] = float("nan")
        _write_group(merge.PARALLEL_ROOT, "g0", g0)
        _write_group(merge.PARALLEL_ROOT, "g1", g1)
        assert merge.main() == 1

    def test_a_clean_set_still_merges(self, merge):
        """The control: without the penalty row the same fixture must go through,
        so the refusal is specific rather than a blanket rejection."""
        g0, g1 = _all_nine()
        _write_group(merge.PARALLEL_ROOT, "g0", g0)
        _write_group(merge.PARALLEL_ROOT, "g1", g1)

        assert merge.main() == 0
        merged = pd.read_csv(os.path.join(merge.TARGET_DIR, "optuna_best_params.csv"))
        assert list(merged["model_name"]) == list(ALL_BASELINES)
        assert "_group" not in merged.columns, "the bookkeeping column must not leak"

    def test_the_committed_g1_result_would_be_refused(self, merge):
        """The real file this defect produced. It is read, never modified.

        `results/hpo_parallel/g1/optuna_best_params.csv` holds SAC at best_value
        100.0. If it is ever repaired or re-run this test stops being about the
        historical artefact, so it skips rather than fails when the penalty row
        is gone.
        """
        real = os.path.join(CODER_DIR, "results", "hpo_parallel", "g1",
                            "optuna_best_params.csv")
        if not os.path.exists(real):
            pytest.skip("the 2026-09-04 g1 result is no longer on disk")
        df = pd.read_csv(real)
        if not any(is_penalty_score(v) for v in df["best_value"]):
            pytest.skip("the g1 result no longer contains a penalty row")

        offenders = merge.penalty_rows(df)
        assert any("SAC" in o for o in offenders)
