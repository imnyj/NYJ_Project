# tests/test_hpo.py
# ============================================================================
# Unit and Integration Tests for Hyperparameter Optimization (Optuna HPO - R3)
# ============================================================================

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
from src.rl_interface import STATE_DIM


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

        # Model-specific signature checks.
        #
        # Every branch here used to be keyed on a baseline that was discarded on
        # 2026-08-28 (HybridPPO, HybridSAC, HybridTD3, MPDQN, PureAoI,
        # DuelingQAoI, SACAoI). `CANONICAL_MODEL_NAMES` never contains any of
        # them, so no branch could match and all nine parametrised cases reduced
        # to `isinstance(params, dict)` -- while `sample_hparams` itself was
        # keyed on the same dead names, which is the bug this test existed to
        # catch. The branches below name the models that actually exist.
        expected_keys = {
            # hidden_dim is searched for the three SB3 baselines so the nine
            # models can be compared at comparable capacity; without it their
            # parameter counts differ by 71x.
            "PPO": {"hidden_dim", "learning_rate", "gamma", "clip_range", "ent_coef",
                    "vf_coef", "n_epochs"},
            "SAC": {"hidden_dim", "learning_rate", "gamma", "tau", "target_update_interval"},
            "TD3": {"hidden_dim", "learning_rate", "gamma", "tau", "policy_delay",
                    "target_policy_noise", "target_noise_clip"},
            "RES-MAPDDPG": {"hidden_dim", "lr_actor", "lr_critic", "gamma", "tau",
                            "num_res_blocks", "epsilon_decay"},
            # `n_step` is absent on purpose: the uniform-sampling SMDP buffer
            # cannot build an n-step return, so the model reports
            # n_step_active=False and searching it would tune a no-op.
            "MA2HDQN": {"hidden_dim", "lr_q", "lr_actor", "lr_critic", "gamma", "tau",
                        "epsilon_decay"},
            "I-HAMAPPO": {"hidden_dim", "lr_actor", "lr_critic", "gamma", "clip_ratio",
                          "entropy_coef", "value_coef"},
            "SPAM-D3QN": {"hidden_dim", "lr", "gamma", "target_update_freq",
                          "epsilon_decay", "per_alpha"},
            # `tau` is absent on purpose: CARLTON removes the target network
            # (use_target_network=False), which is the published method's claim,
            # so tau has nothing to move.
            "CARLTON": {"hidden_dim", "lr", "gamma", "omega"},
            "MADDPG-MT": {"hidden_dim", "actor_lr", "critic_lr", "gamma", "tau",
                          "global_critic_weight", "gumbel_tau"},
        }
        assert model_name in expected_keys, f"{model_name} has no search-space contract here"
        assert set(params) == expected_keys[model_name], (
            f"{model_name}: sampled {sorted(params)}, expected {sorted(expected_keys[model_name])}"
        )

        # Ranges that the paper quotes.
        if "clip_ratio" in params:
            assert 0.1 <= params["clip_ratio"] <= 0.3
        if "clip_range" in params:
            assert 0.1 <= params["clip_range"] <= 0.3
        for coef in ("entropy_coef", "ent_coef"):
            if coef in params:
                assert 1e-4 <= params[coef] <= 0.05
        assert 0.95 <= params["gamma"] <= 0.999

    def test_02_model_name_normalization_and_aliases(self):
        """Alias resolution maps to the canonical names in the baseline registry."""
        from src.baselines import ALL_BASELINES, get_baseline

        # Punctuation and case are the only things an alias may differ by.
        assert normalize_model_name("ppo") == "PPO"
        assert normalize_model_name("res_mapddpg") == "RES-MAPDDPG"
        assert normalize_model_name("RESMAPDDPG") == "RES-MAPDDPG"
        assert normalize_model_name("i-hamappo") == "I-HAMAPPO"
        assert normalize_model_name("spamd3qn") == "SPAM-D3QN"
        assert normalize_model_name("maddpg_mt") == "MADDPG-MT"

        # Every registered baseline resolves to itself.
        for name in ALL_BASELINES:
            assert normalize_model_name(name) == name

        # A class, not a string, resolves through its own __name__.
        assert normalize_model_name(get_baseline("PPO")) == "PPO"

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
        model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        
        metrics = evaluate_model_in_env(
            model=model,
            seed=42,
            n_steps=20,
            train_steps_during_rollout=1,
        )

        assert "mean_error" in metrics
        assert "mean_aoi" in metrics
        assert "outage_rate" in metrics
        assert "avg_power_dbm" in metrics
        assert "avg_power_norm" in metrics
        assert "tx_attempts" in metrics

        # The emptiness signals must always be present. Without them
        # `compute_composite_objective` cannot tell a rollout that measured
        # nothing from a rollout that measured a perfect policy.
        assert "n_observations" in metrics
        assert "run_failed" in metrics
        assert "n_update_failures" in metrics
        assert metrics["n_update_failures"] == 0

        assert metrics["mean_error"] >= 0.0
        assert metrics["mean_aoi"] > 0.0
        assert 0.0 <= metrics["outage_rate"] <= 1.0
        assert 10.0 <= metrics["avg_power_dbm"] <= 23.0
        assert 0.0 <= metrics["avg_power_norm"] <= 1.0
        assert metrics["tx_attempts"] >= 0

    def test_05_evaluate_trial_multiseed(self):
        """Multi-seed evaluation must return a score from rollouts that measured something.

        This used to run DummyPolicy for 15 steps and assert only `score > 0.0`.
        `evaluate_trial_multiseed` returns the failure penalty when every seed
        raises, so the assertion passed for a total failure -- the one outcome it
        existed to catch. It now runs a real baseline long enough to transmit and
        asserts that no seed failed and that the score is a measured one.
        """
        from src.baselines import get_baseline
        from src.hpo import FAILED_RUN_PENALTY

        hparams = {"lr": 1e-3, "hidden_dim": 64, "gamma": 0.98}

        score, avg_metrics = evaluate_trial_multiseed(
            model_cls=get_baseline("CARLTON"),
            hparams=hparams,
            seeds=[42, 101],
            n_steps=40,
        )

        assert isinstance(score, float)
        assert not math.isnan(score) and not math.isinf(score)
        assert score > 0.0
        assert avg_metrics["n_failed_seeds"] == 0, "a seed rollout failed or measured nothing"
        assert avg_metrics["n_update_failures"] == 0, "model.update() raised during the rollout"
        assert score < FAILED_RUN_PENALTY, "score is the failure penalty, not a measurement"
        assert avg_metrics["n_observations"] > 0
        assert avg_metrics["tx_attempts"] > 0
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

    def test_09_string_model_name_resolves_through_the_registry(self):
        """A bare model name must be enough; model_cls is optional.

        This test used to assert the opposite -- that a string raised
        NotImplementedError("Baseline models scraped") -- which locked in a
        regression: evaluate.py and hpo.py had kept the discarded model names
        after the baselines were replaced, so neither could construct any of the
        nine real models. An unknown name must still fail, and loudly.
        """
        from src.hpo import CANONICAL_MODEL_NAMES

        assert "PPO" in CANONICAL_MODEL_NAMES
        study = run_hpo_study(model_name="PPO", n_trials=1, seeds=[42], n_steps=8)
        assert study.best_trial is not None

        with pytest.raises(KeyError, match="Unknown baseline"):
            run_hpo_study(model_name="HybridPPO", n_trials=1, seeds=[42], n_steps=8)


