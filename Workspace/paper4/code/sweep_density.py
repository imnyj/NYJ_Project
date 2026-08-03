import os
import csv
from sim_engine import SimulationRunner

def main():
    densities = [20, 40, 60, 80, 100, 120, 140, 160]
    seeds = [42, 123, 456]
    methods = [
        ("ReactDCC", {}),
        ("AdaptDCC", {'cbr_target': 0.60}),
        ("Heuristic", {}),
        ("Fixed10Hz", {}),
        ("Proposed", {})
    ]
    
    DATA_DIR = "."
    os.makedirs(DATA_DIR, exist_ok=True)
    
    out_file = os.path.join(DATA_DIR, "sweep_density_results_v2.csv")
    
    # Check if file exists to write header
    file_exists = os.path.isfile(out_file)
    with open(out_file, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "method", "scenario", "n_vehicles", "seed", "runtime_sec", 
                "n_cam_events", "CBR_mean", "AoI_mean", "PDR_mean", 
                "energy_efficiency", "ETSI_compliance"
            ])
            
        print("Starting Vehicle Density Sweep Simulations...")
        for density in densities:
            print(f"\n========== RUNNING DENSITY: {density} VEHICLES ==========")
            for method_name, method_params in methods:
                for seed in seeds:
                    print(f"  -> Method: {method_name}, Seed: {seed}")
                    runner = SimulationRunner(
                        scenario='urban_grid',
                        n_vehicles=density,
                        seed=seed,
                        method=method_name,
                        method_params=method_params,
                        duration_steps=3600,
                        warmup_s=30.0
                    )
                    metrics = runner.run()
                    
                    writer.writerow([
                        method_name,
                        'urban_grid',
                        density,
                        seed,
                        metrics["runtime_sec"],
                        metrics["n_cam_events"],
                        metrics["CBR_mean"],
                        metrics["AoI_mean"],
                        metrics["PDR_mean"],
                        metrics["energy_efficiency"],
                        metrics["ETSI_compliance"]
                    ])
                    f.flush()  # Ensure data is saved immediately
                    
    print("\n[SUCCESS] Density sweep completed. Results saved to:", out_file)

if __name__ == "__main__":
    main()
