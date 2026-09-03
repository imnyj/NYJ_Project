"""Regression tests for the divergence guard.

Every test here fails against the code as it stood on 2026-09-02, when PPO's
background training thread died at gradient update 746 out of a 200,000-step run
and the pipeline reported `100/100 done` after burning another 8.8 hours.

The loss series used below are the MEASURED per-episode `mean_loss` columns from
`coder/runs/{mean,accumulate}_seed42/lg/*_progress.csv`, transcribed here so the
tests do not depend on a run directory that will be moved or overwritten. They
are what makes these tests evidence rather than tautology: the healthy series
must not trip the guard and the dead ones must, under one set of thresholds.
"""

import json
import os
import sys
import time

import numpy as np
import pytest
import torch
import torch.nn as nn

from src.divergence_guard import (
    ABORT_DIVERGED,
    ABORT_GRAD_STALL,
    ABORT_TRAINER_CRASH,
    HEALTHY_MAX_EPISODE_LOSS,
    STATUS_COMPLETED,
    DivergenceMonitor,
    scan_progress_rows,
)
from src.hot_swap_trainer import HotSwapTrainer, prepare_scenario
from src.rl_interface import STATE_DIM, ActionDecoder

SEED = 42
WARMUP = 350


# ---------------------------------------------------------------------------
# Measured loss series (coder/runs/*/lg/*_progress.csv, 2026-09-02)
# ---------------------------------------------------------------------------

#: CARLTON, accumulate arm. The WORST-behaved healthy run: peaks at 12.43, which
#: is the largest per-episode loss any of the seven models that trained normally
#: ever recorded. If the guard fires on this it is unusable.
CARLTON_ACC_LOSS = [
    1.0100, 1.0620, 1.1240, 1.2350, 1.4700, 2.0100, 3.2200, 5.9800, 9.1100,
    12.4300, 11.8000, 9.4400, 7.1100, 5.2000, 3.9000, 3.0100, 2.4400, 2.0300,
    1.7600, 1.5700, 1.4400, 1.3500, 1.2800, 1.2300, 1.1900, 1.1700, 1.1500,
    1.1400, 1.1300, 1.1140,
]

#: SPAM-D3QN, mean arm. The opposite scale problem: a healthy model whose loss
#: lives at 5e-4, four orders of magnitude below CARLTON's. A relative-only rule
#: with no absolute floor turns ordinary noise here into a divergence.
SPAMD3QN_MEAN_LOSS = [
    0.0004, 0.0005, 0.0007, 0.0009, 0.0012, 0.0016, 0.0021, 0.0019, 0.0016,
    0.0013, 0.0011, 0.0010, 0.0009, 0.0008, 0.0007, 0.0007, 0.0006, 0.0006,
    0.0006, 0.0005,
]

#: PPO, mean arm, episodes 1-14. Ten ordinary episodes, then 285,247.46 that
#: never changes again because the worker thread is dead. `grad_updates` goes
#: to zero at the same moment.
PPO_MEAN_LOSS = [
    -0.0940, -0.0665, -0.0895, -0.0939, -0.0857, -0.0764, -0.0591, -0.0774,
    0.0116, 0.8827, 285247.4644, 285247.4644, 285247.4644, 285247.4644,
]
PPO_MEAN_GRAD_UPDATES = [23, 50, 64, 72, 84, 91, 91, 33, 46, 77, 115, 0, 0, 0]

#: PPO, accumulate arm, episodes 1-21. Same failure, sixteen episodes later and
#: from a loss baseline three orders of magnitude higher, so the two exercise the
#: absolute floor and the relative rule respectively.
PPO_ACC_LOSS = [
    4.2824, 2.8250, 3.3754, 7.9212, 10.0975, 14.3560, 15.4140, 14.3791,
    15.7991, 13.8376, 14.1913, 13.4176, 15.0053, 14.4981, 14.8532, 28.4782,
    7647842.0, 16105600.0, 16105590.0, 16105590.0, 16105590.0,
]
PPO_ACC_GRAD_UPDATES = [
    40, 124, 86, 73, 89, 90, 91, 39, 50, 74, 76, 83, 91, 98, 108, 233, 68, 81,
    16, 0, 0,
]

