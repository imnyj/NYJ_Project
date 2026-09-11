"""How large is each baseline's per-episode loss AFTER the 2026-09-05 rewiring?

WHY. `src/divergence_guard.py` sets its absolute floor at 1e3 and its relative
rule at 1e3 x the run's own warmup median. Both numbers were read off the
2026-09-02/03 runs, in which the worst healthy episode was 12.43 (CARLTON) and
the mildest real divergence was 285,247. Since then MADDPG-MT gained a second
critic and a task decomposition, SPAM-D3QN got its prioritised replay back,
I-HAMAPPO and RES-MAPDDPG were given the neighbourhood, CARLTON was replaced by
HOORL, and the discount search ceiling dropped from 0.999 to 0.99. Every one of
those changes moves the LEVEL of the loss, and a floor that no longer sits in the
gap between healthy and diverged is wrong in one of two directions: too high and
a real divergence runs to completion, too low and a healthy run is killed.

WHAT IS MEASURED. Every model in `src/baselines.BASELINE_REGISTRY` (the list is
derived, never typed out) runs 4,000 environment steps, the same length as one
HPO rollout, split into 20 episodes of 200 steps so that an episode here and a
pseudo-episode in `hpo.evaluate_model_in_env` cover the same number of steps.
The quantity recorded is `mean_loss` from the progress CSV, which is
`BackgroundTrainer.get_metrics()["mean_recent_loss"]` -- the very column the
12.43 figure came from and the very number `DivergenceMonitor.observe` reads.

THE LIVE GUARD IS WIDENED ON PURPOSE, and only here. `divergence_loss_ratio`,
`divergence_loss_abs_floor` and `max_zero_update_episodes` are set to infinity so
that a run which the CURRENT threshold would abort still produces all twenty
episodes; a truncated trace cannot answer "what is this model's loss range".
The verdict is then reached by replaying the completed rows through
`divergence_guard.scan_progress_rows` with the module's own DEFAULTS -- the
function the scheduled report uses, documented to reach the same verdict as the
live monitor. Nothing about the thresholds themselves is modified. The one live
rule left armed is the non-finite-loss rule, because a NaN loss has already
poisoned the weights and there is nothing further to measure after it.

The warmup median is not recomputed by hand either: the rows are fed to a fresh
`DivergenceMonitor` and its `baseline_loss` is read, so "initial median" means
exactly what the guard means by it (median of |loss| over the first
DEFAULT_WARMUP_EPISODES episodes).

READ-ONLY. Writes only its own CSV/JSON under results/diagnostics and its
scratch under PAPER4_LOSSSCALE_WORK. Scenario files go to an isolated
PAPER4_SUMO_DIR, never the shared package directory.

Usage
    python measure_loss_scale_after_rewiring.py                 # all models
    python measure_loss_scale_after_rewiring.py --model PPO     # one, in-process
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import subprocess
import sys
import time
import traceback
from typing import Any, Dict, List, Optional

CODER = os.environ.get("PAPER4_CODER_ROOT", "/home/imnyj/Workspace/paper4/coder")
sys.path.insert(0, CODER)

DEFAULT_OUT = os.path.join(
    CODER, "results", "diagnostics", "loss_scale_after_rewiring_20260906.csv"
)
#: Same length as one HPO rollout (`hpo.DEFAULT_HPO_N_STEPS`), and the episode
#: length matches `hpo.HPO_CHECK_INTERVAL_STEPS` so the two granularities agree.
TOTAL_STEPS = 4000
EPISODES = 20
DENSITY = 25.0
SEED = 42

#: Files whose modification time is recorded with the measurement. If any of
#: them moves after this ran, the numbers below describe a code generation that
#: no longer exists.
PROVENANCE_FILES = (
    "src/hot_swap_trainer.py",
    "src/rl_interface.py",
    "src/divergence_guard.py",
    "src/hpo.py",
    "src/baselines/__init__.py",
    "src/baselines/maddpg_mt.py",
    "src/baselines/spam_d3qn.py",
    "src/baselines/i_hamappo.py",
    "src/baselines/res_mapddpg.py",
    "src/baselines/hoorl.py",
    "src/baselines/ma2hdqn.py",
    "src/baselines/sb3_ppo.py",
    "src/baselines/sb3_sac.py",
    "src/baselines/sb3_td3.py",
)

CSV_FIELDS = [
    "model", "status", "error",
    "episodes_recorded", "steps_requested", "steps_per_episode",
    "loss_min", "loss_median", "loss_max", "loss_abs_max",
    "warmup_median_guard", "relative_threshold", "effective_threshold",
    "n_episodes_over_current_floor", "max_consecutive_over_floor",
    "replay_verdict_kind", "replay_verdict_episode", "replay_verdict_rule",
    "live_run_status", "grad_updates_total", "zero_update_episodes",
    "n_episodes_zero_updates", "wall_seconds",
    # Per-UPDATE losses, retained by BackgroundTrainer.loss_history (maxlen
    # 1000). The episode column above is a 50-update mean, so a spike inside one
    # episode is averaged down in it and visible only here.
    "update_loss_n", "update_loss_min", "update_loss_median", "update_loss_max",
    "update_term_max_json",
    "loss_series",
]


# --------------------------------------------------------------------------
# one model, in this process
# --------------------------------------------------------------------------
def measure_one(model_name: str, workdir: str, sumo_dir: str) -> Dict[str, Any]:
    """Run one model for TOTAL_STEPS and return its loss statistics."""
    import pandas as pd

    import src.hot_swap_trainer as hst
    from src.baselines import get_baseline
    from src.divergence_guard import (
        DEFAULT_WARMUP_EPISODES,
        DEFAULT_LOSS_ABS_FLOOR,
        DEFAULT_LOSS_RATIO,
        DivergenceMonitor,
        scan_progress_rows,
    )

    out: Dict[str, Any] = {
        "model": model_name,
        "status": "ok",
        "error": "",
        "steps_requested": TOTAL_STEPS,
        "steps_per_episode": TOTAL_STEPS // EPISODES,
    }
    run_dir = os.path.join(workdir, model_name.replace("/", "_"))
    os.makedirs(run_dir, exist_ok=True)

    # Hold on to the trainer so its per-update loss history can be read after
    # the run. Capture only; the class itself is restored in the `finally`.
    captured: List[Any] = []
    real_trainer_cls = hst.HotSwapTrainer

    class _CapturingTrainer(real_trainer_cls):  # type: ignore[misc, valid-type]
        def __init__(self, *a: Any, **kw: Any) -> None:
            super().__init__(*a, **kw)
            captured.append(self)

    hst.HotSwapTrainer = _CapturingTrainer

    started = time.time()
    summary: Optional[Dict[str, Any]] = None
    try:
        summary = hst.run_hot_swap_training(
            model_name=model_name,
            model_cls=get_baseline(model_name),
            total_steps=TOTAL_STEPS,
            episodes=EPISODES,
            density=DENSITY,
            seed=SEED,
            checkpoint_dir=os.path.join(run_dir, "ckpt"),
            tensorboard_dir=os.path.join(run_dir, "tb"),
            log_dir=run_dir,
            validate_every_episodes=0,
            sumo_dir=sumo_dir,
            # Widened so the trace is complete; the verdict is reached below by
            # the module's own defaults instead. See this file's docstring.
            divergence_loss_ratio=float("inf"),
            divergence_loss_abs_floor=float("inf"),
            divergence_loss_patience=10 ** 9,
            max_zero_update_episodes=10 ** 9,
        )
    except Exception as exc:  # noqa: BLE001
        out["status"] = "failed"
        out["error"] = f"{type(exc).__name__}: {exc}"
        out["traceback"] = traceback.format_exc()
    finally:
        hst.HotSwapTrainer = real_trainer_cls
    out["wall_seconds"] = round(time.time() - started, 1)

    if captured:
        history = list(captured[0].background_trainer.loss_history)
        totals = [float(e["loss"]) for e in history
                  if "loss" in e and math.isfinite(float(e["loss"]))]
        out["update_loss_n"] = len(history)
        if totals:
            out["update_loss_min"] = min(totals)
            out["update_loss_max"] = max(totals)
            out["update_loss_median"] = statistics.median(totals)
        term_max: Dict[str, float] = {}
        for entry in history:
            for key, value in entry.items():
                try:
                    val = abs(float(value))
                except (TypeError, ValueError):
                    continue
                if math.isfinite(val):
                    term_max[key] = max(term_max.get(key, 0.0), val)
        out["update_term_max_json"] = json.dumps(
            {k: round(v, 6) for k, v in sorted(term_max.items())}
        )

    csv_path = (summary or {}).get("log_csv_path") or os.path.join(
        run_dir, f"{model_name}_progress.csv"
    )
    if not os.path.isfile(csv_path):
        out["episodes_recorded"] = 0
        if out["status"] == "ok":
            out["status"] = "no_progress_csv"
        return out

    df = pd.read_csv(csv_path)
    rows: List[Dict[str, Any]] = df.to_dict("records")
    out["episodes_recorded"] = len(rows)
    losses = [float(r["mean_loss"]) for r in rows if "mean_loss" in r]
    finite = [v for v in losses if math.isfinite(v)]
    out["loss_series"] = ";".join(f"{v:.6g}" for v in losses)

    if finite:
        out["loss_min"] = min(finite)
        out["loss_max"] = max(finite)
        out["loss_median"] = statistics.median(finite)
        out["loss_abs_max"] = max(abs(v) for v in finite)

    # The guard's own notion of "initial median": feed it the same rows and read
    # the baseline it computed. Constructed with the module defaults.
    monitor = DivergenceMonitor()
    over = 0
    streak = 0
    max_streak = 0
    for idx, row in enumerate(rows, start=1):
        value = row.get("mean_loss")
        if not (isinstance(value, (int, float)) and math.isfinite(float(value))):
            continue
        monitor.observe(
            episode=int(row.get("episode", idx)),
            mean_loss=float(value),
            grad_updates_this_episode=None,
        )
        if abs(float(value)) > DEFAULT_LOSS_ABS_FLOOR:
            over += 1
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    out["warmup_median_guard"] = monitor.baseline_loss
    if monitor.baseline_loss is not None:
        out["relative_threshold"] = abs(monitor.baseline_loss) * DEFAULT_LOSS_RATIO
        out["effective_threshold"] = max(
            abs(monitor.baseline_loss) * DEFAULT_LOSS_RATIO, DEFAULT_LOSS_ABS_FLOOR
        )
    else:
        out["relative_threshold"] = None
        out["effective_threshold"] = DEFAULT_LOSS_ABS_FLOOR
    out["n_episodes_over_current_floor"] = over
    out["max_consecutive_over_floor"] = max_streak
    out["_warmup_episodes"] = DEFAULT_WARMUP_EPISODES

    # The real judgment, by the real function, at the real thresholds.
    verdict = scan_progress_rows(rows)
    out["replay_verdict_kind"] = verdict.kind if verdict else ""
    out["replay_verdict_episode"] = verdict.episode if verdict else ""
    out["replay_verdict_rule"] = (verdict.detail or {}).get("rule", "") if verdict else ""
    out["replay_verdict_reason"] = verdict.reason if verdict else ""

    statuses = [str(r.get("run_status", "")) for r in rows]
    out["live_run_status"] = statuses[-1] if statuses else ""
    if summary:
        out["grad_updates_total"] = summary.get("training_steps")
        out["zero_update_episodes"] = summary.get("zero_update_episodes")
    out["n_episodes_zero_updates"] = sum(
        1 for r in rows if float(r.get("grad_updates_this_episode", 0) or 0) == 0
    )
    return out


# --------------------------------------------------------------------------
# writing the result table
# --------------------------------------------------------------------------
def write_results(results: List[Dict[str, Any]], out_path: str) -> None:
    """Merge `results` into `out_path`, replacing only the models measured now.

    A re-measurement of one model -- HOORL once its offline dataset exists -- is
    the expected way this script is used a second time, and a plain overwrite
    would leave a one-row file where nine rows used to be. Rows for models this
    run did not touch are carried over verbatim, including any column a later
    hand added (the `note` column is written that way), and the row order of the
    existing file is preserved so a diff shows only what changed.
    """
    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    existing: List[Dict[str, Any]] = []
    extra_fields: List[str] = []
    if os.path.isfile(out_path):
        with open(out_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            existing = list(reader)
            extra_fields = [f for f in (reader.fieldnames or [])
                            if f not in CSV_FIELDS]

    fields = CSV_FIELDS + extra_fields
    fresh = {str(r.get("model")): r for r in results}

    merged: List[Dict[str, Any]] = []
    seen = set()
    for old in existing:
        model = str(old.get("model"))
        seen.add(model)
        if model in fresh:
            # Keep the carried-over columns (e.g. `note`) that this run does not
            # produce; overwrite everything it does.
            row = dict(old)
            row.update({k: fresh[model].get(k, "") for k in CSV_FIELDS})
            merged.append(row)
        else:
            merged.append(old)
    for model, res in fresh.items():
        if model not in seen:
            merged.append({k: res.get(k, "") for k in CSV_FIELDS})

    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in merged:
            writer.writerow({k: row.get(k, "") for k in fields})


# --------------------------------------------------------------------------
# provenance
# --------------------------------------------------------------------------
def provenance() -> Dict[str, Any]:
    """Commit and file mtimes, so a later reader can tell which code this was."""
    def git(*args: str) -> str:
        try:
            return subprocess.run(
                ["git", *args], cwd=CODER, capture_output=True, text=True, timeout=30
            ).stdout.strip()
        except Exception:  # noqa: BLE001
            return ""

    info: Dict[str, Any] = {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "git_head": git("rev-parse", "HEAD"),
        "git_head_short": git("rev-parse", "--short", "HEAD"),
        "git_dirty_files": len([l for l in git("status", "--porcelain").splitlines() if l]),
        "total_steps": TOTAL_STEPS,
        "episodes": EPISODES,
        "density": DENSITY,
        "seed": SEED,
        "files": {},
    }
    for rel in PROVENANCE_FILES:
        path = os.path.join(CODER, rel)
        if os.path.isfile(path):
            st = os.stat(path)
            info["files"][rel] = {
                "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st.st_mtime)),
                "bytes": st.st_size,
            }
    return info


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=None,
                        help="measure exactly this model, in this process")
    parser.add_argument("--models", nargs="*", default=None,
                        help="subset of the registry; default is all of it")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--workdir",
                        default=os.environ.get("PAPER4_LOSSSCALE_WORK", ""))
    parser.add_argument("--sumo-dir", default=os.environ.get("PAPER4_SUMO_DIR", ""))
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--total-steps", type=int, default=None)
    parser.add_argument("--episodes", type=int, default=None)
    args = parser.parse_args()

    global TOTAL_STEPS, EPISODES
    if args.total_steps:
        TOTAL_STEPS = int(args.total_steps)
    if args.episodes:
        EPISODES = int(args.episodes)

    workdir = args.workdir or os.path.join(
        "/tmp/claude-1001", "paper4_loss_scale_work"
    )
    os.makedirs(workdir, exist_ok=True)
    sumo_dir = args.sumo_dir or os.path.join(workdir, "sumo")
    os.makedirs(sumo_dir, exist_ok=True)
    os.environ["PAPER4_SUMO_DIR"] = sumo_dir

    if args.model:
        import logging
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
        result = measure_one(args.model, workdir, sumo_dir)
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
        json_out = os.path.join(workdir, f"{name.replace('/', '_')}_result.json")
        log_path = os.path.join(workdir, f"{name.replace('/', '_')}_run.log")
        cmd = [
            sys.executable, os.path.abspath(__file__),
            "--model", name, "--workdir", workdir, "--sumo-dir", sumo_dir,
            "--json-out", json_out,
            "--total-steps", str(TOTAL_STEPS), "--episodes", str(EPISODES),
        ]
        print(f"[{time.strftime('%H:%M:%S')}] running {name} ...", flush=True)
        started = time.time()
        with open(log_path, "w", encoding="utf-8") as fh:
            proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                                  env=dict(os.environ, PYTHONPATH=CODER))
        elapsed = round(time.time() - started, 1)
        if os.path.isfile(json_out):
            with open(json_out, encoding="utf-8") as fh:
                res = json.load(fh)
        else:
            res = {
                "model": name, "status": "subprocess_failed",
                "error": f"exit code {proc.returncode}; see {log_path}",
                "wall_seconds": elapsed,
            }
        res.setdefault("wall_seconds", elapsed)
        results.append(res)
        print(f"    -> {res.get('status')} "
              f"loss[min={res.get('loss_min')}, med={res.get('loss_median')}, "
              f"max={res.get('loss_max')}] "
              f"verdict={res.get('replay_verdict_kind') or 'none'} "
              f"({elapsed}s)", flush=True)

    write_results(results, args.out)
    # The sidecar is merged the same way and for the same reason: a later
    # single-model run must not erase the conditions the other eight were
    # measured under. Each invocation appends its own provenance snapshot, so
    # rows measured under different code generations stay distinguishable.
    meta_path = os.path.splitext(args.out)[0] + "_provenance.json"
    meta: Dict[str, Any] = {}
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, encoding="utf-8") as fh:
                meta = json.load(fh)
        except Exception:  # noqa: BLE001
            meta = {}
    snapshot = provenance()
    snapshot["models_measured"] = names
    history = meta.get("provenance_history")
    if not isinstance(history, list):
        history = [meta["provenance"]] if "provenance" in meta else []
    history.append(snapshot)
    kept = [r for r in meta.get("results", [])
            if str(r.get("model")) not in {str(x.get("model")) for x in results}]
    meta["provenance"] = snapshot
    meta["provenance_history"] = history
    meta["results"] = kept + results
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False, default=str)
    print(f"wrote {args.out}\nwrote {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
