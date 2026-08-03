import os
import re

with open("run_scenario.py", "r") as f:
    content = f.read()

# Add concurrent.futures import
content = content.replace("import datetime", "import datetime\nimport concurrent.futures")

# Add worker functions before Phase 1
worker_funcs = """
# ---------------------------------------------------------------------------
# Worker Functions for Multiprocessing
# ---------------------------------------------------------------------------

def _worker_generate(seed, dur, sumo_dir, traj_path):
    import time
    t0 = time.time()
    sim = CIoVSim(
        seed=seed,
        duration_steps=dur,
        warmup_steps=0,
        sumo_dir=sumo_dir,
        mode='generate',
        trajectory_path=traj_path,
    )
    sim.run(cache_decision_fn=None)
    dt = time.time() - t0
    return seed, dur, dt

def _worker_simulate(density, epsilon, tau_max, gamma, algo_name, seed, duration, warmup_steps, sumo_dir, traj_path, checkpoint_dir, run_id):
    import time
    t_run = time.time()
    algo_fn = ALGORITHMS[algo_name]
    sim = CIoVSim(
        density_per_cell=density,
        seed=seed,
        prediction_error_pct=epsilon,
        tau_max=tau_max,
        gamma=gamma,
        duration_steps=duration,
        warmup_steps=warmup_steps,
        sumo_dir=sumo_dir,
        mode='simulate',
        trajectory_path=traj_path,
        checkpoint_dir=checkpoint_dir,
        run_id=run_id,
    )
    metrics = sim.run(algo_fn)
    run_dt = time.time() - t_run
    
    return {
        'algorithm': algo_name,
        'density': density,
        'pred_error_pct': epsilon,
        'gamma': gamma,
        'tau_max': tau_max,
        'seed': seed,
        'metrics': metrics,
        'run_dt': run_dt
    }

# ---------------------------------------------------------------------------
# Phase 1: Trajectory pre-generation
# ---------------------------------------------------------------------------
"""
content = content.replace("# ---------------------------------------------------------------------------\n# Phase 1: Trajectory pre-generation\n# ---------------------------------------------------------------------------", worker_funcs)

# Update generate_trajectories definition
content = content.replace("def generate_trajectories(scenario_id, output_dir, verbose=True):", "def generate_trajectories(scenario_id, output_dir, workers=1, verbose=True):")

gen_old = """    for seed, dur in combos:
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
              f"{generated} new, {skipped} existing.", flush=True)"""

gen_new = """    jobs = []
    for seed, dur in combos:
        traj_path = os.path.join(traj_dir, _traj_filename(seed, dur))
        if os.path.exists(traj_path):
            if verbose:
                print(f"  [traj] seed={seed} dur={dur} — already exists, skipping.", flush=True)
            skipped += 1
            continue
        jobs.append((seed, dur, sumo_dir, traj_path))

    if jobs:
        if verbose:
            print(f"  [traj] Starting trajectory generation for {len(jobs)} items with {workers} workers...", flush=True)
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_worker_generate, *job): job for job in jobs}
            for future in concurrent.futures.as_completed(futures):
                if _shutdown_requested:
                    print("[run_scenario] Shutdown requested during trajectory generation. Exiting.", flush=True)
                    for f in futures:
                        f.cancel()
                    sys.exit(0)
                try:
                    seed, dur, dt = future.result()
                    generated += 1
                    if verbose:
                        print(f"  [traj] Generated trajectory for seed={seed} dur={dur} in {dt:.1f}s", flush=True)
                except Exception as e:
                    print(f"  [traj] Error generating trajectory: {e}", flush=True)

    if verbose:
        print(f"[run_scenario] Trajectory generation complete: "
              f"{generated} new, {skipped} existing.", flush=True)"""

content = content.replace(gen_old, gen_new)


# Update run_scenario definition
content = content.replace("def run_scenario(scenario_id, output_dir='data', verbose=True):", "def run_scenario(scenario_id, output_dir='data', workers=1, verbose=True):")


sim_old_start = """    try:
        for density in cfg['density_range']:"""

sim_old_end = """                                    print(
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
                                # ── End heartbeat polling ─────────────"""

