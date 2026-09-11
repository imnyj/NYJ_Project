#!/usr/bin/env python
# etc/scripts/measure_observation_gaps.py
# ============================================================================
# FOUR THINGS THE STORED OBSERVATION CANNOT ANSWER ABOUT ITSELF.
#
# ---------------------------------------------------------------------------
# WHY THIS READS THE ENVIRONMENT AND NOT THE DATASET
# ---------------------------------------------------------------------------
# Each of the four questions below is about a value that the observation
# DESTROYS on its way into the dataset:
#
#   1. per-subchannel occupancy -- feature [14] stores the MEAN over the four
#      subchannels, so the spread between them is gone;
#   2. the raw SUMO signal character -- features [8..10] are a three-way one-hot,
#      so every state outside {r, y, g} becomes three zeros and which one it was
#      is gone;
#   3. the raw distance to the stop line -- feature [12] is clipped at
#      `rsu_range`, so 25.4 % of rows read exactly 1.0 and the distance is gone;
#   4. whether a vehicle had a traffic light at all -- `extract_tls_features`
#      reports `inf` for "no upcoming signal" and the clip maps that to the same
#      1.0 as a genuinely distant one.
#
# So the questions are answered by instrumenting the live environment, before
# `StateVectorizer` runs. The alternative -- adding columns and recollecting --
# costs a collection run per question, and the answers are needed in order to
# decide what those columns should be.
#
# ---------------------------------------------------------------------------
# COVERAGE OF THIS MEASUREMENT
# ---------------------------------------------------------------------------
# Stated because it is the question that caught two earlier measurements out.
# The main training run is 100 episodes x 2000 steps over 7 densities, i.e.
# 200,000 environment steps across 14 road cycles. The default here is 7
# densities x 1 seed x 600 steps on road cycle 0, i.e. 4,200 steps on 1 of 14
# cycles -- 2.1 % of the training run's steps. That is adequate for questions 1
# to 4, all of which are about the DISTRIBUTION of a per-step quantity with tens
# of thousands of samples, and it is NOT adequate for anything about rare events
# or about road-to-road variation. `--cycles` widens it when that matters.
#
# No policy is involved in any of the four. Vehicle positions, signal states and
# channel occupancy under a fixed grant are properties of the scenario.
# ============================================================================
from __future__ import annotations

