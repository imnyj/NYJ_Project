#!/usr/bin/env python
# etc/scripts/measure_rollout_cost_nine.py
# ============================================================================
# WHAT ONE HPO TRIAL COSTS, FOR EACH OF THE NINE BASELINES.
#
# ---------------------------------------------------------------------------
# WHY IT HAS TO BE MEASURED AGAIN
# ---------------------------------------------------------------------------
# `results/diagnostics/hpo_group_balance.csv` divides the nine models into four
# GPU groups so the groups finish together, and the division is only as good as
# the per-model costs it is built on. Those costs came from a study run before
# three things changed: the observation went from 17 features to 21, the road
# network became a deterministic function of (density, cycle) rather than of the
# generator's history, and the neighbour cap went from 16 to 192. Each of the
# three changes the work a rollout does, and the third does not change it
# equally across models -- only the four that encode a neighbour set feel it.
#
# ---------------------------------------------------------------------------
# WHY ONE SEED AND A PROJECTION, RATHER THAN A STUDY
# ---------------------------------------------------------------------------
# A trial is three seeds and a study is fifteen trials, so measuring the way the
# old table was built means re-running the search itself. What is needed here is
# the RELATIVE cost of the nine, and one seed at the search's own rollout length
# gives that at a fifteenth of the price. It is the same method the HOORL row of
# the current table was produced by (293.8 s x 3 = 881.5 s), so the new numbers
# and that one are comparable.
#
# WHAT THE PROJECTION ASSUMES, STATED: that the three seeds of a trial cost the
# same as each other. They do not exactly -- a seed whose rollout is condemned
# early stops early, which is the whole point of the divergence guard -- so a
# projection is an upper estimate for any model that sometimes diverges.
#
# ---------------------------------------------------------------------------
# WHY THE MEDIAN OF THE SEARCH SPACE, NOT THE DEFAULTS
# ---------------------------------------------------------------------------
# Cost depends on the hyper-parameters, `hidden_dim` most of all, and the search
# will spend its time somewhere inside the space rather than at the constructor
# defaults. `_MedianTrial` answers every `suggest_*` call with the middle of the
# range it was given, so each model is measured at the centre of the space it
# will actually be searched over. It reads the ranges from `sample_hparams`
# itself, which means a change to the search space reaches this measurement
# without anyone remembering to update it.
# ============================================================================
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: Seeds a trial averages over. Only the count is used here; the single measured
#: seed is the first of them.
TRIAL_SEEDS = (1001, 1002, 1003)


