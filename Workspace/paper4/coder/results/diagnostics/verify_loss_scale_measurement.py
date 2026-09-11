"""Independent checks on `loss_scale_after_rewiring_20260906.csv`.

The measurement's headline claim is a negative one -- no model is judged
diverged -- and a negative can be produced by a broken judgment path just as
easily as by healthy models. Each check below is designed to fail loudly if the
judgment was reached the wrong way.

  1. COLUMN CONTRACT. `scan_progress_rows` reads `mean_loss` and `episode`. If a
     progress CSV lacked either, every row would feed `None` to the monitor and
     the verdict would be "diverged (non-finite)", not "none" -- but a typo in
     the reader here would produce "none" from no data at all. Checked
     explicitly.
  2. THE DETECTOR STILL FIRES. The same rows, multiplied by 1e5, must be
     condemned; the same rows with zero gradient updates must be condemned as a
     stall. A judgment path that returns None for everything fails this.
  3. WARMUP MEDIAN. Recomputed by hand from the first DEFAULT_WARMUP_EPISODES
     rows and compared with the `baseline_loss` the monitor arrived at.
  4. THE ENVIRONMENT MOVED. Every episode must record real decisions, real
     closed intervals and a finite AoI. An episode that observed nothing would
     make its loss row meaningless.
  5. NO STALE ROWS. `global_step` must be the episode index times the episode
     length, so a row left over from an earlier attempt cannot be in the file.
  6. RE-MEASURING ONE MODEL KEEPS THE OTHERS. The HOORL row is meant to be
     filled by a later single-model run, and the obvious implementation of that
     -- rewrite the CSV -- would leave a one-row file. Checked on a COPY of the
     result table, never on the table itself.
"""
from __future__ import annotations

import glob
import math
import os
import statistics
import sys
from typing import Any, Dict, List

CODER = os.environ.get("PAPER4_CODER_ROOT", "/home/imnyj/Workspace/paper4/coder")
sys.path.insert(0, CODER)

import pandas as pd  # noqa: E402

from src.divergence_guard import (  # noqa: E402
    ABORT_DIVERGED,
    ABORT_GRAD_STALL,
    DEFAULT_LOSS_ABS_FLOOR,
    DEFAULT_LOSS_RATIO,
    DEFAULT_WARMUP_EPISODES,
    DivergenceMonitor,
    scan_progress_rows,
)

WORK = os.environ.get(
    "PAPER4_LOSSSCALE_WORK",
    "/tmp/claude-1001/-home-imnyj/a451dd5b-ad4d-4465-95ad-6cfb0c601784/scratchpad/loss_scale",
)
STEPS_PER_EPISODE = 200

failures: List[str] = []
notes: List[str] = []


def check(condition: bool, message: str) -> None:
    if condition:
        print(f"  PASS  {message}")
    else:
        print(f"  FAIL  {message}")
        failures.append(message)


paths = sorted(glob.glob(os.path.join(WORK, "*", "*_progress.csv")))
print(f"progress CSVs found: {len(paths)}\n")