class TestEmptyRunIsNotTheGlobalOptimum:
    """A rollout that measured nothing must never win a minimisation study.

    `AoiV2IEnv.get_metrics` degrades to zeros when no vehicle was ever in range,
    and every term of the composite is a penalty, so an unmeasured run scored
    exactly 0.0 -- below every real trial (the committed studies sit in
    0.887..1.459). Any hyperparameter combination that happened to kill the
    environment was therefore selected as "optimal". Nothing in the 144-test
    suite caught this.
    """

    def test_all_zero_metrics_score_the_failure_penalty(self):
        from src.hpo import FAILED_RUN_PENALTY

        dead = {
            "mean_error": 0.0,
            "mean_aoi": 0.0,
            "outage_rate": 0.0,
            "avg_power_norm": 0.0,
            "n_observations": 0,
            "tx_attempts": 0,
        }
        assert compute_composite_objective(dead) == FAILED_RUN_PENALTY

    def test_empty_run_never_beats_a_real_trial(self):
        """The exact failure mode: an empty run must not rank below a healthy one."""
        healthy = {
            "mean_error": 1.0, "mean_aoi": 2.0, "outage_rate": 0.05,
            "avg_power_norm": 0.5, "n_observations": 900, "tx_attempts": 30,
        }
        for dead in (
            {"mean_error": 0.0, "mean_aoi": 0.0, "outage_rate": 0.0,
             "avg_power_norm": 0.0, "n_observations": 0, "tx_attempts": 12},
            {"mean_error": 0.0, "mean_aoi": 0.0, "outage_rate": 0.0,
             "avg_power_norm": 0.0, "n_observations": 900, "tx_attempts": 0},
            {"mean_error": 0.0, "mean_aoi": 0.0, "outage_rate": 0.0,
             "avg_power_norm": 0.0, "run_failed": True},
        ):
            assert compute_composite_objective(dead) > compute_composite_objective(healthy)

    def test_run_is_empty_tolerates_absent_signals(self):
        """A pre-aggregated dict that says nothing about emptiness is not empty."""
        from src.hpo import run_is_empty

        assert not run_is_empty({"mean_error": 1.0, "mean_aoi": 2.0})
        assert run_is_empty({"n_observations": 0})
        assert run_is_empty({"tx_attempts": 0})
        assert not run_is_empty({"n_observations": 5, "tx_attempts": 5})

    def test_rollout_marks_and_reports_its_own_emptiness(self):
        """The live path must attach the signals, not just tolerate them."""
        from src.hpo import FAILED_RUN_PENALTY

        model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        metrics = evaluate_model_in_env(model=model, seed=42, n_steps=15)

        assert "n_observations" in metrics and "tx_attempts" in metrics
        assert metrics["run_failed"] == (
            metrics["n_observations"] <= 0 or metrics["tx_attempts"] <= 0
        )
        if metrics["run_failed"]:
            assert compute_composite_objective(metrics) == FAILED_RUN_PENALTY


