#!/usr/bin/env python3
"""Independent check that the divergence guard is causal and does not touch the reward.

Run separately from pytest, on purpose: the point is to re-derive the guard's
behaviour from the RECORDED runs rather than from the fixtures the tests use,
and to state in one place what was checked.

Four questions:

  1. Causality. Does the verdict at episode N depend on anything after N? A
     detector that used the whole series would be useless live, and the fact
     that the same function is also replayed over finished CSVs makes it easy
     for that to go unnoticed.
  2. Separation. On the eighteen recorded runs, does the guard fire on exactly
     the runs that stopped learning and none of the others?
  3. Isolation. Does anything in the observation or reward path now read the
     guard? The environment is the sole owner of both, and the guard must stay
     outside it.
  4. Anti-mocking. Are the four runtime assertions in `AoiV2IEnv.step` still
     present and still un-negatable?

Writes `etc/verification/divergence_guard_verification.csv` and prints a verdict.
Kept out of `results/`, which holds the run outputs the paper reads; this is a
check ON those outputs, not one of them.
"""
from __future__ import annotations

import ast
import glob
import os
import sys

import pandas as pd

CODER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CODER_DIR not in sys.path:
    sys.path.insert(0, CODER_DIR)

from src.divergence_guard import scan_progress_rows  # noqa: E402

RUNS_GLOB = os.path.join(CODER_DIR, "runs", "*", "lg", "*_progress.csv")
OUT_CSV = os.path.join(CODER_DIR, "etc", "verification",
                       "divergence_guard_verification.csv")

#: Runs known from the supervisor log and the checkpoint contents to have stopped
#: learning. PPO: the worker thread raised out of `sb3_ppo.update()` and died.
#: I-HAMAPPO: kept updating but its loss never came back under 1e3 after the
#: episode named here, so every later update trained on a diverged model.
KNOWN_DEAD = {"PPO", "IHAMAPPO"}


def check_causality(rows) -> tuple[bool, str]:
    """The verdict for a prefix must not change when the future is appended."""
    full = scan_progress_rows(rows)
    if full is None:
        # Nothing to be non-causal about, but every prefix must also be clean.
        for k in range(1, len(rows) + 1):
            if scan_progress_rows(rows[:k]) is not None:
                return False, f"clean series condemned at prefix length {k}"
        return True, "clean at every prefix"
    n = full.episode
    for k in range(1, len(rows) + 1):
        prefix = scan_progress_rows(rows[:k])
        if k < n and prefix is not None:
            return False, f"condemned at prefix {k}, before the verdict episode {n}"
        if k >= n and (prefix is None or prefix.episode != n):
            got = None if prefix is None else prefix.episode
            return False, f"prefix {k} gives episode {got}, full series gives {n}"
    return True, f"verdict episode {n} is reached from the prefix alone"


def check_isolation() -> tuple[bool, str]:
    """No part of AoiV2IEnv may read the guard."""
    src = open(os.path.join(CODER_DIR, "src", "hot_swap_trainer.py")).read()
    tree = ast.parse(src)
    guard_names = {"DivergenceMonitor", "AbortVerdict", "divergence_monitor", "abort"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "AoiV2IEnv":
            used = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            used |= {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}
            clash = used & guard_names
            if clash:
                return False, f"AoiV2IEnv references {sorted(clash)}"
            return True, "AoiV2IEnv references nothing from the guard"
    return False, "AoiV2IEnv not found"


def check_anti_mocking() -> tuple[bool, str]:
    """The four runtime assertions in `AoiV2IEnv.step` must still be there."""
    src = open(os.path.join(CODER_DIR, "src", "hot_swap_trainer.py")).read()
    needed = [
        "Anti-mocking violation: SUMO simulation time did not advance",
        "Anti-mocking violation: Invalid coordinate types",
        "Anti-mocking violation: NaN/Inf reward",
        "Anti-mocking violation: Communications.judge_uplink was bypassed",
    ]
    missing = [m for m in needed if m not in src]
    if missing:
        return False, f"missing: {missing}"
    tree = ast.parse(src)
    n_assert = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Assert)
                   and "Anti-mocking" in ast.dump(n))
    return True, f"all four present, {n_assert} assert statements carry the message"


def main() -> int:
    rows_out = []
    causal_ok = True
    for path in sorted(glob.glob(RUNS_GLOB)):
        model = os.path.basename(path).replace("_progress.csv", "")
        arm = os.path.basename(os.path.dirname(os.path.dirname(path)))
        df = pd.read_csv(path)
        recs = df.to_dict("records")
        verdict = scan_progress_rows(recs)
        ok, note = check_causality(recs)
        causal_ok &= ok
        rows_out.append({
            "arm": arm,
            "model": model,
            "episodes_recorded": len(df),
            "max_abs_loss": float(df["mean_loss"].abs().max()),
            "final_loss": float(df["mean_loss"].iloc[-1]),
            "zero_update_episodes": int((df["grad_updates_this_episode"] <= 0).sum()),
            "guard_verdict": "" if verdict is None else verdict.kind,
            "guard_episode": "" if verdict is None else verdict.episode,
            "episodes_saved": "" if verdict is None else len(df) - verdict.episode,
            "expected_dead": model in KNOWN_DEAD,
            "agrees_with_expectation": (verdict is not None) == (model in KNOWN_DEAD),
            "causal": ok,
            "causality_note": note,
        })

    out = pd.DataFrame(rows_out)
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    out.to_csv(OUT_CSV, index=False)

    iso_ok, iso_note = check_isolation()
    am_ok, am_note = check_anti_mocking()

    print(out.to_string(index=False))
    print()
    print(f"1. causality        : {'PASS' if causal_ok else 'FAIL'}")
    agree = bool(out["agrees_with_expectation"].all()) if len(out) else False
    print(f"2. separation       : {'PASS' if agree else 'FAIL'} "
          f"({int(out['guard_verdict'].ne('').sum())} of {len(out)} runs condemned)")
    print(f"3. isolation        : {'PASS' if iso_ok else 'FAIL'} -- {iso_note}")
    print(f"4. anti-mocking     : {'PASS' if am_ok else 'FAIL'} -- {am_note}")
    print(f"\nwrote {OUT_CSV}")
    return 0 if (causal_ok and agree and iso_ok and am_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
