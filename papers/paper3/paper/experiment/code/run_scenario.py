#!/usr/bin/env python3
"""
run_scenario.py — Single scenario runner with CLI support.

2026-05-06 patch (urgent):
    * Incremental CSV write: every completed run is flushed to
      <scenario>_full.csv immediately.  Per-metric CSVs are still written
      at the end (cheap derive from full.csv).
    * Resume on restart: if <scenario>_full.csv already exists, the
      (algorithm, density, eps, gamma, tau, seed) tuples already present
      are skipped.
    * Line-buffered stdout via flush=True so progress is visible under
      `tee` / `nohup` without `python -u`.
    * Per-run wallclock printed every run (was every 20 runs).

2026-05-07 patch:
    * Heartbeat logging added to run_scenario() for long-running jobs.
      Interval: <60s -> every 10s, 60-600s -> every 1min, >=600s -> every 1h.
      Each heartbeat prints current time, elapsed, progress %, avg run time,
      ETA, and the last completed (algorithm, density, eps, gamma, tau, seed).

Usage:
    python3 -u run_scenario.py --scenario A --output_dir data/
"""
import argparse
import sys
import os
import csv
import time
import datetime

# Add code directory to path
CODE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CODE_DIR)

from sim_core import CIoVSim
from algorithms import ALGORITHMS

SCENARIO_CONFIGS = {
    'A': {
        'density_range': [1, 2, 3, 4, 5],
        'prediction_error_pct': [0, 10, 20, 30],
        'tau_max_slots': [5],
        'gamma_values': [0.0, 1.0, 2.0, 3.0],
        'seeds': [42, 43, 44, 45, 46, 47, 48, 49, 50, 51],
        'duration_steps': 1800,
        'warmup_steps': 300,
        'algorithms': ['RILP', 'RILP-Greedy', 'Nam2023b', 'Nam2025',
                       'Youn2026', 'V2I-Base', 'V2V-Base', 'Random-K'],
    },
    'B': {
        'density_range': [6, 8, 10, 12, 15, 20],
        'prediction_error_pct': [0, 10, 20, 30],
        'tau_max_slots': [5],
        'gamma_values': [2.0],
        'seeds': [42, 43, 44, 45, 46, 47, 48, 49, 50, 51],
        'duration_steps': 1800,
        'warmup_steps': 300,
        'algorithms': ['RILP-Greedy', 'Nam2023b', 'Nam2025', 'Youn2026',
                       'V2I-Base', 'V2V-Base', 'Random-K'],
    },
    'C': {
        'density_range': [5],
        'prediction_error_pct': [0, 5, 10, 15, 20, 25, 30],
        'tau_max_slots': [5],
        'gamma_values': [2.0],
        'seeds': [42, 43, 44, 45, 46, 47, 48, 49, 50, 51],
        'duration_steps': 1800,
        'warmup_steps': 300,
        'algorithms': ['RILP', 'RILP-Greedy', 'Nam2023b', 'Nam2025',
                       'Youn2026', 'V2I-Base', 'V2V-Base', 'Random-K'],
    },
    'D': {
        'density_range': [5],
        'prediction_error_pct': [10],
        'tau_max_slots': [3, 4, 5, 6, 7, 8],
        'gamma_values': [2.0],
        'seeds': [42, 43, 44, 45, 46, 47, 48, 49, 50, 51],
        'duration_steps': 1800,
        'warmup_steps': 300,
        'algorithms': ['RILP', 'RILP-Greedy', 'Nam2023b', 'Nam2025',
                       'Youn2026', 'V2I-Base', 'V2V-Base', 'Random-K'],
    },
    'E': {
        'density_range': [5],
        'prediction_error_pct': [10],
        'tau_max_slots': [5],
        'gamma_values': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
        'seeds': [42, 43, 44, 45, 46, 47, 48, 49, 50, 51],
        'duration_steps': 1800,
        'warmup_steps': 300,
        'algorithms': ['RILP', 'RILP-Greedy', 'Nam2023b', 'Nam2025',
                       'Youn2026', 'V2I-Base', 'V2V-Base', 'Random-K'],
    },
}

KEY_FIELDS = ['scenario', 'algorithm', 'density', 'pred_error_pct',
              'gamma', 'tau_max', 'seed']
METRIC_FIELDS = ['CHR', 'CDSR', 'AoI_violation_rate', 'PCO', 'RLBI']
ALL_FIELDS = KEY_FIELDS + METRIC_FIELDS