class TestOutageIsCoverageOutage:
    """Outage is the coverage definition, fixed by the user on 2026-08-31."""

    def test_objective_prefers_the_coverage_metric_over_frame_errors(self):
        from src.evaluate import LEGACY_OUTAGE_METRIC_KEY, OUTAGE_METRIC_KEY

        assert OUTAGE_METRIC_KEY == "coverage_outage_rate"
        assert LEGACY_OUTAGE_METRIC_KEY == "packet_loss_rate"

        # `outage_rate` is what the composite reads; when the environment
        # provides the coverage metric it must be that one, not the frame
        # error rate the two columns used to share.
        metrics = {
            "mean_error": 1.0, "mean_aoi": 2.0, "avg_power_norm": 0.5,
            "n_observations": 900, "tx_attempts": 30,
            "outage_rate": 0.4,
        }
        with_coverage = compute_composite_objective(metrics)
        assert with_coverage == pytest.approx(1.0 + 0.5 * 2.0 + 2.0 * 0.4 + 0.2 * 0.5)

    def test_rollout_tags_which_outage_definition_it_scored(self):
        model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        metrics = evaluate_model_in_env(model=model, seed=42, n_steps=15)
        from src.evaluate import LEGACY_OUTAGE_METRIC_KEY, OUTAGE_METRIC_KEY

        assert metrics["outage_metric"] in (OUTAGE_METRIC_KEY, LEGACY_OUTAGE_METRIC_KEY)
        if OUTAGE_METRIC_KEY in metrics:
            assert metrics["outage_metric"] == OUTAGE_METRIC_KEY
            assert metrics["outage_rate"] == metrics[OUTAGE_METRIC_KEY]



def _probe_value(model_cls, key: str):
    """A type-correct probe value for `key`, taken from the constructor default.

    Typing the probe off the declared default is what keeps this test honest: a
    literal guess would either crash on an int-typed knob or, worse, be silently
    coerced. A key no constructor in the MRO declares gets an arbitrary value --
    which is fine, because that is exactly the case the test must flag.
    """
    import inspect as _inspect

    for klass in getattr(model_cls, "__mro__", [model_cls]):
        init = klass.__dict__.get("__init__")
        if init is None:
            continue
        try:
            prm = _inspect.signature(init).parameters.get(key)
        except (TypeError, ValueError):
            continue
        if prm is None or prm.default is _inspect.Parameter.empty:
            continue
        default = prm.default
        if isinstance(default, bool):
            return not default
        if isinstance(default, int):
            return int(default) + 1 if default else 4
        if isinstance(default, float):
            return float(default) * 0.5 if default else 0.123
        if default is None:
            # An `Optional[...] = None` knob carries its type only in the
            # annotation. `hidden_dim: Optional[int] = None` on the three SB3
            # wrappers is the live case: falling through to the 0.123 float
            # probe made `apply_hidden_dim` reject it as non-positive, which
            # looked like a search-space defect and was really a probe defect.
            ann = prm.annotation
            ann_s = ann if isinstance(ann, str) else getattr(ann, "__name__", str(ann))
            if "bool" in ann_s:
                return True
            if "int" in ann_s:
                return 128 if key == "hidden_dim" else 4
            if "float" in ann_s:
                return 0.123
    return 0.123


