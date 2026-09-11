#!/usr/bin/env python3
# etc/scripts/demo_offline_state_distances.py
# ============================================================================
# A WORKED EXAMPLE OF THE CONTROL DESIGN, NOT A DATASET AND NOT A RESULT.
#
# It rolls a few short episodes, keeps only the state matrices, and runs the
# statistics of `src/hoorl_offline_stats.py` over them so the proposed controls
# can be judged on real numbers instead of on a description of them. Nothing it
# writes is fit to be cited: the episodes are short, the observation definition
# is still being changed in six other files, and no trained policy exists yet.
# The state matrices go to a scratch directory; only the derived CSVs land in
# `results/`, tagged `demo`.
#
# Five samples, chosen so that every quantity in the report has something to be
# read against:
#
#   fixed_d20_s2001   the behaviour policy at the middle density
#   fixed_d20_s2002   the same thing at another seed  -> SEED CONTROL, the
#                     distance two runs of one policy score against each other
#   fixed_d05_s2001   the same policy at the sparsest density
#   fixed_d35_s2001   the same policy at the densest    -> REFERENCE SHIFT, the
#                     largest covariate shift the benchmark itself contains
#   varied_d20_s2001  the same policy but with Delta drawn log-uniformly over
#                     the WHOLE decoder range instead of held fixed
#
# The last one is the point of the exercise. HOORL pretrains on data collected at
# one fixed Delta and then goes online with a policy that chooses Delta freely.
# Nobody can say in advance how far that moves the state distribution, because
# Delta changes WHEN the RSU observes, and therefore which states it observes at
# all. `varied_d20_s2001` against `fixed_d20_s2001` is that shift, measured, with
# the seed control below it and the density control beside it.
# ============================================================================

from __future__ import annotations

import argparse
import gc
import json
import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402

from src.hoorl_offline import (  # noqa: E402
    FixedPeriodBehaviourPolicy,
    git_provenance,
    limit_cpu_threads,
    observation_constants,
)
from src.hoorl_offline_stats import (  # noqa: E402
    comparison_report,
    coverage_warnings,
    describe_states,
    write_comparison_report,
    write_state_distribution_csv,
)
from src.rl_interface import STATE_DIM, ActionDecoder  # noqa: E402