for path in paths:
    model = os.path.basename(path).replace("_progress.csv", "")
    df = pd.read_csv(path)
    rows: List[Dict[str, Any]] = df.to_dict("records")
    print(f"[{model}] {len(rows)} episodes")

    # 1. column contract
    check("mean_loss" in df.columns, f"{model}: mean_loss column present")
    check("episode" in df.columns, f"{model}: episode column present")
    check(df["mean_loss"].notna().all(), f"{model}: no missing mean_loss")

    losses = [float(v) for v in df["mean_loss"].tolist()]

    # 2. the detector still fires on data that deserves it
    blown = [dict(r, mean_loss=float(r["mean_loss"]) * 1e5) for r in rows]
    v_blown = scan_progress_rows(blown)
    check(v_blown is not None and v_blown.kind == ABORT_DIVERGED,
          f"{model}: x1e5 rows are condemned as diverged")
    stalled = [dict(r, grad_updates_this_episode=0) for r in rows]
    v_stall = scan_progress_rows(stalled)
    check(v_stall is not None and v_stall.kind == ABORT_GRAD_STALL,
          f"{model}: zero-update rows are condemned as a stall")
    v_real = scan_progress_rows(rows)
    check(v_real is None, f"{model}: as measured, no verdict")

    # 3. warmup median, recomputed
    monitor = DivergenceMonitor()
    for idx, row in enumerate(rows, start=1):
        monitor.observe(episode=int(row.get("episode", idx)),
                        mean_loss=float(row["mean_loss"]),
                        grad_updates_this_episode=None)
    by_hand = statistics.median([abs(v) for v in losses[:DEFAULT_WARMUP_EPISODES]])
    check(monitor.baseline_loss is not None
          and math.isclose(monitor.baseline_loss, by_hand, rel_tol=1e-12),
          f"{model}: warmup median {monitor.baseline_loss} == hand median {by_hand}")
    threshold = max(abs(monitor.baseline_loss or 0.0) * DEFAULT_LOSS_RATIO,
                    DEFAULT_LOSS_ABS_FLOOR)
    margin = threshold / max(abs(v) for v in losses)
    notes.append(f"{model}: threshold {threshold:.6g}, worst episode "
                 f"{max(abs(v) for v in losses):.6g}, margin x{margin:.4g}, "
                 f"relative rule "
                 f"{'binds' if abs(monitor.baseline_loss or 0) * DEFAULT_LOSS_RATIO > DEFAULT_LOSS_ABS_FLOOR else 'inert'}")

    # 4. the environment moved
    check((df["n_decisions"] > 0).all(), f"{model}: every episode made decisions")
    check((df["n_intervals_closed"] > 0).all(),
          f"{model}: every episode closed SMDP intervals")
    check(df["mean_aoi"].notna().all() and (df["mean_aoi"] > 0).all(),
          f"{model}: every episode recorded a positive mean AoI")

    # 5. no stale rows
    expected = [(i + 1) * STEPS_PER_EPISODE for i in range(len(rows))]
    check(df["global_step"].tolist() == expected,
          f"{model}: global_step is 200..{len(rows) * STEPS_PER_EPISODE} with no seam")
    print()

# 6. a single-model re-measurement must not destroy the other rows
RESULT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "loss_scale_after_rewiring_20260906.csv")
if os.path.isfile(RESULT_CSV):
    import csv
    import shutil
    import tempfile

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from measure_loss_scale_after_rewiring import write_results

    print("[merge] single-model re-measurement")
    tmp_dir = tempfile.mkdtemp(prefix="loss_scale_merge_")
    copy = os.path.join(tmp_dir, "table.csv")
    shutil.copy2(RESULT_CSV, copy)
    with open(copy, newline="", encoding="utf-8") as fh:
        before = list(csv.DictReader(fh))

    write_results([{
        "model": "HOORL", "status": "ok", "loss_min": 0.11,
        "loss_median": 0.22, "loss_max": 0.33, "loss_series": "0.11;0.22;0.33",
    }], copy)
    with open(copy, newline="", encoding="utf-8") as fh:
        after = list(csv.DictReader(fh))

    check(len(before) == len(after), "merge: row count unchanged")
    check([r["model"] for r in before] == [r["model"] for r in after],
          "merge: model order unchanged")
    untouched_equal = all(
        a == b for a, b in zip(before, after) if a["model"] != "HOORL"
    )
    check(untouched_equal, "merge: the eight measured rows are byte-identical")
    hoorl_after = next(r for r in after if r["model"] == "HOORL")
    check(hoorl_after["loss_max"] == "0.33", "merge: HOORL row was updated")
    check(hoorl_after.get("note", "").startswith("NOT MEASURED"),
          "merge: the hand-written note column survived the rewrite")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print()

print("--- thresholds and margins ---")
for line in notes:
    print("  " + line)

print()
if failures:
    print(f"{len(failures)} CHECK(S) FAILED")
    for f in failures:
        print("  - " + f)
    raise SystemExit(1)
print("all checks passed")
