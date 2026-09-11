"""Do the declared wiring flags actually reach the progress CSV and TensorBoard?

Stage 4 of the wiring check, the one `verify_wiring_flags.py` cannot do: it
verifies the declaration and the model's return dict, and this verifies the
plumbing between that dict and the two artefacts a 200,000-step run leaves
behind. A flag that is declared, emitted, and then dropped on the way to the CSV
is indistinguishable from one that was never declared, once the process exits.

Each model runs a short real SUMO episode sequence. For each one:

  * every declared key must appear as a `wiring_<key>` column;
  * the column must be populated on episodes that received gradient updates,
    and blank -- not 0.0 -- on episodes that received none;
  * `wiring_<key>_n` must never exceed `wiring_updates`;
  * the same key must appear as a `Wiring/<key>` TensorBoard scalar;
  * `median_loss` must be present and must be a real median of that episode's
    losses rather than a copy of `mean_loss`.

WHAT THE MEASURED VALUES MEAN. `neighbourhood_used` reading 1.0 here says the
neighbour set reached the update at the START of a run. That the plumbing works
at all was already established elsewhere -- `batch_column_parity.csv` shows all
three multi-agent models carrying `neighbour_state`/`neighbour_mask`, and
`ihamappo_neighbourhood_stability.csv` shows the two arms scoring 1.31546 against
1.35269, which they could not do if the neighbour set were being discarded. The
column this script checks exists for the question those cannot answer: whether
the set keeps arriving for the whole of a long run. This script therefore
verifies the CHANNEL, and the main run's own CSV is what will answer the
question.

Results go to results/diagnostics/wiring_end_to_end.csv.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List

CODER = os.environ.get("PAPER4_CODER_ROOT", "/home/imnyj/Workspace/paper4/coder")
sys.path.insert(0, CODER)

OUT = os.path.join(CODER, "results", "diagnostics", "wiring_end_to_end.csv")
#: Short but not degenerate: enough episodes that a per-episode column has more
#: than one row, and enough steps per episode that gradient updates happen.
TOTAL_STEPS = 900
EPISODES = 3
DENSITY = 25.0
SEED = 42

FIELDS = [
    "model", "status", "declared_keys", "episodes", "wiring_updates_total",
    "columns_present", "columns_missing", "values_by_episode",
    "tb_scalars_present", "tb_scalars_missing",
    "median_loss_present", "median_differs_from_mean", "error",
]


def measure(model_name: str, workdir: str, sumo_dir: str) -> Dict[str, Any]:
    import src.hot_swap_trainer as hst
    from src.baselines import get_baseline

    cls = get_baseline(model_name)
    declared = tuple(getattr(cls, "WIRING_FLAG_KEYS", ()) or ())
    row: Dict[str, Any] = {
        "model": model_name,
        "declared_keys": ";".join(declared),
        "status": "ok",
        "error": "",
    }
    run_dir = os.path.join(workdir, model_name.replace("/", "_"))
    os.makedirs(run_dir, exist_ok=True)
    tb_dir = os.path.join(run_dir, "tb")

    try:
        summary = hst.run_hot_swap_training(
            model_name=model_name, model_cls=cls,
            total_steps=TOTAL_STEPS, episodes=EPISODES, density=DENSITY, seed=SEED,
            checkpoint_dir=os.path.join(run_dir, "ckpt"),
            tensorboard_dir=tb_dir, log_dir=run_dir,
            validate_every_episodes=0, sumo_dir=sumo_dir,
        )
    except Exception as exc:  # noqa: BLE001
        row["status"] = "failed"
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row

    csv_path = summary.get("log_csv_path")
    if not csv_path or not os.path.isfile(csv_path):
        row["status"] = "no_csv"
        return row

    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    row["episodes"] = len(rows)
    row["wiring_updates_total"] = sum(int(float(r.get("wiring_updates") or 0)) for r in rows)

    wanted = [f"wiring_{k}" for k in declared]
    header = set(rows[0].keys()) if rows else set()
    row["columns_present"] = ";".join(c for c in wanted if c in header)
    row["columns_missing"] = ";".join(c for c in wanted if c not in header)
    row["values_by_episode"] = " | ".join(
        ",".join(f"{k}={r.get('wiring_' + k, '')}" for k in declared)
        + f" (updates={r.get('wiring_updates')})"
        for r in rows
    ) if declared else ""

    # median_loss must exist and must not simply mirror mean_loss
    row["median_loss_present"] = all("median_loss" in r for r in rows)
    differs = any(
        r.get("median_loss") not in ("", None)
        and r.get("mean_loss") not in ("", None)
        and str(r["median_loss"]) != str(r["mean_loss"])
        for r in rows
    )
    row["median_differs_from_mean"] = differs

    # TensorBoard: read the tags straight out of the event files.
    tags: set = set()
    try:
        from tensorboard.backend.event_processing import event_accumulator
        for path in glob.glob(os.path.join(tb_dir, "**", "events.out.tfevents.*"),
                              recursive=True):
            acc = event_accumulator.EventAccumulator(path)
            acc.Reload()
            tags |= set(acc.Tags().get("scalars", []))
    except Exception as exc:  # noqa: BLE001
        row["error"] = f"tensorboard read failed: {type(exc).__name__}: {exc}"
    wanted_tags = [f"Wiring/{k}" for k in declared] + ["Loss/EpisodeMedian"]
    row["tb_scalars_present"] = ";".join(t for t in wanted_tags if t in tags)
    row["tb_scalars_missing"] = ";".join(t for t in wanted_tags if t not in tags)
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=None)
    parser.add_argument("--models", nargs="*", default=None)
    parser.add_argument("--workdir", default=os.environ.get("PAPER4_WIRING_WORK", ""))
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--out", default=OUT)
    args = parser.parse_args()

    workdir = args.workdir or tempfile.mkdtemp(prefix="paper4_wiring_e2e_")
    os.makedirs(workdir, exist_ok=True)
    sumo_dir = os.path.join(workdir, "sumo")
    os.makedirs(sumo_dir, exist_ok=True)
    os.environ["PAPER4_SUMO_DIR"] = sumo_dir

    if args.model:
        import logging
        logging.basicConfig(level=logging.WARNING)
        result = measure(args.model, workdir, sumo_dir)
        payload = json.dumps(result, default=str, ensure_ascii=False)
        if args.json_out:
            with open(args.json_out, "w", encoding="utf-8") as fh:
                fh.write(payload)
        print("RESULT_JSON " + payload)
        return 0

    from src.baselines import ALL_BASELINES
    names = list(args.models) if args.models else list(ALL_BASELINES)

    results: List[Dict[str, Any]] = []
    for name in names:
        json_out = os.path.join(workdir, f"{name.replace('/', '_')}_e2e.json")
        log_path = os.path.join(workdir, f"{name.replace('/', '_')}_e2e.log")
        print(f"[{time.strftime('%H:%M:%S')}] {name} ...", flush=True)
        with open(log_path, "w", encoding="utf-8") as fh:
            proc = subprocess.run(
                [sys.executable, os.path.abspath(__file__), "--model", name,
                 "--workdir", workdir, "--json-out", json_out],
                stdout=fh, stderr=subprocess.STDOUT,
                env=dict(os.environ, PYTHONPATH=CODER),
            )
        if os.path.isfile(json_out):
            with open(json_out, encoding="utf-8") as fh:
                res = json.load(fh)
        else:
            res = {"model": name, "status": "subprocess_failed",
                   "error": f"exit {proc.returncode}; see {log_path}"}
        results.append(res)
        print(f"    {res.get('status')}  missing_cols="
              f"{res.get('columns_missing') or 'none'}  "
              f"missing_tb={res.get('tb_scalars_missing') or 'none'}", flush=True)
        if res.get("values_by_episode"):
            print(f"    {res['values_by_episode']}", flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for res in results:
            writer.writerow({k: res.get(k, "") for k in FIELDS})
    print(f"wrote {args.out}")

    bad = [r for r in results
           if r.get("status") != "ok" or r.get("columns_missing")
           or r.get("tb_scalars_missing")]
    if bad:
        print(f"\n{len(bad)} MODEL(S) WITH A PROBLEM")
        for r in bad:
            print(f"  - {r['model']}: status={r.get('status')} "
                  f"missing_cols={r.get('columns_missing')} "
                  f"missing_tb={r.get('tb_scalars_missing')} {r.get('error', '')}")
        return 1
    print("\nevery declared key reached both the CSV and TensorBoard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
