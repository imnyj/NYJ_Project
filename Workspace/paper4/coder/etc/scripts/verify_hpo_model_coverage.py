"""Do the launcher's groups schedule exactly the registry, and what space does each get?

Two questions, because the failure of 2026-09-05 needed both to be answered and
only the first was being asked anywhere.

  1. SET EQUALITY, not membership. `etc/preflight_hpo.py` already reports a name
     that is scheduled but absent from the registry, and a registry name that is
     scheduled by no group. This script states the comparison as one set equality
     so the two directions cannot be read separately and one of them forgotten:
     the launcher's group list and `src.baselines.ALL_BASELINES` must be the same
     set. On 2026-09-06 they were not. `etc/run_hpo_parallel.sh` still listed
     CARLTON, which had been replaced in the registry by HOORL, so the run would
     have tuned a model that no longer exists and never tuned one that does.

  2. HOW BIG A SEARCH SPACE each name actually receives. This is the part nothing
     was checking, and it is what made the first failure silent rather than loud.
     `sample_hparams` used to end in a catch-all that handed any unrecognised
     name a three-key space (`lr`, `hidden_dim`, `gamma`). A model that should
     search seven keys searched three, completed its trials, and wrote a normal
     looking row. `assert_hparams_reach_model` could not catch it either, since
     all three keys do reach the constructor. Printing the count per name makes a
     three next to a seven visible at a glance.

Read-only. Nothing here launches a study, edits the launcher or writes to the
results tree; the group list is parsed out of the shell script as text. Output
goes to `results/hpo/model_coverage_check.csv` unless `--out` says otherwise.

Exit status is 0 when the sets match and every scheduled name gets a real search
space, 1 otherwise, so it can gate a launcher.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import optuna  # noqa: E402

from src.baselines import ALL_BASELINES  # noqa: E402
from src.hpo import normalize_model_name, sample_hparams  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_LAUNCHER = os.path.join(ROOT, "etc", "run_hpo_parallel.sh")
DEFAULT_OUT = os.path.join(ROOT, "results", "hpo", "model_coverage_check.csv")

#: The catch-all space that used to absorb unrecognised names. Kept as a number
#: so the report can say "this is the size of the space that meant nothing was
#: really being tuned" rather than leaving the reader to recognise it.
CATCH_ALL_SPACE_SIZE = 3


def parse_group_models(path: str) -> List[str]:
    """The GROUP_MODELS bash array, as one list of specs.

    Parsed rather than sourced: running the launcher to ask it what it would run
    is the one thing this check must not do.
    """
    with open(path) as fh:
        text = fh.read()
    match = re.search(r"^GROUP_MODELS=\((.*?)^\)", text, re.MULTILINE | re.DOTALL)
    if match is None:
        raise ValueError(
            f"no GROUP_MODELS=( ... ) array in {path}. If the launcher stopped "
            "declaring its models that way, this check is reading the wrong place "
            "and must be pointed at the new one rather than deleted."
        )
    return re.findall(r'"([^"]*)"', match.group(1))


def search_space_size(name: str) -> Tuple[Any, str]:
    """(number of keys, note) for one model name, without running a rollout.

    A name that `sample_hparams` refuses is reported as the refusal, not as a
    crash: refusing is the correct behaviour for an unknown name and the report
    has to be able to say so for every name at once.
    """
    study = optuna.create_study(
        sampler=optuna.samplers.RandomSampler(seed=0), direction="minimize"
    )
    trial = study.ask()
    try:
        params = sample_hparams(trial, name)
    except Exception as exc:  # noqa: BLE001
        return "", f"{type(exc).__name__}: {exc}"
    n = len(params)
    note = ""
    if n <= CATCH_ALL_SPACE_SIZE and sorted(params) == ["gamma", "hidden_dim", "lr"]:
        note = (
            f"exactly the {CATCH_ALL_SPACE_SIZE}-key catch-all space "
            "(lr, hidden_dim, gamma); this name is not being tuned as itself"
        )
    return n, note


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--launcher", default=DEFAULT_LAUNCHER)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    groups = parse_group_models(args.launcher)
    scheduled: List[str] = []
    for spec in groups:
        scheduled.extend(spec.split())
    registry = list(ALL_BASELINES)

    print(f"launcher : {args.launcher}")
    for i, spec in enumerate(groups):
        print(f"  g{i}: {spec}")
    print(f"registry : {', '.join(registry)}")
    print()

    rows: List[Dict[str, Any]] = []
    for name in sorted(set(scheduled) | set(registry)):
        n_scheduled = scheduled.count(name)
        size, note = search_space_size(name)
        rows.append({
            "name": name,
            "in_registry": name in registry,
            "times_scheduled": n_scheduled,
            "normalized": normalize_model_name(name),
            "search_space_size": size,
            "note": note,
        })

    width = max(len(r["name"]) for r in rows) + 2
    print(f"{'name':<{width}} {'registry':<9} {'scheduled':<10} {'space':<6} note")
    for r in rows:
        print(f"{r['name']:<{width}} {str(r['in_registry']):<9} "
              f"{r['times_scheduled']:<10} {str(r['search_space_size']):<6} {r['note']}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWROTE {args.out}")

    missing = sorted(set(registry) - set(scheduled))
    unknown = sorted(set(scheduled) - set(registry))
    duplicated = sorted({m for m in scheduled if scheduled.count(m) > 1})
    no_space = [r["name"] for r in rows
                if r["times_scheduled"] and r["search_space_size"] == ""]
    catch_all = [r["name"] for r in rows if r["times_scheduled"] and r["note"]]

    ok = True
    print()
    if set(scheduled) == set(registry) and not duplicated:
        print("PASS  the scheduled set equals the registry, each name once")
    else:
        ok = False
        print("FAIL  the scheduled set does NOT equal the registry")
        if missing:
            print(f"      in the registry, scheduled by no group : {', '.join(missing)}")
        if unknown:
            print(f"      scheduled but not in the registry      : {', '.join(unknown)}")
        if duplicated:
            print(f"      scheduled more than once               : {', '.join(duplicated)}")

    if no_space:
        ok = False
        print(f"FAIL  scheduled with no search space at all: {', '.join(no_space)}")
    if catch_all:
        ok = False
        print(f"FAIL  scheduled but given the catch-all space: {', '.join(catch_all)}")
    if ok:
        print("PASS  every scheduled name receives its own search space")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
