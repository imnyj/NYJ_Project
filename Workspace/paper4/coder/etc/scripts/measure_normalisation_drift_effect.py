#!/usr/bin/env python
# etc/scripts/measure_normalisation_drift_effect.py
# ============================================================================
# WHAT A 0.76 % MOVE IN V_MAX_OBS AND E_REF ACTUALLY DOES TO THE OBSERVATIONS.
#
# ---------------------------------------------------------------------------
# WHY THIS NUMBER IS NEEDED
# ---------------------------------------------------------------------------
# `OfflineDataset.verify_compatibility` compares the stored observation
# normalisers against the live ones and refuses the dataset on any difference.
# `measure_observation_constant_spread.py` shows that two of the nine, V_MAX_OBS
# and E_REF, are draws from the generated road network rather than properties of
# the code, and that they span 0.756 % over 90 scenarios. Under exact equality a
# perfectly valid dataset is therefore rejected whenever the training run's road
# drew a slightly different top speed, which is what happened on 2026-09-06
# (15.912 stored against 15.984 live).
#
# The check still has to catch the failure it was built for: `N_ACTIVE_MAX_OBS`
# moving from 100 to 168 is a 68 % change that silently redefines feature [13].
# So the question is not "exact or not" but "how big a move is indistinguishable
# from noise", and that has an answer that can be measured instead of argued.
#
# ---------------------------------------------------------------------------
# HOW IT IS MEASURED
# ---------------------------------------------------------------------------
# One real sample of states is collected, then RENORMALISED as if it had been
# recorded under a shifted constant, and the two versions are compared with the
# same Wasserstein-1 measure `src/hoorl_offline_stats.py` already defines and
# against the same control: the SPLIT-HALF SAMPLING FLOOR, i.e. the distance two
# halves of one sample show against each other purely from being finite. A drift
# whose effect sits below that floor cannot be detected by any consumer of the
# data, whatever the constant's nominal difference.
#
# The renormalisation is exact rather than approximate. Features 1, 2 and 3 are
# velocity divided by V_MAX_OBS, so restoring the physical value and dividing by
# the other constant is a multiplication by the ratio, with the vectoriser's own
# clipping reapplied. Feature 0 is `e^2 / (e^2 + E_REF^2)`, which is inverted
# exactly for e and re-evaluated at the other E_REF.
#
# Several shift magnitudes are swept, so the output is a curve of "effect versus
# nominal drift" and the tolerance can be read off it rather than picked.
# ============================================================================
from __future__ import annotations

import argparse
import csv
import gc
import json
import math
import os
import random
import sys
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: Nominal relative drifts to sweep, applied to V_MAX_OBS and E_REF. 0.00756 is
#: their measured spread across 90 scenarios. The larger entries do NOT restage
#: the N_ACTIVE_MAX_OBS change of 2026-09-05, which acted on a different feature;
#: they calibrate how large a drift of THESE two constants has to be before it
#: rises above the sampling floor, which is what a tolerance on them needs to
#: know. 0.68 is included because it is the magnitude of that historical change,
#: so the sweep spans from the noise the scenario generator produces to the size
#: of a real redefinition.
DRIFTS: Sequence[float] = (0.001, 0.00756, 0.02, 0.05, 0.10, 0.25, 0.68)


def collect_states(density: float, seed: int, steps: int, warmup_steps: int,
                   sumo_dir: Optional[str], num_channels: int = 4) -> np.ndarray:
    """Real observations from one episode under a log-uniform-Delta policy."""
    from src.hot_swap_trainer import AoiV2IEnv, prepare_scenario
    from src.rl_interface import ActionDecoder

    prepare_scenario(density=float(density), max_steps=int(steps),
                     warmup_steps=int(warmup_steps), seed=int(seed), sumo_dir=sumo_dir)
    decoder = ActionDecoder(num_channels=int(num_channels))
    rng = np.random.default_rng(int(seed))
    lo, hi = 0.5, 10.0

    states: List[np.ndarray] = []
    env: Optional[Any] = None
    try:
        env = AoiV2IEnv(density=float(density), seed=int(seed), max_steps=int(steps),
                        warmup_steps=int(warmup_steps), num_channels=int(num_channels),
                        sumo_dir=sumo_dir)
        obs, _info = env.reset()
        random.seed(int(seed))

        def draw():
            return (float(np.exp(rng.uniform(math.log(lo), math.log(hi)))),
                    int(rng.integers(0, num_channels)),
                    float(rng.uniform(decoder.p_min, decoder.p_max)))

        action_dict = {vid: draw() for vid in obs}
        for _ in range(int(steps)):
            next_obs, _r, _t, _tr, info = env.step(action_dict)
            action_dict = {}
            for vid in info["needs_decision"]:
                if vid in next_obs:
                    action_dict[vid] = draw()
                    states.append(np.asarray(next_obs[vid], dtype=np.float32))
        # Nothing here stores transitions, so no reward is lost by skipping this;
        # it is called anyway so the run does not emit a discarded-interval
        # warning that a later reader would have to rule out.
        env.finalize_open_intervals()
    finally:
        if env is not None:
            try:
                env.close()
            except Exception:  # noqa: BLE001
                pass
            del env
            gc.collect()
    return np.asarray(states, dtype=np.float32)


