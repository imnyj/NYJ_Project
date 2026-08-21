import os

filepath = "/home/imnyj/papers/paper4/sim/sensitivity_runner.py"
with open(filepath, "r") as f:
    content = f.read()

# 1. Modify SA1 loop
old_sa1 = """    for n_veh in [10, 20, 30, 50, 75, 100]:
        for seed in BASE_SEEDS:
            sa1_runs.append({
                "param_name": "n_vehicles",
                "param_value": n_veh,
                "seed": seed,
                "runner_kwargs": {
                    "scenario": BASE_SCENARIO,
                    "n_vehicles": n_veh,
                    "seed": seed,
                    "method": "ReactDCC",
                    "method_params": {},
                    "duration_steps": DURATION_STEPS,
                    "warmup_s": WARMUP_S,
                },
            })"""

new_sa1 = """    methods_sa1 = ["ReactDCC", "AdaptDCC", "Heuristic", "Fixed10Hz", "DecTree", "StdMLP", "Proposed"]
    for n_veh in [10, 20, 30, 50, 75, 100]:
        for method in methods_sa1:
            for seed in BASE_SEEDS:
                sa1_runs.append({
                    "param_name": "n_vehicles",
                    "param_value": n_veh,
                    "method": method,  # track method explicitly
                    "seed": seed,
                    "runner_kwargs": {
                        "scenario": BASE_SCENARIO,
                        "n_vehicles": n_veh,
                        "seed": seed,
                        "method": method,
                        "method_params": {},
                        "duration_steps": DURATION_STEPS,
                        "warmup_s": WARMUP_S,
                    },
                })"""

content = content.replace(old_sa1, new_sa1)

# 2. Add CSV_COLUMNS addition if needed? 
# We'll just leave CSV_COLUMNS alone. But `run_one` needs to return arrays.
old_run_one_return = """            "ETSI_compliance": metrics.get("ETSI_compliance"),
            "runtime_sec": metrics.get("runtime_sec"),
            "n_cam_events": metrics.get("n_cam_events"),
            "status": "ok",
        })"""

new_run_one_return = """            "ETSI_compliance": metrics.get("ETSI_compliance"),
            "runtime_sec": metrics.get("runtime_sec"),
            "n_cam_events": metrics.get("n_cam_events"),
            "cbr_history": metrics.get("cbr_history", []),
            "distance_pdr": metrics.get("distance_pdr", []),
            "method": run_cfg.get("method", run_cfg["runner_kwargs"]["method"]),
            "status": "ok",
        })"""

content = content.replace(old_run_one_return, new_run_one_return)

# 3. Add array dumping in run_sweep
old_run_sweep = """            writer.writerow(row)
            f.flush()
            results.append(row)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] {sweep_id} done. CSV saved.")
    return results"""

new_run_sweep = """            
            # Remove arrays before writing to CSV to avoid huge cells
            row_csv = {k: v for k, v in row.items() if k not in ["cbr_history", "distance_pdr"]}
            # But we want 'method' in CSV for SA1?
            # Let's dynamically add 'method' if not in CSV_COLUMNS
            if "method" not in writer.fieldnames:
                writer.fieldnames.append("method")
            writer.writerow(row_csv)
            f.flush()
            results.append(row)

    # Dump arrays
    import json
    arrays_path = os.path.join(DATA_DIR, f"{sweep_id}_arrays.json")
    with open(arrays_path, "w") as jf:
        json.dump(results, jf)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] {sweep_id} done. CSV and Arrays saved.")
    return results"""

content = content.replace(old_run_sweep, new_run_sweep)

with open(filepath, "w") as f:
    f.write(content)
print("Runner patched.")
