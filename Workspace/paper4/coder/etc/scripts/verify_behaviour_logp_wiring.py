"""What actually reaches the replay buffer, on BOTH paths, in a real run?

The unit tests exercise the wiring with a stub policy. This script exercises the
two production paths instead, against live SUMO, with
`RetrospectiveReplayBuffer.push` instrumented to record what it was handed:

  * `training`     -- `hot_swap_trainer.run_hot_swap_training`
  * `hpo_rollout`  -- `hpo.evaluate_model_in_env` with training enabled

and reports per (model, path), from data rather than from reading the code:

  1. what fraction of pushed transitions carried a finite behaviour log-prob,
  2. what fraction carried a discrete action index,
  3. which columns a sampled batch therefore exposes,
  4. whether `update()` reported using the stored log-prob (`behaviour_logp_stored`).

THE COMPARISON THAT MATTERS is between the two paths for the same model. A
hyper-parameter search that measures a model under different conditions than
training runs it cannot promise that its chosen values transfer; the tuned reward
weights failed exactly that way once already. So the two rows of a model must
carry the same columns: PPO and I-HAMAPPO must show the behaviour log-prob on
both, the five discrete-head models must show `action_idx` on both, and the
purely continuous off-policy models must show neither on either.

Everything is written under a temporary directory; this script never touches
`checkpoints/` or `logs/`.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import tempfile
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import src.Communications as comm  # noqa: E402
import src.hot_swap_trainer as H  # noqa: E402
from src.baselines import get_baseline  # noqa: E402
from src.hpo import evaluate_model_in_env  # noqa: E402
from src.rl_interface import STATE_DIM, RetrospectiveReplayBuffer  # noqa: E402

FIELDS = ["model", "path", "steps", "n_pushed", "frac_with_behaviour_logp",
          "frac_with_action_idx", "logp_column_in_batch", "action_idx_column_in_batch",
          "n_updates", "n_updates_reporting_the_flag", "frac_updates_with_stored_logp",
          "batch_keys"]


class PushSpy:
    """Counts what the buffer was handed alongside each pushed transition."""

    def __init__(self) -> None:
        self.n_pushed = 0
        self.n_with_logp = 0
        self.n_with_idx = 0
        self.buffers: List[RetrospectiveReplayBuffer] = []
        self._orig = RetrospectiveReplayBuffer.push
        spy = self

        def push(self_buf, *args, **kwargs):  # noqa: ANN001
            spy.n_pushed += 1
            logp = kwargs.get("behaviour_log_prob")
            if logp is not None and math.isfinite(float(logp)):
                spy.n_with_logp += 1
            if kwargs.get("action_idx") is not None:
                spy.n_with_idx += 1
            if self_buf not in spy.buffers:
                spy.buffers.append(self_buf)
            return spy._orig(self_buf, *args, **kwargs)

        RetrospectiveReplayBuffer.push = push  # type: ignore[method-assign]

    def restore(self) -> None:
        RetrospectiveReplayBuffer.push = self._orig  # type: ignore[method-assign]


class UpdateSpy:
    """Records the `behaviour_logp_stored` flag every update reports."""

    def __init__(self, model_cls: Any) -> None:
        self.flags: List[float] = []
        #: All updates, whether or not the model reports the flag. The seven
        #: off-policy baselines never report it, so counting only the flagged
        #: ones would make a healthy run look like it never trained.
        self.n_updates = 0
        self._orig = model_cls.update
        spy = self

        def update(self_model, batch):  # noqa: ANN001
            out = spy._orig(self_model, batch)
            spy.n_updates += 1
            if isinstance(out, dict) and "behaviour_logp_stored" in out:
                spy.flags.append(float(out["behaviour_logp_stored"]))
            return out

        model_cls.update = update  # type: ignore[method-assign]
        self.model_cls = model_cls

    def restore(self) -> None:
        self.model_cls.update = self._orig  # type: ignore[method-assign]


def _summarise(name: str, path: str, steps: int, push_spy: "PushSpy",
               update_spy: "UpdateSpy") -> Dict[str, Any]:
    keys: List[str] = []
    for buf in push_spy.buffers:
        if len(buf.buffer) >= 8:
            keys = sorted(buf.sample(8).keys())
            break

    n_pushed = push_spy.n_pushed
    return {
        "model": name,
        "path": path,
        "steps": steps,
        "n_pushed": n_pushed,
        "frac_with_behaviour_logp": round(push_spy.n_with_logp / n_pushed, 6) if n_pushed else "",
        "frac_with_action_idx": round(push_spy.n_with_idx / n_pushed, 6) if n_pushed else "",
        "logp_column_in_batch": "behaviour_log_prob" in keys,
        "action_idx_column_in_batch": "action_idx" in keys,
        "n_updates": update_spy.n_updates,
        "n_updates_reporting_the_flag": len(update_spy.flags),
        "frac_updates_with_stored_logp": (
            round(sum(update_spy.flags) / len(update_spy.flags), 6) if update_spy.flags else ""
        ),
        "batch_keys": "|".join(keys),
    }


def run_training(name: str, steps: int, density: float, seed: int, workdir: str) -> Dict[str, Any]:
    """The production training path: `run_hot_swap_training`."""
    cls = get_baseline(name)
    push_spy = PushSpy()
    update_spy = UpdateSpy(cls)
    try:
        H.run_hot_swap_training(
            model_name=name,
            model_cls=cls,
            total_steps=steps,
            episodes=1,
            density=density,
            batch_size=16,
            swap_interval=10,
            seed=seed,
            checkpoint_dir=os.path.join(workdir, "ck"),
            tensorboard_dir=os.path.join(workdir, "tb"),
            log_dir=os.path.join(workdir, "lg"),
            hparams={"hidden_dim": 64},
        )
    finally:
        push_spy.restore()
        update_spy.restore()
    return _summarise(name, "training", steps, push_spy, update_spy)


def run_hpo_rollout(name: str, steps: int, density: float, seed: int) -> Dict[str, Any]:
    """The search path: one `evaluate_model_in_env` rollout that also trains.

    `train_steps_during_rollout=2` is what an Optuna trial uses, so this is the
    batch an HPO trial's `update()` actually sees.
    """
    cls = get_baseline(name)
    model = cls(state_dim=STATE_DIM, num_channels=comm.NUM_SUBCHANNELS, hidden_dim=64)
    push_spy = PushSpy()
    update_spy = UpdateSpy(cls)
    try:
        evaluate_model_in_env(model=model, seed=seed, n_steps=steps, density=density,
                              train_steps_during_rollout=2, check_divergence=False)
    finally:
        push_spy.restore()
        update_spy.restore()
    return _summarise(name, "hpo_rollout", steps, push_spy, update_spy)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+",
                    default=["PPO", "I-HAMAPPO", "TD3", "SPAM-D3QN", "CARLTON"])
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--density", type=float, default=25.0)
    ap.add_argument("--seed", type=int, default=1001)
    ap.add_argument("--out", default=os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "results", "hpo",
        "behaviour_logp_wiring_check.csv")))
    a = ap.parse_args()

    rows = []
    with tempfile.TemporaryDirectory(prefix="logp_wiring_") as workdir:
        for name in a.models:
            for row in (run_training(name, a.steps, a.density, a.seed, workdir),
                        run_hpo_rollout(name, a.steps, a.density, a.seed)):
                rows.append(row)
                print(json.dumps(row), flush=True)

    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("WROTE", a.out)


if __name__ == "__main__":
    main()