def rollout_states(density, seed, steps, warmup_steps, num_channels,
                   delta_fixed, delta_jitter, sumo_dir):
    """States at the decision epochs of one episode. No reward, no transition."""
    from src.hot_swap_trainer import AoiV2IEnv, DEFAULT_ERROR_MODE, prepare_scenario

    prepare_scenario(density=density, max_steps=steps, warmup_steps=warmup_steps,
                     seed=seed, sumo_dir=sumo_dir)
    decoder = ActionDecoder(num_channels=num_channels)
    policy = FixedPeriodBehaviourPolicy(
        delta_band_center=float(delta_fixed), num_channels=num_channels,
        p_min=decoder.p_min, p_max=decoder.p_max, delta_log_halfwidth=float(delta_jitter),
    )
    rng = np.random.default_rng(seed)
    states = []
    env = None
    t0 = time.time()
    try:
        env = AoiV2IEnv(density=density, seed=seed, max_steps=steps,
                        warmup_steps=warmup_steps, num_channels=num_channels,
                        error_mode=DEFAULT_ERROR_MODE, sumo_dir=sumo_dir)
        obs, _ = env.reset()
        random.seed(seed)
        action_dict = {}
        for vid, vec in obs.items():
            states.append(np.asarray(vec, dtype=np.float32))
            grant, _ch, _lp = policy.sample(rng, decoder)
            action_dict[vid] = grant
        for _ in range(steps):
            next_obs, _r, _t, _tr, info = env.step(action_dict)
            action_dict = {}
            for vid in info["needs_decision"]:
                vec = next_obs.get(vid)
                if vec is None:
                    continue
                states.append(np.asarray(vec, dtype=np.float32))
                grant, _ch, _lp = policy.sample(rng, decoder)
                action_dict[vid] = grant
    finally:
        if env is not None:
            try:
                env.close()
            except Exception:
                pass
            del env
            gc.collect()
    arr = np.asarray(states, dtype=np.float32).reshape(-1, STATE_DIM)
    return arr, round(time.time() - t0, 2), (decoder.delta_min, decoder.delta_max)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--warmup-steps", type=int, default=600)
    ap.add_argument("--num-channels", type=int, default=4)
    ap.add_argument("--delta-fixed", type=float, default=1.0,
                    help="probe value only; the real one is a design decision")
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--sumo-dir", type=str, required=True)
    ap.add_argument("--state-dir", type=str, required=True)
    ap.add_argument("--out-dir", type=str, default="results/hoorl_offline")
    args = ap.parse_args()

    limit_cpu_threads(args.threads)
    os.makedirs(args.state_dir, exist_ok=True)
    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    # `delta_log_halfwidth=6.0` is wide enough that the band clips to the decoder's own
    # [delta_min, delta_max], i.e. Delta covers the whole action axis. That is the
    # extreme of the fixed-to-variable transition, not an estimate of where a
    # trained policy ends up, and the report says so.
    plan = [
        ("fixed_d20_s2001", 20.0, 2001, args.delta_fixed, 0.0),
        ("fixed_d20_s2002", 20.0, 2002, args.delta_fixed, 0.0),
        ("fixed_d05_s2001", 5.0, 2001, args.delta_fixed, 0.0),
        ("fixed_d35_s2001", 35.0, 2001, args.delta_fixed, 0.0),
        ("varied_d20_s2001", 20.0, 2001, args.delta_fixed, 6.0),
    ]

    samples = {}
    provenance = {"episodes": [], "observation_constants": observation_constants(),
                  "git": git_provenance(), "steps": args.steps,
                  "warmup_steps": args.warmup_steps,
                  "delta_fixed_probe_value": args.delta_fixed,
                  "caveat": "SHORT EPISODES, PROBE DELTA, NO TRAINED POLICY. "
                            "Design demonstration only; recompute after the "
                            "observation definition settles."}
    for name, density, seed, delta, jitter in plan:
        arr, secs, drange = rollout_states(
            density, seed, args.steps, args.warmup_steps, args.num_channels,
            delta, jitter, args.sumo_dir)
        samples[name] = arr
        np.savez_compressed(os.path.join(args.state_dir, f"{name}.npz"), state=arr)
        provenance["episodes"].append({
            "name": name, "density": density, "seed": seed,
            "delta_fixed": delta, "delta_jitter": jitter,
            "decoder_delta_range": [float(drange[0]), float(drange[1])],
            "n_states": int(arr.shape[0]), "wall_clock_s": secs,
        })
        print(f"{name}: {arr.shape[0]} states in {secs}s", flush=True)

    for name, arr in samples.items():
        p = write_state_distribution_csv(
            arr, os.path.join(out_dir, f"state_distribution_demo_{name}.csv"),
            extra_columns={"sample": name},
        )
        print("wrote", p)
        for line in coverage_warnings(describe_states(arr)):
            print(f"  coverage, {name}: {line}")

    pairs = [
        ("fixed_d20_s2001", "varied_d20_s2001"),   # the shift of interest
        ("fixed_d20_s2001", "fixed_d20_s2002"),    # seed control
        ("fixed_d05_s2001", "fixed_d35_s2001"),    # reference shift
        ("fixed_d20_s2001", "fixed_d05_s2001"),
        ("fixed_d20_s2001", "fixed_d35_s2001"),
    ]
    report = comparison_report(
        samples, pairs,
        reference_pair=("fixed_d05_s2001", "fixed_d35_s2001"),
        floor_on="fixed_d20_s2001", max_samples=2000, seed=0,
    )
    report["provenance"] = provenance
    csv_path, json_path = write_comparison_report(
        report, os.path.join(out_dir, "state_distance_demo.csv"))
    print("wrote", csv_path, "and", json_path)
    print(json.dumps(
        [{k: r[k] for k in ("sample_a", "sample_b", "mean_normalised_w1",
                            "mean_w1_delta_critical", "energy_distance",
                            "argmax_feature", "w1_over_sampling_floor",
                            "w1_over_reference_shift")}
         for r in report["rows"]], indent=2))
    print("sampling floor:", json.dumps(report["sampling_floor"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
