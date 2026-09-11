#!/usr/bin/env python3
"""Merge the per-group HPO outputs back into one `results/hpo/` directory.

`etc/run_hpo_parallel.sh` splits the nine studies across GPUs, and each group
writes its own `optuna_best_params.csv` holding only the models it ran. This
puts them back together so the rest of the pipeline -- `run_all.py`, which reads
one master CSV -- sees exactly what a serial run would have produced.

The merge refuses rather than guesses in two cases: a model that no group
produced, and a model that two groups both claim. Silently accepting either
would hand training a CSV that is missing a baseline or holds an arbitrary one
of two answers, and neither failure announces itself later.

Usage:
    python etc/merge_hpo_results.py            # merge, refuse on any problem
    python etc/merge_hpo_results.py --dry-run  # report what would be merged
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import sys

import pandas as pd

CODER_DIR = "/home/imnyj/Workspace/paper4/coder"
PARALLEL_ROOT = os.path.join(CODER_DIR, "results", "hpo_parallel")
TARGET_DIR = os.path.join(CODER_DIR, "results", "hpo")
BACKUP_ROOT = "/home/imnyj/Workspace/paper4/backup"

#: The nine baselines the master CSV must end up describing. Imported rather
#: than retyped so a change to the registry cannot silently shrink this check.
sys.path.insert(0, CODER_DIR)
from src.baselines import ALL_BASELINES  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    group_csvs = sorted(glob.glob(os.path.join(PARALLEL_ROOT, "*", "optuna_best_params.csv")))
    if not group_csvs:
        print(f"no group results under {PARALLEL_ROOT}", file=sys.stderr)
        return 1

    frames = []
    origin: dict[str, str] = {}
    duplicates: list[str] = []
    for path in group_csvs:
        group = os.path.basename(os.path.dirname(path))
        df = pd.read_csv(path)
        for name in df["model_name"]:
            if name in origin:
                duplicates.append(f"{name}: {origin[name]} and {group}")
            origin[name] = group
        frames.append(df)
        print(f"{group}: {len(df)} model(s) -- {', '.join(map(str, df['model_name']))}")

    merged = pd.concat(frames, ignore_index=True)
    missing = [m for m in ALL_BASELINES if m not in set(merged["model_name"])]

    if duplicates:
        print("\nREFUSING: the same model came from more than one group:", file=sys.stderr)
        for d in duplicates:
            print(f"  {d}", file=sys.stderr)
        return 1
    if missing:
        print(f"\nREFUSING: no group produced {missing}. Check their logs -- a group "
              "that crashed leaves the others looking complete.", file=sys.stderr)
        return 1

    # Order the rows the way the registry orders the baselines, so the master CSV
    # reads the same regardless of which group finished first.
    merged["_order"] = merged["model_name"].map({n: i for i, n in enumerate(ALL_BASELINES)})
    merged = merged.sort_values("_order").drop(columns="_order")

    trial_csvs = sorted(glob.glob(os.path.join(PARALLEL_ROOT, "*", "optuna_trials_*.csv")))
    print(f"\nmerged: {len(merged)} models, {len(trial_csvs)} trial file(s)")

    if args.dry_run:
        print("(dry run -- nothing written)")
        return 0

    os.makedirs(TARGET_DIR, exist_ok=True)
    stamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    stale = os.path.join(BACKUP_ROOT, f"hpo_pre_merge_{stamp}")
    existing = glob.glob(os.path.join(TARGET_DIR, "optuna_*.csv"))
    if existing:
        os.makedirs(stale, exist_ok=True)
        for p in existing:
            shutil.move(p, os.path.join(stale, os.path.basename(p)))
        print(f"previous CSVs moved to {stale}")

    for p in trial_csvs:
        shutil.copy2(p, os.path.join(TARGET_DIR, os.path.basename(p)))
    out = os.path.join(TARGET_DIR, "optuna_best_params.csv")
    merged.to_csv(out, index=False)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