class TestHparamsActuallyReachModels:
    """Optuna's search space must land on real constructor arguments.

    All nine baselines end their __init__ with **hparams, so a key that does not
    match a named parameter is swallowed without error and the trial trains at
    library defaults while reporting a tuned value. That is exactly what happened
    between 2026-08-28 and 2026-08-30: sample_hparams was still keyed on the
    discarded model names, so every branch missed and only `gamma` took effect.
    """

    def test_every_sampled_key_is_a_real_constructor_argument(self):
        from src.hpo import CANONICAL_MODEL_NAMES, assert_hparams_reach_model

        unreachable = {
            name: missing
            for name in CANONICAL_MODEL_NAMES
            if (missing := assert_hparams_reach_model(name))
        }
        assert not unreachable, (
            f"These sampled hyperparameters would vanish into **hparams: {unreachable}"
        )

    def test_every_sampled_key_is_actually_CONSUMED_by_the_model(self):
        """Name matching is not consumption. This checks the value was absorbed.

        Every baseline `__init__` ends in `**hparams` and forwards the remainder
        up the chain; `BaseAgent.__init__` is the terminus and parks whatever is
        left on `self.hparams` purely for the save file. So "the key is still in
        `model.hparams` after construction" is an EXACT test for "no constructor
        in the MRO named it, and it therefore changed nothing" -- and unlike a
        signature whitelist on the leaf class it does not reject keys that are
        legitimately forwarded through `super().__init__(**hparams)` chains or
        through the SB3 wrappers' `**algo_kwargs`.

        Measured before the routing fix: `density=55.0`, `warmup_steps=9` and
        `total_nonsense=1` were all accepted in silence by SPAMD3QN, PPO and
        CARLTON, so an HPO CSV column could claim a value the run never used.
        """
        from src.baselines import get_baseline
        from src.hpo import CANONICAL_MODEL_NAMES, _search_space_keys
        from src.rl_interface import STATE_DIM as _SD

        swallowed = {}
        for name in CANONICAL_MODEL_NAMES:
            cls = get_baseline(name)
            keys = list(_search_space_keys(name))
            probe = {k: _probe_value(cls, k) for k in keys}
            model = cls(state_dim=_SD, num_channels=4, **probe)
            leftovers = getattr(model, "hparams", {}) or {}
            unused = sorted(k for k in keys if k in leftovers)
            if unused:
                swallowed[name] = unused
        assert not swallowed, (
            "these sampled hyperparameters were absorbed by `**hparams` and had no "
            f"effect on training: {swallowed}"
        )

    def test_the_consumption_check_would_catch_a_bogus_key(self):
        """Guard against the test above passing vacuously."""
        from src.baselines import get_baseline
        from src.rl_interface import STATE_DIM as _SD

        model = get_baseline("CARLTON")(state_dim=_SD, num_channels=4, total_nonsense=1)
        assert "total_nonsense" in (getattr(model, "hparams", {}) or {})

    def test_search_space_is_not_the_generic_fallback(self):
        """Each baseline needs its own space, not the three-key default."""
        from src.hpo import CANONICAL_MODEL_NAMES, _search_space_keys

        generic = {"lr", "hidden_dim", "gamma"}
        for name in CANONICAL_MODEL_NAMES:
            keys = set(_search_space_keys(name))
            assert keys != generic, f"{name} is falling through to the generic fallback"
            assert len(keys) >= 4, f"{name} samples only {sorted(keys)}"

    def test_sampled_values_take_effect_at_runtime(self):
        """Name matching is necessary but not sufficient -- check the value lands."""
        from src.baselines import get_baseline

        ppo = get_baseline("PPO")(
            state_dim=STATE_DIM, num_channels=4,
            learning_rate=9.9e-4, clip_range=0.29, ent_coef=0.049,
        )
        sb3 = ppo._sb3
        assert sb3.policy.optimizer.param_groups[0]["lr"] == pytest.approx(9.9e-4)
        assert sb3.clip_range(1.0) == pytest.approx(0.29)
        assert sb3.ent_coef == pytest.approx(0.049)

        carlton = get_baseline("CARLTON")(
            state_dim=STATE_DIM, num_channels=4, lr=7e-4, omega=0.77,
        )
        assert carlton.optimizer.param_groups[0]["lr"] == pytest.approx(7e-4)
        assert carlton.omega == pytest.approx(0.77)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestOpenIntervalsReachTheBuffer:
    """HPO's training rollout must not lose the intervals open at the cut-off.

    `evaluate_model_in_env` pushes a transition only when `step()` reports the
    interval closed, so every interval still in flight when the step budget ran
    out was dropped -- measured at 12.3 % of a 600-step episode, biased towards
    long Delta. The trial then tuned hyperparameters against a buffer that had
    seen long-Delta successes but not long-Delta failures.
    """

    def test_finalised_intervals_are_pushed_and_nothing_is_discarded(self, monkeypatch, caplog):
        import logging as _logging
        import src.hpo as hpo
        from src.baselines import get_baseline

        seen = {"finalized": 0, "instances": []}
        real_cls = hpo.AoiV2IEnv

        class _SpyEnv(real_cls):
            def finalize_open_intervals(self):
                recs = super().finalize_open_intervals()
                seen["finalized"] += len(recs)
                return recs

        def _factory(*a, **k):
            env = _SpyEnv(*a, **k)
            seen["instances"].append(env)
            return env

        monkeypatch.setattr(hpo, "AoiV2IEnv", _factory)

        model = get_baseline("CARLTON")(state_dim=STATE_DIM, num_channels=4, hidden_dim=64)
        with caplog.at_level(_logging.WARNING):
            hpo.evaluate_model_in_env(
                model=model, seed=42, n_steps=60, train_steps_during_rollout=1
            )

        assert seen["instances"], "the spy env was never constructed"
        env = seen["instances"][0]
        assert not env.interval_start_t, "intervals were still open at close()"
        assert seen["finalized"] > 0, "no interval was in flight; the test proves nothing"
        assert not [r for r in caplog.records if "discarding" in r.getMessage()], (
            "close() reported discarded SMDP intervals"
        )


