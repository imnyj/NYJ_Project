#!/usr/bin/env python
# etc/scripts/measure_bound_candidates.py
# ============================================================================
# WHAT EACH CANDIDATE NORMALISATION BOUND DOES TO THE DATA.
#
# ---------------------------------------------------------------------------
# WHY A TABLE AND NOT A RULE
# ---------------------------------------------------------------------------
# Raising a clipping bound is a trade with two sides and no formula that settles
# it. Raising `N_ACTIVE_MAX_OBS` removes the samples piled at 1.0 -- 9.31 % of
# this collection -- and in exchange compresses every other sample into a
# narrower part of [0, 1]. Which side wins depends on whether the clipped region
# is one the policy needs to act differently in, and that is not knowable from
# the data alone.
#
# So this produces both sides for each candidate and leaves the choice to a
# reader who can see them together. It applies no rule and recommends nothing.
#
# ---------------------------------------------------------------------------
# WHY IT COSTS ALMOST NOTHING
# ---------------------------------------------------------------------------
# Because the dataset stores the pre-normalisation values. Every row here is
# produced by re-reading one collection through
# `rl_interface.renormalise_states` -- the same function the training path uses
# -- rather than by collecting once per candidate. Before the raw columns existed
# this table would have cost twenty minutes of SUMO per row.
#
# ---------------------------------------------------------------------------
# WHAT THE COLUMNS MEAN
# ---------------------------------------------------------------------------
#   frac_clipped      what fraction of samples the bound destroys
#   mean, std         where the surviving distribution sits and how wide it is
#   std_over_used     variation INSIDE the occupied span -- the measure that
#                     decides whether a feature is informative, as distinct from
#                     whether it uses its whole nominal range
#   n_distinct        resolution actually available to a network
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

#: (constant, observation feature, candidate values). The candidates bracket the
#: current value and the measured maximum rather than exploring freely: a bound
#: below the maximum clips, one far above it wastes range, and the interesting
#: region is between.
#: EVERY constant that normalises a feature is swept, not only the ones already
#: suspected of clipping. Three were found to clip by looking; the rest were
#: assumed not to, and "assumed not to" is the judgement that has failed most
#: often in this project -- `N_ACTIVE_MAX_OBS` was a literal 100 believed
#: settled, `CBR_REF` was 0.25 believed settled, and `QUEUE_MAX` was classified
#: as a code constant and therefore never examined until this table was widened.
#: Each row costs a re-read of one file, so there is no reason to sample.
#:
#: Where a constant serves several features the FIRST is swept and the others
#: move with it; they share a divisor, so a candidate that suits one and not the
#: others is a reason to split the constant rather than to pick between them.
CANDIDATES: Dict[str, Any] = {
    "N_ACTIVE_MAX_OBS": {"feature": 13,
                         "values": [168.0, 200.0, 220.0, 250.0, 300.0, 400.0]},
    "DIST_TO_STOPLINE_REF_M": {"feature": 12,
                               "values": [300.0, 600.0, 900.0, 1200.0]},
    "QUEUE_MAX": {"feature": 15, "values": [10.0, 20.0, 30.0, 40.0, 50.0]},
    "A_MAX": {"feature": 4, "values": [3.0, 5.0, 8.0, 10.0]},
    "V_MAX_OBS": {"feature": 3, "values": [12.0, 15.912, 18.0, 22.0]},
    "E_REF": {"feature": 0, "values": [6.0, 13.26, 20.0, 30.0]},
    "PHASE_REMAINING_REF_S": {"feature": 11, "values": [45.0, 60.0, 90.0, 120.0]},
    "RSU_RANGE": {"feature": 7, "values": [200.0, 300.0, 400.0, 600.0]},
}


def profile(col: np.ndarray) -> Dict[str, Any]:
    """Where a candidate bound leaves the feature.

    `frac_clipped` is tested on the MAGNITUDE. It used to read `col >= 1.0`, and
    on the four signed features -- acceleration [4], the velocity pair [1, 2] and
    the relative position pair [5, 6] -- that only ever saw the positive end.
    Acceleration is the case where it mattered: braking is the large-magnitude
    side of that distribution, SUMO's emergency manoeuvre decelerates at 9.0 m/s2
    against an `A_MAX` of 5.0, and every clipped sample was therefore negative and
    invisible. The table reported 0.0 clipped for `A_MAX` at every candidate down
    to 3.0, which is what a bound table exists to disprove.
    """
    used = float(col.max() - col.min())
    return {
        "frac_clipped": round(float((np.abs(col) >= 1.0).mean()), 5),
        "frac_clipped_positive": round(float((col >= 1.0).mean()), 5),
        "frac_clipped_negative": round(float((col <= -1.0).mean()), 5),
        "frac_at_zero": round(float((col <= 0.0).mean()), 5),
        "mean": round(float(col.mean()), 5),
        "std": round(float(col.std()), 5),
        "used_span": round(used, 5),
        "std_over_used": round(float(col.std() / used), 4) if used > 0 else 0.0,
        "n_distinct": int(np.unique(np.round(col, 6)).size),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", default=DEFAULT_DATASET)
    p.add_argument("--out-dir", default=os.path.join(ROOT, "results", "hoorl_offline"))
    args = p.parse_args(argv)

    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    from src.hoorl_offline import OfflineDataset
    from src.rl_interface import observation_constants_live

    ds = OfflineDataset.load(os.path.abspath(args.dataset))
    if not ds.metadata.get("contents_manifest", {}).get("has_raw_columns"):
        raise SystemExit(
            f"{args.dataset} has no raw columns, so a bound cannot be re-applied "
            "without recollecting. This table is only cheap on a format-3 file.")
    live = observation_constants_live()

    rows: List[Dict[str, Any]] = []
    for constant, spec in CANDIDATES.items():
        j = int(spec["feature"])
        for value in spec["values"]:
            target = dict(live)
            target[constant] = float(value)
            states = ds.renormalised_states(target)
            row = {"constant": constant, "feature": j, "candidate": float(value),
                   "is_current": int(abs(float(value) - float(live[constant])) < 1e-9)}
            row.update(profile(states[:, j].astype(np.float64)))
            rows.append(row)
            print(f"{constant:24s} = {value:8.1f}  feature[{j:2d}]  "
                  f"clipped {row['frac_clipped']:.5f}  mean {row['mean']:.4f}  "
                  f"std {row['std']:.4f}  std/used {row['std_over_used']:.4f}  "
                  f"distinct {row['n_distinct']}", flush=True)

    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, "bound_candidates.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    meta = {
        "dataset": os.path.abspath(args.dataset),
        "n_transitions": int(len(ds)),
        "current_constants": live,
        "road_cycles_in_dataset": sorted({int(r.get("road_cycle") or 0)
                                          for r in ds.metadata["per_episode"]}),
        "coverage_caveat": (
            "This collection visited road cycles 0-2 while training walks 0-14, "
            "so a bound chosen to just clear the maximum here will be exceeded on "
            "roads this table never saw. Read it together with the fifteen-cycle "
            "n_active measurement, which is what says how much headroom the "
            "unseen roads require."),
        "no_recommendation": (
            "No candidate is marked preferred. The trade has two sides -- samples "
            "destroyed against resolution lost -- and which matters depends on "
            "whether the clipped region needs different behaviour, which this "
            "data cannot answer."),
    }
    json_path = os.path.join(args.out_dir, "bound_candidates.json")
    with open(json_path, "w") as fh:
        json.dump(meta, fh, indent=2, sort_keys=True, default=float)
    print(f"\n{csv_path}\n{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