sim_new = """    jobs = []
    for density in cfg['density_range']:
        for epsilon in cfg['prediction_error_pct']:
            for tau_max in cfg['tau_max_slots']:
                for gamma in cfg['gamma_values']:
                    for algo_name in cfg['algorithms']:
                        for seed in cfg['seeds']:
                            key = (algo_name, density, epsilon, float(gamma), tau_max, seed)
                            if key in done_keys:
                                continue

                            run_id = (
                                f"{scenario_id}_{algo_name}"
                                f"_d{density}_e{epsilon}"
                                f"_g{gamma}_t{tau_max}_s{seed}"
                            )
                            traj_path = os.path.join(
                                traj_dir,
                                _traj_filename(seed, duration),
                            )
                            jobs.append((density, epsilon, tau_max, gamma, algo_name, seed, duration, cfg['warmup_steps'], sumo_dir, traj_path, checkpoint_dir, run_id))

    try:
        if jobs:
            print(f"[run_scenario] Starting simulation of {len(jobs)} items with {workers} workers...", flush=True)
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {}
                for job in jobs:
                    if _shutdown_requested:
                        break
                    future = executor.submit(_worker_simulate, *job)
                    futures[future] = job

                for future in concurrent.futures.as_completed(futures):
                    if _shutdown_requested:
                        print("[run_scenario] Shutdown requested. Saving progress and exiting ...", flush=True)
                        for f in futures:
                            f.cancel()
                        break
                    
                    try:
                        res = future.result()
                        algo_name = res['algorithm']
                        density = res['density']
                        epsilon = res['pred_error_pct']
                        gamma = res['gamma']
                        tau_max = res['tau_max']
                        seed = res['seed']
                        metrics = res['metrics']
                        run_dt = res['run_dt']
                        
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
                            'AoI_violation_rate': round(metrics['AoI_violation_rate'], 6),
                            'PCO': round(metrics['PCO'], 6),
                            'RLBI': round(metrics['RLBI'], 6),
                        }
                        full_writer.writerow(row)
                        full_f.flush()
                        os.fsync(full_f.fileno())
                        run_count += 1
                        new_count += 1
                        
                        elapsed = time.time() - t0
                        eta_s = (elapsed / max(1, new_count)) * (total_runs - run_count)
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
                        
                        last_combo = (algo_name, density, epsilon, gamma, tau_max, seed)
                        now = time.time()
                        elapsed_since_t0 = now - t0
                        interval = _heartbeat_interval(elapsed_since_t0)
                        if now - last_heartbeat_t >= interval:
                            now_dt = datetime.datetime.now()
                            now_str_hb = now_dt.strftime('%Y-%m-%d %H:%M:%S')
                            elapsed_fmt = _fmt_elapsed(elapsed_since_t0)
                            pct = (run_count / total_runs * 100 if total_runs > 0 else 0.0)
                            avg_run_s = (elapsed_since_t0 / new_count if new_count > 0 else 0.0)
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

                    except Exception as e:
                        print(f"  [simulate] Error in simulation worker: {e}", flush=True)"""

match = re.search(r"    try:\n        for density in cfg\['density_range'\]:.*?                                # ── End heartbeat polling ─────────────", content, re.DOTALL)
if match:
    content = content[:match.start()] + sim_new + content[match.end():]
else:
    print("Could not find sim_old_start block to replace!")

# argparse changes
arg_old = """    parser.add_argument(
        '--verbose', action='store_true', default=True,
        help='Verbose output (default: True)',
    )
    args = parser.parse_args()"""

arg_new = """    parser.add_argument(
        '--verbose', action='store_true', default=True,
        help='Verbose output (default: True)',
    )
    parser.add_argument(
        '--workers', type=int, default=max(1, min(10, (os.cpu_count() or 2) // 2)),
        help='Number of parallel worker processes (default: max 10 or half of CPU count)',
    )
    args = parser.parse_args()"""
content = content.replace(arg_old, arg_new)

content = content.replace("verbose = args.verbose", "verbose = args.verbose\n    workers = args.workers")

content = content.replace("generate_trajectories(scenario_id, output_dir, verbose)", "generate_trajectories(scenario_id, output_dir, workers, verbose)")
content = content.replace("run_scenario(scenario_id, output_dir, verbose)", "run_scenario(scenario_id, output_dir, workers, verbose)")

with open("run_scenario_patched.py", "w") as f:
    f.write(content)

print("Patch applied to run_scenario_patched.py")