# ============================================================================
# Divergence guard, wired into HPO
#
# Why these exist. Every learning rate that destroyed a 200,000-step training
# run on 2026-09-02 was chosen by src/hpo.py, and HPO could not have known: its
# objective is `mean_error / mean_aoi / outage / power`, and a policy whose loss
# has run away still produces ordinary values for all four. Nothing in the
# objective read the loss. These tests hold the wiring in place.
#
# The rollout tests below drive `evaluate_model_in_env` against a stub
# environment rather than SUMO. That is deliberate and is not the kind of
# mocking this project forbids: no number here is reported as a result. They
# check that a loss trace of a known shape produces a known verdict, in a few
# milliseconds, so that removing the wiring fails a test instead of failing a
# 200,000-step run. The corresponding claim about the REAL environment -- that
# the two hyperparameter sets which actually diverged are caught inside
# DEFAULT_HPO_N_STEPS -- is measured in
# `results/hpo/divergence_detection_check.csv`, not asserted here.
# ============================================================================

import numpy as np

import src.divergence_guard as dg
import src.hpo as hpo
from src.hot_swap_trainer import BackgroundTrainer
from src.hpo import (
    DEFAULT_HPO_N_STEPS,
    FAILED_RUN_PENALTY,
    HPO_CHECK_INTERVAL_STEPS,
    HPO_LOSS_WINDOW,
    RolloutLossTracker,
    make_divergence_monitor,
    run_diverged,
)


class _StubEnv:
    """The narrowest environment `evaluate_model_in_env` will accept.

    One vehicle, whose SMDP interval closes on every step, so a gradient update
    happens on every step once the buffer holds 16 transitions. That makes the
    step index and the update index proportional and the tests below short.
    """

    def __init__(self, *args, **kwargs):
        self.max_steps = int(kwargs.get("max_steps", 100))
        self.t = 0
        self.vid = "v0"

    def _obs(self):
        return {self.vid: np.full(STATE_DIM, 0.1, dtype=np.float32)}

    def reset(self):
        return self._obs(), {}

    def step(self, action_dict):
        self.t += 1
        completed = [{
            "vid": self.vid, "reward": -0.01, "done": False, "delta_actual": 1.0,
            "transmitted": True,
        }]
        info = {"completed": completed, "needs_decision": [self.vid]}
        return self._obs(), {self.vid: -0.01}, {}, {}, info

    def finalize_open_intervals(self):
        return []

    def get_metrics(self):
        return {
            "mean_error": 1.0, "mean_aoi": 1.0, "coverage_outage_rate": 0.1,
            "packet_loss_rate": 0.1, "avg_tx_power_dbm": 15.0,
            "n_observations": 100 * self.t, "tx_attempts": self.t,
        }

    def close(self):
        pass


class _ScriptedLossModel(DummyPolicy):
    """A policy whose `update()` reports losses from a script, in order.

    The weights are irrelevant; what is under test is what the rollout does with
    the number `update()` returns, which before this change it discarded.
    """

    def __init__(self, losses, **kwargs):
        super().__init__(state_dim=STATE_DIM, num_channels=4, hidden_dim=8, **kwargs)
        self._losses = list(losses)
        self.n_update_calls = 0

    def update(self, batch):
        idx = min(self.n_update_calls, len(self._losses) - 1)
        self.n_update_calls += 1
        return {"loss": float(self._losses[idx])}


def _rollout(monkeypatch, losses, n_steps=1200, **kwargs):
    monkeypatch.setattr(hpo, "AoiV2IEnv", _StubEnv)
    model = _ScriptedLossModel(losses)
    return hpo.evaluate_model_in_env(
        model=model, seed=7, n_steps=n_steps, train_steps_during_rollout=1, **kwargs
    )


class TestHpoAndTrainingJudgeDivergenceIdentically:
    """One rule, one module. Two thresholds would let HPO pass what training aborts."""

    def test_monitor_is_configured_from_the_shared_defaults(self):
        state = make_divergence_monitor().state()
        assert state["loss_abs_floor"] == dg.DEFAULT_LOSS_ABS_FLOOR
        assert state["loss_ratio"] == dg.DEFAULT_LOSS_RATIO
        assert state["loss_patience"] == dg.DEFAULT_LOSS_PATIENCE
        assert state["warmup_episodes"] == dg.DEFAULT_WARMUP_EPISODES
        assert state["max_zero_update_episodes"] == dg.DEFAULT_MAX_ZERO_UPDATE_EPISODES

    def test_hpo_holds_no_threshold_of_its_own(self):
        """`src/hpo.py` must not restate a number the guard already owns."""
        import inspect
        source = inspect.getsource(hpo)
        body = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        assert "DivergenceMonitor(" not in body.replace(
            "return DivergenceMonitor(", ""
        ), "construct the monitor through make_divergence_monitor()"

    def test_loss_window_matches_the_trainers(self):
        """The monitor is fed the same statistic in both places or the two
        verdicts are not comparable: the trainer averages `loss_history[-50:]`."""
        tracker = RolloutLossTracker()
        assert tracker.losses.maxlen == HPO_LOSS_WINDOW == 50

        values = [float(i) for i in range(200)]
        for v in values:
            tracker.observe_update({"loss": v})
        expected = round(float(np.mean(values[-HPO_LOSS_WINDOW:])), 4)
        assert tracker.mean_recent_loss == expected

    def test_finiteness_uses_the_trainers_predicate(self):
        tracker = RolloutLossTracker()
        tracker.observe_update({"loss": 1.0, "actor_loss": float("nan")})
        assert tracker.consecutive_nonfinite == 1
        assert not BackgroundTrainer._loss_dict_is_finite({"loss": 1.0, "actor_loss": float("nan")})


