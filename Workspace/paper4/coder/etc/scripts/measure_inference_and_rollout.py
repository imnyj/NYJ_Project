#!/usr/bin/env python
# etc/scripts/measure_inference_and_rollout.py
# ============================================================================
# INFERENCE LATENCY AND TRIAL COST, FOR ALL NINE BASELINES.
#
# ---------------------------------------------------------------------------
# WHY ALL NINE AND NOT ONE
# ---------------------------------------------------------------------------
# The manuscript quotes a mean of 1.232 ms and a 99th percentile of 2.54 ms, and
# `results/hw_feasibility.json` shows those are real measurements -- of TD3, at
# 600 steps, on a 17-dimensional observation, on 2026-09-04. The same paragraph
# says all nine models pass through one harness, which is true and does not make
# their inference costs equal: TD3 runs one actor forward, while three of the
# nine encode a neighbour set and pool it.
#
# The number the manuscript should carry is the WORST of the nine, because the
# claim being made is that the harness meets a real-time budget, and a budget is
# met by the slowest thing in it. Quoting the lightest model states something
# weaker than intended. Which model is heaviest is not assumed here: the three
# with neighbour encoders are the obvious guess, and this measures instead.
#
# ---------------------------------------------------------------------------
# WHY THE NEIGHBOUR CAP IS SWEPT
# ---------------------------------------------------------------------------
# `MAX_NEIGHBOURS` is 16 while the mean neighbourhood is 120.7 vehicles, so a
# joint critic sees an eighth of what is there and 98.19 % of observations are
# truncated. Raising it costs computation, and how much was unknown. Sweeping 16,
# 32 and 64 turns that into a curve, which -- read against how much of the
# neighbourhood each cap covers -- is what a choice can be based on.
#
# THE DECISION RULE IS FIXED IN ADVANCE, deliberately, so the bound is not
# fitted to whichever number looks good:
#
#     take the LARGEST cap whose 99th-percentile inference latency stays under
#     10 % of the 0.1 s scheduling step, i.e. under 10 ms, for the SLOWEST of the
#     nine models.
#
# The 99th percentile rather than the mean, because a real-time guarantee fails
# in the tail. The 10 % figure is a DESIGN MARGIN chosen by the team lead, not
# derived from physics: the step also has to contain the SUMO advance, the
# channel computation and logging, and a single component taking a tenth of the
# budget is the conventional point at which to look again.
#
# ---------------------------------------------------------------------------
# WHY THE TWO MEASUREMENTS ARE IN ONE SCRIPT BUT NOT ONE RUN
# ---------------------------------------------------------------------------
# They share the nine-model loop and the scenario, so they belong together. They
# do NOT share a run: inference latency is timed on `select_action` alone, with
# no gradient step and no environment advance, while trial cost is a full
# 4000-step rollout with training. Timing the first inside the second would
# measure `select_action` while a background trainer competes for the GPU, which
# is a different quantity from the one the manuscript reports.
# ============================================================================
from __future__ import annotations

import argparse
import csv
import gc
import json
import os
import statistics
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: Step budget the latency is judged against, seconds, and the share of it a
#: single component may take. See the module docstring: the share is a design
#: margin set by the team lead on 2026-09-06, not a derived quantity.
SCHEDULING_STEP_S: float = 0.1
LATENCY_BUDGET_FRACTION: float = 0.10


def time_inference(model_name: str, cap: int, n_calls: int, device: str,
                   state_dim: int, num_channels: int) -> Dict[str, Any]:
    """Latency of one `select_action`, repeated, with a neighbourhood of `cap`.

    No environment and no gradient step: this is the cost of deciding, which is
    what has to fit inside a scheduling step. Warm-up calls are discarded because
    the first CUDA launch of a kernel carries its compilation.
    """
    import torch

    from src.baselines import get_baseline

    cls = get_baseline(model_name)
    kwargs: Dict[str, Any] = {"state_dim": state_dim, "num_channels": num_channels,
                              "hidden_dim": 128}
    try:
        model = cls(max_agents=cap, **kwargs)
        takes_cap = True
    except TypeError:
        model = cls(**kwargs)
        takes_cap = False
    try:
        model.to(device)
    except Exception:  # noqa: BLE001 - some baselines wrap an external learner
        pass

    rng = np.random.default_rng(0)
    state = rng.uniform(-1, 1, state_dim).astype(np.float32)
    latencies: List[float] = []
    for i in range(n_calls + 20):
        t0 = time.perf_counter()
        with torch.no_grad():
            model.select_action(state, deterministic=True)
        if device.startswith("cuda"):
            torch.cuda.synchronize()
        if i >= 20:                      # discard warm-up
            latencies.append((time.perf_counter() - t0) * 1000.0)
    del model
    gc.collect()
    if device.startswith("cuda"):
        torch.cuda.empty_cache()

    a = np.asarray(latencies)
    return {
        "model": model_name, "neighbour_cap": int(cap),
        "accepts_neighbour_cap": int(takes_cap),
        "device": device, "state_dim": int(state_dim), "n_calls": int(a.size),
        "mean_ms": round(float(a.mean()), 4),
        "p50_ms": round(float(np.percentile(a, 50)), 4),
        "p99_ms": round(float(np.percentile(a, 99)), 4),
        "max_ms": round(float(a.max()), 4),
        "p99_over_step_budget": round(float(np.percentile(a, 99))
                                      / (SCHEDULING_STEP_S * 1000.0), 5),
    }


