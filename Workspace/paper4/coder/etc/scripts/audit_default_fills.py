#!/usr/bin/env python
# etc/scripts/audit_default_fills.py
# ============================================================================
# WHERE A MISSING VALUE IS REPLACED BY A PRESENT ONE.
#
# ---------------------------------------------------------------------------
# WHY THIS PATTERN AND NOT ANOTHER
# ---------------------------------------------------------------------------
# Four defects found on 2026-09-06 had the same shape: something unknown was
# filled with a number, and the number then read as a fact.
#
#   `behaviour_log_prob` missing -> 0.0, which asserts probability one;
#   `action_idx` missing -> 0 via `or`, which asserts subchannel 0;
#   `dist_to_stopline` absent -> the clip ceiling, which asserts "as far as the
#       RSU can see" and is indistinguishable from a real reading at that range;
#   `tls_features` empty -> state "g", which asserts a green light.
#
# None raised, none logged, and each was found by measuring rather than reading.
# This script finds the rest of the family so the same class can be closed in one
# pass instead of one incident at a time.
#
# ---------------------------------------------------------------------------
# THE SECOND COLUMN IS THE IMPORTANT ONE
# ---------------------------------------------------------------------------
# A default is dangerous in proportion to how easily it is mistaken for a
# measurement, and that is decided by whether the default VALUE can also occur
# legitimately. Three cases this month were invisible for exactly that reason:
#
#   `E_REF` fallback 13.32 against a real network maximum of 13.32;
#   `dist_to_stopline` default `rsu_range` against a clip ceiling of `rsu_range`;
#   `DELTA_MAX` fallback 45.0 against a real longest red phase of 45.0.
#
# When the two coincide, no amount of inspecting the stored value distinguishes
# them, and the only remedy is a separate flag. So each finding is classified as
# COLLIDES (the default is inside the range of legitimate values, so it needs a
# flag), DISTINCT (the default cannot occur naturally, e.g. NaN or a negative
# sentinel, so the value itself is enough), or UNKNOWN.
#
# Detection is textual and therefore over-reports: a `.get(k, d)` on a config
# dictionary is not a scientific claim. The output is a list to review, not a
# list of defects, and every row carries its file and line so review is cheap.
# ============================================================================
from __future__ import annotations

import argparse
import ast
import csv
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

#: Paths whose defaults can reach a measurement. A default in a CLI parser or a
#: plotting helper cannot, and listing those would bury the ones that can.
SCIENTIFIC_PATHS = ("src/rl_interface.py", "src/hot_swap_trainer.py",
                    "src/hoorl_offline.py", "src/dynamics_predictor.py",
                    "src/evaluate.py", "src/hpo.py", "src/Communications.py",
                    "src/baselines/")

#: Literals that cannot be confused with a measurement. A NaN propagates and a
#: negative sentinel is outside every observation's range, so both announce
#: themselves; 0.0 and 1.0 do not, and 0 is a real subchannel.
DISTINCT_DEFAULTS = ("nan", "float('nan')", 'float("nan")', "none", "-1", "-1.0",
                     "float('inf')", 'float("inf")', "inf")


def classify(default_src: str) -> str:
    d = default_src.strip().lower()
    if any(d == k or d.endswith(k) for k in DISTINCT_DEFAULTS):
        return "DISTINCT"
    if re.fullmatch(r"-?\d+(\.\d+)?(e-?\d+)?", d):
        return "COLLIDES"
    if d in ("{}", "[]", "()", "''", '""'):
        return "DISTINCT"
    return "UNKNOWN"


def scan(path: str) -> List[Dict[str, Any]]:
    try:
        text = open(path, encoding="utf-8").read()
        tree = ast.parse(text)
    except (OSError, SyntaxError):
        return []
    lines = text.splitlines()
    out: List[Dict[str, Any]] = []

    def add(node: ast.AST, form: str, key: str, default_src: str) -> None:
        ln = getattr(node, "lineno", 0)
        out.append({
            "file": os.path.relpath(path, ROOT), "line": ln, "form": form,
            "key": key, "default": default_src,
            "collision_risk": classify(default_src),
            "source": lines[ln - 1].strip()[:160] if 0 < ln <= len(lines) else "",
        })

    for node in ast.walk(tree):
        # `d.get(key, default)` with a default given.
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "get" and len(node.args) == 2:
            add(node, ".get(key, default)", ast.unparse(node.args[0]),
                ast.unparse(node.args[1]))
        # `x or default` -- the form that also swallows a legitimate 0 or "".
        elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) \
                and len(node.values) == 2:
            add(node, "x or default", ast.unparse(node.values[0]),
                ast.unparse(node.values[1]))
        # `x if x is not None else default` and `x if cond else default`.
        elif isinstance(node, ast.IfExp):
            add(node, "conditional default", ast.unparse(node.test)[:60],
                ast.unparse(node.orelse))
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default=os.path.join(
        ROOT, "results", "diagnostics", "default_fill_audit.csv"))
    args = p.parse_args(argv)

    files: List[str] = []
    for dirpath, _d, filenames in os.walk(os.path.join(ROOT, "src")):
        if "__pycache__" in dirpath:
            continue
        files += [os.path.join(dirpath, f) for f in filenames if f.endswith(".py")]

    rows: List[Dict[str, Any]] = []
    for f in sorted(files):
        rel = os.path.relpath(f, ROOT)
        if not any(rel.startswith(p_) for p_ in SCIENTIFIC_PATHS):
            continue
        rows += scan(f)

    rows.sort(key=lambda r: ({"COLLIDES": 0, "UNKNOWN": 1, "DISTINCT": 2}[r["collision_risk"]],
                             r["file"], r["line"]))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    by_risk: Dict[str, int] = {}
    by_form: Dict[str, int] = {}
    for r in rows:
        by_risk[r["collision_risk"]] = by_risk.get(r["collision_risk"], 0) + 1
        by_form[r["form"]] = by_form.get(r["form"], 0) + 1
    print(f"{len(rows)} default-fill sites in the scientific path")
    print("  by collision risk:", by_risk)
    print("  by form:", by_form)
    print("\nHighest risk (`x or default`, which also swallows a legitimate 0):")
    for r in rows:
        if r["form"] == "x or default" and r["collision_risk"] == "COLLIDES":
            print(f"  {r['file']}:{r['line']}  {r['source'][:110]}")
    print(f"\n{args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
