"""Check that every dimension of the observation vector actually carries a signal.

Three separate features in this project shipped wired-but-dead: velocity X/Y and
heading were frozen at 0 by a stale velocity computation, CBR was never placed in
the state dict, and n_active fell back to its default of 1 for every vehicle in
every step. Each looked fine in a grep and passed the whole test suite. This runs
the production environment and reports, per dimension, how much variation it shows,
so a constant feature cannot hide again.

A dimension may legitimately be constant over a short window (a signal phase that
never changes, an indicator that never fires), so the report distinguishes "no
variation observed" from "structurally dead" and prints enough for a human to judge.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np  # noqa: E402

from src.hot_swap_trainer import AoiV2IEnv  # noqa: E402
from src.rl_interface import STATE_DIM, ActionDecoder  # noqa: E402

LABELS = [
    "AoI age", "vel X", "vel Y", "speed", "accel", "rel X", "rel Y", "dist RSU",
    "TLS red", "TLS yellow", "TLS green", "time to switch", "dist stopline",
    "n_active", "CBR", "dynamics indicator", "n_queue", "heading",
]
STEPS = 1000  # must span a full 90 s signal cycle at 0.1 s steps


def main() -> int:
    env = AoiV2IEnv(density=45.0, seed=42, max_steps=STEPS, warmup_steps=60)
    obs, _ = env.reset()
    dec = ActionDecoder(num_channels=4)
    rows = []
    for _ in range(STEPS):
        # Grant every vehicle each step, round-robin across subchannels, so the
        # transmission path runs and CBR is actually exercised. Without grants the
        # channel is idle and CBR is legitimately but uninformatively zero.
        action = {
            vid: dec.encode_action(0.5, j % 4, 15.0)
            for j, vid in enumerate(sorted(obs))
        }
        obs, *_ = env.step(action)
        rows.extend(np.asarray(v, dtype=np.float64) for v in obs.values())

    if not rows:
        print("no observations produced")
        return 1
    mat = np.vstack(rows)
    print(f"observations: {mat.shape[0]:,}   dims: {mat.shape[1]} (expected {STATE_DIM})")
    print(f"\n{'#':>3} {'feature':<20} {'min':>9} {'max':>9} {'mean':>9} {'distinct':>9}  status")
    dead = []
    for i in range(mat.shape[1]):
        col = mat[:, i]
        n_distinct = len(np.unique(np.round(col, 6)))
        label = LABELS[i] if i < len(LABELS) else f"dim{i}"
        status = "live" if n_distinct > 1 else "NO VARIATION"
        if n_distinct <= 1:
            dead.append((i, label, float(col[0])))
        print(f"{i:>3} {label:<20} {col.min():>9.4f} {col.max():>9.4f} "
              f"{col.mean():>9.4f} {n_distinct:>9}  {status}")

    print()
    if dead:
        print(f"{len(dead)} dimension(s) showed no variation over {STEPS} steps:")
        for i, label, val in dead:
            print(f"  [{i}] {label} constant at {val}")
        print("Judge each: an indicator that never fired is fine, a feature that is "
              "never supplied is a bug.")
        return 1
    print(f"All {mat.shape[1]} dimensions vary. No dead features.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