class TestDivergingRolloutIsCaught:
    """A rollout whose loss runs away must be condemned and scored the penalty."""

    def test_sustained_high_loss_is_flagged(self, monkeypatch):
        metrics = _rollout(monkeypatch, losses=[1.0e9])
        assert metrics["diverged"] is True
        assert metrics["divergence_kind"] == dg.ABORT_DIVERGED
        assert metrics["divergence_rule"] == "sustained_high_loss"
        assert compute_composite_objective(metrics) == FAILED_RUN_PENALTY

    def test_nonfinite_loss_is_flagged_without_waiting_for_a_boundary(self, monkeypatch):
        """A NaN poisons the weights at the update that produced it, so the
        verdict must not wait for the next `HPO_CHECK_INTERVAL_STEPS` boundary."""
        metrics = _rollout(monkeypatch, losses=[float("nan")])
        assert metrics["diverged"] is True
        assert metrics["divergence_rule"] == "non_finite_update_streak"
        assert metrics["steps_completed"] < HPO_CHECK_INTERVAL_STEPS

    def test_the_rollout_stops_instead_of_finishing(self, monkeypatch):
        """Stopping is what makes a 4000-step rollout affordable: the trials that
        would cost the most are exactly the ones already known to have failed."""
        metrics = _rollout(monkeypatch, losses=[1.0e9], n_steps=4000)
        assert metrics["diverged"] is True
        assert metrics["steps_completed"] < 4000

    def test_a_healthy_rollout_is_not_flagged(self, monkeypatch):
        """The control. A guard that condemns everything proves nothing."""
        rng = np.random.default_rng(0)
        losses = list(np.abs(rng.normal(0.5, 0.2, size=4000)))
        metrics = _rollout(monkeypatch, losses=losses)
        assert metrics["diverged"] is False
        assert metrics["steps_completed"] == 1200
        assert compute_composite_objective(metrics) < FAILED_RUN_PENALTY

    def test_a_recoverable_spike_is_not_flagged(self, monkeypatch):
        """I-HAMAPPO/mean hit 145,990 at one episode, 4,141 at the next and 0.79
        at the one after, then trained for 83 more episodes. `loss_patience` is
        what keeps that run alive, and it has to survive the HPO wiring too."""
        # One pseudo-episode's worth of updates at a huge loss, then back down.
        losses = [1.0e9] * HPO_CHECK_INTERVAL_STEPS + [0.5] * 4000
        metrics = _rollout(monkeypatch, losses=losses)
        assert metrics["diverged"] is False

    def test_the_guard_can_be_turned_off(self, monkeypatch):
        metrics = _rollout(monkeypatch, losses=[1.0e9], check_divergence=False)
        assert metrics["diverged"] is False
        assert metrics["steps_completed"] == 1200

    def test_buffer_fill_is_not_mistaken_for_a_gradient_stall(self, monkeypatch):
        """No update can happen until 16 SMDP intervals have closed. Counting
        those opening steps as zero-update pseudo-episodes would trip the stall
        rule on every healthy rollout, so the clock starts at the first update."""
        metrics = _rollout(monkeypatch, losses=[0.5] * 4000)
        assert metrics["diverged"] is False
        assert metrics["n_grad_updates"] > 0


