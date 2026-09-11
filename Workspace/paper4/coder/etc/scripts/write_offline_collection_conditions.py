#!/usr/bin/env python
# etc/scripts/write_offline_collection_conditions.py
# ============================================================================
# THE COLLECTION CONDITIONS, DERIVED FROM THE DATASET RATHER THAN RESTATED.
#
# ---------------------------------------------------------------------------
# WHY THIS IS A SCRIPT AND NOT A DOCUMENT SOMEBODY WRITES
# ---------------------------------------------------------------------------
# The conditions a dataset was collected under -- the behaviour policy, the Delta
# band, the density mix, the seeds, the observation normalisers, the commit --
# have to be recorded, and the obvious way to record them is to type them into a
# file next to the data. That file is then a SECOND claim about the collection,
# maintained by hand, and the moment a re-collection changes anything the two
# disagree with no way to tell which is right.
#
# So this reads the dataset's own metadata and the arrays themselves, and emits
# the conditions in the flat forms a reader or a table wants. Nothing here is
# typed in. If the dataset is recollected, rerunning this is the whole update,
# and a figure that quotes a number from these files is quoting the data.
#
# The one thing it adds beyond transcription is the DELTA COVERAGE table, which
# is a property of the collected rows rather than of the arguments: a band was
# requested, and what the environment actually delivered inside it is a separate
# question with a separate answer.
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

N_DELTA_BINS: int = 12


def flatten(prefix: str, value: Any, out: List[Dict[str, str]]) -> None:
    """One row per leaf, so a nested metadata tree becomes a readable table."""
    if isinstance(value, dict):
        for key in sorted(value):
            flatten(f"{prefix}.{key}" if prefix else str(key), value[key], out)
    elif isinstance(value, (list, tuple)) and value and isinstance(value[0], dict):
        for i, item in enumerate(value):
            flatten(f"{prefix}[{i}]", item, out)
    else:
        out.append({"key": prefix, "value": json.dumps(value, default=str)})


def delta_coverage(delta_t: np.ndarray, lo: float, hi: float) -> List[Dict[str, Any]]:
    """What the collection actually delivered along the Delta axis.

    Binned on the MEASURED interval, so an interval that was requested at 8 s and
    closed at 2 s because the vehicle left coverage counts as a 2 s sample. The
    edges span the delivered range rather than the requested band, since
    finalisation at the episode boundary and early range exits both put samples
    outside it and pretending otherwise would hide them.
    """
    lo_e = max(1e-6, min(float(lo), float(delta_t.min())))
    hi_e = max(float(hi), float(delta_t.max()))
    edges = np.geomspace(lo_e, hi_e, N_DELTA_BINS + 1)
    idx = np.clip(np.digitize(delta_t, edges) - 1, 0, N_DELTA_BINS - 1)
    rows: List[Dict[str, Any]] = []
    for b in range(N_DELTA_BINS):
        m = idx == b
        rows.append({
            "bin": b,
            "delta_lo_s": float(edges[b]),
            "delta_hi_s": float(edges[b + 1]),
            "n": int(m.sum()),
            "fraction": float(m.mean()),
            "inside_requested_band": int(edges[b] >= lo * 0.999 and edges[b + 1] <= hi * 1.001),
        })
    return rows


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", required=True, help="path to the collected npz")
    p.add_argument("--out-dir", type=str,
                   default=os.path.join(ROOT, "results", "hoorl_offline"))
    args = p.parse_args(argv)

    from src.hoorl_offline import OfflineDataset
    from src.hoorl_offline_synthetic import is_synthetic

    dataset = OfflineDataset.load(os.path.abspath(args.dataset))
    meta = dataset.metadata
    if is_synthetic(meta):
        raise SystemExit(
            "this is the SYNTHETIC test fixture. Its 'conditions' would describe "
            "manufactured numbers and must not be written next to real results."
        )

    os.makedirs(args.out_dir, exist_ok=True)

    rows: List[Dict[str, str]] = []
    flatten("", meta, rows)
    cond_path = os.path.join(args.out_dir, "collection_conditions.csv")
    with open(cond_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["key", "value"])
        w.writeheader()
        w.writerows(rows)

    per_ep = meta.get("per_episode", [])
    cell_path = os.path.join(args.out_dir, "collection_cells.csv")
    if per_ep:
        fields = sorted({k for rec in per_ep for k in rec})
        with open(cell_path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(per_ep)

    band = meta.get("behaviour_policy", {}).get("delta_band", [0.5, 10.0])
    delta_t = np.asarray(dataset.arrays["delta_t"], dtype=np.float64)
    cov = delta_coverage(delta_t, float(band[0]), float(band[1]))
    cov_path = os.path.join(args.out_dir, "collection_delta_coverage.csv")
    with open(cov_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cov[0]))
        w.writeheader()
        w.writerows(cov)

    inside = float(((delta_t >= float(band[0]) * 0.999) &
                    (delta_t <= float(band[1]) * 1.001)).mean())
    summary = {
        "dataset": os.path.abspath(args.dataset),
        "n_transitions": int(len(dataset)),
        "state_dim": int(dataset.state_dim),
        "requested_delta_band_s": [float(band[0]), float(band[1])],
        "delivered_delta_min_s": float(delta_t.min()),
        "delivered_delta_max_s": float(delta_t.max()),
        "delivered_delta_geomean_s": float(math.exp(np.log(delta_t).mean())),
        "fraction_inside_requested_band": inside,
        "coverage_complete": bool(meta.get("coverage_complete", False)),
        "transitions_by_density": meta.get("transitions_by_density"),
        "observation_constants": meta.get("observation_constants"),
        "observation_constant_drift_between_cells":
            meta.get("observation_constant_drift_between_cells"),
        "git": meta.get("git"),
        "wall_clock_s": meta.get("wall_clock_s"),
        "npz_bytes": os.path.getsize(os.path.abspath(args.dataset)),
    }
    json_path = os.path.join(args.out_dir, "collection_conditions.json")
    with open(json_path, "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True, default=str)

    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    print(f"\n{cond_path}\n{cell_path}\n{cov_path}\n{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
