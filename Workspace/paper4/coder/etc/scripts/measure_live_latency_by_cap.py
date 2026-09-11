#!/usr/bin/env python
# etc/scripts/measure_live_latency_by_cap.py
# ============================================================================
# DOES THE NEIGHBOUR CAP COST ANYTHING IN A LIVE RUN?
#
# ---------------------------------------------------------------------------
# WHY THE EARLIER ANSWER DOES NOT SETTLE THIS
# ---------------------------------------------------------------------------
# `measure_inference_and_rollout.py` swept the cap and found the 99th-percentile
# latency flat from 16 to 192. That measurement calls `select_action` in a loop
# on a random state with nothing else running, and its p99 for I-HAMAPPO was
# about 1.5 ms. The same model measured inside a real 600-step run reports 4.74
# to 6.45 ms. A THREEFOLD GAP between the two conditions is enough that "flat in
# the quiet condition" cannot be carried over: in a live run SUMO, the channel
# computation and the background trainer are all competing, and a neighbour
# encoder that never waited for a kernel in the quiet case may wait in this one.
#
# ---------------------------------------------------------------------------
# WHAT HAS TO BE PATCHED, AND WHY BOTH
# ---------------------------------------------------------------------------
# The cap reaches a run by two independent routes and changing one alone
# measures nothing:
#
#   * `hot_swap_trainer.MAX_NEIGHBOURS` sets how wide a neighbourhood the
#     `NeighbourhoodView` builds. A module-level name, looked up per call, so
#     assigning to it works.
#   * the model's own `max_agents`, which every baseline takes as a DEFAULT
#     ARGUMENT bound when its module was imported. Assigning to
#     `rl_interface.MAX_NEIGHBOURS` afterwards does nothing at all to it. It has
#     to be passed in, which `run_hot_swap_training(hparams=...)` allows.
#
# This is the same shape as the `QUEUE_MAX_DEFAULT` trap found on 2026-09-07,
# where patching a module attribute that had already been bound as a default led
# to the conclusion that a check was blind when it was the probe that was inert.
#
# ---------------------------------------------------------------------------
# WHY REPEATS, AND WHY BOTH PLACEMENTS
# ---------------------------------------------------------------------------
# The two placements of the existing measurement differ by 1.7 ms at p99 and
# nothing yet says whether that is the placement or run-to-run variation. With
# one run per cell a cap difference smaller than that spread cannot be told from
# noise, so each cell is repeated and the spread is reported beside the mean. A
# tail statistic over 600 steps is itself noisy, which is the reason to report
# the p99 of each run rather than pooling them into one number that hides how
# much they moved.
# ============================================================================
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
from typing import Any, Dict, List, Optional, Sequence

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

TMP = "/home/imnyj/Workspace/paper4/coder/etc/temp"


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default="I-HAMAPPO")
    p.add_argument("--caps", type=int, nargs="+", default=[16, 192])
    p.add_argument("--steps", type=int, default=600)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--out-dir", default=os.path.join(ROOT, "results", "diagnostics"))
    args = p.parse_args(argv)

    import torch

    import src.hot_swap_trainer as hst
    from src.baselines import get_baseline
    from src.rl_interface import STATE_DIM

    if torch.cuda.device_count() < 2:
        print("two visible GPUs are needed to compare the placements")
        return 2

    original_cap = hst.MAX_NEIGHBOURS
    os.makedirs(TMP, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    try:
        for cap in args.caps:
            for tag, act, rest in (("isolated", "cuda:0", "cuda:1"),
                                   ("shared", "cuda:0", "cuda:0")):
                for rep in range(args.repeats):
                    hst.MAX_NEIGHBOURS = int(cap)
                    summary = hst.run_hot_swap_training(
                        model_name=get_baseline(args.model),
                        total_steps=args.steps,
                        episodes=1,
                        seed=42 + rep,
                        act_device=act,
                        rest_device=rest,
                        hparams={"max_agents": int(cap)},
                        validate_every_episodes=0,
                        checkpoint_dir=os.path.join(TMP, "capcmp_ckpt"),
                        tensorboard_dir=os.path.join(TMP, "capcmp_tb"),
                        log_csv_path=os.path.join(TMP, f"capcmp_{cap}_{tag}_{rep}.csv"),
                    )
                    lat = summary.get("inference_latency", {})
                    row = {
                        "model": args.model, "cap": int(cap), "placement": tag,
                        "repeat": rep, "seed": 42 + rep,
                        "state_dim": int(STATE_DIM), "steps": int(args.steps),
                        "training_steps": summary.get("training_steps"),
                        "throughput_steps_per_sec": summary.get("throughput_steps_per_sec"),
                        "mean_ms": lat.get("mean_latency_ms"),
                        "p50_ms": lat.get("p50_latency_ms"),
                        "p95_ms": lat.get("p95_latency_ms"),
                        "p99_ms": lat.get("p99_latency_ms"),
                    }
                    rows.append(row)
                    print(f"cap {cap:>3d} {tag:8s} rep {rep}  mean {row['mean_ms']}  "
                          f"p95 {row['p95_ms']}  p99 {row['p99_ms']}", flush=True)
    finally:
        hst.MAX_NEIGHBOURS = original_cap

    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, "live_latency_by_cap.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def _cell(cap: int, placement: Optional[str], key: str) -> Dict[str, Any]:
        vals = [float(r[key]) for r in rows if r["cap"] == cap
                and (placement is None or r["placement"] == placement)
                and r[key] is not None]
        return {"n": len(vals), "mean": round(statistics.mean(vals), 4),
                "min": round(min(vals), 4), "max": round(max(vals), 4),
                "spread": round(max(vals) - min(vals), 4)}

    summary: Dict[str, Any] = {
        "model": args.model, "state_dim": int(STATE_DIM), "steps": int(args.steps),
        "repeats_per_cell": int(args.repeats),
        "gpus": [torch.cuda.get_device_name(i)
                 for i in range(torch.cuda.device_count())],
        "torch_version": torch.__version__,
        "sumo_dir": os.environ.get("PAPER4_SUMO_DIR", "(shared default)"),
        "by_cap": {str(c): {"p99": _cell(c, None, "p99_ms"),
                            "mean": _cell(c, None, "mean_ms")}
                   for c in args.caps},
        "by_cap_and_placement": {
            f"{c}/{pl}": _cell(c, pl, "p99_ms")
            for c in args.caps for pl in ("isolated", "shared")},
        "reading": (
            "The cap costs something in a live run only if the gap BETWEEN caps "
            "exceeds the spread WITHIN a cap. The within-cap spread is the "
            "measurement's own noise, and with a tail statistic over 600 steps it "
            "is not small."),
    }
    json_path = os.path.join(args.out_dir, "live_latency_by_cap.json")
    with open(json_path, "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True, default=float)
    print("\n" + json.dumps(summary["by_cap"], indent=2, sort_keys=True))
    print(json.dumps(summary["by_cap_and_placement"], indent=2, sort_keys=True))
    print(f"\n{csv_path}\n{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
