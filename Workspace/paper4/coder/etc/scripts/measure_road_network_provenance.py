#!/usr/bin/env python
# etc/scripts/measure_road_network_provenance.py
# ============================================================================
# WHICH ROAD NETWORK DOES EACH ENTRY POINT ACTUALLY RUN ON?
#
# ---------------------------------------------------------------------------
# THE QUESTION
# ---------------------------------------------------------------------------
# `make_sumo_set` draws every edge's speed limit from a MODULE-GLOBAL random
# generator, `_gen_rng`. `seed_generation(seed)` reseeds it; nothing else does.
# The generated road is therefore a function of that generator's STATE at the
# moment of generation, and its state depends on everything that has generated a
# network earlier in the same process.
#
# Three entry points reach `make_sumo_files`, and only one of them names a seed:
#
#   * TRAINING calls `prepare_scenario`, which calls `seed_generation(seed)`;
#   * EVALUATION calls neither. `AoiV2IEnv._init_sumo` calls `make_sumo_files`
#     directly, so the road is whatever `_gen_rng` happens to hold;
#   * THE SEARCH constructs environments per trial, through the same path.
#
# That difference is invisible in every log. `V_MAX_OBS` is read off the
# generated network, so it is a fingerprint of the road, and this script prints
# it at each point a road could change.
#
# ---------------------------------------------------------------------------
# THE SPECIFIC WORRY THIS TESTS
# ---------------------------------------------------------------------------
# `make_sumo_files` reuses a cached file set when the on-disk signature matches
# the requested (num_blocks, density, flow_end_s), and regenerates otherwise.
# The benchmark loop is `for model: for density: for seed:`, so the density
# cycles 5..35 inside every model. When it wraps back to 5 for the SECOND model
# the signature no longer matches (the directory holds density 35), a
# regeneration happens, and `_gen_rng` has advanced in the meantime.
#
# If that is what happens, model 1 and model 2 are scored at density 5 on
# DIFFERENT ROADS, and the comparison the paper rests on is between models that
# never faced the same problem. This script reproduces the loop's generation
# sequence exactly -- same calls, same order -- and prints the fingerprint, so
# the answer is measured rather than argued.
#
# No SUMO episode is simulated. Only networks are written, which is what the
# environment's constructor does before it starts libsumo.
# ============================================================================
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional, Sequence

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def fingerprint(sumo_dir: str) -> Dict[str, float]:
    """The road's identity, as the observation normalisers see it.

    `refresh_scenario_constants` is what `AoiV2IEnv._init_sumo` calls right after
    generating, so these are exactly the values an episode would run under.
    """
    from src.rl_interface import refresh_scenario_constants

    c = refresh_scenario_constants(sumo_dir)
    return {
        "V_MAX_OBS": round(float(c["V_MAX_OBS"]), 6),
        "V_LIMIT": round(float(c["V_LIMIT"]), 6),
        "E_REF": round(float(c["E_REF"]), 6),
        "DELTA_MAX": round(float(c["DELTA_MAX"]), 6),
    }


def gen_rng_state_digest() -> str:
    """A short digest of `_gen_rng`'s internal state, to show when it moves."""
    import hashlib

    import src.sumo.make_sumo_set as ss

    return hashlib.sha256(repr(ss._gen_rng.getstate()).encode()).hexdigest()[:12]


def simulate_evaluation_loop(sumo_dir: str, models: Sequence[str],
                             densities: Sequence[float], n_steps: int,
                             warmup_steps: int) -> List[Dict[str, Any]]:
    """The generation calls `run_full_benchmark` makes, in its order.

    `evaluate_single_run` builds one `AoiV2IEnv` per (model, density, seed) and
    the constructor generates. Seeds are collapsed to one here because the
    environment's `seed` argument is not passed to the generator at all, which is
    precisely the finding: within a density the road cannot change with the seed,
    only with what generated before.
    """
    import src.sumo.make_sumo_set as ss

    rows: List[Dict[str, Any]] = []
    for m_i, model in enumerate(models):
        for density in densities:
            before = gen_rng_state_digest()
            # Exactly what `AoiV2IEnv._init_sumo` does: no seed_generation.
            ss.make_sumo_files(base_path=sumo_dir, density=float(density),
                               flow_end_s=scenario_flow_end(n_steps, warmup_steps))
            after = gen_rng_state_digest()
            row = {
                "path": "evaluation",
                "model_index": m_i,
                "model": model,
                "density": float(density),
                "gen_rng_before": before,
                "gen_rng_after": after,
                "regenerated": int(before != after),
            }
            row.update(fingerprint(sumo_dir))
            rows.append(row)
    return rows


def scenario_flow_end(n_steps: int, warmup_steps: int) -> float:
    from src.hot_swap_trainer import scenario_flow_end_s

    return float(scenario_flow_end_s(int(n_steps), int(warmup_steps)))


