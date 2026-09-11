#!/usr/bin/env python3
# etc/scripts/probe_offline_collection_cost.py
# ============================================================================
# TIMING PROBE, NOT A COLLECTION RUN.
#
# It measures two things that a transition-count proposal cannot be written
# without, and writes NO dataset:
#
#   1. wall-clock seconds per environment step, on CPU, with no model and no
#      gradient, at several densities;
#   2. how many CLOSED intervals (i.e. stored transitions) one step yields,
#      which is what actually converts a time budget into a transition count.
#
# (2) is dominated by Delta: a vehicle in coverage contributes roughly one
# transition every Delta seconds, so the yield scales as
# (vehicles in coverage) * STEP_LENGTH / Delta. The probe sweeps Delta so the
# proposal can be stated as a cost curve rather than a single guess.
#
# Everything runs inside whatever PAPER4_SUMO_DIR points at, so it cannot
# disturb the shared scenario directory.
# ============================================================================

from __future__ import annotations

import argparse
import csv
import gc
import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402

from src.hoorl_offline import FixedPeriodBehaviourPolicy, limit_cpu_threads  # noqa: E402
from src.rl_interface import ActionDecoder  # noqa: E402


def probe_one(density: float, delta_fixed: float, seed: int, steps: int,
              warmup_steps: int, num_channels: int, sumo_dir: str) -> dict:
    from src.hot_swap_trainer import AoiV2IEnv, DEFAULT_ERROR_MODE, prepare_scenario

    prepare_scenario(density=density, max_steps=steps, warmup_steps=warmup_steps,
                     seed=seed, sumo_dir=sumo_dir)
    decoder = ActionDecoder(num_channels=num_channels)
    delta = float(min(max(delta_fixed, decoder.delta_min), decoder.delta_max))
    policy = FixedPeriodBehaviourPolicy(
        delta_band_center=delta, num_channels=num_channels,
        p_min=decoder.p_min, p_max=decoder.p_max,
    )
    rng = np.random.default_rng(seed)

    env = None
    n_closed = 0
    n_veh_samples = []
    t_setup0 = time.time()
    try:
        env = AoiV2IEnv(density=density, seed=seed, max_steps=steps,
                        warmup_steps=warmup_steps, num_channels=num_channels,
                        error_mode=DEFAULT_ERROR_MODE, sumo_dir=sumo_dir)
        obs, _ = env.reset()
        random.seed(seed)
        setup_s = time.time() - t_setup0

        action_dict = {}
        for vid in obs:
            grant, _ch, _lp = policy.sample(rng, decoder)
            action_dict[vid] = grant

        t0 = time.time()
        for _ in range(steps):
            next_obs, _r, _t, _tr, info = env.step(action_dict)
            n_closed += len(info["completed"])
            n_veh_samples.append(len(next_obs))
            action_dict = {}
            for vid in info["needs_decision"]:
                if vid in next_obs:
                    grant, _ch, _lp = policy.sample(rng, decoder)
                    action_dict[vid] = grant
            obs = next_obs
        loop_s = time.time() - t0
    finally:
        if env is not None:
            try:
                env.close()
            except Exception:
                pass
            del env
            gc.collect()

    mean_veh = float(np.mean(n_veh_samples)) if n_veh_samples else 0.0
    return {
        "density": density,
        "delta_fixed": delta,
        "seed": seed,
        "error_mode": DEFAULT_ERROR_MODE,
        "steps": steps,
        "warmup_steps": warmup_steps,
        "setup_s": round(setup_s, 2),
        "loop_s": round(loop_s, 2),
        "steps_per_s": round(steps / loop_s, 2) if loop_s > 0 else 0.0,
        "mean_vehicles_in_coverage": round(mean_veh, 2),
        "transitions": n_closed,
        "transitions_per_step": round(n_closed / steps, 4) if steps else 0.0,
        "transitions_per_s_wall": round(n_closed / loop_s, 2) if loop_s > 0 else 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--densities", type=float, nargs="+", default=[5.0, 20.0, 35.0])
    ap.add_argument("--deltas", type=float, nargs="+", default=[1.0, 5.0])
    ap.add_argument("--seed", type=int, default=2001)
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--warmup-steps", type=int, default=600)
    ap.add_argument("--num-channels", type=int, default=4)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--sumo-dir", type=str, required=True)
    ap.add_argument("--out", type=str, required=True)
    args = ap.parse_args()

    limit_cpu_threads(args.threads)
    rows = []
    for delta in args.deltas:
        for density in args.densities:
            row = probe_one(density, delta, args.seed, args.steps,
                            args.warmup_steps, args.num_channels, args.sumo_dir)
            rows.append(row)
            print(row, flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
