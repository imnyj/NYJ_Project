#!/usr/bin/env python
# etc/scripts/compare_road_scheme_datasets.py
# ============================================================================
# HOW MUCH DID CHANGING THE ROAD SCHEME ACTUALLY MOVE THE DATA?
#
# ---------------------------------------------------------------------------
# THE QUESTION
# ---------------------------------------------------------------------------
# The HOORL offline dataset was collected twice on 2026-09-06 under two
# different rules for choosing the road network:
#
#   * PER-CELL RESEED (the first collection). `prepare_scenario` was called once
#     per (density, seed) cell with the FLOW seed, so the road was a function of
#     the traffic seed and the sequence matched no training run.
#   * ROAD CYCLE (the second). The road is `road_seed(density, cycle)` with
#     `cycle = cell_index // len(densities)`, the same expression the trainer
#     uses for its episodes, so cell i runs on the road training episode i runs
#     on.
#
# The second is the correct one and the first was discarded. But "the roads were
# different" is a statement about the generator, not about the data, and offline
# reinforcement learning cares about the latter: what matters is whether the
# STATE DISTRIBUTION the learner pre-trains on moved. This measures that.
#
# ---------------------------------------------------------------------------
# WHY THE ANSWER NEEDS TWO CONTROLS
# ---------------------------------------------------------------------------
# A distance between two samples is meaningless alone. Both controls come from
# `src/hoorl_offline_stats.py` and both are computed here at the sample sizes
# actually used:
#
#   * the SPLIT-HALF FLOOR -- what one sample scores against itself purely from
#     being finite. A distance below it is indistinguishable from noise.
#   * the DENSITY-5-TO-35 REFERENCE SHIFT -- the largest covariate shift the
#     experiment already contains and already handles. Expressing the road
#     difference as a fraction of it turns an abstract number into a claim a
#     reader can act on.
#
# A road difference that lands below the floor would mean the first collection
# was not, in the end, measurably different data -- which would be worth knowing
# and is not the same as saying the scheme did not need fixing. The scheme needed
# fixing because the offline and online halves must be the same MDP by
# construction, not because a distance happened to be large.
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

DATA = "/home/imnyj/Workspace/paper4/data/hoorl_offline"


def _states_by_density(npz_path: str, meta_path: str) -> Dict[float, np.ndarray]:
    """Split a dataset's state matrix into per-density blocks.

    The rows carry no density column, so the per-episode transition counts in the
    metadata give the contiguous block each cell contributed, in the metadata's
    own order. The total is asserted against the array length: if the two ever
    disagree the split is silently wrong, and every per-density number after it
    would describe the wrong rows.
    """
    from src.hoorl_offline_stats import _as_states

    with np.load(npz_path) as data:
        states = _as_states(np.asarray(data["state"], dtype=np.float64))
    meta = json.load(open(meta_path))
    out: Dict[float, List[np.ndarray]] = {}
    off = 0
    for rec in meta["per_episode"]:
        k = int(rec["transitions"])
        if k:
            out.setdefault(float(rec["density"]), []).append(states[off:off + k])
        off += k
    if off != states.shape[0]:
        raise ValueError(
            f"{npz_path}: per_episode transitions sum to {off} but the state array "
            f"has {states.shape[0]} rows; the per-density split would be wrong."
        )
    return {d: np.concatenate(v, axis=0) for d, v in out.items()}


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--new", default=os.path.join(DATA, "hoorl_offline.npz"))
    p.add_argument("--old", default=os.path.join(
        DATA, "hoorl_offline_percell_reseed_20260906.npz"))
    p.add_argument("--subsample", type=int, default=4000,
                   help="rows drawn from each sample; the floor is measured at "
                        "the same size, because it grows as the sample shrinks")
    p.add_argument("--out-dir", type=str,
                   default=os.path.join(ROOT, "results", "hoorl_offline"))
    args = p.parse_args(argv)

    from src.hoorl_offline_stats import DISTANCE_SPEC, comparison_report

    rng = np.random.default_rng(0)

    def draw(a: np.ndarray, n: int) -> np.ndarray:
        if a.shape[0] <= n:
            return a
        return a[rng.choice(a.shape[0], n, replace=False)]

    new_meta = os.path.splitext(args.new)[0] + ".meta.json"
    old_meta = os.path.splitext(args.old)[0] + ".meta.json"
    new_by_d = _states_by_density(args.new, new_meta)
    old_by_d = _states_by_density(args.old, old_meta)

    samples: Dict[str, np.ndarray] = {
        "new_all": draw(np.concatenate(list(new_by_d.values())), args.subsample),
        "old_all": draw(np.concatenate(list(old_by_d.values())), args.subsample),
    }
    pairs = [("old_all", "new_all")]
    # The reference shift is taken WITHIN the new dataset, so the unit is a
    # property of the data being kept rather than of the data being discarded.
    lo, hi = min(new_by_d), max(new_by_d)
    samples[f"new_d{lo:g}"] = draw(new_by_d[lo], args.subsample)
    samples[f"new_d{hi:g}"] = draw(new_by_d[hi], args.subsample)
    reference_pair = (f"new_d{lo:g}", f"new_d{hi:g}")
    pairs.append(reference_pair)
    # Per density, so a difference concentrated in one part of the grid is not
    # averaged away by the pooled comparison.
    for d in sorted(set(new_by_d) & set(old_by_d)):
        samples[f"old_d{d:g}"] = draw(old_by_d[d], args.subsample)
        if f"new_d{d:g}" not in samples:
            samples[f"new_d{d:g}"] = draw(new_by_d[d], args.subsample)
        pairs.append((f"old_d{d:g}", f"new_d{d:g}"))

    report = comparison_report(samples, pairs, reference_pair=reference_pair,
                               floor_on="new_all")
    report["distance_spec"] = DISTANCE_SPEC
    report["subsample"] = int(args.subsample)
    report["new_dataset"] = os.path.abspath(args.new)
    report["old_dataset"] = os.path.abspath(args.old)
    report["what_differs"] = (
        "Both collections used the same behaviour policy, the same Delta band "
        "[0.5, 10] s, the same density grid and the same flow seeds. The ONLY "
        "difference is which road network each cell ran on: the old one reseeded "
        "per cell with the flow seed, the new one uses road_seed(density, cycle) "
        "and therefore matches the roads of training episodes 0..20."
    )

    os.makedirs(args.out_dir, exist_ok=True)
    json_path = os.path.join(args.out_dir, "road_scheme_dataset_distance.json")
    with open(json_path, "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True, default=float)
    rows = report.get("pairs") or report.get("rows") or []
    if rows:
        csv_path = os.path.join(args.out_dir, "road_scheme_dataset_distance.csv")
        keys: List[str] = []
        for r in rows:
            for k in r:
                if k not in keys:
                    keys.append(k)
        with open(csv_path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in keys})
        print(f"{csv_path}")
    print(json.dumps(report, indent=2, sort_keys=True, default=float)[:4000])
    print(f"\n{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
