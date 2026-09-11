#!/usr/bin/env python
# etc/scripts/measure_observation_constant_spread.py
# ============================================================================
# HOW MUCH THE OBSERVATION-NORMALISING CONSTANTS MOVE BETWEEN SCENARIOS.
#
# ---------------------------------------------------------------------------
# THE PROBLEM THIS MEASURES
# ---------------------------------------------------------------------------
# `OfflineDataset.verify_compatibility` refuses a dataset whose stored
# observation constants differ from the live ones, and it compares them for
# EXACT equality. That is right for the constants that are properties of the
# CODE, and wrong for the ones that are properties of a GENERATED NETWORK.
#
# `make_sumo_set` randomises each edge's speed limit around `AV_SPEED` by
# +/- `DEL_SPEED`, so `V_LIMIT`, and with it `V_MAX_OBS = V_LIMIT * speedFactor`
# and `E_REF = V_LIMIT`, are draws, not constants. Measured here: a dataset
# collected against one generated network was rejected against another over a
# V_MAX_OBS of 15.912 versus 15.984, a difference of 0.45 %, which is not a
# changed observation definition -- it is the same definition applied to a
# different road.
#
# An exact comparison therefore fails valid datasets, and the response to a
# check that cries wolf is that people stop running it. The response to that is
# NOT to delete the check but to give it the right tolerance, and the right
# tolerance is a measured one.
#
# ---------------------------------------------------------------------------
# WHAT IS MEASURED
# ---------------------------------------------------------------------------
# Each constant is read after `prepare_scenario` for a grid of (seed,
# force_regenerate, directory) cells, so both sources of variation are covered:
# a re-rolled network within one directory, and independently generated
# directories. The output is the observed relative spread of each constant,
# which is what a tolerance has to clear.
#
# The complementary number, and the reason a loose tolerance is safe, is the
# SAMPLING FLOOR of the state-distribution distance already measured in
# `results/hoorl_offline/w1_floor_vs_sample_size.csv`. A normalisation that
# moves by x per cent moves every affected feature by at most x per cent, and if
# that is far below the distance two halves of one sample already show, no
# consumer can tell the two datasets apart anyway.
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

#: The constants read after every scenario, and what each one is a property of.
#: `code` must match exactly across scenarios; `scenario` is a draw and can only
#: be required to match within a tolerance.
CONSTANT_ORIGIN: Dict[str, str] = {
    "N_ACTIVE_MAX_OBS": "code",   # DENSITY_GRID x RSU coverage
    "DELTA_MIN": "code",          # literal
    "RSU_RANGE": "code",          # literal in make_sumo_set
    "A_MAX": "code",              # StateVectorizer default
    "QUEUE_MAX": "code",          # StateVectorizer default
    "PHASE_REMAINING_REF_S": "code",   # literal inside vectorize_from_dict
    "DELTA_MAX": "scenario",      # longest red phase in the generated plan
    "V_MAX_OBS": "scenario",      # max edge speed x max speedFactor
    "E_REF": "scenario",          # max edge speed
}


def read_constants() -> Dict[str, float]:
    """Every normaliser, read live. Mirrors `hoorl_offline.observation_constants`."""
    import src.rl_interface as rli

    vec = rli.StateVectorizer()
    # The feature-11 divisor is a literal with no module constant, so it is
    # PROBED rather than restated: feed a known time-to-switch and invert.
    probe = vec.vectorize_from_dict({"tls_features": {"state": "g", "time_to_switch": 1.0}})
    phase_ref = 1.0 / float(probe[11]) if float(probe[11]) > 0.0 else float("nan")
    return {
        "N_ACTIVE_MAX_OBS": float(rli.N_ACTIVE_MAX_OBS),
        "V_MAX_OBS": float(rli.V_MAX_OBS),
        "E_REF": float(rli.E_REF),
        "DELTA_MAX": float(rli.DELTA_MAX),
        "DELTA_MIN": float(rli.DELTA_MIN),
        "RSU_RANGE": float(vec.rsu_range),
        "A_MAX": float(vec.a_max),
        "QUEUE_MAX": float(vec.queue_max),
        "PHASE_REMAINING_REF_S": float(phase_ref),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seeds", type=int, nargs="+",
                   default=[42, 101, 2001, 2002, 2003, 7, 12345])
    p.add_argument("--densities", type=float, nargs="+", default=[5.0, 20.0, 35.0])
    p.add_argument("--n-dirs", type=int, default=3)
    p.add_argument("--steps", type=int, default=2000)
    p.add_argument("--warmup-steps", type=int, default=1200)
    p.add_argument("--out-dir", type=str,
                   default=os.path.join(ROOT, "results", "hoorl_offline"))
    args = p.parse_args(argv)

    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    from src.hot_swap_trainer import prepare_scenario

    rows: List[Dict[str, Any]] = []
    tmp_root = tempfile.mkdtemp(prefix="obs_const_spread_")
    try:
        for d_i in range(int(args.n_dirs)):
            sumo_dir = os.path.join(tmp_root, f"dir{d_i}")
            os.makedirs(sumo_dir, exist_ok=True)
            for seed in args.seeds:
                for density in args.densities:
                    for force in (True, False):
                        prepare_scenario(
                            density=float(density), max_steps=int(args.steps),
                            warmup_steps=int(args.warmup_steps), seed=int(seed),
                            force_regenerate=bool(force), sumo_dir=sumo_dir,
                        )
                        row: Dict[str, Any] = {
                            "dir": f"dir{d_i}", "seed": int(seed),
                            "density": float(density),
                            "force_regenerate": int(bool(force)),
                        }
                        row.update(read_constants())
                        rows.append(row)
    finally:
        import shutil

        shutil.rmtree(tmp_root, ignore_errors=True)

    os.makedirs(args.out_dir, exist_ok=True)
    fields = ["dir", "seed", "density", "force_regenerate"] + list(CONSTANT_ORIGIN)
    csv_path = os.path.join(args.out_dir, "observation_constant_spread.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    summary: Dict[str, Any] = {"n_cells": len(rows), "constants": {}}
    for key, origin in CONSTANT_ORIGIN.items():
        values = sorted({round(float(r[key]), 9) for r in rows})
        lo, hi = min(values), max(values)
        rel = 0.0 if lo == 0 else (hi - lo) / abs(lo)
        summary["constants"][key] = {
            "origin": origin,
            "n_distinct": len(values),
            "min": lo,
            "max": hi,
            "relative_spread": rel,
            "values": values[:12],
        }
    json_path = os.path.join(args.out_dir, "observation_constant_spread.json")
    with open(json_path, "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)

    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"\n{csv_path}\n{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
