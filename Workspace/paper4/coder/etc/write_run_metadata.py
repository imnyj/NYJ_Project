#!/usr/bin/env python3
"""Record which code a run started from, next to the results that run produces.

WHY THIS EXISTS. The previous main training finished on 2026-09-03 at 11:38.
`src/divergence_guard.py` was first committed the same day at 15:37 -- four hours
after the run it was supposed to be watching had already ended. Nothing in the
outputs said so. It surfaced only because someone noticed that the progress CSV
header was missing the `run_status` column the current code writes, and worked
backwards from there. Building a safeguard and having a run actually use it are
two different events, and the artefacts recorded neither.

A commit hash alone is not enough here. Several sessions edit this tree at once,
so the hash names a state the working tree may not be in. `git status --porcelain`
is therefore recorded too, in full: which files differed from the commit is what
someone will need months later to decide whether a result is trustworthy.

The record also carries the settings that distinguish this run from the previous
one: the observation ceiling, whether the objective scores packet loss, and the
discount range. A directory called `hpo_parallel_v2` says only that it is not the
first attempt, and the commit says which code rather than how it was configured.

Written as `run_metadata.json` in each group's output directory, so a directory of
results carries its own provenance rather than depending on a log that may be
rotated away.

Usage:
    python etc/write_run_metadata.py --output-dir DIR --group g0 --gpu 0 \\
        --models PPO MADDPG-MT --n-trials 15 --seeds 1001 1002 1003 \\
        --sumo-dir DIR --log-path FILE
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
from typing import Any, Dict, List

CODER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO_DIR = "/home/imnyj"

#: Paths whose uncommitted state actually changes what a run computes. A dirty
#: notebook or a dirty log is noise; a dirty `src/` is the reason this file exists.
SIGNIFICANT_PREFIXES = ("Workspace/paper4/coder/src/", "Workspace/paper4/coder/etc/")


def _git(*args: str) -> str:
    """Run a git command in the repository, returning '' when it cannot be read."""
    try:
        out = subprocess.run(
            ["git", "-C", REPO_DIR, *args],
            capture_output=True, text=True, timeout=60, check=True,
        )
        return out.stdout.rstrip("\n")
    except (OSError, subprocess.SubprocessError):
        return ""


def porcelain_entries() -> List[Dict[str, str]]:
    """`git status --porcelain` split into status code and path.

    Kept as structured entries rather than one blob so a later reader can filter
    by path without reparsing. Renames keep their whole `old -> new` payload.
    """
    raw = _git("status", "--porcelain")
    entries: List[Dict[str, str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        entries.append({"status": line[:2].strip(), "path": line[3:]})
    return entries


def run_conditions() -> Dict[str, Any]:
    """The settings that distinguish this run from the previous one, read live.

    A commit hash says which code, not what that code was configured to do, and
    the directory name (`hpo_parallel_v2`) says only that it is not the first
    attempt. Someone comparing two result sets months from now needs the three
    things that actually changed: the observation ceiling that was saturating the
    contention feature, whether the objective scores packet loss or a constant,
    and the discount upper bound.

    Read out of the live code rather than restated here, and through the same
    helpers the pre-flight gate uses, so this record cannot claim one thing while
    the gate checks another. Every field degrades to None with a recorded reason
    rather than raising: a run must not fail to start because its provenance note
    could not be assembled.
    """
    conditions: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    sys.path.insert(0, CODER_DIR)
    sys.path.insert(0, os.path.join(CODER_DIR, "etc"))

    try:
        from src.rl_interface import N_ACTIVE_MAX_OBS
        conditions["n_active_max_obs"] = float(N_ACTIVE_MAX_OBS)
    except Exception as exc:  # noqa: BLE001
        conditions["n_active_max_obs"] = None
        errors["n_active_max_obs"] = f"{type(exc).__name__}: {exc}"

    try:
        import preflight_hpo as pf
        from src.hpo import compute_composite_objective

        literals, visited = pf._reachable_code_literals(compute_composite_objective)
        conditions["objective_reads_packet_loss_rate"] = "packet_loss_rate" in literals
        conditions["objective_functions_read"] = visited

        base = {"mean_error": 1.0, "mean_aoi": 1.0, "avg_power_norm": 0.5,
                "packet_loss_rate": 0.0}
        low = float(compute_composite_objective(base))
        high = float(compute_composite_objective(dict(base, packet_loss_rate=0.30)))
        # The static read says the key is mentioned; this says the score moves.
        conditions["objective_delta_for_loss_0_to_0p30"] = round(high - low, 6)
    except Exception as exc:  # noqa: BLE001
        conditions["objective_reads_packet_loss_rate"] = None
        errors["objective"] = f"{type(exc).__name__}: {exc}"

    try:
        import preflight_hpo as pf
        ranges = pf._gamma_ranges(os.path.join(CODER_DIR, "src", "hpo.py"))
        bounds = sorted({(lo, hi) for _, lo, hi in ranges}, key=str)
        conditions["gamma_search_ranges"] = [{"low": lo, "high": hi} for lo, hi in bounds]
        conditions["gamma_sites"] = len(ranges)
        conditions["gamma_uniform_across_models"] = len(bounds) == 1
        if len(bounds) == 1 and isinstance(bounds[0][1], (int, float)):
            hi = float(bounds[0][1])
            conditions["gamma_high"] = hi
            conditions["gamma_effective_horizon_decisions"] = (
                round(1.0 / (1.0 - hi), 1) if hi < 1.0 else None
            )
    except Exception as exc:  # noqa: BLE001
        conditions["gamma_search_ranges"] = None
        errors["gamma"] = f"{type(exc).__name__}: {exc}"

    if errors:
        conditions["read_errors"] = errors
    return conditions


def collect(args: argparse.Namespace) -> Dict[str, Any]:
    entries = porcelain_entries()
    significant = [
        e for e in entries
        if any(e["path"].startswith(p) for p in SIGNIFICANT_PREFIXES)
    ]
    head = _git("rev-parse", "HEAD")
    return {
        "launched_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "git": {
            "commit": head,
            "commit_short": head[:8],
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "commit_date": _git("log", "-1", "--format=%cI"),
            "commit_subject": _git("log", "-1", "--format=%s"),
            "working_tree_clean": not entries,
            "uncommitted_count": len(entries),
            "uncommitted": [f"{e['status']} {e['path']}" for e in entries],
            "uncommitted_in_code_paths": [f"{e['status']} {e['path']}" for e in significant],
            "code_paths_watched": list(SIGNIFICANT_PREFIXES),
        },
        "conditions": run_conditions(),
        "run": {
            "group": args.group,
            "gpu": args.gpu,
            "models": args.models,
            "n_trials": args.n_trials,
            "seeds": args.seeds,
            "output_dir": args.output_dir,
            "sumo_dir": args.sumo_dir,
            "log_path": args.log_path,
            "python": sys.executable,
            "coder_dir": CODER_DIR,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--group", required=True)
    ap.add_argument("--gpu", default="")
    ap.add_argument("--models", nargs="*", default=[])
    ap.add_argument("--n-trials", type=int, default=0)
    ap.add_argument("--seeds", nargs="*", default=[])
    ap.add_argument("--sumo-dir", default="")
    ap.add_argument("--log-path", default="")
    ap.add_argument("--stdout", action="store_true", help="print the record instead of writing it")
    args = ap.parse_args()

    record = collect(args)
    if args.stdout:
        print(json.dumps(record, indent=2))
        return 0

    os.makedirs(args.output_dir, exist_ok=True)
    path = os.path.join(args.output_dir, "run_metadata.json")
    with open(path, "w") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")

    git, cond = record["git"], record["conditions"]
    state = "clean" if git["working_tree_clean"] else f"{git['uncommitted_count']} uncommitted"
    print(f"  {args.group}: commit {git['commit_short']} ({state}) -> {path}")
    print(f"      n_active_max_obs={cond.get('n_active_max_obs')} "
          f"objective_reads_loss={cond.get('objective_reads_packet_loss_rate')} "
          f"gamma_high={cond.get('gamma_high')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