def simulate_training_loop(sumo_dir: str, models: Sequence[str],
                           densities: Sequence[float], seed: int,
                           n_steps: int, warmup_steps: int) -> List[Dict[str, Any]]:
    """The generation calls `run_all.py` makes, in its order.

    `run_hot_swap_training` calls `prepare_scenario(seed=...)` once per run, and
    `run_all.py` loops nine models in ONE process. The question is whether that
    per-run reseed is enough to give every model the same road, given that each
    episode afterwards regenerates through `_init_sumo` without a seed.
    """
    import src.sumo.make_sumo_set as ss
    from src.hot_swap_trainer import prepare_scenario

    rows: List[Dict[str, Any]] = []
    for m_i, model in enumerate(models):
        before = gen_rng_state_digest()
        prepare_scenario(density=float(densities[0]), max_steps=int(n_steps),
                         warmup_steps=int(warmup_steps), seed=int(seed),
                         sumo_dir=sumo_dir)
        row = {"path": "training", "model_index": m_i, "model": model,
               "density": float(densities[0]), "gen_rng_before": before,
               "gen_rng_after": gen_rng_state_digest(), "regenerated": 1,
               "stage": "prepare_scenario"}
        row.update(fingerprint(sumo_dir))
        rows.append(row)
        # Episodes afterwards cycle the density WITHOUT reseeding, the same way
        # the trainer's episode loop does.
        for density in densities[1:]:
            before = gen_rng_state_digest()
            ss.make_sumo_files(base_path=sumo_dir, density=float(density),
                               flow_end_s=scenario_flow_end(n_steps, warmup_steps))
            row = {"path": "training", "model_index": m_i, "model": model,
                   "density": float(density), "gen_rng_before": before,
                   "gen_rng_after": gen_rng_state_digest(),
                   "regenerated": int(before != gen_rng_state_digest()),
                   "stage": "episode"}
            row.update(fingerprint(sumo_dir))
            rows.append(row)
    return rows


def summarise(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Does one density always get one road, within a path?"""
    out: Dict[str, Any] = {}
    for path in sorted({r["path"] for r in rows}):
        sub = [r for r in rows if r["path"] == path]
        by_density: Dict[float, set] = {}
        for r in sub:
            by_density.setdefault(r["density"], set()).add(r["V_MAX_OBS"])
        inconsistent = {f"{d:g}": sorted(v) for d, v in by_density.items() if len(v) > 1}
        out[path] = {
            "n_generations": len(sub),
            "distinct_roads_overall": len(sorted({r["V_MAX_OBS"] for r in sub})),
            "roads": sorted({r["V_MAX_OBS"] for r in sub}),
            "densities_whose_road_changed_between_models": inconsistent,
            "same_road_for_every_model_at_a_given_density": not inconsistent,
        }
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--models", nargs="+", default=None,
                   help="defaults to the nine registered baselines")
    p.add_argument("--densities", type=float, nargs="+", default=None)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--eval-steps", type=int, default=4000)
    p.add_argument("--eval-warmup", type=int, default=1200)
    p.add_argument("--out-dir", type=str,
                   default=os.path.join(ROOT, "results", "diagnostics"))
    args = p.parse_args(argv)

    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    from src.baselines import ALL_BASELINES
    from src.sumo.make_sumo_set import DENSITY_GRID

    models = args.models or sorted(ALL_BASELINES)
    densities = args.densities or [float(d) for d in DENSITY_GRID]

    rows: List[Dict[str, Any]] = []
    # Two FRESH processes cannot be simulated in one, so each path gets its own
    # directory and its own reseed of `_gen_rng` to the import-time default --
    # which is the state a newly started process is in.
    import importlib

    import src.sumo.make_sumo_set as ss

    for name, fn in (("evaluation", simulate_evaluation_loop),
                     ("training", simulate_training_loop)):
        with tempfile.TemporaryDirectory(prefix=f"roadprov_{name}_") as td:
            # Restore the generator to exactly what `import make_sumo_set` gives,
            # so each path is measured from a cold process state.
            importlib.reload(ss)
            if name == "evaluation":
                rows.extend(simulate_evaluation_loop(
                    td, models, densities, args.eval_steps, args.eval_warmup))
            else:
                rows.extend(simulate_training_loop(
                    td, models, densities, args.seed,
                    args.eval_steps, args.eval_warmup))

    os.makedirs(args.out_dir, exist_ok=True)
    fields = ["path", "model_index", "model", "density", "stage", "regenerated",
              "gen_rng_before", "gen_rng_after", "V_MAX_OBS", "V_LIMIT", "E_REF",
              "DELTA_MAX"]
    csv_path = os.path.join(args.out_dir, "road_network_provenance.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})

    summary = summarise(rows)
    json_path = os.path.join(args.out_dir, "road_network_provenance.json")
    with open(json_path, "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True, default=str)

    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    print(f"\n{csv_path}\n{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
