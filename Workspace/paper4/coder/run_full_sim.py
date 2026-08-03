import os
import sys
import csv
import multiprocessing
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "../code"))
from sim_engine import SimulationRunner

# List of all 16 models
MODELS = [
    "Fixed10Hz",
    "ReactDCC",
    "AdaptDCC",
    "Heuristic",
    "QLearning",
    "SARSA",
    "DecTree",
    "StdMLP",
    "ActorCritic",
    "PPO",
    "DDPG",
    "DecisionTransformer",
    "DuelingDQN",
    "MoEDQN",
    "Proposed",
    "ResNetMoEDQN"
]

DENSITIES = list(range(10, 101))
SEEDS = [42] # We can use one or a few seeds to generate raw data

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
OUT_CSV = os.path.join(DATA_DIR, "raw_metrics_density.csv")

def write_header_if_needed():
    file_exists = os.path.isfile(OUT_CSV)
    with open(OUT_CSV, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "method", "n_vehicles", "seed", "runtime_sec", 
                "n_cam_events", "CBR_mean", "AoI_mean", "PDR_mean", 
                "energy_efficiency", "ETSI_compliance", "timestamp"
            ])

def run_simulation(args):
    method, density, seed = args
    print(f"[{method}] Starting density {density} with seed {seed}")
    
    method_params = {}
    if method == "AdaptDCC":
        method_params = {'cbr_target': 0.60}
        
    runner = SimulationRunner(
        scenario='urban_grid',
        n_vehicles=density,
        seed=seed,
        method=method,
        method_params=method_params,
        duration_steps=3600,
        warmup_s=30.0
    )
    metrics = runner.run()
    
    # Write result immediately
    with open(OUT_CSV, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            method, density, seed, metrics.get('runtime_sec', 0),
            metrics.get('n_cam_events', 0), metrics.get('CBR_mean', 0),
            metrics.get('AoI_mean', 0), metrics.get('PDR_mean', 0),
            metrics.get('energy_efficiency', 0), metrics.get('ETSI_compliance', 0),
            time.time()
        ])
    print(f"[{method}] Completed density {density} with seed {seed}")
    return method, density

def main():
    write_header_if_needed()
    
    # Build tasks
    tasks = []
    for method in MODELS:
        for density in DENSITIES:
            for seed in SEEDS:
                tasks.append((method, density, seed))
                
    print(f"Total tasks to run: {len(tasks)}")
    
    # We will process models sequentially to report as requested, but multi-process densities
    for method in MODELS:
        print(f"Starting pipeline for model: {method}")
        method_tasks = [(m, d, s) for (m, d, s) in tasks if m == method]
        
        with multiprocessing.Pool(processes=min(multiprocessing.cpu_count(), len(DENSITIES))) as pool:
            pool.map(run_simulation, method_tasks)
            
        print(f"Completed pipeline for model: {method}")
        # The agent should be notified to report. We will write a signal file.
        with open(os.path.join(DATA_DIR, f"{method}_completed.txt"), "w") as f:
            f.write("done\n")

if __name__ == "__main__":
    main()
