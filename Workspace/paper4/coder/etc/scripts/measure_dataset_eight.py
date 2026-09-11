#!/usr/bin/env python
# etc/scripts/measure_dataset_eight.py
# ============================================================================
# THE EIGHT MEASUREMENTS THE FORMAT-3 DATASET WAS COLLECTED TO MAKE POSSIBLE.
#
# ---------------------------------------------------------------------------
# WHY THEY ARE ONE SCRIPT
# ---------------------------------------------------------------------------
# All eight read the same file and five of them need columns that did not exist
# before format 3: `tls_state_code` for the character distribution,
# `dist_to_stopline_m` for the clipped distances, `n_neighbours` for the
# neighbourhood sizes, `cell_index` for joining a row to the constants that
# normalised it, and `action_raw` for the Delta range. Splitting them would mean
# loading a 22 MB file eight times and, worse, would let one of them silently run
# against a file that lacks its column.
#
# ---------------------------------------------------------------------------
# THE QUESTION EACH ONE ANSWERS
# ---------------------------------------------------------------------------
#   1. How many neighbours are there really? -- decides whether MAX_NEIGHBOURS
#      is a cap or a description.
#   2. How unequal are the four subchannels at one instant? -- the reason the
#      per-channel features were added at all.
#   3. How far away are the stop lines that feature [12] clips? -- and, split by
#      ROAD CYCLE, whether the 300-400 m gap seen on one road is geometry or an
#      accident of that road. If it is geometry it recurs; if it does not recur,
#      the explanation was wrong and so is the case for raising the bound.
#   4. Which SUMO signal characters occur? -- settles whether the all-zero
#      one-hot needs a mapping rule or means "no signal".
#   5. What is the peak in-coverage vehicle count per density? -- the tail that
#      N_ACTIVE_MAX_OBS has to clear, uncensored because the raw count is stored.
#   6. Does re-normalising the raw columns reproduce the stored vector? -- the
#      offline/online divergence detector.
#   7. What fraction of actions falls outside the current range, and what does
#      dropping them do to the Delta DISTRIBUTION? -- a count alone would hide a
#      cut that removes one end of the axis.
#   8. Which part of its nominal range does each feature use, AND HOW MUCH DOES
#      IT VARY INSIDE THAT PART? The second half is the one that matters. A
#      feature confined to a narrow band is useless only if it is nearly constant
#      there; if it moves with conditions inside that band it is informative, and
#      "does it use the whole range" is the wrong question. Both are reported.
#
# Every table is written with the dataset's own provenance so a number can never
# be read without knowing which collection produced it.
# ============================================================================
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DEFAULT_DATASET = "/home/imnyj/Workspace/paper4/data/hoorl_offline/hoorl_offline.npz"