class TestDivergingTrialIsPenalised:
    """Trial-level scoring, which is what Optuna actually selects on."""

    @staticmethod
    def _patch_seeds(monkeypatch, verdicts):
        """Make each seed's rollout return a canned metrics dict."""
        calls = {"n": 0}

        def fake_rollout(**kwargs):
            i = calls["n"]
            calls["n"] += 1
            diverged = verdicts[i]
            return {
                "mean_error": 1.0, "mean_aoi": 1.0, "outage_rate": 0.1,
                "avg_power_norm": 0.5, "n_observations": 100, "tx_attempts": 10,
                "n_update_failures": 0, "run_failed": False,
                "diverged": diverged,
                "divergence_kind": dg.ABORT_DIVERGED if diverged else "",
                "divergence_rule": "sustained_high_loss" if diverged else "",
                "divergence_reason": "scripted" if diverged else "",
                "divergence_episode": 3 if diverged else -1,
                "divergence_mean_loss": 1.0e9 if diverged else float("nan"),
                "steps_completed": 600 if diverged else 4000,
                "n_grad_updates": 1200,
            }

        monkeypatch.setattr(hpo, "evaluate_model_in_env", fake_rollout)
        return calls

    def test_one_diverged_seed_of_three_fails_the_trial(self, monkeypatch):
        """A per-seed penalty alone is not enough at the real score scale: one
        penalised seed of three averages to at least 33.3, and PPO's worst
        HEALTHY committed trial scored 35.815."""
        self._patch_seeds(monkeypatch, [False, True, False])
        score, avg = evaluate_trial_multiseed(
            model_cls=DummyPolicy, hparams={}, seeds=[1, 2, 3], n_steps=10
        )
        assert score == FAILED_RUN_PENALTY
        assert avg["diverged"] is True
        assert avg["n_diverged_seeds"] == 1

    def test_a_healthy_trial_keeps_its_real_score(self, monkeypatch):
        self._patch_seeds(monkeypatch, [False, False, False])
        score, avg = evaluate_trial_multiseed(
            model_cls=DummyPolicy, hparams={}, seeds=[1, 2, 3], n_steps=10
        )
        assert score < FAILED_RUN_PENALTY
        assert avg["diverged"] is False
        assert avg["n_diverged_seeds"] == 0

    def test_the_verdict_reaches_the_trial_attributes(self, monkeypatch):
        """Without this the trial CSV cannot tell a rejected trial from a bad
        one, which is the state the 2026-09-02 studies were left in."""
        self._patch_seeds(monkeypatch, [True, False, False])
        study = optuna.create_study(direction="minimize")
        trial = study.ask()
        score, avg = evaluate_trial_multiseed(
            model_cls=DummyPolicy, hparams={}, seeds=[11, 22, 33], n_steps=10, trial=trial,
        )
        assert trial.user_attrs["diverged_seed11"] is True
        assert trial.user_attrs["diverged_seed22"] is False
        assert avg["divergence_rule"] == "sustained_high_loss"
        assert avg["divergence_seed"] == 11
        assert avg["divergence_at_env_step"] == 600

    def test_a_diverging_study_cannot_report_a_clean_best_row(self, monkeypatch, tmp_path):
        """If every trial diverges, `study.best_trial` is a diverged trial and
        its hyperparameters would go straight into a 200,000-step run."""
        self._patch_seeds(monkeypatch, [True] * 100)
        study = run_hpo_study(
            model_name="DummyPolicy", model_cls=DummyPolicy, n_trials=2,
            seeds=[1], n_steps=10,
        )
        assert all(t.value == FAILED_RUN_PENALTY for t in study.trials)
        _, record = save_study_results(study, model_name="DummyPolicy", output_dir=str(tmp_path))
        assert record["best_trial_diverged"] is True
        assert record["n_diverged_trials"] == 2


class TestRolloutLengthCanSeeDivergence:
    """The length has to admit a verdict at all, which 350 steps did not."""

    def test_default_length_admits_the_full_patience_window(self):
        needed = HPO_CHECK_INTERVAL_STEPS * dg.DEFAULT_LOSS_PATIENCE
        assert DEFAULT_HPO_N_STEPS >= needed, (
            f"a verdict needs {needed} steps of sustained over-threshold loss and "
            f"the rollout is only {DEFAULT_HPO_N_STEPS}"
        )
        # The old 350 could not have produced one.
        assert 350 < needed

    def test_default_length_admits_the_relative_rule_too(self):
        """The absolute floor fires from the first pseudo-episode, but the
        relative rule needs `warmup_episodes` to establish a per-model scale
        first, and models in this pipeline settle four orders of magnitude
        apart (SPAM-D3QN at 5e-4, CARLTON at 12)."""
        needed = HPO_CHECK_INTERVAL_STEPS * (
            dg.DEFAULT_WARMUP_EPISODES + dg.DEFAULT_LOSS_PATIENCE
        )
        assert DEFAULT_HPO_N_STEPS >= needed