#: I-HAMAPPO, mean arm, episodes 1-20. Spikes to 145,990 at episode 16 and is
#: back to 0.79 at episode 18, then trains for another 83 episodes. This is the
#: series that forbids a one-episode threshold.
IHAMAPPO_MEAN_LOSS_RECOVERING = [
    0.1386, -0.0007, -0.0011, 0.0102, 0.0237, 1.0165, 21.9171, 37.9163,
    10.3220, 5.1239, 2.9366, 516.0425, 0.7008, 1.5927, 33.2971, 145990.1390,
    4141.0159, 0.7910, 25.1288, 2.1867,
]


def _feed(monitor, losses, grads=None):
    """Push a loss series through the monitor and return the first verdict."""
    for i, loss in enumerate(losses):
        g = None if grads is None else grads[i]
        verdict = monitor.observe(episode=i + 1, mean_loss=loss,
                                  grad_updates_this_episode=g)
        if verdict is not None:
            return verdict
    return None


# ---------------------------------------------------------------------------
# 1. The detector, on the measured series
# ---------------------------------------------------------------------------
class TestDetectorAgainstMeasuredRuns:
    def test_the_worst_behaved_healthy_run_is_not_condemned(self):
        """CARLTON peaked at 12.43 and trained all 100 episodes."""
        assert max(CARLTON_ACC_LOSS) == pytest.approx(HEALTHY_MAX_EPISODE_LOSS)
        assert _feed(DivergenceMonitor(), CARLTON_ACC_LOSS) is None

    def test_a_healthy_run_four_orders_of_magnitude_smaller_is_not_condemned(self):
        """SPAM-D3QN's loss lives at 5e-4 and still quadruples between episodes.

        Without the absolute floor the relative rule would read those ordinary
        ratios as divergence.
        """
        assert _feed(DivergenceMonitor(), SPAMD3QN_MEAN_LOSS) is None

    def test_ppo_mean_arm_is_stopped_at_episode_13(self):
        verdict = _feed(DivergenceMonitor(), PPO_MEAN_LOSS, PPO_MEAN_GRAD_UPDATES)
        assert verdict is not None
        assert verdict.kind == ABORT_DIVERGED
        # 11, 12, 13 are the three consecutive over-threshold episodes.
        assert verdict.episode == 13
        # The real run went to 100. Stopping at 13 is 87 episodes of SUMO saved.
        assert verdict.episode < 100

    def test_ppo_accumulate_arm_is_stopped_at_episode_19(self):
        verdict = _feed(DivergenceMonitor(), PPO_ACC_LOSS, PPO_ACC_GRAD_UPDATES)
        assert verdict is not None
        assert verdict.kind == ABORT_DIVERGED
        assert verdict.episode == 19
        # Fired on the model's OWN scale, not on the absolute floor alone: this
        # run's baseline is ~4.28, so its threshold is 4282, not 1000.
        assert verdict.detail["loss_threshold"] > 4000.0

    def test_a_run_that_spikes_and_recovers_is_left_alone(self):
        """I-HAMAPPO hit 145,990 and was back to 0.79 two episodes later.

        A one-episode threshold would have killed a run that went on to train
        for another 83 episodes, which is why `loss_patience` exists.
        """
        assert _feed(DivergenceMonitor(), IHAMAPPO_MEAN_LOSS_RECOVERING) is None

    def test_the_same_spike_is_condemned_once_it_persists(self):
        """The patience is a delay, not an amnesty."""
        persisting = IHAMAPPO_MEAN_LOSS_RECOVERING[:16] + [145990.0, 145990.0]
        verdict = _feed(DivergenceMonitor(), persisting)
        assert verdict is not None and verdict.kind == ABORT_DIVERGED
        assert verdict.episode == 18


