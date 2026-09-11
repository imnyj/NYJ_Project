#!/usr/bin/env python
# etc/scripts/measure_realised_cbr.py
# ============================================================================
# WHAT SUBCHANNEL OCCUPANCY ACTUALLY REACHES, UNDER THE CORRECTED CHANNEL MODEL.
#
# ---------------------------------------------------------------------------
# WHAT THIS IS FOR
# ---------------------------------------------------------------------------
# `CBR_REF` divides the congestion term of the reward and observation feature
# [14]. It is 0.60, an ACHIEVABILITY bound: one subchannel forced to saturation,
# every vehicle granted every step at 23 dBm, measured at 0.591 for density 50.
# Realised occupancy under an ordinary policy does not exceed 0.04, so `r_cong`
# never rises above 0.067 and at weight 0.2 contributes about 0.2 % of the total
# penalty. The term is present in the objective and absent from the gradient.
#
# The rule for the replacement was FIXED BEFORE THIS RAN and is written in
# `results/diagnostics/cbr_ref_criterion.md`: the 99th percentile of per-step,
# per-subchannel occupancy, pooled over the seven training densities, under the
# fixed behaviour policy, after the settled warm-up. This script only measures;
# it applies no rule and picks no value, so that the number cannot be chosen by
# trying quantiles until one looks right.
#
# ---------------------------------------------------------------------------
# WHY IT HAS TO BE RUN AFTER THE SHADOWING CORRECTION
# ---------------------------------------------------------------------------
# Occupancy is airtime spent, and airtime is spent by retransmissions. The
# shadowing defect made every retry an independent channel draw, which changes
# how many retries a burst needs and therefore how much of the channel is
# occupied. A reference measured under the old model would describe a channel
# nobody is going to simulate.
#
# ---------------------------------------------------------------------------
# WHAT IS RECORDED
# ---------------------------------------------------------------------------
# Every per-step, per-subchannel occupancy sample, summarised per density and
# pooled, with several quantiles reported side by side. The extra quantiles are
# there so the chosen one can be read in context, NOT so it can be reconsidered.
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

#: Reported for context. The RULE names 99; the others are printed so the shape
#: of the tail is visible.
QUANTILES = (50.0, 90.0, 95.0, 99.0, 99.9, 100.0)