def _load_done_keys(full_path):
    """Return set of (algo, density, eps, gamma, tau, seed) already written."""
    done = set()
    if not os.path.exists(full_path):
        return done
    try:
        with open(full_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row['algorithm'], int(row['density']),
                       int(row['pred_error_pct']), float(row['gamma']),
                       int(row['tau_max']), int(row['seed']))
                done.add(key)
    except Exception as e:
        print(f"[run_scenario] Warning: could not parse existing "
              f"{full_path}: {e}", flush=True)
    return done


def _open_full_csv_for_append(full_path):
    """Open the full CSV in append mode; write header if file is new."""
    is_new = not os.path.exists(full_path) or os.path.getsize(full_path) == 0
    f = open(full_path, 'a', newline='', buffering=1)  # line-buffered
    writer = csv.DictWriter(f, fieldnames=ALL_FIELDS)
    if is_new:
        writer.writeheader()
        f.flush()
    return f, writer


def _heartbeat_interval(elapsed_s):
    """Return the heartbeat interval in seconds based on elapsed time.

    t < 60s   -> every 10s
    60 <= t < 600s -> every 60s (1 min)
    t >= 600s -> every 3600s (1 hour)
    """
    if elapsed_s < 60:
        return 10
    elif elapsed_s < 600:
        return 60
    else:
        return 3600


def _fmt_elapsed(seconds):
    """Format elapsed seconds into a human-readable string.

    Examples: 45s, 12m 30s, 2h 05m 10s
    """
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}m {s:02d}s"
    else:
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}h {m:02d}m {s:02d}s"


def _fmt_eta(seconds):
    """Format ETA seconds into a human-readable string."""
    if seconds <= 0:
        return "0s"
    seconds = int(seconds)
    if seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}m {s:02d}s"
    else:
        h, rem = divmod(seconds, 3600)
        m = rem // 60
        return f"{h}h {m:02d}m"