def _write(path: str, rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return ""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    keys: List[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", default=DEFAULT_DATASET)
    p.add_argument("--out-dir", default=os.path.join(ROOT, "results", "hoorl_offline"))
    args = p.parse_args(argv)

    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    from src.hoorl_offline import (CLOSE_REASON_LABELS, OfflineDataset,
                                   filter_actions_in_range)
    from src.hoorl_offline_stats import FEATURE_SPEC
    from src.rl_interface import (MAX_NEIGHBOURS as _MAX_NEIGHBOURS,
                                  PHASE_REMAINING_REF_S, RAW_OBSERVATION_FIELDS,
                                  StateVectorizer, TLS_STATE_CODES)

    ds = OfflineDataset.load(os.path.abspath(args.dataset))
    # Measure the observation AS A RUN WOULD SEE IT, not as it was written.
    #
    # `load` returns the vectors exactly as collected. The training loader calls
    # `reconcile_to_current_constants` before using them, so measuring the raw
    # load would describe a normalisation no run applies -- and after three bounds
    # moved on 2026-09-06 that difference is large: feature [13] reads 9.31 %
    # clipped as collected and 0 % as a run sees it.
    #
    # Measurement 6 must run BEFORE that reconciliation. It recomputes each
    # feature from the raw columns using the constants RECORDED IN THE FILE, so
    # it only has something to compare against while the vectors still carry the
    # normalisation those constants produced. Verifying after reconciliation
    # compares current-constant vectors against collection-time constants and
    # fails for a reason that says nothing about the raw columns.
    raw_check = ds.verify_raw_columns()
    reconciliation = ds.reconcile_to_current_constants()
    meta = ds.metadata
    manifest = meta.get("contents_manifest", {})
    if not manifest.get("has_raw_columns"):
        raise SystemExit(
            f"{args.dataset} has no raw columns (contents_manifest={manifest}). "
            "Five of these eight measurements need them; run a format-3 "
            "collection first rather than reporting partial answers."
        )
    idx = {n: i for i, n in enumerate(RAW_OBSERVATION_FIELDS)}
    raw = ds.arrays["state_raw"].astype(np.float64)
    st = ds.arrays["state"].astype(np.float64)
    cell = ds.arrays["cell_index"]
    per_cell = {int(r["cell_index"]): r for r in meta["per_episode"]}
    dens = np.array([per_cell[int(c)]["density"] for c in cell])
    cyc = np.array([int(per_cell[int(c)].get("road_cycle") or 0) for c in cell])
    out: Dict[str, Any] = {
        "dataset": os.path.abspath(args.dataset),
        "n_transitions": int(len(ds)),
        "contents_manifest": manifest,
        "road_seed": meta.get("road_seed"),
        "reconciliation": reconciliation,
        "git": meta.get("git"),
        "coverage_note": (
            "Every table below is the WHOLE collection, not a sample of it: "
            f"{len(ds)} transitions over {manifest.get('state_dim')} features, "
            f"road cycles {sorted(set(int(c) for c in cyc))} of the 0..14 a "
            "100-episode training run walks. It therefore covers the roads of "
            "training episodes 0..20 and says nothing about the later ones."
        ),
    }
    paths: List[str] = []

    # 1. neighbourhood size ---------------------------------------------------
    nb = raw[:, idx["n_neighbours"]]
    rows1 = []
    for d in sorted(set(dens)):
        m = dens == d
        rows1.append({"density": float(d), "n": int(m.sum()),
                      "mean": round(float(nb[m].mean()), 2),
                      "p50": float(np.percentile(nb[m], 50)),
                      "p90": float(np.percentile(nb[m], 90)),
                      "p99": float(np.percentile(nb[m], 99)),
                      "max": float(nb[m].max()),
                      "frac_above_16": round(float((nb[m] > 16).mean()), 4),
                      "frac_above_32": round(float((nb[m] > 32).mean()), 4)})
    paths.append(_write(os.path.join(args.out_dir, "m1_neighbour_counts.csv"), rows1))
    out["m1_neighbours"] = {
        "mean_over_all": round(float(nb.mean()), 2), "max": float(nb.max()),
        # Read from the constant rather than written as a literal: the key said
        # "_16" while the cap was 192, so the number under it answered a question
        # nobody was asking any more.
        "cap": int(_MAX_NEIGHBOURS),
        "fraction_above_cap": round(float((nb > _MAX_NEIGHBOURS).mean()), 4),
        "fraction_above_16": round(float((nb > 16).mean()), 4)}

    # 2. subchannel spread ----------------------------------------------------
    ch = raw[:, [idx[f"cbr_ch{k}"] for k in range(4)]]
    mean_ch = ch.mean(axis=1)
    spread = ch.max(axis=1) - ch.min(axis=1)
    live = mean_ch > 0
    rows2 = []
    for d in sorted(set(dens)):
        m = (dens == d) & live
        if not m.any():
            continue
        rows2.append({"density": float(d), "n": int(m.sum()),
                      "mean_occupancy": round(float(mean_ch[m].mean()), 6),
                      "spread_mean": round(float(spread[m].mean()), 6),
                      "spread_p99": round(float(np.percentile(spread[m], 99)), 6),
                      "spread_over_mean": round(float(spread[m].mean() / mean_ch[m].mean()), 3),
                      "frac_max_equals_used": ""})
    paths.append(_write(os.path.join(args.out_dir, "m2_subchannel_spread.csv"), rows2))
    out["m2_spread_over_mean"] = {
        "overall": round(float(spread[live].mean() / mean_ch[live].mean()), 3),
        "fraction_of_steps_with_no_transmission": round(float((~live).mean()), 4)}

    # 3. stop-line distances, BY ROAD CYCLE -----------------------------------
    dist = raw[:, idx["dist_to_stopline_m"]]
    meas = raw[:, idx["dist_to_stopline_measured"]] > 0
    edges = [0, 50, 100, 150, 200, 250, 300, 350, 400, 500, 600, 700, 800, 900, 1e9]
    rows3 = []
    for c in sorted(set(int(x) for x in cyc)):
        m = (cyc == c) & meas
        h, _ = np.histogram(dist[m], bins=edges)
        for j in range(len(h)):
            rows3.append({"road_cycle": c, "lo_m": edges[j], "hi_m": edges[j + 1],
                          "count": int(h[j]),
                          "fraction": round(float(h[j] / max(1, m.sum())), 5)})
    paths.append(_write(os.path.join(args.out_dir, "m3_stopline_by_cycle.csv"), rows3))
    gaps = {}
    for c in sorted(set(int(x) for x in cyc)):
        m = (cyc == c) & meas
        empty = [(edges[j], edges[j + 1]) for j in range(len(edges) - 1)
                 if np.histogram(dist[m], bins=edges)[0][j] == 0
                 and edges[j] < dist[m].max()]
        gaps[str(c)] = [[float(a), float(b)] for a, b in empty]
    out["m3_stopline"] = {
        "rsu_range_m": 300.0,
        "fraction_beyond_rsu_range": round(float((dist[meas] >= 300.0).mean()), 4),
        "fraction_no_signal": round(float((~meas).mean()), 4),
        "p50": round(float(np.percentile(dist[meas], 50)), 1),
        "p90": round(float(np.percentile(dist[meas], 90)), 1),
        "max": round(float(dist[meas].max()), 1),
        "empty_bins_per_road_cycle": gaps,
        "gap_note": (
            "The 300-400 m gap was explained by block geometry. If that holds it "
            "recurs on every road; `empty_bins_per_road_cycle` is where to check. "
            "A gap on one cycle only would falsify the explanation and with it "
            "the case for raising the [12] bound to 900 m."),
    }

    # 4. signal characters ----------------------------------------------------
    code = raw[:, idx["tls_state_code"]]
    inv = {v: k for k, v in TLS_STATE_CODES.items()}
    rows4 = []
    for v in sorted(set(code)):
        n = int((code == v).sum())
        rows4.append({"tls_state_code": int(v), "character": inv.get(int(v), "UNLISTED"),
                      "count": n, "fraction": round(n / len(code), 5),
                      "onehot": ("ALL ZERO" if inv.get(int(v)) not in ("r", "y", "g", "G")
                                 else inv.get(int(v)))})
    paths.append(_write(os.path.join(args.out_dir, "m4_tls_characters.csv"), rows4))
    out["m4_tls"] = {r["character"]: r["fraction"] for r in rows4}

    # 5. in-coverage count, uncensored ---------------------------------------
    na = raw[:, idx["n_active"]]
    rows5 = []
    for d in sorted(set(dens)):
        m = dens == d
        rows5.append({"density": float(d), "n": int(m.sum()),
                      "mean": round(float(na[m].mean()), 2),
                      "p99": float(np.percentile(na[m], 99)),
                      "p999": float(np.percentile(na[m], 99.9)),
                      "max": float(na[m].max())})
    paths.append(_write(os.path.join(args.out_dir, "m5_n_active_uncensored.csv"), rows5))
    from src.rl_interface import N_ACTIVE_MAX_OBS
    out["m5_n_active"] = {"cap": float(N_ACTIVE_MAX_OBS), "max_seen": float(na.max()),
                          "fraction_at_or_above_cap": round(float((na >= N_ACTIVE_MAX_OBS).mean()), 5)}

    # 6. normalisation cross-check -----------------------------------------
    #
    # Through `OfflineDataset.verify_raw_columns`, which is the PRODUCTION path:
    # `verify_renormalisation` -> `renormalise_states`, the same function the
    # training loader calls. This section used to carry its own arithmetic, and
    # that made it a check on a formula written in a measurement script rather
    # than on the code a run executes -- the two agreed until the per-channel
    # features became relative, at which point the script's copy would have gone
    # on reporting a match against its own stale definition.
    check = raw_check
    rows6 = [{"feature": j, "max_abs_error": e,
              "matches": bool(e <= check["atol"])}
             for j, e in sorted(check["per_feature_abs_error"].items())]
    out["m6_all_match"] = bool(check["matches"])
    out["m6_worst"] = {"feature": check["worst_feature"],
                       "abs_error": check["worst_abs_error"],
                       "atol": check["atol"]}
    paths.append(_write(os.path.join(args.out_dir, "m6_normalisation_check.csv"), rows6))

    # 7. Delta range and what dropping does ----------------------------------
    _filtered, report = filter_actions_in_range(ds)
    out["m7_delta_range"] = report
    paths.append(_write(os.path.join(args.out_dir, "m7_delta_range.csv"), [{
        "n_before": report["n_before"], "n_dropped": report["n_dropped"],
        "fraction_dropped": report["fraction_dropped"],
        "geomean_before_s": report["delta_before"]["geomean_s"],
        "geomean_after_s": report["delta_after"].get("geomean_s"),
        "p99_before_s": report["delta_before"]["p99_s"],
        "p99_after_s": report["delta_after"].get("p99_s")}]))

    # 8. per-feature used range AND variation inside it ----------------------
    rows8 = []
    for j, (name, lo, hi, meaning) in enumerate(FEATURE_SPEC):
        col = st[:, j]
        nominal = max(hi - lo, 1e-12)
        used = float(col.max() - col.min())
        rows8.append({
            "index": j, "feature": name,
            "nominal_low": lo, "nominal_high": hi,
            "observed_min": round(float(col.min()), 6),
            "observed_max": round(float(col.max()), 6),
            "used_span_over_nominal": round(used / nominal, 4),
            # The second question, and the one that decides usefulness: does it
            # MOVE inside whatever span it occupies?
            "std": round(float(col.std()), 6),
            "std_over_used_span": round(float(col.std() / used), 4) if used > 0 else 0.0,
            "std_over_nominal": round(float(col.std() / nominal), 6),
            "n_unique": int(np.unique(np.round(col, 6)).size),
            "frac_at_observed_min": round(float((col == col.min()).mean()), 4),
            "frac_at_observed_max": round(float((col == col.max()).mean()), 4),
            "meaning": meaning,
        })
    paths.append(_write(os.path.join(args.out_dir, "m8_feature_usage.csv"), rows8))
    out["m8_note"] = (
        "`used_span_over_nominal` answers 'does it use the range'; "
        "`std_over_used_span` answers 'does it vary inside what it uses'. The "
        "second is the one that decides whether a feature is informative -- a "
        "narrow but varying feature carries signal, a wide but nearly constant "
        "one does not."
    )

    json_path = os.path.join(args.out_dir, "dataset_eight_measurements.json")
    with open(json_path, "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True, default=float)
    print(json.dumps(out, indent=2, sort_keys=True, default=float)[:6000])
    for p_ in paths:
        print(p_)
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
