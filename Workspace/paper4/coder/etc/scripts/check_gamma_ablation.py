"""Is the discount factor what destabilised the two on-policy baselines?

`results/hpo/optuna_best_params.csv` gave I-HAMAPPO gamma = 0.99862780 and PPO
gamma = 0.99750732, the two largest of the nine studies; the third, SAC, sits far
below at 0.97283624. At a 0.5 s decision interval those two discounts carry an
effective horizon of 728.8 s and 401.2 s, both longer than the 200 s episode, so
the return the critic is asked to fit extends past anything the rollout ever
observes. The same two models are also the only two without a target critic and
without GAE, so the discount and the algorithm structure are perfectly confounded
in the committed evidence and neither can be blamed from it alone.

`results/hpo/divergence_detection_check.csv` already ruled the learning rate out:
holding gamma at the selected value and dropping the rate to 3e-4 delayed PPO's
NaN from step 588 to 2493 without preventing it, and left I-HAMAPPO at a mean
loss of 37867 against a healthy ceiling of 12.43. The discount was never varied.
This script varies it, and nothing else.

Three arms per model, all under the CURRENT code:

  * `gamma097` -- the selected hyperparameters verbatim, with gamma alone
    replaced by 0.97, near the SAC value and giving a 33.3 s horizon;
  * `gamma099` -- the same, with gamma replaced by 0.99 (100 s horizon). Added
    2026-09-05: with only `gamma097` and `selected` the curve has two points, and
    two points cannot separate a monotone trend from an interior optimum, which
    is exactly the distinction the HPO gamma upper bound turns on;
  * `selected`  -- the selected hyperparameters verbatim, re-run here rather than
    quoted from `onpolicy_fix_check.csv`.

The control arm is re-run because the earlier file is not a like-for-like
comparison any more: `src/sumo/generated.rou.xml` was regenerated on 2026-09-04
at 15:58 after that file was written, so the two would differ by the traffic
demand as well as by gamma. Re-running both arms in one session removes that.

Output goes to the path given by `--out`, with the column set of
`divergence_detection_check.csv`, so rows can be read side by side. The default
is `results/hpo/gamma_ablation_20260904.csv`, the single-seed run of 2026-09-04,
and writing into an existing file now requires `--allow-append` so that run stays
usable as a control. The widened sweep of 2026-09-05 (three arms x three seeds,
sharded over four GPUs by `etc/scripts/run_gamma_ablation_v2.sh`) writes to
`results/hpo/gamma_ablation_v2_20260905.csv` instead.
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

#: The discount the ablation moves to. Chosen as the value SAC's study settled on
#: (0.97283624 rounded down), so the arm sits inside the range the seven stable
#: models were tuned in rather than at an arbitrary round number.
ABLATION_GAMMA: float = 0.97

#: The second ablation discount, added on 2026-09-05. Two points cannot tell a
#: monotone trend from an interior optimum, and the value the HPO search range's
#: upper bound would be moved to is exactly this one, so it has to be measured
#: rather than interpolated. 0.99 carries a 100 s effective horizon, still above
#: the 50-54 s a vehicle is measured to stay inside RSU range but far below the
#: 401 s and 729 s of the selected values.
ABLATION_GAMMA_2: float = 0.99

# Verbatim from results/hpo/optuna_best_params.csv, column hparams_json -- the
# same dictionaries check_onpolicy_fix.py and the pre-fix check used, so the
# three files differ only by the one hyperparameter named in the arm.
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
GAMMA097: Dict[str, Dict[str, Any]] = {
    name: dict(hp, gamma=ABLATION_GAMMA) for name, hp in SELECTED.items()
}
GAMMA099: Dict[str, Dict[str, Any]] = {
    name: dict(hp, gamma=ABLATION_GAMMA_2) for name, hp in SELECTED.items()
}
ARMS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "selected": SELECTED,
    "gamma097": GAMMA097,
    "gamma099": GAMMA099,
}

#: Column set of results/hpo/divergence_detection_check.csv, in its order.
FIELDS = ["model", "arm", "seed", "n_steps", "wall_s", "diverged", "divergence_rule",
          "divergence_pseudo_episode", "divergence_at_env_step", "n_grad_updates",
          "mean_recent_loss", "max_consecutive_nonfinite_losses", "composite_score",
          "n_update_failures", "n_observations", "tx_attempts", "hparams",
          "divergence_reason"]

#: Everything the verdict is read from, kept beside the comparable columns rather
#: than inside them so the file stays loadable next to the older two.
EXTRA_FIELDS = ["gamma", "effective_horizon_s", "divergence_threshold",
                "divergence_baseline_loss", "divergence_pseudo_episodes_seen",
                "mean_aoi", "mean_error", "packet_loss_rate", "coverage_outage_rate",
                "avg_tx_power_dbm", "mean_cbr"]

#: The SMDP discount is `gamma ** delta_t` with `delta_t` measured in SECONDS
#: (`rl_interface.py:818`, `base_agent.py:198`), so 1/(1-gamma) is already a time
#: in seconds and needs no step-length conversion. Reported only; the rollout
#: computes nothing from it.
HORIZON_UNIT_S: float = 1.0

#: The ceiling a healthy rollout of this pipeline reached, quoted in the
#: divergence_reason of results/hpo/divergence_detection_check.csv. A mean loss
#: three orders of magnitude above it is what "still broken" looks like.
HEALTHY_LOSS_CEILING: float = 12.43

#: The verdict threshold this run is judged against, from the task: a mean loss
#: above it, or a NaN divergence, says the discount was not the cause.
VERDICT_LOSS_LIMIT: float = 1000.0


def one(model_name: str, arm: str, hparams: Dict[str, Any], seed: int, n_steps: int):
    cls = get_baseline(model_name)
    model = cls(state_dim=STATE_DIM, num_channels=comm.NUM_SUBCHANNELS, **hparams)
    t0 = time.time()
    m = evaluate_model_in_env(model=model, seed=seed, n_steps=n_steps, density=25.0,
                              train_steps_during_rollout=2, check_divergence=True)
    wall = time.time() - t0
    gamma = float(hparams["gamma"])
    row = {
        "model": model_name, "arm": arm, "seed": seed, "n_steps": n_steps,
        "wall_s": round(wall, 1),
        "diverged": bool(m.get("diverged")),
        "divergence_rule": m.get("divergence_rule", ""),
        "divergence_pseudo_episode": m.get("divergence_episode", -1),
        "divergence_at_env_step": m.get("steps_completed", -1),
        "n_grad_updates": m.get("n_grad_updates", 0),
        "mean_recent_loss": m.get("mean_recent_loss"),
        "max_consecutive_nonfinite_losses": m.get("max_consecutive_nonfinite_losses", 0),
        "composite_score": round(compute_composite_objective(m), 4),
        "n_update_failures": m.get("n_update_failures", 0),
        "n_observations": m.get("n_observations", 0),
        "tx_attempts": m.get("tx_attempts", 0),
        "hparams": json.dumps(hparams),
        "divergence_reason": m.get("divergence_reason", ""),
        "gamma": gamma,
        "effective_horizon_s": round(HORIZON_UNIT_S / max(1e-12, 1.0 - gamma), 2),
        "divergence_threshold": m.get("divergence_threshold"),
        "divergence_baseline_loss": m.get("divergence_baseline_loss"),
        "divergence_pseudo_episodes_seen": m.get("divergence_pseudo_episodes_seen", 0),
        "mean_aoi": m.get("mean_aoi"),
        "mean_error": m.get("mean_error"),
        "packet_loss_rate": m.get("packet_loss_rate"),
        "coverage_outage_rate": m.get("coverage_outage_rate"),
        "avg_tx_power_dbm": m.get("avg_tx_power_dbm"),
        "mean_cbr": m.get("mean_cbr"),
    }
    return row


def verdict(rows: List[Dict[str, Any]]) -> List[str]:
    """One line per (model, seed, lowered-gamma arm) saying whether it stayed healthy.

    Keyed by seed as well as by arm since 2026-09-05: with three seeds in one
    file a dict keyed by arm alone kept only whichever row happened to come last
    and reported it as if it were the arm's result.
    """
    lines: List[str] = []
    ablation_arms = [a for a in ARMS if a != "selected"]
    for model_name in sorted({r["model"] for r in rows}):
        for seed in sorted({r["seed"] for r in rows if r["model"] == model_name}):
            by_arm = {
                r["arm"]: r for r in rows
                if r["model"] == model_name and r["seed"] == seed
            }
            ref = by_arm.get("selected")
            ref_txt = (
                f"; selected-gamma arm diverged={ref['diverged']} loss={ref['mean_recent_loss']}"
                if ref else ""
            )
            for arm in ablation_arms:
                low = by_arm.get(arm)
                if low is None:
                    continue
                loss = float(low["mean_recent_loss"])
                broken = bool(low["diverged"]) or loss > VERDICT_LOSS_LIMIT
                lines.append(
                    f"[{model_name}] seed={seed} gamma={low['gamma']}: "
                    f"diverged={low['diverged']} mean_recent_loss={loss:.4f} -> "
                    f"{'GAMMA IS NOT THE CAUSE' if broken else 'within the healthy range'} "
                    f"(limit {VERDICT_LOSS_LIMIT:.0f}, healthy ceiling {HEALTHY_LOSS_CEILING})"
                    f"{ref_txt}"
                )
    return lines


def _append_row(path: str, fields: List[str], row: Dict[str, Any]) -> None:
    """Append one finished condition, header included on first write.

    Rows are flushed as they finish rather than accumulated to the end: a shard
    of this script now runs for roughly twenty minutes, and losing every measured
    condition because the last one raised is not a trade worth making.
    """
    exists = os.path.exists(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a" if exists else "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerow(row)
        f.flush()
        os.fsync(f.fileno())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["PPO", "I-HAMAPPO"])
    ap.add_argument("--arms", nargs="+", default=["selected", "gamma097"],
                    choices=sorted(ARMS), metavar="ARM")
    ap.add_argument("--seeds", nargs="+", type=int, default=[1001])
    ap.add_argument("--n-steps", type=int, default=DEFAULT_HPO_N_STEPS)
    ap.add_argument("--out", default=os.path.join(RESULTS_DIR, "gamma_ablation_20260904.csv"))
    ap.add_argument("--allow-append", action="store_true",
                    help="write into --out even though it already exists")
    a = ap.parse_args()

    # gamma_ablation_20260904.csv -- which is still this script's default --out --
    # is the single-seed control the widened sweep is compared against. Appending
    # to it would leave the control and the new run indistinguishable inside one
    # file, so an existing destination has to be named deliberately.
    if os.path.exists(a.out) and not a.allow_append:
        print(f"REFUSING TO WRITE: {a.out} already exists.\n"
              f"Pass --out with a new path, or --allow-append to add to it.",
              file=sys.stderr, flush=True)
        raise SystemExit(3)

    fields = FIELDS + EXTRA_FIELDS
    rows: List[Dict[str, Any]] = []
    for model_name in a.models:
        for arm in a.arms:
            hp = ARMS[arm][model_name]
            for seed in a.seeds:
                row = one(model_name, arm, hp, seed, a.n_steps)
                rows.append(row)
                _append_row(a.out, fields, row)
                print(json.dumps({k: row[k] for k in fields
                                  if k not in ("hparams", "divergence_reason")}), flush=True)

    print("WROTE", a.out, flush=True)
    for line in verdict(rows):
        print(line, flush=True)


if __name__ == "__main__":
    main()
