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

2026-05-21 patch:
    * Two-phase execution: --phase generate | simulate | auto
      - generate: pre-generate SUMO trajectories (one SUMO run per unique
        seed × duration combo) so algorithm evaluation never needs SUMO.
      - simulate: evaluate algorithms using pre-generated trajectories.
      - auto (default): generate missing trajectories, then simulate.
    * Checkpoint/resume for intra-run recovery after unexpected shutdowns.
      CIoVSim accepts checkpoint_dir and run_id; saves state every 100 steps.
    * Graceful signal handling: SIGTERM/SIGINT set a shutdown flag; after each
      completed run the flag is checked and the runner exits cleanly.
    * Scenario configs updated to match experiment_spec.json.
    * sumo_dir resolution passed through to CIoVSim.

Usage:
    # Auto mode (generate then simulate):
    python3 -u run_scenario.py --scenario A --output_dir data/

    # Generate trajectories only:
    python3 -u run_scenario.py --scenario A --output_dir data/ --phase generate

    # Simulate only (trajectories must exist):
    python3 -u run_scenario.py --scenario A --output_dir data/ --phase simulate
"""
import argparse
import signal
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

# ---------------------------------------------------------------------------
# Graceful shutdown flag
# ---------------------------------------------------------------------------
_shutdown_requested = False


def _signal_handler(signum, frame):
    """Handle SIGTERM / SIGINT: set the shutdown flag."""
    global _shutdown_requested
    sig_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
    print(f"\n[run_scenario] Received {sig_name}. Will exit cleanly after "
          f"current run completes ...", flush=True)
    _shutdown_requested = True


# Register signal handlers (SIGTERM may not exist on all platforms)
signal.signal(signal.SIGINT, _signal_handler)
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, _signal_handler)

# ---------------------------------------------------------------------------
# SUMO directory resolution
# ---------------------------------------------------------------------------
_DEFAULT_SUMO_DIR = os.path.normpath(os.path.join(
    CODE_DIR, "../../../../SumoNetSim1.1.6/src/sumo"
))
_FALLBACK_SUMO_DIR = "/home/imnyj/paper-ai.v1/SumoNetSim1.1.6/src/sumo"


def _resolve_sumo_dir():
    """Return the best available SUMO config directory."""
    for d in [_DEFAULT_SUMO_DIR, _FALLBACK_SUMO_DIR]:
        cfg = os.path.join(d, "generated.sumocfg")
        if os.path.isfile(cfg):
            return d
    return _FALLBACK_SUMO_DIR

# ---------------------------------------------------------------------------
# Scenario configurations  (per experiment_spec.json)
# ---------------------------------------------------------------------------
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
        'duration_steps': 3600,
        'warmup_steps': 600,
        'algorithms': ['RILP-Greedy', 'Nam2023b', 'Nam2025', 'Youn2026',
                       'V2I-Base', 'V2V-Base', 'Random-K'],
    },
    'C': {
        'density_range': [5, 10],
        'prediction_error_pct': [0, 5, 10, 15, 20, 25, 30],
        'tau_max_slots': [5],
        'gamma_values': [0.0, 1.0, 2.0, 3.0, 4.0],
        'seeds': [42, 43, 44, 45, 46, 47, 48, 49, 50, 51],
        'duration_steps': 3600,
        'warmup_steps': 600,
        'algorithms': ['RILP', 'RILP-Greedy', 'Nam2023b', 'Nam2025',
                       'Youn2026', 'V2I-Base', 'V2V-Base', 'Random-K'],
    },
    'D': {
        'density_range': [10],
        'prediction_error_pct': [20],
        'tau_max_slots': [3, 4, 5, 6, 7, 8, 10],
        'gamma_values': [2.0],
        'seeds': [42, 43, 44, 45, 46, 47, 48, 49, 50, 51],
        'duration_steps': 3600,
        'warmup_steps': 600,
        'algorithms': ['RILP', 'RILP-Greedy', 'Nam2023b', 'Nam2025',
                       'Youn2026', 'Random-K'],
    },
    'E': {
        'density_range': [1, 5, 10, 20],
        'prediction_error_pct': [0, 10, 20, 30],
        'tau_max_slots': [5],
        'gamma_values': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0,
                         3.5, 4.0, 4.5, 5.0],
        'seeds': [42, 43, 44, 45, 46, 47, 48, 49, 50, 51],
        'duration_steps': 3600,
        'warmup_steps': 600,
        'algorithms': ['RILP', 'RILP-Greedy'],
    },
}

KEY_FIELDS = ['scenario', 'algorithm', 'density', 'pred_error_pct',
              'gamma', 'tau_max', 'seed']
METRIC_FIELDS = ['CHR', 'CDSR', 'AoI_violation_rate', 'PCO', 'RLBI']
ALL_FIELDS = KEY_FIELDS + METRIC_FIELDS


# ---------------------------------------------------------------------------
# Helpers — resume, CSV, heartbeat, formatting
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Phase 1: Trajectory pre-generation
# ---------------------------------------------------------------------------

def _traj_filename(seed, duration):
    """Canonical trajectory filename for a (seed, duration) pair."""
    return f"traj_seed{seed}_dur{duration}.pkl"


def generate_trajectories(scenario_id, output_dir, verbose=True):
    """Pre-generate SUMO trajectories for every unique (seed, duration) combo.

    This runs SUMO once per seed (deterministic by seed+duration), saving the
    full vehicle trajectory to disk.  Later simulation phase replays these
    trajectories without touching SUMO.

    Parameters
    ----------
    scenario_id : str
        One of the keys in SCENARIO_CONFIGS.
    output_dir : str
        Root output directory.  Trajectories are saved under
        ``<output_dir>/trajectories/``.
    verbose : bool
        Print progress messages.
    """
    global _shutdown_requested

    cfg = SCENARIO_CONFIGS[scenario_id]
    traj_dir = os.path.join(output_dir, 'trajectories')
    os.makedirs(traj_dir, exist_ok=True)

    sumo_dir = _resolve_sumo_dir()
    duration = cfg['duration_steps']

    # Collect unique (seed, duration) combos
    combos = set()
    for seed in cfg['seeds']:
        combos.add((seed, duration))

    combos = sorted(combos)  # deterministic order
    generated = 0
    skipped = 0

    for seed, dur in combos:
        if _shutdown_requested:
            print("[run_scenario] Shutdown requested during trajectory "
                  "generation. Exiting.", flush=True)
            sys.exit(0)

        traj_path = os.path.join(traj_dir, _traj_filename(seed, dur))
        if os.path.exists(traj_path):
            if verbose:
                print(f"  [traj] seed={seed} dur={dur} — already exists, "
                      f"skipping.", flush=True)
            skipped += 1
            continue

        t0 = time.time()
        if verbose:
            print(f"  [traj] Generating trajectory for seed={seed} "
                  f"dur={dur} ...", end='', flush=True)

        sim = CIoVSim(
            seed=seed,
            duration_steps=dur,
            warmup_steps=0,     # generate full trajectory, no warmup skip
            sumo_dir=sumo_dir,
            mode='generate',
            trajectory_path=traj_path,
        )
        sim.run(cache_decision_fn=None)

        dt = time.time() - t0
        generated += 1
        if verbose:
            print(f" done in {dt:.1f}s", flush=True)

    if verbose:
        print(f"[run_scenario] Trajectory generation complete: "
              f"{generated} new, {skipped} existing.", flush=True)


# ---------------------------------------------------------------------------
# Phase 2: Algorithm evaluation (simulation)
# ---------------------------------------------------------------------------

def run_scenario(scenario_id, output_dir='data', verbose=True):
    """Run a full scenario and save per-metric CSVs incrementally.

    Assumes trajectories already exist under ``<output_dir>/trajectories/``.
    Uses CIoVSim in mode='simulate' so SUMO is never launched.
    """
    global _shutdown_requested

    cfg = SCENARIO_CONFIGS[scenario_id]
    os.makedirs(output_dir, exist_ok=True)

    traj_dir = os.path.join(output_dir, 'trajectories')
    checkpoint_dir = os.path.join(output_dir, 'checkpoints')
    os.makedirs(checkpoint_dir, exist_ok=True)

    sumo_dir = _resolve_sumo_dir()
    duration = cfg['duration_steps']

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
                                # ── Shutdown check ────────────────────
                                if _shutdown_requested:
                                    print(
                                        "[run_scenario] Shutdown requested. "
                                        "Saving progress and exiting ...",
                                        flush=True,
                                    )
                                    raise SystemExit(0)

                                key = (algo_name, density, epsilon,
                                       float(gamma), tau_max, seed)
                                if key in done_keys:
                                    continue

                                t_run = time.time()

                                # Build run_id for checkpoint naming
                                run_id = (
                                    f"{scenario_id}_{algo_name}"
                                    f"_d{density}_e{epsilon}"
                                    f"_g{gamma}_t{tau_max}_s{seed}"
                                )

                                # Trajectory file path
                                traj_path = os.path.join(
                                    traj_dir,
                                    _traj_filename(seed, duration),
                                )

                                sim = CIoVSim(
                                    density_per_cell=density,
                                    seed=seed,
                                    prediction_error_pct=epsilon,
                                    tau_max=tau_max,
                                    gamma=gamma,
                                    duration_steps=duration,
                                    warmup_steps=cfg['warmup_steps'],
                                    sumo_dir=sumo_dir,
                                    mode='simulate',
                                    trajectory_path=traj_path,
                                    checkpoint_dir=checkpoint_dir,
                                    run_id=run_id,
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

                                # ── Heartbeat polling ─────────────────
                                last_combo = (algo_name, density, epsilon,
                                              gamma, tau_max, seed)
                                now = time.time()
                                elapsed_since_t0 = now - t0
                                interval = _heartbeat_interval(elapsed_since_t0)
                                if now - last_heartbeat_t >= interval:
                                    now_dt = datetime.datetime.now()
                                    now_str_hb = now_dt.strftime(
                                        '%Y-%m-%d %H:%M:%S')
                                    elapsed_fmt = _fmt_elapsed(
                                        elapsed_since_t0)
                                    pct = (run_count / total_runs * 100
                                           if total_runs > 0 else 0.0)
                                    avg_run_s = (elapsed_since_t0 / new_count
                                                 if new_count > 0 else 0.0)
                                    eta_hb = avg_run_s * (
                                        total_runs - run_count)
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
                                # ── End heartbeat polling ─────────────

    except SystemExit:
        # Graceful shutdown via signal handler
        pass
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

    if _shutdown_requested:
        print("[run_scenario] Exiting due to shutdown signal. "
              "Partial results saved. Resume with the same command.",
              flush=True)
        return None

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


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='CIoV Experiment Runner — Two-Phase Execution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Full auto run (generate + simulate):
  python3 -u run_scenario.py --scenario A --output_dir data/

  # Pre-generate trajectories only:
  python3 -u run_scenario.py --scenario A --output_dir data/ --phase generate

  # Simulate only (requires pre-generated trajectories):
  python3 -u run_scenario.py --scenario A --output_dir data/ --phase simulate
""",
    )
    parser.add_argument(
        '--scenario', default='A',
        choices=list(SCENARIO_CONFIGS.keys()),
        help='Scenario ID to run (default: A)',
    )
    parser.add_argument(
        '--output_dir', default='data',
        help='Output directory (default: data/)',
    )
    parser.add_argument(
        '--phase', default='auto',
        choices=['generate', 'simulate', 'auto'],
        help=(
            'Execution phase. '
            'generate: only pre-generate SUMO trajectories. '
            'simulate: only run algorithm evaluation (requires trajectories). '
            'auto: generate missing trajectories, then simulate. '
            '(default: auto)'
        ),
    )
    parser.add_argument(
        '--verbose', action='store_true', default=True,
        help='Verbose output (default: True)',
    )
    args = parser.parse_args()

    scenario_id = args.scenario
    output_dir = args.output_dir
    phase = args.phase
    verbose = args.verbose

    cfg = SCENARIO_CONFIGS[scenario_id]
    traj_dir = os.path.join(output_dir, 'trajectories')

    # ── Phase determination ───────────────────────────────────────────
    need_generate = False
    need_simulate = False

    if phase == 'generate':
        need_generate = True
    elif phase == 'simulate':
        need_simulate = True
    else:
        # auto: check if all trajectories exist
        need_simulate = True
        duration = cfg['duration_steps']
        for seed in cfg['seeds']:
            traj_path = os.path.join(
                traj_dir, _traj_filename(seed, duration))
            if not os.path.exists(traj_path):
                need_generate = True
                break

    # ── Phase 1: Generate trajectories ────────────────────────────────
    if need_generate:
        print(f"\n{'='*60}", flush=True)
        print(f"  Phase 1: Trajectory Generation — Scenario {scenario_id}",
              flush=True)
        print(f"{'='*60}\n", flush=True)
        generate_trajectories(scenario_id, output_dir, verbose)
        if _shutdown_requested:
            return

    # ── Phase 2: Simulate ─────────────────────────────────────────────
    if need_simulate:
        # Verify all trajectories exist before starting simulation
        duration = cfg['duration_steps']
        missing = []
        for seed in cfg['seeds']:
            traj_path = os.path.join(
                traj_dir, _traj_filename(seed, duration))
            if not os.path.exists(traj_path):
                missing.append(traj_path)
        if missing:
            print(f"[run_scenario] ERROR: {len(missing)} trajectory file(s) "
                  f"missing. Run with --phase generate first.", flush=True)
            for p in missing[:5]:
                print(f"  Missing: {p}", flush=True)
            if len(missing) > 5:
                print(f"  ... and {len(missing)-5} more", flush=True)
            sys.exit(1)

        print(f"\n{'='*60}", flush=True)
        print(f"  Phase 2: Algorithm Evaluation — Scenario {scenario_id}",
              flush=True)
        print(f"{'='*60}\n", flush=True)
        run_scenario(scenario_id, output_dir, verbose)


if __name__ == '__main__':
    main()
