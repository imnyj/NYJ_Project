"""Merge the sharded gamma sweep and reduce it over seeds.

`etc/scripts/run_gamma_ablation_v2.sh` runs one process per (model, seed) and
each writes its own CSV, so the sweep arrives as six files with identical
columns. This script concatenates them in a fixed order -- model, then gamma
descending, then seed -- so the merged file reads as a sweep rather than as
whatever order the shards happened to finish in.

The reduction exists because the question the sweep was run to answer is not
"which arm scored best" but "is the gap between arms larger than the gap between
seeds". A per-condition table cannot show that; a table carrying the mean and the
sample standard deviation across the three seeds can. The standard deviation uses
the n-1 denominator, so with three seeds it is an estimate of the seed-to-seed
spread and not a description of the three numbers in hand.

No verdict is computed here and none should be added. The reduced numbers go to
whoever decides the HPO search range.
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import statistics
from typing import Any, Dict, List

#: Columns reduced across seeds. Everything the discount decision is read from,
#: plus the two divergence counters, which are summed instead of averaged
#: further down because a mean of failure counts hides which seed failed.
MEAN_COLUMNS: List[str] = [
    "composite_score",
    "mean_error",
    "mean_aoi",
    "mean_recent_loss",
    "packet_loss_rate",
    "coverage_outage_rate",
    "avg_tx_power_dbm",
    "mean_cbr",
    "wall_s",
]

#: Divergence evidence. Reported as totals and worst-cases across the seed group,
#: never as means: "0.33 diverged runs" is not a fact about anything.
SUMMARY_FIELDS: List[str] = (
    ["model", "arm", "gamma", "effective_horizon_s", "n_seeds", "seeds"]
    + [f"{c}_{stat}" for c in MEAN_COLUMNS for stat in ("mean", "std")]
    + ["n_diverged", "n_update_failures_total", "max_consecutive_nonfinite_losses_max"]
)


def _read_shards(shard_root: str) -> List[Dict[str, str]]:
    paths = sorted(glob.glob(os.path.join(shard_root, "*.csv")))
    if not paths:
        raise SystemExit(f"no shard CSVs under {shard_root}")
    rows: List[Dict[str, str]] = []
    header: List[str] = []
    for path in paths:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise SystemExit(f"{path} has no header")
            if not header:
                header = list(reader.fieldnames)
            elif list(reader.fieldnames) != header:
                raise SystemExit(
                    f"{path} has a different column set from the first shard; "
                    f"refusing to merge files that are not the same measurement"
                )
            for row in reader:
                row["_shard"] = os.path.basename(path)
                rows.append(row)
    return rows


def _sort_key(row: Dict[str, str]):
    # Gamma descending puts the selected value first and the sweep reads
    # top-down from the longest horizon to the shortest.
    return (row["model"], -float(row["gamma"]), int(row["seed"]))


def _mean_std(values: List[float]):
    mean = statistics.fmean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return mean, std


def _as_bool(text: str) -> bool:
    return str(text).strip().lower() in ("true", "1", "yes")


def summarize(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    groups: Dict[Any, List[Dict[str, str]]] = {}
    for row in rows:
        groups.setdefault((row["model"], row["arm"], row["gamma"]), []).append(row)

    out: List[Dict[str, Any]] = []
    for (model, arm, gamma), group in groups.items():
        group = sorted(group, key=lambda r: int(r["seed"]))
        summary: Dict[str, Any] = {
            "model": model,
            "arm": arm,
            "gamma": float(gamma),
            "effective_horizon_s": float(group[0]["effective_horizon_s"]),
            "n_seeds": len(group),
            "seeds": " ".join(r["seed"] for r in group),
        }
        for column in MEAN_COLUMNS:
            values = [float(r[column]) for r in group if r.get(column) not in (None, "")]
            if len(values) != len(group):
                # A blank in a reduced column means a condition did not produce
                # the number; averaging what is left would quietly change what
                # the row is the mean of.
                summary[f"{column}_mean"] = ""
                summary[f"{column}_std"] = ""
                continue
            mean, std = _mean_std(values)
            summary[f"{column}_mean"] = round(mean, 6)
            summary[f"{column}_std"] = round(std, 6)
        summary["n_diverged"] = sum(1 for r in group if _as_bool(r["diverged"]))
        summary["n_update_failures_total"] = sum(int(r["n_update_failures"]) for r in group)
        summary["max_consecutive_nonfinite_losses_max"] = max(
            int(r["max_consecutive_nonfinite_losses"]) for r in group
        )
        out.append(summary)

    out.sort(key=lambda s: (s["model"], -s["gamma"]))
    return out


def _write(path: str, fields: List[str], rows: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print("WROTE", path, flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard-root", required=True)
    ap.add_argument("--merged-out", required=True)
    ap.add_argument("--summary-out", required=True)
    a = ap.parse_args()

    rows = _read_shards(a.shard_root)
    rows.sort(key=_sort_key)
    merged_fields = [k for k in rows[0] if k != "_shard"] + ["shard"]
    for row in rows:
        row["shard"] = row.pop("_shard")
    _write(a.merged_out, merged_fields, rows)

    summary = summarize(rows)
    _write(a.summary_out, SUMMARY_FIELDS, summary)

    print(f"{len(rows)} conditions, {len(summary)} (model, gamma) groups", flush=True)
    for s in summary:
        print(
            f"{s['model']:<10} gamma={s['gamma']:<20} "
            f"composite={s['composite_score_mean']} +/- {s['composite_score_std']}  "
            f"err={s['mean_error_mean']} +/- {s['mean_error_std']}  "
            f"aoi={s['mean_aoi_mean']} +/- {s['mean_aoi_std']}  "
            f"loss={s['mean_recent_loss_mean']} +/- {s['mean_recent_loss_std']}  "
            f"diverged={s['n_diverged']}/{s['n_seeds']} "
            f"update_failures={s['n_update_failures_total']} "
            f"max_nonfinite={s['max_consecutive_nonfinite_losses_max']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