# ---------------------------------------------------------------------------
# 2. The detector's individual rules
# ---------------------------------------------------------------------------
class TestDetectorRules:
    def test_a_non_finite_episode_loss_is_condemned_immediately(self):
        m = DivergenceMonitor()
        for i, loss in enumerate([1.0, 1.0, 1.0]):
            assert m.observe(episode=i + 1, mean_loss=loss) is None
        verdict = m.observe(episode=4, mean_loss=float("nan"))
        assert verdict is not None
        assert verdict.kind == ABORT_DIVERGED
        assert verdict.episode == 4
        assert verdict.detail["rule"] == "non_finite_loss"

    def test_infinite_loss_counts_as_non_finite(self):
        m = DivergenceMonitor()
        assert m.observe(episode=1, mean_loss=float("inf")) is not None

    def test_three_episodes_without_a_gradient_update_stop_the_run(self):
        """20,000 env steps with no learning is the waste this rule exists for."""
        m = DivergenceMonitor()
        assert m.observe(episode=1, mean_loss=0.5, grad_updates_this_episode=10) is None
        assert m.observe(episode=2, mean_loss=0.5, grad_updates_this_episode=0) is None
        assert m.observe(episode=3, mean_loss=0.5, grad_updates_this_episode=0) is None
        verdict = m.observe(episode=4, mean_loss=0.5, grad_updates_this_episode=0)
        assert verdict is not None
        assert verdict.kind == ABORT_GRAD_STALL
        assert verdict.episode == 4
        assert verdict.detail["streak"] == 3

    def test_the_zero_update_streak_resets_on_a_productive_episode(self):
        m = DivergenceMonitor()
        for ep, g in enumerate([0, 0, 5, 0, 0], start=1):
            assert m.observe(episode=ep, mean_loss=0.5,
                             grad_updates_this_episode=g) is None
        assert m.zero_update_streak == 2

    def test_a_verdict_is_latched(self):
        """A good episode after a condemned one must not un-fail the run."""
        m = DivergenceMonitor()
        first = _feed(m, PPO_MEAN_LOSS, PPO_MEAN_GRAD_UPDATES)
        assert first is not None
        again = m.observe(episode=99, mean_loss=0.001, grad_updates_this_episode=500)
        assert again is first

    def test_a_blow_up_before_the_warmup_window_closes_is_still_caught(self):
        """The relative rule cannot fire yet; the absolute floor must."""
        m = DivergenceMonitor(warmup_episodes=10)
        verdict = _feed(m, [0.5, 1e9, 1e9, 1e9])
        assert verdict is not None and verdict.episode == 4
        assert m.baseline_loss is None

    def test_the_thresholds_separate_the_measured_populations(self):
        """No threshold can be chosen after the fact to make this pass.

        The largest healthy episode loss and the smallest diverged one are four
        orders of magnitude apart; the floor has to sit between them.
        """
        m = DivergenceMonitor()
        assert HEALTHY_MAX_EPISODE_LOSS < m.loss_abs_floor < min(
            abs(v) for v in PPO_MEAN_LOSS if abs(v) > 1e3
        )


# ---------------------------------------------------------------------------
# 3. Replaying a finished progress CSV -- what the scheduled report does
# ---------------------------------------------------------------------------
class TestScanProgressRows:
    def _rows(self, losses, grads=None):
        return [
            {"episode": i + 1, "mean_loss": v,
             "grad_updates_this_episode": None if grads is None else grads[i]}
            for i, v in enumerate(losses)
        ]

    def test_a_finished_dead_run_is_recognised_from_its_csv_alone(self):
        verdict = scan_progress_rows(
            self._rows(PPO_MEAN_LOSS, PPO_MEAN_GRAD_UPDATES))
        assert verdict is not None and verdict.kind == ABORT_DIVERGED

    def test_a_finished_healthy_run_is_not(self):
        assert scan_progress_rows(self._rows(CARLTON_ACC_LOSS)) is None

    def test_a_missing_gradient_column_does_not_crash_the_scan(self):
        assert scan_progress_rows([{"episode": 1, "mean_loss": 0.5}]) is None

    def test_a_nan_gradient_cell_is_treated_as_unknown_not_as_zero(self):
        rows = [{"episode": i, "mean_loss": 0.5,
                 "grad_updates_this_episode": float("nan")} for i in range(1, 9)]
        assert scan_progress_rows(rows) is None


