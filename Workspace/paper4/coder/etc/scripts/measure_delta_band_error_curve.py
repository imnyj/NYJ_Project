#!/usr/bin/env python
# etc/scripts/measure_delta_band_error_curve.py
# ============================================================================
# WHERE THE PREDICTION ERROR SATURATES ALONG THE DELTA AXIS.
#
# ---------------------------------------------------------------------------
# THE QUESTION THIS ANSWERS
# ---------------------------------------------------------------------------
# HOORL's behaviour policy needs a Delta band, and the band cannot be chosen by
# argument. The decoder's full range is [0.1, 45] s, and a behaviour policy that
# spreads Delta over all of it spends most of its budget in a region where the
# dead-reckoned belief is already useless: past some interval length the RSU's
# prediction error is so large that observation feature [0],
# `norm_sq_error(e) = e^2 / (e^2 + E_REF^2)`, sits against 1.0 and carries no
# information about which Delta was chosen. A dataset collected there teaches an
# offline learner nothing except that long silences are bad, which it can also
# learn from one sample.
#
# The other end has the mirror problem. Below some interval length the vehicle
# has barely moved, feature [0] is EXACTLY 0.0 for a large fraction of the
# samples, and again the value stops separating one Delta from another.
#
# So the band is bounded by measurement on both sides:
#
#   * the lower edge is where samples of exactly 0.0 stop dominating;
#   * the upper edge is where the mean stops rising, i.e. where the feature
#     saturates.
#
# ---------------------------------------------------------------------------
# WHAT IS MEASURED, AND AGAINST WHAT
# ---------------------------------------------------------------------------
# Delta is drawn LOG-UNIFORMLY over the decoder's whole range so that every
# decade of the axis gets the same number of samples; a uniform draw would put
# 98 % of them above 1 s and leave the short end unresolved. Every closed
# interval contributes one row carrying the REQUESTED Delta, the MEASURED
# `delta_actual`, the observation feature [0] read out of the next observation,
# the raw dead-reckoning error in metres that the environment reported for that
# interval, and whether the interval ended in a transmission.
#
# Both the feature and the raw metres are kept because they answer different
# halves of the question. The feature is what the policy sees and is therefore
# what "carries information" refers to; the metres are unnormalised and show
# whether a flat stretch of the feature is a real physical plateau or an
# artefact of the E_REF normalisation.
#
# ---------------------------------------------------------------------------
# TRANSMITTED VERSUS NOT
# ---------------------------------------------------------------------------
# `last_pred_err` is refreshed only when a report actually lands. An interval
# that closed because the vehicle left RSU range carries the PREVIOUS interval's
# error into the next observation, so its feature [0] is not a reading of its own
# Delta. Those rows are counted and reported but the headline curve is computed
# from transmitted intervals only. Mixing them would flatten the curve at the
# long end, which is precisely the region the upper edge is read off.
#
# ---------------------------------------------------------------------------
# COST
# ---------------------------------------------------------------------------
# A few minutes of CPU. No model is built and no gradient is taken. Threads are
# limited so this can run beside a hyper-parameter search.
# ============================================================================
from __future__ import annotations

import argparse
import csv
import gc
import json
import logging
import math
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

logger = logging.getLogger("delta_band")

#: Edges of the log-spaced Delta bins the rows are aggregated into. Chosen to
#: give roughly three bins per decade over the decoder's full range, which is
#: fine enough to locate a knee and coarse enough that every bin holds a few
#: hundred samples at the sample sizes this script collects.
N_BINS: int = 15


def limit_threads(n: int = 1) -> None:
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                "NUMEXPR_NUM_THREADS"):
        os.environ[var] = str(max(1, int(n)))
    import torch

    torch.set_num_threads(max(1, int(n)))


