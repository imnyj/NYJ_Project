#!/usr/bin/env python3
# etc/scripts/measure_hoorl_pretrain_cost.py
# ============================================================================
# What HOORL's offline stage costs, measured, against what a rollout costs,
# also measured.
#
# The decision this feeds is whether `iql_expectile` and `iql_beta` can be
# searched. They change the pretraining result, so Optuna sampling them
# continuously means every trial pretrains again and no result is reusable. That
# is affordable or it is not, and the ratio to a rollout is what says which.
#
# The rollout side is NOT measured here. It is read from
# `results/hpo_parallel/*/optuna_trials_*.csv`, where 4000-step rollouts are
# already recorded with their durations, because re-measuring a number the
# project already has is how two slightly different numbers end up in circulation.
#
# The pretraining side is timed on a SYNTHETIC dataset. The offline loop's cost
# is set by the update count, the batch size and the network width; the contents
# of the batch do not enter it. Collecting the real dataset is blocked, and it
# would not change this measurement if it were not.
# ============================================================================

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import statistics
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
import torch  # noqa: E402

from src.baselines import get_baseline  # noqa: E402
from src.hoorl_offline import OfflineDataset  # noqa: E402
from src.hoorl_wiring import (  # noqa: E402
    DEFAULT_OFFLINE_ALGORITHM,
    DEFAULT_PRETRAIN_BATCH_SIZE,
    DEFAULT_PRETRAIN_UPDATES,
)
from src.rl_interface import STATE_DIM, ActionDecoder  # noqa: E402

#: HOORL is a twin-critic maximum-entropy actor-critic with an extra discrete
#: head. SAC is the closest architecture, but every SAC trial in the 4000-step
#: parallel search failed with a zero duration, so it carries no usable timing.
#: TD3 and MADDPG-MT are the next closest -- both twin-critic actor-critics that
#: completed all 15 trials -- and are what the rollout baseline is read from.
ROLLOUT_REFERENCE_MODELS = ("TD3", "MADDPG-MT")


def parse_timedelta(text: str):
    m = re.match(r"(\d+) days (\d+):(\d+):([\d.]+)", str(text))
    if not m:
        return None
    d, h, mi, s = m.groups()
    return int(d) * 86400 + int(h) * 3600 + int(mi) * 60 + float(s)


def rollout_cost() -> dict:
    """Measured 4000-step rollout durations, from the recorded search."""
    out = {}
    for model in ROLLOUT_REFERENCE_MODELS:
        for path in glob.glob(os.path.join(
                ROOT, "results", "hpo_parallel", "*", f"optuna_trials_{model}.csv")):
            rows = list(csv.DictReader(open(path)))
            if not rows:
                continue
            seed_cols = [k for k in rows[0] if "steps_completed" in k]
            steps = []
            for r in rows:
                for k in seed_cols:
                    try:
                        steps.append(int(float(r[k])))
                    except (TypeError, ValueError):
                        pass
            durations = [parse_timedelta(r.get("duration")) for r in rows]
            durations = [d for d in durations if d]
            if not durations:
                continue
            out[model] = {
                "source": os.path.relpath(path, ROOT),
                "n_trials": len(durations),
                "seeds_per_trial": len(seed_cols),
                "steps_per_rollout": int(statistics.median(steps)) if steps else None,
                "trial_mean_s": round(statistics.mean(durations), 1),
                "trial_median_s": round(statistics.median(durations), 1),
                "per_seed_rollout_s": round(
                    statistics.mean(durations) / max(1, len(seed_cols)), 1),
            }
    return out


def synthetic_dataset(n, seed=0, gamma=0.99):
    rng = np.random.default_rng(seed)
    dec = ActionDecoder(num_channels=4)
    deltas = np.exp(rng.uniform(np.log(dec.delta_min), np.log(dec.delta_max), n))
    chans = rng.integers(0, 4, n)
    powers = rng.uniform(dec.p_min, dec.p_max, n)
    actions = np.stack([dec.encode_action(float(d), int(c), float(p))
                        for d, c, p in zip(deltas, chans, powers)]).astype(np.float32)
    arrays = {
        "state": rng.uniform(-1, 1, (n, STATE_DIM)).astype(np.float32),
        "action": actions,
        "reward": rng.normal(-1.0, 0.5, n).astype(np.float32),
        "next_state": rng.uniform(-1, 1, (n, STATE_DIM)).astype(np.float32),
        "done": (rng.random(n) < 0.02).astype(np.float32),
        "delta_t": deltas.astype(np.float32),
        "action_idx": chans.astype(np.int64),
        "behaviour_log_prob": np.full(n, -np.log(4.0), dtype=np.float32),
    }
    return OfflineDataset(arrays, {"state_dim": STATE_DIM, "synthetic": True}, gamma=gamma)