import argparse
import collections
import csv
import gc
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def probe_cell(density: float, seed: int, cycle: int, steps: int,
               warmup_steps: int, sumo_dir: Optional[str],
               num_channels: int = 4) -> Dict[str, Any]:
    """One episode, recording the four raw quantities before normalisation."""
    import random as _random

    from src.hot_swap_trainer import AoiV2IEnv, prepare_scenario
    from src.sumo.make_sumo_set import seed_road_network

    used_seed = seed_road_network(float(density), int(cycle))
    prepare_scenario(density=float(density), max_steps=int(steps),
                     warmup_steps=int(warmup_steps), seed=int(used_seed),
                     sumo_dir=sumo_dir)

    cbr_rows: List[np.ndarray] = []
    tls_chars: collections.Counter = collections.Counter()
    stopline_raw: List[float] = []
    stopline_inf = 0
    stopline_total = 0
    onehot_all_zero = 0
    onehot_total = 0

    env: Optional[Any] = None
    try:
        env = AoiV2IEnv(density=float(density), seed=int(seed), max_steps=int(steps),
                        warmup_steps=int(warmup_steps), num_channels=int(num_channels),
                        sumo_dir=sumo_dir)
        obs, _info = env.reset()
        _random.seed(int(seed))
        rng = np.random.default_rng(int(seed))

        def draw():
            return (float(np.exp(rng.uniform(math.log(0.5), math.log(10.0)))),
                    int(rng.integers(0, num_channels)),
                    float(rng.uniform(env.decoder.p_min, env.decoder.p_max)))

        action = {vid: draw() for vid in obs}
        for _ in range(int(steps)):
            next_obs, _r, _t, _tr, info = env.step(action)
            # 1. The four subchannel occupancies at this instant, raw.
            cbr_rows.append(np.asarray(env.subchannel_cbr, dtype=np.float64).copy())
            # 2/3/4. The telemetry dict the vectoriser is about to consume, per
            # vehicle that is being observed. `_get_vehicle_state_dict` is the
            # environment's own builder, so these are the values that reach
            # `StateVectorizer` and not a reconstruction of them.
            for vid in next_obs:
                st = env._get_vehicle_state_dict(vid)
                if not st:
                    continue
                tls = st.get("tls_features") or {}
                ch = str(tls.get("state", "none"))
                tls_chars[ch] += 1
                onehot_total += 1
                if ch.lower() not in ("r", "red", "y", "yellow", "g", "green"):
                    onehot_all_zero += 1
                d = tls.get("dist_to_stopline", None)
                stopline_total += 1
                if d is None or not np.isfinite(float(d)):
                    stopline_inf += 1
                else:
                    stopline_raw.append(float(d))
            action = {vid: draw() for vid in info["needs_decision"] if vid in next_obs}
        env.finalize_open_intervals()
        rsu_range = float(env.rsu_range)
    finally:
        if env is not None:
            try:
                env.close()
            except Exception:  # noqa: BLE001
                pass
            del env
            gc.collect()

    cbr = np.vstack(cbr_rows) if cbr_rows else np.zeros((0, num_channels))
    spread = cbr.max(axis=1) - cbr.min(axis=1) if cbr.size else np.zeros(0)
    mean_over_ch = cbr.mean(axis=1) if cbr.size else np.zeros(0)
    raw = np.asarray(stopline_raw, dtype=np.float64)
    at_or_past = float((raw >= rsu_range).mean()) if raw.size else float("nan")

    return {
        "density": float(density), "seed": int(seed), "cycle": int(cycle),
        "road_seed": int(used_seed), "steps": int(steps),
        # 1. channel spread
        "cbr_mean_over_channels": float(mean_over_ch.mean()) if cbr.size else float("nan"),
        "cbr_spread_mean": float(spread.mean()) if spread.size else float("nan"),
        "cbr_spread_p99": float(np.percentile(spread, 99)) if spread.size else float("nan"),
        "cbr_spread_max": float(spread.max()) if spread.size else float("nan"),
        "cbr_spread_over_mean": (float(spread.mean() / mean_over_ch.mean())
                                 if cbr.size and mean_over_ch.mean() > 0 else float("nan")),
        "cbr_var_between_channels_mean": float(cbr.var(axis=1).mean()) if cbr.size else float("nan"),
        "cbr_max_channel_mean": float(cbr.max(axis=1).mean()) if cbr.size else float("nan"),
        # 2. signal characters
        "n_observations": int(onehot_total),
        "frac_onehot_all_zero": (onehot_all_zero / onehot_total) if onehot_total else float("nan"),
        "tls_char_counts": dict(tls_chars),
        # 3/4. stop-line distance
        "rsu_range": rsu_range,
        "n_stopline": int(stopline_total),
        "frac_stopline_infinite": (stopline_inf / stopline_total) if stopline_total else float("nan"),
        "frac_stopline_at_or_past_rsu_range": at_or_past,
        "stopline_p50": float(np.percentile(raw, 50)) if raw.size else float("nan"),
        "stopline_p90": float(np.percentile(raw, 90)) if raw.size else float("nan"),
        "stopline_p99": float(np.percentile(raw, 99)) if raw.size else float("nan"),
        "stopline_max": float(raw.max()) if raw.size else float("nan"),
        "_stopline_raw": raw,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--densities", type=float, nargs="+", default=None)
    p.add_argument("--seeds", type=int, nargs="+", default=[2001])
    p.add_argument("--cycles", type=int, nargs="+", default=[0])
    p.add_argument("--steps", type=int, default=600)
    p.add_argument("--warmup-steps", type=int, default=1200)
    p.add_argument("--sumo-dir", type=str, default=None)
    p.add_argument("--out-dir", type=str,
                   default=os.path.join(ROOT, "results", "hoorl_offline"))
    args = p.parse_args(argv)

    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    from src.sumo.make_sumo_set import DENSITY_GRID

    densities = args.densities or [float(d) for d in DENSITY_GRID]
    rows = [probe_cell(d, s, c, args.steps, args.warmup_steps, args.sumo_dir)
            for c in args.cycles for d in densities for s in args.seeds]

    all_raw = np.concatenate([r.pop("_stopline_raw") for r in rows]) \
        if rows else np.zeros(0)
    chars: collections.Counter = collections.Counter()
    for r in rows:
        chars.update(r["tls_char_counts"])

    for r in rows:
        print(f"density {r['density']:5.1f} cycle {r['cycle']}: "
              f"cbr mean {r['cbr_mean_over_channels']:.5f} spread mean "
              f"{r['cbr_spread_mean']:.5f} p99 {r['cbr_spread_p99']:.5f} "
              f"(spread/mean {r['cbr_spread_over_mean']:.3f}); "
              f"one-hot all-zero {r['frac_onehot_all_zero']:.5f}; "
              f"stopline inf {r['frac_stopline_infinite']:.5f} "
              f">=range {r['frac_stopline_at_or_past_rsu_range']:.5f}", flush=True)

    os.makedirs(args.out_dir, exist_ok=True)
    fields = [k for k in rows[0] if k != "tls_char_counts"]
    csv_path = os.path.join(args.out_dir, "observation_gaps_by_cell.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})

    total_chars = sum(chars.values())
    char_rows = [{"tls_state_char": c, "count": n,
                  "fraction": n / total_chars if total_chars else float("nan"),
                  "maps_to_onehot": ("red" if c.lower() in ("r", "red") else
                                     "yellow" if c.lower() in ("y", "yellow") else
                                     "green" if c.lower() in ("g", "green") else
                                     "ALL ZERO")}
                 for c, n in chars.most_common()]
    char_path = os.path.join(args.out_dir, "tls_state_char_distribution.csv")
    with open(char_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(char_rows[0]))
        w.writeheader()
        w.writerows(char_rows)

    rsu_range = rows[0]["rsu_range"]
    edges = [0, 25, 50, 75, 100, 150, 200, 250, 300, 400, 600, 900, 1e9]
    hist, _ = np.histogram(all_raw, bins=edges)
    hist_rows = [{"lo_m": edges[i], "hi_m": edges[i + 1], "count": int(hist[i]),
                  "fraction": float(hist[i] / all_raw.size) if all_raw.size else float("nan"),
                  "beyond_rsu_range": int(edges[i] >= rsu_range)}
                 for i in range(len(hist))]
    hist_path = os.path.join(args.out_dir, "dist_to_stopline_raw_histogram.csv")
    with open(hist_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(hist_rows[0]))
        w.writeheader()
        w.writerows(hist_rows)

    summary = {
        "coverage": {
            "cells": len(rows), "steps_per_cell": int(args.steps),
            "cycles": [int(c) for c in args.cycles],
            "env_steps_measured": len(rows) * int(args.steps),
            "training_run_env_steps": 100 * 2000,
            "fraction_of_training_run": len(rows) * int(args.steps) / (100 * 2000),
            "road_cycles_of_14_covered": len(set(args.cycles)),
        },
        "channel_spread": {
            "mean_spread": float(np.nanmean([r["cbr_spread_mean"] for r in rows])),
            "mean_spread_over_mean_occupancy":
                float(np.nanmean([r["cbr_spread_over_mean"] for r in rows])),
            "max_spread_seen": float(np.nanmax([r["cbr_spread_max"] for r in rows])),
        },
        "tls_chars": {
            "total": total_chars,
            "all_zero_fraction": sum(r["count"] for r in char_rows
                                     if r["maps_to_onehot"] == "ALL ZERO") / total_chars
            if total_chars else float("nan"),
            "by_char": {r["tls_state_char"]: r["fraction"] for r in char_rows},
        },
        "stop_line": {
            "rsu_range_m": rsu_range,
            "n_finite": int(all_raw.size),
            "fraction_infinite_of_all":
                float(np.nanmean([r["frac_stopline_infinite"] for r in rows])),
            "fraction_at_or_past_rsu_range_of_finite":
                float((all_raw >= rsu_range).mean()) if all_raw.size else float("nan"),
            "p50": float(np.percentile(all_raw, 50)) if all_raw.size else float("nan"),
            "p90": float(np.percentile(all_raw, 90)) if all_raw.size else float("nan"),
            "p99": float(np.percentile(all_raw, 99)) if all_raw.size else float("nan"),
            "max": float(all_raw.max()) if all_raw.size else float("nan"),
        },
    }
    json_path = os.path.join(args.out_dir, "observation_gaps.json")
    with open(json_path, "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True, default=float)
    print("\n" + json.dumps(summary, indent=2, sort_keys=True, default=float))
    print(f"\n{csv_path}\n{char_path}\n{hist_path}\n{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