# ---------------------------------------------------------------------------
# 4. BackgroundTrainer: the failures that used to be silent
# ---------------------------------------------------------------------------
class _BasePolicy(nn.Module):
    def __init__(self, state_dim=STATE_DIM, num_channels=4, gamma=0.9, **hparams):
        super().__init__()
        self.state_dim = int(state_dim)
        self.num_channels = int(num_channels)
        self.gamma = float(gamma)
        self.hparams = hparams
        self.decoder = ActionDecoder(num_channels=num_channels)
        self.net = nn.Linear(self.state_dim, 3)
        self.optimizer = torch.optim.Adam(self.net.parameters(), lr=1e-3)

    def select_action(self, state, deterministic=False):
        return (1.0, 0, 15.0), np.zeros(3, dtype=np.float32), {}

    def update(self, batch):  # pragma: no cover - overridden
        raise NotImplementedError


class NaNLossPolicy(_BasePolicy):
    """Reports a NaN loss without touching its own weights.

    Deliberately leaves the parameters finite, so the existing hot-swap NaN guard
    stays silent and only the loss-finiteness check can notice. That is the real
    ordering: PPO's loss went non-finite ten gradient updates before the swap
    that would have refused, and the thread died in between.
    """

    def update(self, batch):
        return {"loss": float("nan")}


class ExplodingPolicy(_BasePolicy):
    """Raises out of `update()` exactly as `sb3_ppo` did on 2026-09-02.

    The real traceback ended in
    `ValueError: Expected parameter loc ... found invalid values: tensor([[nan...`
    raised from `Normal.__init__` inside `evaluate_actions`.
    """

    def update(self, batch):
        raise ValueError(
            "Expected parameter loc (Tensor of shape (32, 3)) of distribution "
            "Normal to satisfy the constraint Real(), but found invalid values"
        )


def _fill_buffer(trainer, n=64):
    s = np.zeros(STATE_DIM, dtype=np.float32)
    for _ in range(n):
        trainer.replay_buffer.push(s, np.zeros(3, dtype=np.float32), -0.1, s,
                                   False, 1.0)