class _MedianTrial:
    """An Optuna trial that always answers with the centre of the range.

    Not a mock of the search: it is a deterministic point INSIDE the search
    space, used so that nine models are compared at a comparable place in their
    own spaces. Log-scaled floats take the geometric centre, because that is the
    centre of the distribution the sampler actually draws from.
    """

    def __init__(self) -> None:
        self.params: Dict[str, Any] = {}

    def _record(self, name: str, value: Any) -> Any:
        self.params[name] = value
        return value

    def suggest_float(self, name: str, low: float, high: float,
                      log: bool = False, step: Optional[float] = None) -> float:
        mid = (low * high) ** 0.5 if log else (low + high) / 2.0
        return self._record(name, float(mid))

    def suggest_int(self, name: str, low: int, high: int, step: int = 1,
                    log: bool = False) -> int:
        return self._record(name, int((low + high) // 2))

    def suggest_categorical(self, name: str, choices: Sequence[Any]) -> Any:
        return self._record(name, list(choices)[len(choices) // 2])

    def set_user_attr(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--models", nargs="+", default=None)
    p.add_argument("--n-steps", type=int, default=None,
                   help="rollout length; defaults to the search's own")
    p.add_argument("--seed", type=int, default=TRIAL_SEEDS[0])
    p.add_argument("--density", type=float, default=25.0)
    p.add_argument("--out-dir", default=os.path.join(ROOT, "results", "diagnostics"))
    args = p.parse_args(argv)

    import torch

    from src.baselines import ALL_BASELINES, get_baseline
    from src.hoorl_wiring import offline_hparams
    from src.hot_swap_trainer import prepare_scenario
    from src.hpo import (
        DEFAULT_HPO_N_STEPS, DEFAULT_PRETRAIN_BATCH_SIZE, DEFAULT_PRETRAIN_UPDATES,
        HPO_ROAD_CYCLE, _rollout_scenario_spec, composite_objective_terms,
        evaluate_model_in_env, pretrain_hoorl, sample_hparams,
    )
    from src.rl_interface import MAX_NEIGHBOURS, STATE_DIM
    import src.Communications as comm
    from src.sumo.make_sumo_set import seed_road_network

    n_steps = args.n_steps or DEFAULT_HPO_N_STEPS
    models = args.models or sorted(ALL_BASELINES)
    rows: List[Dict[str, Any]] = []

    for name in models:
        cls = get_baseline(name)
        trial = _MedianTrial()
        try:
            hparams = sample_hparams(trial, name)
        except Exception as exc:  # noqa: BLE001
            rows.append({"model": name, "error": f"{type(exc).__name__}: {exc}"})
            print(f"{name:14s} search space refused the name: {exc}", flush=True)
            continue

        # The scenario before the model, the same order `evaluate_trial_multiseed`
        # keeps: the decoder and the vectoriser read constants off the network on
        # disk, so a model built first describes a network nobody simulated.
        spec = _rollout_scenario_spec(density=args.density, n_steps=n_steps)
        prepare_scenario(density=spec["density"], max_steps=spec["max_steps"],
                         warmup_steps=spec["warmup_steps"],
                         seed=seed_road_network(spec["density"], HPO_ROAD_CYCLE))

        t_build = time.perf_counter()
        model = cls(state_dim=STATE_DIM, num_channels=comm.NUM_SUBCHANNELS,
                    **offline_hparams(cls, hparams))
        build_s = time.perf_counter() - t_build

        t_pre = time.perf_counter()
        offline = pretrain_hoorl(model, num_updates=DEFAULT_PRETRAIN_UPDATES,
                                 batch_size=DEFAULT_PRETRAIN_BATCH_SIZE,
                                 require_offline=True)
        pretrain_s = time.perf_counter() - t_pre

        t0 = time.perf_counter()
        try:
            metrics = evaluate_model_in_env(
                model=model, seed=args.seed, n_steps=n_steps,
                density=args.density, train_steps_during_rollout=2)
            err = ""
        except Exception as exc:  # noqa: BLE001
            metrics, err = {}, f"{type(exc).__name__}: {exc}"
        rollout_s = time.perf_counter() - t0

        seed_s = build_s + pretrain_s + rollout_s
        row = {
            "model": name,
            "hidden_dim": hparams.get("hidden_dim", ""),
            "build_s": round(build_s, 2),
            "pretrain_s": round(pretrain_s, 2),
            "rollout_s": round(rollout_s, 2),
            "one_seed_s": round(seed_s, 2),
            "projected_trial_s": round(seed_s * len(TRIAL_SEEDS), 1),
            "projected_15trial_h": round(seed_s * len(TRIAL_SEEDS) * 15 / 3600.0, 2),
            "steps_completed": int(metrics.get("steps_completed", 0) or 0),
            "n_grad_updates": int(metrics.get("n_grad_updates", 0) or 0),
            "n_observations": int(metrics.get("n_observations", 0) or 0),
            "offline_pretrained": int(offline is not None),
            "score": round(float(sum(composite_objective_terms(metrics).values())), 4)
                     if metrics else "",
            "error": err,
        }
        rows.append(row)
        print(f"{name:14s} rollout {rollout_s:8.1f} s  pretrain {pretrain_s:6.1f} s  "
              f"-> trial {row['projected_trial_s']:8.1f} s  "
              f"({row['projected_15trial_h']:.2f} h for 15){'  ' + err if err else ''}",
              flush=True)
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    os.makedirs(args.out_dir, exist_ok=True)
    keys: List[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    csv_path = os.path.join(args.out_dir, "rollout_cost_nine.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})

    ok = [r for r in rows if not r.get("error") and r.get("one_seed_s")]
    json_path = os.path.join(args.out_dir, "rollout_cost_nine.json")
    with open(json_path, "w") as fh:
        json.dump({
            "n_steps": int(n_steps),
            "seed_measured": int(args.seed),
            "seeds_per_trial": len(TRIAL_SEEDS),
            "density": float(args.density),
            "road_cycle": int(HPO_ROAD_CYCLE),
            "state_dim": int(STATE_DIM),
            "max_neighbours": int(MAX_NEIGHBOURS),
            "device": ("cuda:0" if torch.cuda.is_available() else "cpu"),
            "gpus": [torch.cuda.get_device_name(i)
                     for i in range(torch.cuda.device_count())],
            "hparams": "median of each model's own search space (_MedianTrial)",
            "total_measured_s": round(sum(r["one_seed_s"] for r in ok), 1),
            "projection_caveat": (
                "projected_trial_s assumes the three seeds of a trial cost the "
                "same. A model that sometimes diverges stops early on those "
                "seeds, so its projection is an upper estimate."),
        }, fh, indent=2, sort_keys=True, default=float)
    print(f"\n{csv_path}\n{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