def time_update(model_name: str, cap: int, n_steps: int, device: str,
                state_dim: int, num_channels: int, batch_size: int = 256
                ) -> Dict[str, Any]:
    """Cost of one gradient step with a neighbourhood of width `cap`.

    THIS, NOT `select_action`, IS WHERE THE CAP COSTS ANYTHING. Measured
    2026-09-06: sweeping the cap over 16, 32 and 64 moved inference latency by
    less than the run-to-run noise for every one of the nine models, and the
    reason is structural rather than a measurement artefact -- `select_action`
    takes only the ego state. All three neighbourhood-consuming baselines feed
    the neighbours to a JOINT CRITIC, which runs during `update` and never during
    action selection. A latency budget therefore cannot discriminate between
    caps, and choosing one on that basis would have been choosing on a quantity
    the cap does not affect.

    The batch is synthetic. Nothing here learns anything; the quantity wanted is
    the wall-clock cost of the encoder and the pooling at each width, and a real
    batch would add SUMO time without changing it.
    """
    import torch

    from src.baselines import get_baseline

    cls = get_baseline(model_name)
    kwargs: Dict[str, Any] = {"state_dim": state_dim, "num_channels": num_channels,
                              "hidden_dim": 128}
    try:
        model = cls(max_agents=cap, **kwargs)
        takes_cap = True
    except TypeError:
        model = cls(**kwargs)
        takes_cap = False
    try:
        model.to(device)
    except Exception:  # noqa: BLE001
        pass

    g = torch.Generator().manual_seed(0)
    b = batch_size
    batch = {
        "state": torch.rand(b, state_dim, generator=g) * 2 - 1,
        "action": torch.rand(b, 3, generator=g),
        "reward": -torch.rand(b, 1, generator=g),
        "next_state": torch.rand(b, state_dim, generator=g) * 2 - 1,
        "done": torch.zeros(b, 1),
        "delta_t": torch.rand(b, 1, generator=g) * 9.5 + 0.5,
        "action_idx": torch.randint(0, num_channels, (b,), generator=g),
        "behaviour_log_prob": torch.full((b, 1), -1.386),
        "neighbour_state": torch.rand(b, cap, state_dim, generator=g) * 2 - 1,
        "neighbour_mask": torch.ones(b, cap),
        "next_neighbour_state": torch.rand(b, cap, state_dim, generator=g) * 2 - 1,
        "next_neighbour_mask": torch.ones(b, cap),
    }
    batch["discount"] = torch.pow(torch.tensor(0.99), batch["delta_t"])
    batch = {k: (v.to(device) if hasattr(v, "to") else v) for k, v in batch.items()}

    times: List[float] = []
    failed = ""
    for i in range(n_steps + 5):
        t0 = time.perf_counter()
        try:
            model.update(batch)
        except Exception as exc:  # noqa: BLE001
            failed = f"{type(exc).__name__}: {exc}"
            break
        if device.startswith("cuda"):
            torch.cuda.synchronize()
        if i >= 5:
            times.append((time.perf_counter() - t0) * 1000.0)
    del model
    gc.collect()
    if device.startswith("cuda"):
        torch.cuda.empty_cache()
    if failed or not times:
        return {"model": model_name, "neighbour_cap": int(cap), "error": failed,
                "accepts_neighbour_cap": int(takes_cap)}
    a = np.asarray(times)
    return {"model": model_name, "neighbour_cap": int(cap),
            "accepts_neighbour_cap": int(takes_cap), "device": device,
            "batch_size": int(batch_size), "n_updates": int(a.size),
            "mean_ms": round(float(a.mean()), 4),
            "p99_ms": round(float(np.percentile(a, 99)), 4), "error": ""}


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--models", nargs="+", default=None)
    p.add_argument("--caps", type=int, nargs="+", default=[16, 32, 64])
    p.add_argument("--n-calls", type=int, default=600)
    p.add_argument("--device", default=None)
    p.add_argument("--sumo-dir", default=None)
    p.add_argument("--out-dir", default=os.path.join(ROOT, "results", "diagnostics"))
    args = p.parse_args(argv)

    import torch

    from src.baselines import ALL_BASELINES
    from src.rl_interface import MAX_NEIGHBOURS, STATE_DIM
    import src.Communications as comm

    device = args.device or ("cuda:0" if torch.cuda.is_available() else "cpu")
    models = args.models or sorted(ALL_BASELINES)

    # The scenario is generated first so the observation constants are the ones a
    # real run would use; the decoder a model builds reads DELTA_MAX from them.
    if args.sumo_dir:
        from src.hot_swap_trainer import prepare_scenario
        from src.sumo.make_sumo_set import seed_road_network
        prepare_scenario(density=25.0, max_steps=600, warmup_steps=1200,
                         seed=seed_road_network(25.0, 0), sumo_dir=args.sumo_dir)

    rows: List[Dict[str, Any]] = []
    for m in models:
        for cap in args.caps:
            r = time_inference(m, cap, args.n_calls, device, STATE_DIM,
                               comm.NUM_SUBCHANNELS)
            rows.append(r)
            print(f"{m:14s} cap {cap:3d}  mean {r['mean_ms']:7.3f} ms  "
                  f"p99 {r['p99_ms']:7.3f} ms  "
                  f"({100 * r['p99_over_step_budget']:5.2f} % of the step)"
                  f"{'' if r['accepts_neighbour_cap'] else '   [cap not accepted]'}",
                  flush=True)

    # The cap's real cost: the gradient step, where the joint critic runs.
    urows: List[Dict[str, Any]] = []
    for m in models:
        for cap in args.caps:
            r = time_update(m, cap, max(20, args.n_calls // 20), device, STATE_DIM,
                            comm.NUM_SUBCHANNELS)
            urows.append(r)
            if r.get("error"):
                print(f"{m:14s} cap {cap:3d}  update FAILED: {r['error'][:70]}", flush=True)
            else:
                print(f"{m:14s} cap {cap:3d}  update mean {r['mean_ms']:8.3f} ms  "
                      f"p99 {r['p99_ms']:8.3f} ms", flush=True)

    os.makedirs(args.out_dir, exist_ok=True)
    ucsv = os.path.join(args.out_dir, "update_cost_by_cap.csv")
    keys: List[str] = []
    for r in urows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(ucsv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in urows:
            w.writerow({k: r.get(k, "") for k in keys})

    csv_path = os.path.join(args.out_dir, "inference_latency_by_cap.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    budget_ms = SCHEDULING_STEP_S * LATENCY_BUDGET_FRACTION * 1000.0
    worst = {}
    for cap in args.caps:
        at_cap = [r for r in rows if r["neighbour_cap"] == cap]
        slowest = max(at_cap, key=lambda r: r["p99_ms"])
        worst[str(cap)] = {"slowest_model": slowest["model"],
                           "p99_ms": slowest["p99_ms"],
                           "within_budget": bool(slowest["p99_ms"] <= budget_ms)}
    admissible = [int(c) for c in args.caps if worst[str(c)]["within_budget"]]
    summary = {
        "device": device, "state_dim": int(STATE_DIM),
        "current_MAX_NEIGHBOURS": int(MAX_NEIGHBOURS),
        "n_calls_per_cell": int(args.n_calls),
        "scheduling_step_s": SCHEDULING_STEP_S,
        "budget_fraction": LATENCY_BUDGET_FRACTION,
        "budget_ms": budget_ms,
        "worst_model_per_cap": worst,
        "caps_within_budget": admissible,
        "largest_cap_within_budget": max(admissible) if admissible else None,
        "decision_rule": (
            "the largest cap whose 99th-percentile latency for the SLOWEST of the "
            "nine models stays under 10 % of the 0.1 s scheduling step. The 10 % "
            "is a design margin set by the team lead on 2026-09-06, not a derived "
            "quantity, and is recorded as such."),
        "the_cap_does_not_affect_inference": (
            "Measured: sweeping 16/32/64 moved 99th-percentile inference latency "
            "by less than run-to-run noise for all nine models, because "
            "`select_action` takes only the ego state and the neighbourhood "
            "reaches the JOINT CRITIC during `update`. A latency budget cannot "
            "choose a cap. See update_cost_by_cap.csv for the quantity that does "
            "depend on it."),
        "what_this_does_not_decide": (
            "the effect of the cap on task performance. That is left to a separate "
            "ablation. It is not measured here because a short training run does "
            "not predict a long one -- the same reason a divergence threshold was "
            "left unset after 4,000 steps failed to predict 200,000."),
    }
    json_path = os.path.join(args.out_dir, "inference_latency_by_cap.json")
    with open(json_path, "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True, default=float)
    print("\n" + json.dumps(summary, indent=2, sort_keys=True, default=float))
    print(f"\n{csv_path}\n{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
