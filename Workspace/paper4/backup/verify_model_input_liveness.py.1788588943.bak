#!/usr/bin/env python3
"""Observation liveness measured where it matters: the model's own input.

design_spec_v2 principle P3.

The predecessor of this script (`verify_observation_liveness.py`) sampled what
`env.step()` RETURNS. Those vectors were genuinely live -- and the model never
saw them. The training loop used the returned dict only to enumerate vehicle
ids, and the scheduler rebuilt its own vector from a four-key state dict, so 15
of 18 dimensions reached the policy as constants. A liveness check that does not
intercept `select_action` cannot see that class of defect at all.

This script hooks the actual inference call. Any dimension it reports as DEAD is
a dimension the network cannot condition on, whatever the environment computes.

Usage:
    cd /home/imnyj/Workspace/paper4/coder
    /home/imnyj/venv/bin/python etc/scripts/verify_model_input_liveness.py [--steps 600]

Exit code 0 when every dimension varies, 1 otherwise.
"""
from __future__ import annotations
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np  # noqa: E402

import src.hot_swap_trainer as H  # noqa: E402
from src.baselines import get_baseline  # noqa: E402

FEATURE_NAMES = [
    "0  last_pred_err", "1  vel_x", "2  vel_y", "3  speed", "4  accel",
    "5  dx", "6  dy", "7  dist_to_rsu",
    "8  tls_red", "9  tls_yellow", "10 tls_green",
    "11 time_to_switch", "12 dist_to_stopline",
    "13 n_active", "14 cbr", "15 n_queue", "16 heading",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("--model", type=str, default="PPO")
    ap.add_argument("--density", type=float, default=25.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--scratch", type=str, default="etc/temp/liveness")
    args = ap.parse_args()

    seen: list = []
    original = H.HotSwapRLScheduler.decide_grant

    def spy(self, vid, state_vec):
        seen.append(np.asarray(state_vec, dtype=np.float32).copy())
        return original(self, vid, state_vec)

    H.HotSwapRLScheduler.decide_grant = spy
    try:
        H.run_hot_swap_training(
            model_cls=get_baseline(args.model), model_name=args.model,
            episodes=1, total_steps=args.steps, density=args.density, seed=args.seed,
            resume=False,
            checkpoint_dir=os.path.join(args.scratch, "ck"),
            tensorboard_dir=os.path.join(args.scratch, "tb"),
            log_csv_path=os.path.join(args.scratch, "progress.csv"),
        )
    finally:
        H.HotSwapRLScheduler.decide_grant = original

    if not seen:
        print("FAIL: the model was never asked for a decision.")
        return 1

    V = np.array(seen)
    n_dims = V.shape[1]
    if n_dims != len(FEATURE_NAMES):
        print(f"WARNING: vector width {n_dims} != {len(FEATURE_NAMES)} labelled features.")

    print(f"\nModel inference inputs sampled: {V.shape[0]} vectors x {n_dims} dims "
          f"({args.model}, {args.steps} steps, density {args.density})\n")
    print(f"{'dimension':<20}{'unique':>9}{'mean':>11}{'std':>11}{'min':>10}{'max':>10}   verdict")
    dead = []
    for i in range(n_dims):
        col = V[:, i]
        uniq = len(np.unique(np.round(col, 6)))
        name = FEATURE_NAMES[i] if i < len(FEATURE_NAMES) else f"{i} ?"
        verdict = ""
        if uniq <= 1:
            verdict = "DEAD"
            dead.append(name)
        elif uniq == 2 and set(np.unique(np.round(col, 6))) <= {0.0, 1.0}:
            verdict = "binary (expected for one-hots)"
        print(f"{name:<20}{uniq:>9}{col.mean():>11.5f}{col.std():>11.5f}"
              f"{col.min():>10.4f}{col.max():>10.4f}   {verdict}")

    print()
    if dead:
        print(f"FAIL: {len(dead)}/{n_dims} dimensions are constant at the model input: {dead}")
        return 1
    print(f"PASS: all {n_dims} dimensions vary at the model input.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