def run_scenario(scenario_id, output_dir='data', verbose=True):
    """Run a full scenario and save per-metric CSVs incrementally."""
    cfg = SCENARIO_CONFIGS[scenario_id]
    os.makedirs(output_dir, exist_ok=True)

    full_path = os.path.join(output_dir, f'{scenario_id}_full.csv')
    done_keys = _load_done_keys(full_path)
    if done_keys:
        print(f"[run_scenario] Resume: {len(done_keys)} runs already in "
              f"{full_path}; will skip those.", flush=True)

    full_f, full_writer = _open_full_csv_for_append(full_path)

    total_runs = (len(cfg['density_range']) * len(cfg['prediction_error_pct']) *
                  len(cfg['tau_max_slots']) * len(cfg['gamma_values']) *
                  len(cfg['algorithms']) * len(cfg['seeds']))

    run_count = len(done_keys)
    new_count = 0
    t0 = time.time()

    # ── Heartbeat initialisation ──────────────────────────────────────
    last_heartbeat_t = t0
    last_combo = None  # tracks most recently completed combo for heartbeat

    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(
        f"[HEARTBEAT] 시작 | {now_str} | "
        f"시나리오={scenario_id} | total_runs={total_runs} | "
        f"already_done={len(done_keys)}",
        flush=True,
    )

    try:
        for density in cfg['density_range']:
            for epsilon in cfg['prediction_error_pct']:
                for tau_max in cfg['tau_max_slots']:
                    for gamma in cfg['gamma_values']:
                        for algo_name in cfg['algorithms']:
                            algo_fn = ALGORITHMS[algo_name]
                            for seed in cfg['seeds']:
                                key = (algo_name, density, epsilon,
                                       float(gamma), tau_max, seed)
                                if key in done_keys:
                                    continue
                                t_run = time.time()
                                sim = CIoVSim(
                                    density_per_cell=density,
                                    seed=seed,
                                    prediction_error_pct=epsilon,
                                    tau_max=tau_max,
                                    gamma=gamma,
                                    duration_steps=cfg['duration_steps'],
                                    warmup_steps=cfg['warmup_steps'],
                                )
                                metrics = sim.run(algo_fn)
                                row = {
                                    'scenario': scenario_id,
                                    'algorithm': algo_name,
                                    'density': density,
                                    'pred_error_pct': epsilon,
                                    'gamma': gamma,
                                    'tau_max': tau_max,
                                    'seed': seed,
                                    'CHR': round(metrics['CHR'], 6),
                                    'CDSR': round(metrics['CDSR'], 6),
                                    'AoI_violation_rate': round(
                                        metrics['AoI_violation_rate'], 6),
                                    'PCO': round(metrics['PCO'], 6),
                                    'RLBI': round(metrics['RLBI'], 6),
                                }
                                full_writer.writerow(row)
                                full_f.flush()
                                os.fsync(full_f.fileno())
                                run_count += 1
                                new_count += 1
                                run_dt = time.time() - t_run
                                elapsed = time.time() - t0
                                eta_s = (elapsed / max(1, new_count)) * \
                                        (total_runs - run_count)
                                print(
                                    f'  [{run_count}/{total_runs}] '
                                    f'd={density} eps={epsilon} g={gamma} '
                                    f'tau={tau_max} algo={algo_name:<11} '
                                    f'seed={seed} | CHR={metrics["CHR"]:.3f} '
                                    f'AoI={metrics["AoI_violation_rate"]:.3f} '
                                    f'| run={run_dt:.1f}s tot={elapsed:.0f}s '
                                    f'eta={eta_s/60:.0f}m',
                                    flush=True,
                                )

                                # ── Heartbeat polling ─────────────────────────
                                last_combo = (algo_name, density, epsilon,
                                              gamma, tau_max, seed)
                                now = time.time()
                                elapsed_since_t0 = now - t0
                                interval = _heartbeat_interval(elapsed_since_t0)
                                if now - last_heartbeat_t >= interval:
                                    now_dt = datetime.datetime.now()
                                    now_str_hb = now_dt.strftime('%Y-%m-%d %H:%M:%S')
                                    elapsed_fmt = _fmt_elapsed(elapsed_since_t0)
                                    pct = (run_count / total_runs * 100
                                           if total_runs > 0 else 0.0)
                                    avg_run_s = (elapsed_since_t0 / new_count
                                                 if new_count > 0 else 0.0)
                                    eta_hb = avg_run_s * (total_runs - run_count)
                                    eta_fmt = _fmt_eta(eta_hb)
                                    combo_str = (
                                        f'algo={last_combo[0]} '
                                        f'd={last_combo[1]} '
                                        f'eps={last_combo[2]} '
                                        f'g={last_combo[3]} '
                                        f'tau={last_combo[4]} '
                                        f'seed={last_combo[5]}'
                                    )
                                    print(
                                        f'[HEARTBEAT] {now_str_hb} | '
                                        f'경과={elapsed_fmt} | '
                                        f'진행={run_count}/{total_runs} '
                                        f'({pct:.1f}%) | '
                                        f'평균={avg_run_s:.1f}s/run | '
                                        f'ETA={eta_fmt} | '
                                        f'최근완료: {combo_str}',
                                        flush=True,
                                    )
                                    last_heartbeat_t = now
                                # ── End heartbeat polling ─────────────────────

    finally:
        full_f.close()

    # ── Heartbeat: 종료 ───────────────────────────────────────────────────
    elapsed_total = time.time() - t0
    now_str_end = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    elapsed_fmt_end = _fmt_elapsed(elapsed_total)
    print(
        f"[HEARTBEAT] 종료 | {now_str_end} | "
        f"총 경과={elapsed_fmt_end} | "
        f"완료={run_count}/{total_runs} | "
        f"신규={new_count} | 재개={len(done_keys)}",
        flush=True,
    )

    # ── Derive per-metric CSVs from full CSV ──────────────────────────────
    print(f"[run_scenario] Writing per-metric CSVs from {full_path} ...",
          flush=True)
    with open(full_path, 'r', newline='') as f:
        all_rows = list(csv.DictReader(f))

    for metric in METRIC_FIELDS:
        metric_path = os.path.join(output_dir, f'{scenario_id}_{metric}.csv')
        with open(metric_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=KEY_FIELDS + [metric])
            writer.writeheader()
            for r in all_rows:
                writer.writerow({k: r[k] for k in KEY_FIELDS + [metric]})
        print(f"  Saved: {metric_path} ({len(all_rows)} rows)", flush=True)

    elapsed = time.time() - t0
    print(f"Scenario {scenario_id} done: {new_count} new runs "
          f"(+{len(done_keys)} resumed) in {elapsed:.1f}s "
          f"-> total {run_count}/{total_runs}", flush=True)
    return all_rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CIoV Experiment Runner')
    parser.add_argument('--scenario', default='A',
                        choices=list(SCENARIO_CONFIGS.keys()))
    parser.add_argument('--output_dir', default='data')
    parser.add_argument('--verbose', action='store_true', default=True)
    args = parser.parse_args()
    run_scenario(args.scenario, args.output_dir, args.verbose)