class TestDivergenceThatArrivesAsACrash:
    """Divergence does not always present as a large loss.

    Once NaN is in the weights, SB3 raises `ValueError: Expected parameter loc
    ... found invalid values: tensor([[nan, nan, nan]])` out of the next
    `select_action`, before the non-finite-loss streak can reach its threshold.
    That is verbatim how the PPO worker died on 2026-09-02, and it is also what
    a 2000-step HPO rollout of PPO does at SB3's own default learning rate
    (measured 2026-09-03). Scoring it FAILED_RUN_PENALTY as an unexplained
    exception was already the right number; recording WHY is what lets the trial
    CSV distinguish a diverging hyperparameter set from a coding error.
    """

    class _NaNThenCrashModel(_ScriptedLossModel):
        def __init__(self):
            super().__init__(losses=[float("nan")])
            self.poisoned = False

        def update(self, batch):
            self.poisoned = True
            return super().update(batch)

        def select_action(self, state, deterministic=False):
            if self.poisoned:
                raise ValueError(
                    "Expected parameter loc of distribution Normal to satisfy the "
                    "constraint Real(), but found invalid values: tensor([[nan, nan, nan]])"
                )
            return super().select_action(state, deterministic)

    class _CleanCrashModel(_ScriptedLossModel):
        """Crashes with no non-finite loss behind it: an ordinary bug."""

        def __init__(self):
            super().__init__(losses=[0.5])
            self.calls = 0

        def select_action(self, state, deterministic=False):
            self.calls += 1
            if self.calls > 40:
                raise RuntimeError("size mismatch in forward()")
            return super().select_action(state, deterministic)

    def test_a_crash_after_a_nan_loss_is_recorded_as_divergence(self, monkeypatch):
        monkeypatch.setattr(hpo, "AoiV2IEnv", _StubEnv)
        model = self._NaNThenCrashModel()
        metrics = hpo.evaluate_model_in_env(
            model=model, seed=7, n_steps=1200, train_steps_during_rollout=1
        )
        assert metrics["diverged"] is True
        assert metrics["divergence_rule"] == "crash_after_nonfinite_loss"
        assert metrics["max_consecutive_nonfinite_losses"] >= 1
        assert compute_composite_objective(metrics) == FAILED_RUN_PENALTY

    def test_a_crash_with_no_nan_behind_it_is_still_raised(self, monkeypatch):
        """Relabelling every exception as divergence would bury real bugs."""
        monkeypatch.setattr(hpo, "AoiV2IEnv", _StubEnv)
        with pytest.raises(RuntimeError, match="size mismatch"):
            hpo.evaluate_model_in_env(
                model=self._CleanCrashModel(), seed=7, n_steps=1200,
                train_steps_during_rollout=1,
            )


# ============================================================================
# The rollout must hand the buffer everything the training path hands it.
#
# `evaluate_model_in_env` used to discard the `info` dict `select_action`
# returns, so an HPO trial trained the five discrete-head baselines on a
# re-derived action index and the two PPO-family baselines on no importance
# ratio at all -- while `run_hot_swap_training` gave both models the real thing.
# A search that measures a model under different conditions than training runs it
# cannot promise that its chosen hyper-parameters transfer. The same defect, in
# the form of tuned reward weights that never reached the trainer, has already
# been fixed once in this project.
#
# The live measurement across both paths is in
# `results/hpo/behaviour_logp_wiring_check.csv`; what is asserted here is the
# wiring, so that removing it fails a test instead of costing a search.
# ============================================================================
class TestRolloutForwardsWhatTheModelReported:
    class _ReportingModel(DummyPolicy):
        """A policy with both a discrete head and a log-probability to report."""

        def __init__(self, **kwargs):
            super().__init__(state_dim=STATE_DIM, num_channels=4, hidden_dim=8, **kwargs)
            self.seen_batches = []
            self.calls = 0

        def select_action(self, state, deterministic=False):
            grant, raw, info = super().select_action(state, deterministic)
            self.calls += 1
            info = dict(info)
            info["action_idx"] = self.calls % 4
            info["log_prob"] = -0.25 * self.calls
            return grant, raw, info

        def update(self, batch):
            self.seen_batches.append(sorted(batch.keys()))
            return {"loss": 0.1}

    def _run(self, monkeypatch):
        monkeypatch.setattr(hpo, "AoiV2IEnv", _StubEnv)
        model = self._ReportingModel()
        hpo.evaluate_model_in_env(model=model, seed=7, n_steps=60,
                                  train_steps_during_rollout=1, check_divergence=False)
        assert model.seen_batches, "the rollout never trained, so nothing was measured"
        return model

    def test_the_discrete_action_index_reaches_the_batch(self, monkeypatch):
        model = self._run(monkeypatch)
        assert all("action_idx" in keys for keys in model.seen_batches)

    def test_the_behaviour_log_prob_reaches_the_batch(self, monkeypatch):
        model = self._run(monkeypatch)
        assert all("behaviour_log_prob" in keys for keys in model.seen_batches)

    def test_a_model_that_reports_neither_gets_neither(self, monkeypatch):
        """The legacy key set is preserved for the purely continuous baselines."""
        monkeypatch.setattr(hpo, "AoiV2IEnv", _StubEnv)

        class _Silent(self._ReportingModel):
            def select_action(self, state, deterministic=False):
                grant, raw, _info = super().select_action(state, deterministic)
                return grant, raw, {}

        model = _Silent()
        hpo.evaluate_model_in_env(model=model, seed=7, n_steps=60,
                                  train_steps_during_rollout=1, check_divergence=False)
        assert model.seen_batches
        for keys in model.seen_batches:
            assert "action_idx" not in keys
            assert "behaviour_log_prob" not in keys
