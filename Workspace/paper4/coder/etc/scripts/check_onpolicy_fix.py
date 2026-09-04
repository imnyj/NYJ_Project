"""Does storing the behaviour log-probability stop the two on-policy baselines
from diverging?

Same procedure as the run that produced `results/hpo/divergence_detection_check.csv`
-- the hyperparameters `results/hpo/optuna_best_params.csv` selected for PPO and
I-HAMAPPO, plus a control arm at the on-policy customary 3e-4, through
`evaluate_model_in_env` with the divergence guard on -- but written to a
DIFFERENT file so the pre-fix evidence is not overwritten.

Two things are recorded per run:

  * the divergence verdict, one row in `onpolicy_fix_check.csv`, directly
    comparable to the corresponding row of the pre-fix file;
  * the importance-ratio diagnostics every `update()` now returns, aggregated
    into `onpolicy_ratio_diagnostics.csv`. The ratio being something other than
    1.0 is the whole point of the fix: with the denominator recomputed from the
    current policy it was 1.0 exactly, with zero spread and a clip fraction of
    zero, so PPO's clipping never acted.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np  # noqa: E402

import src.Communications as comm  # noqa: E402
from src.baselines import get_baseline  # noqa: E402
from src.hpo import (  # noqa: E402
    DEFAULT_HPO_N_STEPS,
    compute_composite_objective,
    evaluate_model_in_env,
)
from src.rl_interface import STATE_DIM  # noqa: E402

RESULTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "results", "hpo")
)

# Verbatim from results/hpo/optuna_best_params.csv, column hparams_json --
# identical to the pre-fix check so the two files differ only by the code.
SELECTED: Dict[str, Dict[str, Any]] = {
    "PPO": {"hidden_dim": 64, "learning_rate": 0.0010809366764261586,
            "gamma": 0.9975073184286054, "clip_range": 0.2361881493638004,
            "ent_coef": 0.02051249550821203, "vf_coef": 0.5638821363327259,
            "n_epochs": 4},
    "I-HAMAPPO": {"hidden_dim": 64, "lr_actor": 0.0008433020501242809,
                  "lr_critic": 0.0005608338145080542, "gamma": 0.9986278038774985,
                  "clip_ratio": 0.24947883746104182,
                  "entropy_coef": 0.004483168971211849,
                  "value_coef": 0.5771926186506204},
}
CONTROL: Dict[str, Dict[str, Any]] = {
    "PPO": dict(SELECTED["PPO"], learning_rate=3e-4),
    "I-HAMAPPO": dict(SELECTED["I-HAMAPPO"], lr_actor=3e-4, lr_critic=3e-4),
}

FIELDS = ["model", "arm", "seed", "n_steps", "wall_s", "diverged", "divergence_rule",
          "divergence_pseudo_episode", "divergence_at_env_step", "n_grad_updates",
          "divergence_threshold", "divergence_baseline_loss", "divergence_pseudo_episodes_seen",
          "mean_recent_loss", "max_consecutive_nonfinite_losses", "composite_score",
          "n_update_failures", "n_observations", "tx_attempts", "hparams",
          "divergence_reason"]

#: Keys the two on-policy `update()` methods report about the importance ratio.
#: PPO reports the FIRST inner epoch specifically, because that is the epoch the
#: old code pinned at 1.0; I-HAMAPPO takes a single gradient step per update.
RATIO_KEYS = ["behaviour_logp_stored", "first_epoch_ratio_mean", "first_epoch_ratio_std",
              "first_epoch_ratio_max", "first_epoch_clip_fraction",
              "mean_ratio", "ratio_std", "ratio_max", "clip_fraction"]

DIAG_FIELDS = ["model", "arm", "seed", "n_updates", "frac_updates_with_stored_logp",
               "ratio_mean_avg", "ratio_mean_min", "ratio_mean_max",
               "ratio_std_avg", "ratio_max_max", "clip_fraction_avg",
               "frac_updates_with_ratio_exactly_one"]


class RatioRecorder:
    """Wraps `model.update` and keeps the ratio diagnostics it returns."""

    def __init__(self, model: Any) -> None:
        self.model = model
        self.records: List[Dict[str, float]] = []
        self._inner = model.update
        model.update = self._update  # type: ignore[method-assign]

    def _update(self, batch: Dict[str, Any]) -> Dict[str, float]:
        out = self._inner(batch)
        if isinstance(out, dict):
            kept = {k: float(out[k]) for k in RATIO_KEYS if k in out}
            if kept:
                self.records.append(kept)
        return out

    @staticmethod
    def _col(records: List[Dict[str, float]], *names: str) -> np.ndarray:
        """First present of `names`, over the records that carry it."""
        for name in names:
            vals = [r[name] for r in records if name in r]
            if vals:
                return np.asarray(vals, dtype=np.float64)
        return np.asarray([], dtype=np.float64)

    def summary(self) -> Dict[str, Any]:
        recs = self.records
        if not recs:
            return {k: "" for k in DIAG_FIELDS[3:]}
        stored = self._col(recs, "behaviour_logp_stored")
        means = self._col(recs, "first_epoch_ratio_mean", "mean_ratio")
        stds = self._col(recs, "first_epoch_ratio_std", "ratio_std")
        maxs = self._col(recs, "first_epoch_ratio_max", "ratio_max")
        clips = self._col(recs, "first_epoch_clip_fraction", "clip_fraction")
        exactly_one = np.mean(np.abs(means - 1.0) < 1e-6) if means.size else float("nan")
        return {
            "n_updates": len(recs),
            "frac_updates_with_stored_logp": round(float(stored.mean()), 6) if stored.size else "",
            "ratio_mean_avg": round(float(means.mean()), 6) if means.size else "",
            "ratio_mean_min": round(float(means.min()), 6) if means.size else "",
            "ratio_mean_max": round(float(means.max()), 6) if means.size else "",
            "ratio_std_avg": round(float(stds.mean()), 6) if stds.size else "",
            "ratio_max_max": round(float(maxs.max()), 6) if maxs.size else "",
            "clip_fraction_avg": round(float(clips.mean()), 6) if clips.size else "",
            "frac_updates_with_ratio_exactly_one": round(float(exactly_one), 6),
        }


def one(model_name: str, arm: str, hparams: Dict[str, Any], seed: int, n_steps: int):
    cls = get_baseline(model_name)
    model = cls(state_dim=STATE_DIM, num_channels=comm.NUM_SUBCHANNELS, **hparams)
    recorder = RatioRecorder(model)
    t0 = time.time()
    m = evaluate_model_in_env(model=model, seed=seed, n_steps=n_steps, density=25.0,
                              train_steps_during_rollout=2, check_divergence=True)
    wall = time.time() - t0
    row = {
        "model": model_name, "arm": arm, "seed": seed, "n_steps": n_steps,
        "wall_s": round(wall, 1),
        "diverged": bool(m.get("diverged")),
        "divergence_rule": m.get("divergence_rule", ""),
        "divergence_pseudo_episode": m.get("divergence_episode", -1),
        "divergence_at_env_step": m.get("steps_completed", -1),
        "n_grad_updates": m.get("n_grad_updates", 0),
        "divergence_threshold": m.get("divergence_threshold"),
        "divergence_baseline_loss": m.get("divergence_baseline_loss"),
        "divergence_pseudo_episodes_seen": m.get("divergence_pseudo_episodes_seen", 0),
        "mean_recent_loss": m.get("mean_recent_loss"),
        "max_consecutive_nonfinite_losses": m.get("max_consecutive_nonfinite_losses", 0),
        "composite_score": round(compute_composite_objective(m), 4),
        "n_update_failures": m.get("n_update_failures", 0),
        "n_observations": m.get("n_observations", 0),
        "tx_attempts": m.get("tx_attempts", 0),
        "hparams": json.dumps(hparams),
        "divergence_reason": m.get("divergence_reason", ""),
    }
    diag = {"model": model_name, "arm": arm, "seed": seed}
    diag.update(recorder.summary())
    return row, diag


def _write(path: str, fields: List[str], rows: List[Dict[str, Any]]) -> None:
    exists = os.path.exists(path)
    with open(path, "a" if exists else "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerows(rows)
    print("WROTE", path, flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["PPO", "I-HAMAPPO"])
    ap.add_argument("--arms", nargs="+", default=["selected", "control"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[1001])
    ap.add_argument("--n-steps", type=int, default=DEFAULT_HPO_N_STEPS)
    ap.add_argument("--out", default=os.path.join(RESULTS_DIR, "onpolicy_fix_check.csv"))
    ap.add_argument("--diag-out",
                    default=os.path.join(RESULTS_DIR, "onpolicy_ratio_diagnostics.csv"))
    a = ap.parse_args()

    rows: List[Dict[str, Any]] = []
    diags: List[Dict[str, Any]] = []
    for model_name in a.models:
        for arm in a.arms:
            hp = (SELECTED if arm == "selected" else CONTROL)[model_name]
            for seed in a.seeds:
                row, diag = one(model_name, arm, hp, seed, a.n_steps)
                rows.append(row)
                diags.append(diag)
                print(json.dumps({k: row[k] for k in FIELDS if k != "hparams"}), flush=True)
                print(json.dumps(diag), flush=True)

    _write(a.out, FIELDS, rows)
    _write(a.diag_out, DIAG_FIELDS, diags)


if __name__ == "__main__":
    main()
