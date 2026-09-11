#!/usr/bin/env python
# etc/scripts/measure_reward_term_balance.py
# ============================================================================
# HOW THE FOUR REWARD TERMS DIVIDE THE PENALTY, AFTER CBR_REF WAS RECALCULATED.
#
# RECORD ONLY. The weights 0.5 / 0.2 / 0.2 / 0.1 are FIXED for this run by
# decision: all nine baselines have to be scored against one objective or the
# rows of the results table are not comparable with each other, and the
# environment asserts the reward it forms matches the weights it was given. So
# this measures the balance and changes nothing. If the balance turns out far
# from what the weights suggest, that is a finding for after the comparison, not
# a reason to retune inside it.
#
# WHY IT IS WORTH MEASURING AT ALL. `CBR_REF` went from 0.60 to 0.02 on
# 2026-09-07, so the congestion term is about thirty times larger than it was.
# The weight did not change; the quantity it multiplies did. Before the change
# the term was about 0.2 % of the mean penalty, which is a term that exists in
# the objective and not in the gradient.
#
# The terms are read from `AoiV2IEnv`'s own decomposition, the same tuple the
# environment asserts sums to the scalar reward, so nothing here re-derives the
# reward from its parts.
# ============================================================================
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

TERM_NAMES = ("w1_error", "w2_power", "w3_congestion", "w4_redundant")
DEFAULT_DATASET = "/home/imnyj/Workspace/paper4/data/hoorl_offline/hoorl_offline.npz"


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--steps", type=int, default=400)
    p.add_argument("--densities", type=float, nargs="+", default=[5.0, 20.0, 35.0])
    p.add_argument("--dataset", default=DEFAULT_DATASET)
    p.add_argument("--out-dir", default=os.path.join(ROOT, "results", "diagnostics"))
    args = p.parse_args(argv)

    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    import src.hot_swap_trainer as hst
    from src.hoorl_offline import FixedPeriodBehaviourPolicy, OfflineDataset
    from src.rl_interface import ActionDecoder
    from src.sumo.make_sumo_set import road_seed, seed_road_network

    bp = OfflineDataset.load(os.path.abspath(args.dataset)).metadata["behaviour_policy"]
    policy = FixedPeriodBehaviourPolicy(
        delta_band_center=float(bp.get("delta_band_center", bp.get("delta_fixed"))),
        num_channels=int(bp["num_channels"]),
        p_min=float(bp["p_min"]), p_max=float(bp["p_max"]),
        delta_log_halfwidth=float(
            bp.get("delta_log_halfwidth", bp.get("delta_jitter"))))

    rows: List[Dict[str, Any]] = []
    pooled: List[List[float]] = []
    for density in args.densities:
        seed_road_network(density, 0)
        hst.prepare_scenario(density=density, max_steps=args.steps,
                             warmup_steps=hst.DEFAULT_WARMUP_STEPS,
                             seed=road_seed(density, 0))
        env = hst.AoiV2IEnv(density=density, seed=2001, max_steps=args.steps,
                            warmup_steps=hst.DEFAULT_WARMUP_STEPS)
        obs, _info = env.reset()
        decoder = ActionDecoder()
        rng = np.random.default_rng(int(density) * 7919 + 11)
        terms: List[List[float]] = []
        open_vids, actions = set(), {}
        for vid in obs:
            grant, _c, _l = policy.sample(rng, decoder)
            actions[vid] = grant
            open_vids.add(vid)
        for _step in range(args.steps):
            obs, _r, _t, _tr, info = env.step(actions)
            for rec in info["completed"]:
                rt = rec.get("reward_terms")
                if rt is not None:
                    terms.append([float(x) for x in rt])
                open_vids.discard(rec["vid"])
            actions = {}
            for vid in obs:
                if vid not in open_vids:
                    grant, _c, _l = policy.sample(rng, decoder)
                    actions[vid] = grant
                    open_vids.add(vid)
            open_vids &= set(obs)
        env.finalize_open_intervals()
        env.close()

        a = np.abs(np.asarray(terms, dtype=np.float64))
        total = a.sum(axis=1)
        share = a.sum(axis=0) / max(1e-12, a.sum())
        row = {"density": density, "n_intervals": len(terms),
               "mean_penalty": round(float(total.mean()), 6)}
        for i, nm in enumerate(TERM_NAMES):
            row[f"{nm}_mean_abs"] = round(float(a[:, i].mean()), 6)
            row[f"{nm}_share"] = round(float(share[i]), 5)
        rows.append(row)
        pooled.extend(terms)
        print(f"density {density:>4.0f}  n {len(terms):>5d}  shares " +
              "  ".join(f"{nm.split('_')[0]} {row[f'{nm}_share']:.4f}"
                        for nm in TERM_NAMES), flush=True)

    A = np.abs(np.asarray(pooled, dtype=np.float64))
    pooled_share = A.sum(axis=0) / max(1e-12, A.sum())
    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, "reward_term_balance.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summary = {
        "CBR_REF": float(hst.CBR_REF),
        "weights": {k: float(v) for k, v in hst.DEFAULT_REWARD_WEIGHTS.items()},
        "weights_are_fixed": ("0.5/0.2/0.2/0.1 for this run by decision; all nine "
                              "baselines must be scored against one objective"),
        "n_intervals": int(A.shape[0]),
        "pooled_share_of_total_penalty": {
            nm: round(float(pooled_share[i]), 5) for i, nm in enumerate(TERM_NAMES)},
        "pooled_mean_abs": {
            nm: round(float(A[:, i].mean()), 6) for i, nm in enumerate(TERM_NAMES)},
        "reading": ("share is each term's contribution to the summed magnitude of "
                    "the four, so it says how much of the gradient each one can "
                    "account for. A weight is what a term is multiplied BY; a "
                    "share is what it amounts to."),
    }
    json_path = os.path.join(args.out_dir, "reward_term_balance.json")
    with open(json_path, "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True, default=float)
    print("\n" + json.dumps(summary["pooled_share_of_total_penalty"],
                            indent=2, sort_keys=True))
    print(f"\n{csv_path}\n{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