def renormalise(states: np.ndarray, v_ratio: float, e_ratio: float) -> np.ndarray:
    """The same physical situations as if the normalisers had been scaled.

    `v_ratio` is new_V_MAX_OBS / old_V_MAX_OBS and `e_ratio` the same for E_REF.
    Features 1, 2 and 3 are linear in 1 / V_MAX_OBS and are simply rescaled, with
    the vectoriser's clipping reapplied. Feature 0 is inverted exactly:

        f = e^2 / (e^2 + E^2)   =>   e^2 = E^2 * f / (1 - f)

    so the physical error is recovered and re-squashed at the other E. A value of
    exactly 1.0 has no finite inverse and stays 1.0, which is correct: an error
    that saturated one reference saturates a reference within a per cent of it.
    """
    out = np.array(states, dtype=np.float64, copy=True)
    out[:, 1] = np.clip(out[:, 1] / v_ratio, -1.0, 1.0)
    out[:, 2] = np.clip(out[:, 2] / v_ratio, -1.0, 1.0)
    out[:, 3] = np.clip(out[:, 3] / v_ratio, 0.0, 1.0)

    f = out[:, 0]
    finite = f < 1.0
    ratio = np.zeros_like(f)
    ratio[finite] = f[finite] / (1.0 - f[finite])
    # e^2 / E_new^2 = (e^2 / E_old^2) / e_ratio^2
    scaled = ratio / (e_ratio ** 2)
    out[finite, 0] = scaled[finite] / (1.0 + scaled[finite])
    return out.astype(np.float32)


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--density", type=float, default=20.0)
    p.add_argument("--seed", type=int, default=2001)
    p.add_argument("--steps", type=int, default=1200)
    p.add_argument("--warmup-steps", type=int, default=600)
    p.add_argument("--sumo-dir", type=str, default=None)
    p.add_argument("--out-dir", type=str,
                   default=os.path.join(ROOT, "results", "hoorl_offline"))
    args = p.parse_args(argv)

    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    states = collect_states(args.density, args.seed, args.steps,
                            args.warmup_steps, args.sumo_dir)
    if states.shape[0] < 200:
        raise SystemExit(f"only {states.shape[0]} states collected; run longer")

    from src.hoorl_offline_stats import (
        energy_distance,
        mean_normalised_w1,
        split_half_floor,
    )

    floor = split_half_floor(states, repeats=9)
    floor_w1 = float(floor["mean_normalised_w1_mean"]) if isinstance(floor, dict) \
        else float(floor[0])

    rows: List[Dict[str, Any]] = []
    for drift in DRIFTS:
        shifted = renormalise(states, 1.0 + float(drift), 1.0 + float(drift))
        w1 = float(mean_normalised_w1(states, shifted))
        ed = float(energy_distance(states, shifted))
        rows.append({
            "nominal_relative_drift": float(drift),
            "mean_normalised_w1": w1,
            "energy_distance": ed,
            "w1_over_sampling_floor": w1 / floor_w1 if floor_w1 > 0 else float("nan"),
            "detectable": int(w1 > floor_w1),
        })
        print(f"drift {drift:8.5f} -> W1 {w1:.6f}  ({w1 / floor_w1:6.3f} x floor)"
              f"  energy {ed:.6f}")

    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, "normalisation_drift_effect.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    meta = {
        "n_states": int(states.shape[0]),
        "density": float(args.density),
        "seed": int(args.seed),
        "steps": int(args.steps),
        "split_half_floor_mean_normalised_w1": floor_w1,
        "floor_detail": floor if isinstance(floor, dict) else None,
        "note": (
            "A drift whose mean normalised W1 sits below the split-half sampling "
            "floor is indistinguishable from the noise a finite sample already "
            "shows, so no consumer of the dataset can be affected by it."
        ),
    }
    with open(os.path.join(args.out_dir, "normalisation_drift_effect.json"), "w") as fh:
        json.dump(meta, fh, indent=2, sort_keys=True, default=float)
    print(json.dumps(meta, indent=2, sort_keys=True, default=float))
    print(f"\n{csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