class TestBackgroundTrainerSurfacesSilentDeaths:
    def _trainer(self, cls):
        return HotSwapTrainer(model_cls=cls, state_dim=STATE_DIM, num_channels=4,
                              batch_size=4, swap_interval=1000)

    def test_a_run_of_non_finite_losses_is_fatal(self):
        trainer = self._trainer(NaNLossPolicy)
        bg = trainer.background_trainer
        _fill_buffer(trainer)
        for _ in range(bg.max_consecutive_nonfinite_losses):
            bg.train_step()
        assert bg.consecutive_nonfinite_losses >= bg.max_consecutive_nonfinite_losses
        assert bg.fatal_error is not None
        assert bg.fatal_kind == ABORT_DIVERGED
        # The swap guard cannot have been what noticed: the weights are finite.
        assert bg.get_metrics()["hot_swap_stats"]["failed_swaps"] == 0
        assert all(torch.isfinite(p).all() for p in trainer.rest_model.parameters())

    def test_one_unlucky_batch_is_not_fatal(self):
        trainer = self._trainer(NaNLossPolicy)
        bg = trainer.background_trainer
        _fill_buffer(trainer)
        bg.train_step()
        assert bg.fatal_error is None

    def test_a_finite_loss_clears_the_streak(self):
        trainer = self._trainer(NaNLossPolicy)
        bg = trainer.background_trainer
        _fill_buffer(trainer)
        bg.train_step()
        assert bg.consecutive_nonfinite_losses == 1
        trainer.rest_model.update = lambda batch: {"loss": 0.5}
        bg.train_step()
        assert bg.consecutive_nonfinite_losses == 0

    def test_a_worker_thread_that_raises_records_why_instead_of_vanishing(self):
        """This is the exact 2026-09-02 failure.

        Before the guard, `_worker_loop` had no handler: `threading` printed the
        traceback to stderr, the thread ended, and every observable on the
        trainer stayed exactly as it was. `fatal_error` stayed None, so the
        episode loop's `if trainer_metrics.get("fatal_error")` never fired.
        """
        trainer = self._trainer(ExplodingPolicy)
        bg = trainer.background_trainer
        _fill_buffer(trainer)
        trainer.start()
        deadline = time.time() + 10.0
        while time.time() < deadline and bg.fatal_error is None:
            time.sleep(0.02)
        try:
            assert bg.fatal_error is not None, "the thread died without saying so"
            assert bg.fatal_kind == ABORT_TRAINER_CRASH
            assert "Normal" in (bg.worker_traceback or "")
            assert bg.worker_is_dead()
            assert bg.get_metrics()["fatal_kind"] == ABORT_TRAINER_CRASH
        finally:
            trainer.stop()

    def test_a_live_worker_is_not_reported_as_dead(self):
        trainer = self._trainer(NaNLossPolicy)
        bg = trainer.background_trainer
        assert not bg.worker_is_dead(), "never started is not dead"
        trainer.start()
        try:
            assert not bg.worker_is_dead()
        finally:
            trainer.stop()
        assert not bg.worker_is_dead(), "a requested stop is not a death"


# ---------------------------------------------------------------------------
# 5. End to end: the run must stop, and must say so where a reader will look
# ---------------------------------------------------------------------------
class ExplodingLossPolicy(_BasePolicy):
    """Trains normally, then reports a runaway (but finite) loss.

    Finite on purpose: the non-finite check must not be what catches this, so
    the test exercises the magnitude rule the way the accumulate-arm PPO run
    would have been caught.
    """

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.calls = 0

    def update(self, batch):
        self.calls += 1
        loss = self.net(batch["state"]).mean()
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return {"loss": 1.0 if self.calls <= 3 else 1.0e9}


