import os
import csv
import json
import pandas as pd
from sensitivity_runner import define_sweeps, run_sweep, DATA_DIR

sweeps = define_sweeps()

# Filter to ONLY 'Proposed'
for sweep_id, runs in sweeps.items():
    proposed_runs = [r for r in runs if r.get("method") == "Proposed" or r.get("runner_kwargs", {}).get("method") == "Proposed"]
    print(f"{sweep_id} Proposed runs: {len(proposed_runs)}")
    
    # Run them
    if not proposed_runs: continue
    
    new_results = run_sweep(sweep_id + "_temp", proposed_runs)
    
    # Load existing CSV
    csv_path = os.path.join(DATA_DIR, f"{sweep_id}_results.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        # Drop old Proposed
        if 'method' in df.columns:
            df = df[df['method'] != 'Proposed']
        elif 'param_name' in df.columns:
            # for SA2, SA3, SA4 if method was param_value
            # Actually, SA2 has param_name='method', param_value='Proposed'
            mask = ~((df['param_name'] == 'method') & (df['param_value'] == 'Proposed'))
            df = df[mask]
            
        # Append new
        new_df = pd.DataFrame([r for r in new_results])
        if 'cbr_history' in new_df.columns:
            new_df = new_df.drop(columns=['cbr_history', 'distance_pdr'])
            
        df = pd.concat([df, new_df], ignore_index=True)
        df.to_csv(csv_path, index=False)
        print(f"Updated {csv_path}")

        # Update JSON arrays
        json_path = os.path.join(DATA_DIR, f"{sweep_id}_arrays.json")
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                old_arrays = json.load(f)
            
            # keep non-Proposed
            old_arrays = [x for x in old_arrays if x.get("method") != "Proposed"]
            old_arrays.extend(new_results)
            
            with open(json_path, 'w') as f:
                json.dump(old_arrays, f)
            print(f"Updated {json_path}")