def collect_rows(
    densities: Sequence[float],
    seeds: Sequence[int],
    steps: int,
    warmup_steps: int,
    num_channels: int,
    error_mode: str,
    sumo_dir: Optional[str],
    band: Optional[tuple] = None,
) -> List[Dict[str, Any]]:
    """Roll a log-uniform-Delta policy and return one row per CLOSED interval.

    Nothing here builds an observation or a reward. The observation comes back
    from `AoiV2IEnv.step`, and the error and the interval length come out of the
    environment's own completion record, so a row cannot disagree with what the
    trainer would have stored for the same interval.
    """
    from src.hot_swap_trainer import AoiV2IEnv, prepare_scenario
    from src.rl_interface import ActionDecoder

    rows: List[Dict[str, Any]] = []
    for density in densities:
        for seed in seeds:
            prepare_scenario(
                density=float(density), max_steps=int(steps),
                warmup_steps=int(warmup_steps), seed=int(seed), sumo_dir=sumo_dir,
            )
            decoder = ActionDecoder(num_channels=int(num_channels))
            # The default is the decoder's WHOLE range, which is what the band
            # is chosen from. A narrower `band` re-runs the same measurement
            # inside a candidate band, which is how the transition RATE of a
            # candidate is measured rather than modelled: the rate depends on
            # truncation as well as on E[1/Delta], and truncation is a property
            # of the traffic, not of the draw.
            lo, hi = float(decoder.delta_min), float(decoder.delta_max)
            if band is not None:
                lo = max(lo, float(band[0]))
                hi = min(hi, float(band[1]))
            rng = np.random.default_rng(int(seed))

            def draw() -> tuple:
                delta = float(np.exp(rng.uniform(math.log(lo), math.log(hi))))
                ch = int(rng.integers(0, int(num_channels)))
                power = float(rng.uniform(decoder.p_min, decoder.p_max))
                return (delta, ch, power)

            env: Optional[Any] = None
            n_before = len(rows)
            started = time.time()
            try:
                env = AoiV2IEnv(
                    density=float(density), seed=int(seed), max_steps=int(steps),
                    warmup_steps=int(warmup_steps), num_channels=int(num_channels),
                    error_mode=str(error_mode), sumo_dir=sumo_dir,
                )
                obs, _info = env.reset()
                random.seed(int(seed))

                open_delta: Dict[str, float] = {}
                action_dict: Dict[str, Any] = {}
                for vid in obs:
                    grant = draw()
                    open_delta[vid] = grant[0]
                    action_dict[vid] = grant

                for _step in range(int(steps)):
                    next_obs, _r, _term, _trunc, step_info = env.step(action_dict)
                    action_dict = {}
                    for rec in step_info["completed"]:
                        vid = rec["vid"]
                        requested = open_delta.pop(vid, None)
                        if requested is None:
                            continue
                        s2 = next_obs.get(vid)
                        rows.append({
                            "density": float(density),
                            "seed": int(seed),
                            "delta_requested": float(requested),
                            "delta_actual": float(rec["delta_actual"]),
                            "transmitted": int(bool(rec["transmitted"])),
                            "err_m": float(rec["error"]),
                            "r_err": float(rec["r_err"]),
                            # The feature the policy sees. None when the vehicle
                            # is already gone from the observation, which is
                            # recorded rather than imputed.
                            "feat0_next": (
                                float(s2[0]) if s2 is not None else float("nan")
                            ),
                            "next_obs_present": int(s2 is not None),
                        })
                    for vid in step_info["needs_decision"]:
                        if vid not in next_obs:
                            continue
                        grant = draw()
                        open_delta[vid] = grant[0]
                        action_dict[vid] = grant
                    for vid in [v for v in open_delta if v not in next_obs]:
                        open_delta.pop(vid, None)
                    obs = next_obs

                for rec in env.finalize_open_intervals():
                    vid = rec["vid"]
                    requested = open_delta.pop(vid, None)
                    if requested is None:
                        continue
                    s2 = obs.get(vid)
                    rows.append({
                        "density": float(density),
                        "seed": int(seed),
                        "delta_requested": float(requested),
                        "delta_actual": float(rec["delta_actual"]),
                        "transmitted": int(bool(rec["transmitted"])),
                        "err_m": float(rec["error"]),
                        "r_err": float(rec["r_err"]),
                        "feat0_next": float(s2[0]) if s2 is not None else float("nan"),
                        "next_obs_present": int(s2 is not None),
                    })
            finally:
                if env is not None:
                    try:
                        env.close()
                    except Exception:  # noqa: BLE001
                        logger.warning("close failed", exc_info=True)
                    del env
                    gc.collect()
            logger.info(
                "density %.1f seed %d: %d intervals in %.1f s",
                density, seed, len(rows) - n_before, time.time() - started,
            )
    return rows