@pytest.mark.slow
class TestRunAbortsAndSaysSo:
    def _run(self, tmp_path, cls, **kw):
        from src.hot_swap_trainer import run_hot_swap_training

        prepare_scenario(25.0, 200, WARMUP, SEED, force_regenerate=True)
        return run_hot_swap_training(
            model_name=cls.__name__, model_cls=cls,
            total_steps=1000, episodes=5, density=25.0,
            batch_size=4, swap_interval=1000, seed=SEED, warmup_steps=WARMUP,
            checkpoint_dir=str(tmp_path / "ckpt"),
            tensorboard_dir=str(tmp_path / "tb"),
            log_dir=str(tmp_path / "logs"),
            **kw,
        )

    def test_a_diverging_model_stops_early_and_the_summary_says_why(self, tmp_path):
        summary = self._run(
            tmp_path, ExplodingLossPolicy,
            # One episode of warmup and no patience, so a five-episode test can
            # reach a verdict. The rule is the production one; only the window is
            # shortened.
            divergence_warmup_episodes=1, divergence_loss_patience=1,
        )
        assert summary["status"] == ABORT_DIVERGED
        assert summary["abort_kind"] == ABORT_DIVERGED
        assert summary["abort_reason"]
        assert 1 <= summary["abort_episode"] < 5
        # The 2026-09-02 report read `100/100`. The count must not say that.
        assert summary["total_steps"] < 1000

    def test_the_progress_csv_carries_the_abort_on_its_last_row(self, tmp_path):
        import pandas as pd

        summary = self._run(
            tmp_path, ExplodingLossPolicy,
            divergence_warmup_episodes=1, divergence_loss_patience=1,
        )
        df = pd.read_csv(summary["log_csv_path"])
        assert "run_status" in df.columns
        assert list(df["run_status"])[:-1] == ["ok"] * (len(df) - 1)
        assert df["run_status"].iloc[-1] == ABORT_DIVERGED
        assert str(df["abort_reason"].iloc[-1]).strip()
        assert len(df) == summary["abort_episode"]

    def test_the_status_sidecar_is_written_next_to_the_csv(self, tmp_path):
        summary = self._run(
            tmp_path, ExplodingLossPolicy,
            divergence_warmup_episodes=1, divergence_loss_patience=1,
        )
        path = summary["status_json_path"]
        assert os.path.isfile(path)
        assert os.path.dirname(path) == os.path.dirname(summary["log_csv_path"])
        payload = json.load(open(path))
        assert payload["status"] == ABORT_DIVERGED
        assert payload["abort_episode"] == summary["abort_episode"]
        assert payload["episodes_requested"] == 5
        assert payload["episodes_completed"] < 5

    def test_a_dead_training_thread_stops_the_run(self, tmp_path):
        summary = self._run(tmp_path, ExplodingPolicy)
        assert summary["status"] == ABORT_TRAINER_CRASH
        assert summary["abort_episode"] < 5
        assert "Normal" in json.load(
            open(summary["status_json_path"]))["worker_traceback"]

    def test_a_healthy_short_run_is_still_reported_as_completed(self, tmp_path):
        """The guard must not turn every run into a failure."""
        class HealthyPolicy(_BasePolicy):
            def update(self, batch):
                loss = self.net(batch["state"]).mean()
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                return {"loss": float(loss.item())}

        summary = self._run(tmp_path, HealthyPolicy)
        assert summary["status"] == STATUS_COMPLETED
        assert summary["abort_kind"] is None
        assert json.load(open(summary["status_json_path"]))["status"] == STATUS_COMPLETED


# ---------------------------------------------------------------------------
# 6. The scheduled report must not call a dead run `done`
# ---------------------------------------------------------------------------
def _load_report_module():
    """Load `etc/report_progress.py` by path; it is a script, not a package.

    `sys.path` is restored afterwards because the module inserts its own
    hardcoded CODER_DIR at position 0 on import, which would otherwise decide
    where every LATER `import` in this session resolves from.
    """
    import importlib.util

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "etc", "report_progress.py")
    spec = importlib.util.spec_from_file_location("report_progress_under_test", path)
    module = importlib.util.module_from_spec(spec)
    saved_path = list(sys.path)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = saved_path
    return module


def _fake_run_dir(tmp_path, model, losses, grads=None, status=None):
    import pandas as pd

    lg = tmp_path / "lg"
    lg.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, v in enumerate(losses):
        rows.append({
            "episode": i + 1, "density": 25.0, "mean_loss": v,
            "grad_updates_this_episode": 10 if grads is None else grads[i],
            "grad_updates_total": 10 * (i + 1),
            "reward_per_sec_selected": -0.1, "mean_reward": -0.1,
            "mean_aoi": 12.0, "mean_error": 5.0, "coverage_outage_rate": 0.3,
        })
    pd.DataFrame(rows).to_csv(lg / f"{model}_progress.csv", index=False)
    (tmp_path / "run_config.json").write_text(json.dumps({"episodes": len(losses)}))
    if status is not None:
        (lg / f"{model}_status.json").write_text(json.dumps(status))
    return str(tmp_path)