#: The behaviour policy the current offline collection used, read from its
#: metadata so the two cannot drift apart.
DEFAULT_DATASET = "/home/imnyj/Workspace/paper4/data/hoorl_offline/hoorl_offline.npz"


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--steps", type=int, default=400)
    p.add_argument("--dataset", default=DEFAULT_DATASET)
    p.add_argument("--out-dir", default=os.path.join(ROOT, "results", "diagnostics"))
    args = p.parse_args(argv)

    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    from src.hoorl_offline import FixedPeriodBehaviourPolicy, OfflineDataset
    from src.hot_swap_trainer import (CBR_REF, DEFAULT_WARMUP_STEPS, AoiV2IEnv,
                                      prepare_scenario)
    from src.rl_interface import ActionDecoder
    from src.sumo.make_sumo_set import DENSITY_GRID, road_seed, seed_road_network

    bp = OfflineDataset.load(os.path.abspath(args.dataset)).metadata["behaviour_policy"]
    # Both spellings are accepted: files collected before the 2026-09-07 rename
    # carry only the old keys, and newer ones carry both.
    policy = FixedPeriodBehaviourPolicy(
        delta_band_center=float(bp.get("delta_band_center", bp.get("delta_fixed"))),
        num_channels=int(bp["num_channels"]),
        p_min=float(bp["p_min"]), p_max=float(bp["p_max"]),
        delta_log_halfwidth=float(
            bp.get("delta_log_halfwidth", bp.get("delta_jitter"))))

    rows: List[Dict[str, Any]] = []
    pooled: List[float] = []
    per_density: Dict[float, List[float]] = {}

    for density in [float(d) for d in DENSITY_GRID]:
        seed_road_network(density, 0)
        prepare_scenario(density=density, max_steps=args.steps,
                         warmup_steps=DEFAULT_WARMUP_STEPS,
                         seed=road_seed(density, 0))
        env = AoiV2IEnv(density=density, seed=2001, max_steps=args.steps,
                        warmup_steps=DEFAULT_WARMUP_STEPS)
        obs, _info = env.reset()
        decoder = ActionDecoder()
        rng = np.random.default_rng(int(density) * 7919 + 11)
        samples: List[float] = []
        # The env is driven exactly as `collect_offline_dataset` drives it: a
        # fixed number of steps, a grant issued for every vehicle at the start
        # and thereafter only for the vehicles whose interval just closed. The
        # action is the (Delta, channel, power) TUPLE, not the decoder's unit
        # coordinate. Re-granting every vehicle every step, which a first version
        # of this script did, ends the episode on the first call and produces
        # four samples of zero.
        open_vids = set()
        actions = {}
        for vid in obs:
            grant, _ch, _lp = policy.sample(rng, decoder)
            actions[vid] = grant
            open_vids.add(vid)
        for _step in range(int(args.steps)):
            obs, _r, _term, _trunc, info = env.step(actions)
            # Every subchannel is a sample: the reward reads the occupancy of the
            # ONE channel a grant used, so the population the reference has to
            # cover is per (step, subchannel), not per step.
            samples.extend(float(c) for c in env.subchannel_cbr)
            actions = {}
            for rec in info["completed"]:
                open_vids.discard(rec["vid"])
            # A grant is issued to any in-range vehicle without one open: the ones
            # whose interval just closed, and the ones that have entered coverage
            # since the last step.
            for vid in obs:
                if vid not in open_vids:
                    grant, _ch, _lp = policy.sample(rng, decoder)
                    actions[vid] = grant
                    open_vids.add(vid)
            open_vids &= set(obs)
        env.finalize_open_intervals()
        env.close()
        per_density[density] = samples
        pooled.extend(samples)
        row = {"density": density, "n_samples": len(samples),
               "mean": round(float(np.mean(samples)), 6) if samples else 0.0}
        for q in QUANTILES:
            row[f"p{q:g}"] = round(float(np.percentile(samples, q)), 6) if samples else 0.0
        rows.append(row)
        print(f"density {density:>4.0f}  n {len(samples):>6d}  "
              f"mean {row['mean']:.5f}  p99 {row['p99']:.5f}  "
              f"max {row['p100']:.5f}", flush=True)

    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, "realised_cbr_by_density.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    summary: Dict[str, Any] = {
        "criterion_file": "results/diagnostics/cbr_ref_criterion.md",
        "criterion": ("99th percentile of per-step per-subchannel occupancy, "
                      "pooled over the seven training densities; fixed before "
                      "this measurement ran"),
        "current_CBR_REF": float(CBR_REF),
        "steps_per_density": int(args.steps),
        "warmup_steps": int(DEFAULT_WARMUP_STEPS),
        "behaviour_policy": bp,
        "n_pooled_samples": len(pooled),
        "pooled": {f"p{q:g}": round(float(np.percentile(pooled, q)), 6)
                   for q in QUANTILES},
        "pooled_mean": round(float(np.mean(pooled)), 6),
    }
    chosen = float(np.percentile(pooled, 99.0))
    summary["value_selected_by_the_rule"] = round(chosen, 6)
    summary["rounded_up_to_2dp"] = float(np.ceil(chosen * 100.0) / 100.0)
    summary["fraction_clipped_at_that_value"] = round(
        float(np.mean(np.asarray(pooled) >= summary["rounded_up_to_2dp"])), 5)
    json_path = os.path.join(args.out_dir, "realised_cbr.json")
    with open(json_path, "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True, default=float)
    print("\n" + json.dumps(summary["pooled"], indent=2, sort_keys=True))
    print(f"rule selects {summary['value_selected_by_the_rule']}, "
          f"rounded {summary['rounded_up_to_2dp']}, "
          f"clipping {summary['fraction_clipped_at_that_value']}")
    print(f"\n{csv_path}\n{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