def bin_rows(rows: List[Dict[str, Any]], lo: float, hi: float,
             transmitted_only: bool) -> List[Dict[str, Any]]:
    """Aggregate feature [0] and the raw error into log-spaced Delta bins."""
    sel = [r for r in rows if r["next_obs_present"] == 1
           and not math.isnan(r["feat0_next"])
           and (r["transmitted"] == 1 or not transmitted_only)]
    if not sel:
        return []
    edges = np.geomspace(lo, hi, N_BINS + 1)
    # Binned by the MEASURED interval, not the requested one. A requested 45 s
    # that ended after 3 s because the vehicle left range is a 3 s sample, and
    # binning it at 45 s would drag the long bins down with short intervals.
    d = np.array([r["delta_actual"] for r in sel], dtype=np.float64)
    f = np.array([r["feat0_next"] for r in sel], dtype=np.float64)
    e = np.array([r["err_m"] for r in sel], dtype=np.float64)
    idx = np.clip(np.digitize(d, edges) - 1, 0, N_BINS - 1)

    out: List[Dict[str, Any]] = []
    for b in range(N_BINS):
        m = idx == b
        n = int(m.sum())
        if n == 0:
            out.append({
                "bin": b, "delta_lo": float(edges[b]), "delta_hi": float(edges[b + 1]),
                "delta_geomean": float(math.sqrt(edges[b] * edges[b + 1])), "n": 0,
            })
            continue
        fb, eb = f[m], e[m]
        out.append({
            "bin": b,
            "delta_lo": float(edges[b]),
            "delta_hi": float(edges[b + 1]),
            "delta_geomean": float(math.sqrt(edges[b] * edges[b + 1])),
            "n": n,
            "feat0_mean": float(fb.mean()),
            "feat0_std": float(fb.std()),
            "feat0_median": float(np.median(fb)),
            "feat0_q1": float(np.percentile(fb, 25)),
            "feat0_q3": float(np.percentile(fb, 75)),
            "feat0_p99": float(np.percentile(fb, 99)),
            # The two saturation readings the band is chosen from.
            "frac_exact_zero": float((fb == 0.0).mean()),
            "frac_above_0p9": float((fb > 0.9).mean()),
            "n_unique_feat0": int(np.unique(fb).size),
            "err_m_mean": float(eb.mean()),
            "err_m_median": float(np.median(eb)),
        })
    return out


def realisability_by_request(rows: List[Dict[str, Any]], lo: float,
                             hi: float) -> List[Dict[str, Any]]:
    """How faithfully each REQUESTED Delta is actually delivered.

    The error curve alone cannot bound the band, because it says nothing about
    whether a requested interval happens at all. Two mechanisms break the
    request, one at each end, and both are invisible in a plot of error against
    the measured interval:

      * at the short end the simulation advances in fixed steps and a report
        cannot land sooner than the next one, so several distinct requests
        collapse onto the same realised interval. Those transitions carry
        different actions with identical consequences;
      * at the long end the vehicle leaves RSU coverage before the interval
        closes, the report never happens, and the interval is truncated. The
        stored action then describes an intention the environment never carried
        out.

    `transmitted_frac` and the median ratio of realised to requested interval
    measure the two directly, per request decade.
    """
    edges = np.geomspace(lo, hi, N_BINS + 1)
    req = np.array([r["delta_requested"] for r in rows], dtype=np.float64)
    act = np.array([r["delta_actual"] for r in rows], dtype=np.float64)
    tx = np.array([r["transmitted"] for r in rows], dtype=np.float64)
    idx = np.clip(np.digitize(req, edges) - 1, 0, N_BINS - 1)

    out: List[Dict[str, Any]] = []
    for b in range(N_BINS):
        m = idx == b
        n = int(m.sum())
        row: Dict[str, Any] = {
            "bin": b, "req_lo": float(edges[b]), "req_hi": float(edges[b + 1]),
            "req_geomean": float(math.sqrt(edges[b] * edges[b + 1])), "n": n,
        }
        if n:
            row.update({
                "transmitted_frac": float(tx[m].mean()),
                "actual_over_requested_median": float(np.median(act[m] / req[m])),
                "actual_median_s": float(np.median(act[m])),
                "actual_mean_s": float(act[m].mean()),
                "n_unique_actual": int(np.unique(act[m]).size),
            })
        out.append(row)
    return out


