#!/usr/bin/env python
# etc/scripts/measure_queue_max_band.py
# ============================================================================
# THE QUEUE_MAX SWEEP, WITH THE COMPARISON BAND RECOMPUTED EACH TIME.
#
# ---------------------------------------------------------------------------
# WHY THIS IS NOT PART OF measure_bound_candidates.py
# ---------------------------------------------------------------------------
# That table reports each candidate on its own: how much it clips, how wide the
# surviving distribution is. Those numbers answer "what does this bound cost"
# but not "is the result still legible next to the other features", and the
# second question is the one that stopped `QUEUE_MAX` from going to 30 or 40. A
# bound that clips nothing and leaves the feature with the smallest spread in
# the vector has bought silence.
#
# ---------------------------------------------------------------------------
# THE MISTAKE THIS FILE EXISTS TO PREVENT
# ---------------------------------------------------------------------------
# The band must be recomputed under the constants now in force. It was first
# read out of a stored `m8_feature_usage.csv` that had been written when
# `N_ACTIVE_MAX_OBS` was 168, and under that stale band feature [13] carries a
# std of 0.2603 instead of 0.1749 -- one rank above `n_queue_norm` instead of one
# below. Every candidate's percentile then shifts by a whole bucket, which is
# enough to move a decision. The band here is rebuilt from the same reconciled
# states the candidate is measured on, so the two can never disagree.
#
# ---------------------------------------------------------------------------
# WHICH FEATURES FORM THE BAND, AND WHY THESE TWELVE
# ---------------------------------------------------------------------------
# Only the features a normalising constant divides. The one-hot signal flags
# [8..10] have a std fixed by their own prevalence, `heading_cos` [16] is a
# geometric projection with no bound to choose, and the per-subchannel features
# [17..20] are ratios to a mean rather than fractions of a ceiling. Ranking
# `n_queue_norm` against any of those compares it to a quantity no bound
# decision can move.
#
# ---------------------------------------------------------------------------
# THE PERCENTILE CONVENTION, STATED BECAUSE IT CHANGES THE NUMBER
# ---------------------------------------------------------------------------
# `percentile_below` is the fraction of the twelve whose std is strictly SMALLER
# than the candidate's. With twelve features the buckets are 8.3 apart, and the
# alternative convention (counting the feature itself, rank/n) reads one bucket
# higher throughout. Both were in use in this project's notes at one point and
# the disagreement looked like a measurement error; only the convention differed.
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

DEFAULT_DATASET = "/home/imnyj/Workspace/paper4/data/hoorl_offline/hoorl_offline.npz"

#: The features a normalising constant divides. See the header for why the other
#: nine are excluded.
MAGNITUDE_FEATURES = (0, 1, 2, 3, 4, 5, 6, 7, 11, 12, 13, 15)

#: Bracketing the value in force (20 at the time of the sweep) and the first
#: candidate that clips nothing (40). The intermediate values exist because
#: choosing 30 over 40 alone would have left the whole interval 20-30 unexamined,
#: and the chosen value came out of it.
CANDIDATES = (20.0, 22.0, 24.0, 25.0, 26.0, 28.0, 30.0, 40.0)

QUEUE_FEATURE = 15


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", default=DEFAULT_DATASET)
    p.add_argument("--out-dir", default=os.path.join(ROOT, "results", "hoorl_offline"))
    args = p.parse_args(argv)

    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    from src.hoorl_offline import OfflineDataset
    from src.rl_interface import observation_constants_live

    ds = OfflineDataset.load(os.path.abspath(args.dataset))
    live = observation_constants_live()

    rows: List[Dict[str, Any]] = []
    for value in CANDIDATES:
        target = dict(live)
        target["QUEUE_MAX"] = float(value)
        states = ds.renormalised_states(target).astype(np.float64)
        col = states[:, QUEUE_FEATURE]
        # The band comes from THIS array, so it carries the same constants the
        # candidate is being judged under.
        stds = {j: float(states[:, j].std()) for j in MAGNITUDE_FEATURES}
        mine = stds[QUEUE_FEATURE]
        below = sum(1 for j, s in stds.items() if j != QUEUE_FEATURE and s < mine)
        rows.append({
            "queue_max": float(value),
            "is_current": int(abs(float(value) - float(live["QUEUE_MAX"])) < 1e-9),
            "frac_clipped": round(float((col >= 1.0).mean()), 5),
            "mean": round(float(col.mean()), 5),
            "std": round(mine, 5),
            "rank_among_magnitude": below + 1,
            "n_magnitude_features": len(MAGNITUDE_FEATURES),
            "percentile_below": round(100.0 * below / len(MAGNITUDE_FEATURES), 1),
            "percentile_inclusive": round(100.0 * (below + 1) / len(MAGNITUDE_FEATURES), 1),
            "n_distinct": int(np.unique(np.round(col, 6)).size),
        })
        print(f"QUEUE_MAX {value:5.1f}  clipped {rows[-1]['frac_clipped']:.5f}  "
              f"std {mine:.4f}  rank {rows[-1]['rank_among_magnitude']}/12  "
              f"pct_below {rows[-1]['percentile_below']:.1f}  "
              f"distinct {rows[-1]['n_distinct']}", flush=True)

    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, "queue_max_candidates.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    json_path = os.path.join(args.out_dir, "queue_max_candidates.json")
    with open(json_path, "w") as fh:
        json.dump({
            "dataset": os.path.abspath(args.dataset),
            "n_transitions": int(len(ds)),
            "constants_in_force": live,
            "magnitude_features": list(MAGNITUDE_FEATURES),
            "band_source": ("recomputed from the reconciled states of this same "
                            "dataset for every candidate, not read from a stored "
                            "m8 table"),
            "percentile_convention": ("percentile_below counts features with a "
                                      "strictly smaller std; percentile_inclusive "
                                      "counts the feature itself"),
        }, fh, indent=2, sort_keys=True, default=float)
    print(f"\n{csv_path}\n{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
