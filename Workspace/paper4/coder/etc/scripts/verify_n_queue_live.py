"""Live SUMO check that n_queue is a real, varying signal rather than a silent zero.

Runs the production environment for a short window and records the distribution of the
n_queue feature (state vector index 16) across all observed vehicles. An always-zero
result means the feature is wired but dead, which is the failure mode this script exists
to catch. Written under etc/scripts per the project's workspace-cleanliness rule.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.hot_swap_trainer import AoiV2IEnv  # noqa: E402
from src.rl_interface import STATE_DIM  # noqa: E402

# The signal cycle is 42 s green + 3 s yellow per direction (90 s full cycle), and
# step-length is 0.1 s, so a window shorter than ~900 steps can miss every red phase
# and make a live n_queue look identical to a dead one.
N_STEPS = 1000
QUEUE_IDX = 16
VEL_X_IDX = 1
VEL_Y_IDX = 2
HEADING_IDX = 17


def main() -> int:
    env = AoiV2IEnv(density=45.0, seed=42, max_steps=N_STEPS, warmup_steps=60)
    obs, info = env.reset()

    queue_vals = []
    heading_vals = []
    vel_vals = []
    dims_seen = set()

    for _ in range(N_STEPS):
        action = {vid: env.action_space_sample() if hasattr(env, "action_space_sample") else None
                  for vid in obs}
        action = {vid: a for vid, a in action.items() if a is not None}
        try:
            obs, rew, term, trunc, info = env.step(action)
        except Exception as exc:  # noqa: BLE001
            print(f"step failed: {type(exc).__name__}: {exc}")
            break
        for vec in obs.values():
            dims_seen.add(len(vec))
            queue_vals.append(round(float(vec[QUEUE_IDX]), 4))
            heading_vals.append(round(float(vec[HEADING_IDX]), 3))
            vel_vals.append((round(float(vec[VEL_X_IDX]), 3), round(float(vec[VEL_Y_IDX]), 3)))

    env.close() if hasattr(env, "close") else None

    print(f"observed state dims      : {sorted(dims_seen)} (expected [{STATE_DIM}])")
    print(f"vehicle-observations seen: {len(queue_vals)}")
    if not queue_vals:
        print("VERDICT: FAIL - no vehicle observations produced")
        return 1

    nonzero_q = [v for v in queue_vals if v > 0.0]
    print(f"n_queue  nonzero: {len(nonzero_q)}/{len(queue_vals)}"
          f"  max={max(queue_vals)}  distinct={len(set(queue_vals))}")
    print(f"n_queue  top values: {Counter(queue_vals).most_common(6)}")
    print(f"heading  range: [{min(heading_vals)}, {max(heading_vals)}]"
          f"  distinct={len(set(heading_vals))}")
    nonzero_v = [v for v in vel_vals if v != (0.0, 0.0)]
    print(f"vel(x,y) nonzero: {len(nonzero_v)}/{len(vel_vals)}  distinct={len(set(vel_vals))}")

    q_live = bool(nonzero_q) and len(set(queue_vals)) > 1
    h_live = len(set(heading_vals)) > 1
    v_live = bool(nonzero_v)
    print(f"  n_queue live={q_live}   heading live={h_live}   velocity live={v_live}"
          f"   dims ok={dims_seen == {STATE_DIM}}")
    ok = q_live and h_live and v_live and dims_seen == {STATE_DIM}
    print(f"VERDICT: {'PASS - all three design features are live' if ok else 'FAIL - at least one feature is dead'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