def write_csv(path: str, rows: List[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fieldnames))
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--densities", type=float, nargs="+", default=[5.0, 20.0, 35.0])
    p.add_argument("--seeds", type=int, nargs="+", default=[2001, 2002])
    p.add_argument("--steps", type=int, default=900)
    p.add_argument("--warmup-steps", type=int, default=600)
    p.add_argument("--num-channels", type=int, default=4)
    p.add_argument("--error-mode", type=str, default="accumulate")
    p.add_argument("--delta-lo", type=float, default=None,
                   help="restrict the behaviour policy to this band; the default "
                        "is the decoder's whole range, which is what the band is "
                        "chosen FROM")
    p.add_argument("--delta-hi", type=float, default=None)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--sumo-dir", type=str, default=None)
    p.add_argument("--out-dir", type=str,
                   default=os.path.join(ROOT, "results", "hoorl_offline"))
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    limit_threads(int(args.threads))

    started = time.time()
    rows = collect_rows(
        densities=[float(d) for d in args.densities],
        seeds=[int(s) for s in args.seeds],
        steps=int(args.steps),
        warmup_steps=int(args.warmup_steps),
        num_channels=int(args.num_channels),
        error_mode=str(args.error_mode),
        sumo_dir=args.sumo_dir,
        band=None if args.delta_lo is None and args.delta_hi is None
        else (args.delta_lo or 0.0, args.delta_hi or 1e9),
    )
    elapsed = time.time() - started

    # READ AFTER COLLECTION, NEVER BEFORE. `V_MAX_OBS`, `E_REF` and `DELTA_MAX`
    # are module-level constants derived from the scenario ON DISK and evaluated
    # once at import; `prepare_scenario` refreshes them through
    # `refresh_scenario_constants`. Reading them before the first
    # `prepare_scenario` returns the import-time fallback of an empty scenario
    # directory, which was measured here as E_REF 13.32 and V_MAX_OBS 13.32
    # against the post-refresh 13.26 and 15.912. Those are the numbers the
    # observation is normalised by, so recording the wrong pair would describe a
    # different observation from the one that was actually collected.
    import src.rl_interface as rli

    decoder = rli.ActionDecoder(num_channels=int(args.num_channels))
    lo, hi = float(decoder.delta_min), float(decoder.delta_max)
    E_REF, V_MAX_OBS = float(rli.E_REF), float(rli.V_MAX_OBS)
    logger.info("decoder Delta range after refresh: [%.3f, %.3f] s", lo, hi)

    raw_path = os.path.join(args.out_dir, "delta_band_raw_intervals.csv")
    write_csv(raw_path, rows, [
        "density", "seed", "delta_requested", "delta_actual", "transmitted",
        "err_m", "r_err", "feat0_next", "next_obs_present",
    ])

    tx = bin_rows(rows, lo, hi, transmitted_only=True)
    allr = bin_rows(rows, lo, hi, transmitted_only=False)
    fields = [
        "bin", "delta_lo", "delta_hi", "delta_geomean", "n", "feat0_mean",
        "feat0_std", "feat0_median", "feat0_q1", "feat0_q3", "feat0_p99",
        "frac_exact_zero", "frac_above_0p9", "n_unique_feat0",
        "err_m_mean", "err_m_median",
    ]
    tx_path = os.path.join(args.out_dir, "delta_band_error_curve_transmitted.csv")
    all_path = os.path.join(args.out_dir, "delta_band_error_curve_all.csv")
    write_csv(tx_path, tx, fields)
    write_csv(all_path, allr, fields)

    real_path = os.path.join(args.out_dir, "delta_band_realisability.csv")
    write_csv(real_path, realisability_by_request(rows, lo, hi), [
        "bin", "req_lo", "req_hi", "req_geomean", "n", "transmitted_frac",
        "actual_over_requested_median", "actual_median_s", "actual_mean_s",
        "n_unique_actual",
    ])

    summary = {
        "decoder_delta_min": lo,
        "decoder_delta_max": hi,
        "E_REF": float(E_REF),
        "V_MAX_OBS": float(V_MAX_OBS),
        "densities": [float(d) for d in args.densities],
        "seeds": [int(s) for s in args.seeds],
        "steps": int(args.steps),
        "warmup_steps": int(args.warmup_steps),
        "error_mode": str(args.error_mode),
        "requested_band": None if args.delta_lo is None and args.delta_hi is None
        else [args.delta_lo, args.delta_hi],
        "n_intervals": len(rows),
        "n_transmitted": int(sum(r["transmitted"] for r in rows)),
        "n_next_obs_present": int(sum(r["next_obs_present"] for r in rows)),
        "wall_clock_s": round(elapsed, 2),
        "n_bins": N_BINS,
        "note": (
            "feat0 is observation feature [0], norm_sq_error(last_pred_err). Rows "
            "are binned by delta_actual, the MEASURED interval, not by the "
            "requested Delta. The transmitted-only curve is the headline: an "
            "interval that closed without a report carries the previous "
            "interval's error into the next observation."
        ),
    }
    with open(os.path.join(args.out_dir, "delta_band_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)

    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"\nraw rows      -> {raw_path}")
    print(f"transmitted   -> {tx_path}")
    print(f"all closures  -> {all_path}")
    print(f"realisability -> {real_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