def time_pretrain(device, n_transitions, num_updates, batch_size, hidden_dim) -> dict:
    HOORL = get_baseline("HOORL")
    torch.manual_seed(0)
    model = HOORL(state_dim=STATE_DIM, num_channels=4, hidden_dim=hidden_dim,
                  offline_algorithm=DEFAULT_OFFLINE_ALGORITHM).to(device)
    ds = synthetic_dataset(n_transitions)
    # A few untimed updates first: the first CUDA kernel launch and the first
    # allocation of every buffer are one-off costs that would otherwise be
    # charged to a short run and not to a long one.
    model.set_phase("offline")
    for _ in range(5):
        model.offline_update(ds.sample(batch_size))
    if device.type == "cuda":
        torch.cuda.synchronize()

    t0 = time.time()
    model.pretrain(ds, num_updates=num_updates, batch_size=batch_size)
    if device.type == "cuda":
        torch.cuda.synchronize()
    elapsed = time.time() - t0
    return {
        "device": str(device),
        "hidden_dim": hidden_dim,
        "n_transitions": n_transitions,
        "num_updates": num_updates,
        "batch_size": batch_size,
        "pretrain_s": round(elapsed, 2),
        "ms_per_update": round(1000.0 * elapsed / max(1, num_updates), 3),
        "offline_updates": float(model.offline_updates.item()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--transitions", type=int, default=200000,
                    help="dataset size; the proposed collection target")
    ap.add_argument("--updates", type=int, nargs="+",
                    default=[DEFAULT_PRETRAIN_UPDATES])
    ap.add_argument("--batch-size", type=int, default=DEFAULT_PRETRAIN_BATCH_SIZE)
    ap.add_argument("--hidden-dims", type=int, nargs="+", default=[64, 128, 256])
    ap.add_argument("--n-trials", type=int, default=15)
    ap.add_argument("--n-models", type=int, default=9)
    ap.add_argument("--seeds-per-trial", type=int, default=3)
    ap.add_argument("--out-dir", type=str,
                    default=os.path.join(ROOT, "results", "hoorl_offline"))
    args = ap.parse_args()

    devices = [torch.device("cpu")]
    if torch.cuda.is_available():
        devices.append(torch.device("cuda:0"))

    rollouts = rollout_cost()
    per_seed = [v["per_seed_rollout_s"] for v in rollouts.values()]
    rollout_s = statistics.mean(per_seed) if per_seed else float("nan")
    trial_s = statistics.mean([v["trial_mean_s"] for v in rollouts.values()]) \
        if rollouts else float("nan")

    print("=== measured 4000-step rollout cost (from the recorded search) ===")
    for m, v in rollouts.items():
        print(f"  {m:12s} trial {v['trial_mean_s']:8.1f}s over {v['seeds_per_trial']} seeds "
              f"-> {v['per_seed_rollout_s']:7.1f}s per rollout of "
              f"{v['steps_per_rollout']} steps  [{v['source']}]")
    print(f"  reference: {rollout_s:.1f}s per rollout, {trial_s:.1f}s per 3-seed trial\n")

    rows = []
    for device in devices:
        for hidden in args.hidden_dims:
            for updates in args.updates:
                r = time_pretrain(device, args.transitions, updates,
                                  args.batch_size, hidden)
                # HOORL pretrains once per MODEL, and hpo builds a fresh model per
                # seed, so a 3-seed trial pays for it three times unless the call
                # site is arranged otherwise. Both readings are given.
                r["pretrain_per_trial_s"] = round(r["pretrain_s"] * args.seeds_per_trial, 1)
                r["rollout_reference_s"] = round(rollout_s, 1)
                r["pct_of_one_rollout"] = round(100.0 * r["pretrain_s"] / rollout_s, 2)
                r["pct_of_one_trial"] = round(
                    100.0 * r["pretrain_per_trial_s"] / trial_s, 2)
                added = r["pretrain_per_trial_s"] * args.n_trials
                base_all = trial_s * args.n_trials * args.n_models
                r["added_s_for_15_trials"] = round(added, 1)
                r["added_min_for_15_trials"] = round(added / 60.0, 1)
                r["nine_model_search_multiplier"] = round(1.0 + added / base_all, 4)
                rows.append(r)
                print(f"  {str(device):9s} hidden={hidden:3d} updates={updates:5d} "
                      f"-> {r['pretrain_s']:7.2f}s ({r['ms_per_update']:.2f} ms/update), "
                      f"{r['pct_of_one_rollout']:6.2f}% of one rollout, "
                      f"9-model search x{r['nine_model_search_multiplier']:.4f}")

    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, "pretrain_cost.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    json_path = os.path.join(args.out_dir, "pretrain_cost.json")
    with open(json_path, "w") as fh:
        json.dump({
            "rollout_reference": rollouts,
            "rollout_reference_note":
                "SAC is architecturally closest to HOORL but every SAC trial in the "
                "4000-step parallel search failed with a zero duration, so TD3 and "
                "MADDPG-MT (twin-critic actor-critics, 15/15 trials completed) are "
                "used instead.",
            "pretrain_dataset": "SYNTHETIC; the offline loop's cost does not depend "
                                "on batch contents",
            "settings": vars(args),
            "rows": rows,
        }, fh, indent=2, default=str)
    print(f"\nwrote {csv_path} and {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
