#!/usr/bin/env python
# etc/scripts/measure_n_active_tail.py
# ============================================================================
# THE TRUE TAIL OF THE IN-COVERAGE VEHICLE COUNT, PER DENSITY.
#
# ---------------------------------------------------------------------------
# WHY THE COLLECTED DATASET CANNOT ANSWER THIS
# ---------------------------------------------------------------------------
# Observation feature [13] is `clip(n_active / N_ACTIVE_MAX_OBS, 0, 1)`. Above
# the cap the feature is exactly 1.0 and the excess is destroyed, so a dataset of
# observations is CENSORED at the cap and its maximum is the cap, not the count.
# Measured on the 133,405-transition collection: densities 5, 10 and 15 never
# reach the cap and their maxima are real (34, 73, 127), while 20, 25, 30 and 35
# all report a maximum of exactly 168.0 with 0.55 % to 6.62 % of rows pinned
# there. From that data the true peak is unknowable; all it says is ">= 168".
#
# So the count is read here from the environment's own `_count_active_vehicles()`
# BEFORE any normalisation, which is the only place the uncensored number exists.
#
# ---------------------------------------------------------------------------
# WHY THIS MATTERS FOR THE CAP ITSELF
# ---------------------------------------------------------------------------
# `N_ACTIVE_MAX_OBS` is derived from `max(DENSITY_GRID) * rsu_coverage_lane_km()`,
# a free-flow capacity, and it was raised from a literal 100 to 168 on the
# strength of a MEAN in-range count of 141.7 at density 35. A ceiling chosen to
# prevent saturation cannot be set from a central tendency: the mean says where
# the distribution sits, and the cap has to clear its TAIL. This script produces
# the tail.
#
# It deliberately does not change the constant. Moving it invalidates every
# dataset and every checkpoint normalised against the current value, so the
# decision is separate from the measurement.
#
# ---------------------------------------------------------------------------
# WHAT IT DOES NOT CONTROL FOR
# ---------------------------------------------------------------------------
# The road network. Edge speed limits are drawn per generated network and affect
# throughput, so the counts belong to the roads this run happened to generate.
# The seed and the resulting `V_MAX_OBS` are recorded per cell for that reason.
# No policy is involved: vehicle count is a property of the scenario, not of the
# scheduler, so a fixed trivial grant is used and its choice cannot bias the
# answer.
# ============================================================================
from __future__ import annotations

import argparse
import csv
import gc
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def measure(density: float, seed: int, steps: int, warmup_steps: int,
            sumo_dir: Optional[str], cycle: int) -> Dict[str, Any]:
    """Per-step in-coverage vehicle counts for one (density, cycle, seed) episode.

    The road is named by `(density, cycle)` through `seed_road_network`, so the
    count is attributable to a road a reader can regenerate. The first version of
    this script reseeded to a single value per cell, which put every density on
    the SAME road and reported a maximum of 167 -- just under the cap -- while the
    collected dataset, spread over eight roads, was censored at the cap in 6.6 %
    of its density-20 rows. One road cannot answer a question about the tail
    across roads.
    """
    from src.hot_swap_trainer import AoiV2IEnv, prepare_scenario
    from src.sumo.make_sumo_set import seed_road_network

    used_seed = seed_road_network(float(density), int(cycle))
    prepare_scenario(density=float(density), max_steps=int(steps),
                     warmup_steps=int(warmup_steps), seed=int(used_seed),
                     sumo_dir=sumo_dir)

    counts: List[int] = []
    env: Optional[Any] = None
    try:
        env = AoiV2IEnv(density=float(density), seed=int(seed), max_steps=int(steps),
                        warmup_steps=int(warmup_steps), sumo_dir=sumo_dir)
        obs, _info = env.reset()
        # A standing grant that never expires within the episode, so the loop
        # advances the simulation and nothing else. The count does not depend on
        # it: `_count_active_vehicles` asks SUMO who is inside the coverage disc.
        grant = (10.0, 0, float(env.decoder.p_min))
        action = {vid: grant for vid in obs}
        for _ in range(int(steps)):
            next_obs, _r, _t, _tr, info = env.step(action)
            counts.append(int(env._count_active_vehicles()))
            action = {vid: grant for vid in info["needs_decision"] if vid in next_obs}
        env.finalize_open_intervals()
        import src.rl_interface as rli
        v_max = float(rli.V_MAX_OBS)
    finally:
        if env is not None:
            try:
                env.close()
            except Exception:  # noqa: BLE001
                pass
            del env
            gc.collect()

    a = np.asarray(counts, dtype=np.float64)
    return {
        "density": float(density), "seed": int(seed), "cycle": int(cycle),
        "road_seed": int(used_seed),
        "V_MAX_OBS": round(v_max, 6), "n_steps": int(a.size),
        "mean": round(float(a.mean()), 2),
        "p50": float(np.percentile(a, 50)),
        "p95": float(np.percentile(a, 95)),
        "p99": float(np.percentile(a, 99)),
        "p999": float(np.percentile(a, 99.9)),
        "max": float(a.max()),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--densities", type=float, nargs="+", default=None)
    p.add_argument("--seeds", type=int, nargs="+", default=[2001])
    p.add_argument("--steps", type=int, default=600)
    p.add_argument("--warmup-steps", type=int, default=1200)
    p.add_argument("--cycles", type=int, nargs="+", default=[0, 1, 2, 15],
                   help="road cycles to cover; 0-2 are the collection's, 15 is "
                        "evaluation's, and training walks 0-13")
    p.add_argument("--sumo-dir", type=str, default=None)
    p.add_argument("--out-dir", type=str,
                   default=os.path.join(ROOT, "results", "hoorl_offline"))
    args = p.parse_args(argv)

    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    from src.sumo.make_sumo_set import DENSITY_GRID

    densities = args.densities or [float(d) for d in DENSITY_GRID]
    rows = [measure(d, s, args.steps, args.warmup_steps, args.sumo_dir, c)
            for c in args.cycles for d in densities for s in args.seeds]
    for r in rows:
        print(f"density {r['density']:5.1f} seed {r['seed']}: mean {r['mean']:7.2f} "
              f"p99 {r['p99']:6.1f} p99.9 {r['p999']:6.1f} max {r['max']:6.1f} "
              f"(road {r['V_MAX_OBS']})", flush=True)

    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, "n_active_tail_uncensored.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    import src.rl_interface as rli

    overall_max = max(r["max"] for r in rows)
    summary = {
        "current_N_ACTIVE_MAX_OBS": float(rli.N_ACTIVE_MAX_OBS),
        "max_observed_over_all_cells": overall_max,
        "cap_exceeded": bool(overall_max > float(rli.N_ACTIVE_MAX_OBS)),
        "densities": densities, "seeds": [int(s) for s in args.seeds],
        "steps": int(args.steps), "warmup_steps": int(args.warmup_steps),
        "cycles": [int(c) for c in args.cycles],
        "note": (
            "Counts read from AoiV2IEnv._count_active_vehicles() BEFORE the clip, "
            "so unlike observation feature [13] they are not censored at the cap. "
            "No policy is involved. The constant is NOT changed here."
        ),
    }
    with open(os.path.join(args.out_dir, "n_active_tail_uncensored.json"), "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)
    print("\n" + json.dumps(summary, indent=2, sort_keys=True))
    print(f"\n{csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