class TestScheduledReport:
    def test_a_diverged_run_is_not_shown_as_done(self, tmp_path):
        """The 2026-09-02 report showed PPO as `done 100/100`.

        Its progress CSV had a full complement of rows, so row-count alone said
        the run had finished. Only the loss series says otherwise.
        """
        rp = _load_report_module()
        run_dir = _fake_run_dir(tmp_path, "PPO", PPO_MEAN_LOSS, PPO_MEAN_GRAD_UPDATES)
        rec = rp.scan_run(run_dir)["models"][0]
        assert rec["episodes_done"] == len(PPO_MEAN_LOSS)
        assert rec["episodes_done"] >= rec["target_episodes"]
        assert rec["state"] != "done"
        assert rec["abort_kind"] == ABORT_DIVERGED
        assert rec["status_source"] == "csv-scan"

    def test_the_sidecar_wins_over_the_csv_scan(self, tmp_path):
        rp = _load_report_module()
        run_dir = _fake_run_dir(
            tmp_path, "PROBE", [0.5] * 6, grads=[0] * 6,
            status={"status": ABORT_TRAINER_CRASH, "abort_episode": 2,
                    "abort_reason": "the background training thread died"},
        )
        rec = rp.scan_run(run_dir)["models"][0]
        assert rec["abort_kind"] == ABORT_TRAINER_CRASH
        assert rec["abort_episode"] == 2
        assert rec["status_source"] == "sidecar"

    def test_a_healthy_run_is_still_shown_as_done(self, tmp_path):
        rp = _load_report_module()
        run_dir = _fake_run_dir(tmp_path, "CARLTON", CARLTON_ACC_LOSS)
        rec = rp.scan_run(run_dir)["models"][0]
        assert rec["state"] == "done"
        assert "abort_kind" not in rec

    def test_a_completed_sidecar_does_not_mark_the_run_as_aborted(self, tmp_path):
        rp = _load_report_module()
        run_dir = _fake_run_dir(tmp_path, "CARLTON", CARLTON_ACC_LOSS,
                                status={"status": STATUS_COMPLETED})
        rec = rp.scan_run(run_dir)["models"][0]
        assert rec["state"] == "done"

    def test_the_abort_reaches_the_problem_list(self, tmp_path):
        rp = _load_report_module()
        run_dir = _fake_run_dir(tmp_path, "PPO", PPO_MEAN_LOSS, PPO_MEAN_GRAD_UPDATES)
        problems = rp.scan_run(run_dir)["problems"]
        assert any("발산" in p for p in problems)


# ---------------------------------------------------------------------------
# 7. run_all must record an aborted model as a failure and keep going
# ---------------------------------------------------------------------------
class TestRunAllRecordsAbortedModels:
    def test_an_aborted_model_is_a_failure_and_the_next_model_still_runs(
            self, monkeypatch, tmp_path, caplog):
        import run_all

        calls = []

        def fake_run(**kwargs):
            name = kwargs["model_name"]
            name = getattr(name, "__name__", str(name))
            calls.append(name)
            if len(calls) == 1:
                return {"status": ABORT_DIVERGED, "abort_kind": ABORT_DIVERGED,
                        "abort_episode": 13,
                        "abort_reason": "loss stayed above 1000 for 3 episodes"}
            return {"status": STATUS_COMPLETED}

        monkeypatch.setattr(run_all, "run_hot_swap_training", fake_run)
        monkeypatch.setattr(run_all, "load_hparams_from_csv", lambda p: {})

        with caplog.at_level("ERROR"):
            rc = run_all.main([
                "--models", "PPO", "SAC", "--episodes", "1",
                "--steps-per-episode", "10", "--hparams-csv", "",
                "--checkpoint-dir", str(tmp_path / "ck"),
                "--tensorboard-dir", str(tmp_path / "tb"),
                "--log-dir", str(tmp_path / "lg"),
            ])

        assert len(calls) == 2, "an aborted model must not stop the other models"
        assert rc == 1, "an aborted model must not be reported as success"
        text = caplog.text
        assert "Failed training PPO" in text
        assert ABORT_DIVERGED in text
        assert "episode 13" in text
