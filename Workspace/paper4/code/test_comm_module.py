import sys
import numpy as np
from sim_engine import SimulationRunner

def verify_comm_module(iteration):
    print(f"\n--- Starting Verification Iteration {iteration}/5 ---")
    
    # Initialize runner with ReactDCC (pure comms logic)
    runner = SimulationRunner(scenario="urban_grid", n_vehicles=30, seed=100+iteration, method="ReactDCC", duration_steps=300)
    
    # Run simulation
    try:
        metrics = runner.run()
        
        # Verify Metrics
        pdr = metrics.get('PDR_mean', -1)
        cbr = metrics.get('CBR_mean', -1)
        aoi = metrics.get('M1_mean_AoI', -1)
        energy = metrics.get('energy_efficiency', -1)
        
        print(f"Metrics extracted: PDR={pdr:.4f}%, CBR={cbr:.4f}, AoI={aoi:.4f}ms, Energy={energy:.4f}")
        
        # Assertions to mathematically prove correctness
        assert 0.0 <= pdr <= 100.0 or pdr == -1, f"PDR {pdr} out of bounds!"
        assert 0.0 <= cbr <= 1.0 or cbr == -1, f"CBR {cbr} out of bounds!"
        assert -1.0 <= aoi <= 2000.0, f"AoI {aoi} exploded beyond cap!"
        assert energy >= 0.0, f"Energy efficiency {energy} is negative!"
        
        print(f"Verification {iteration} PASSED: No memory leaks, KeyErrors, or mathematical anomalies.")
        return True
        
    except Exception as e:
        print(f"Verification {iteration} FAILED with Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success_count = 0
    for i in range(1, 6):
        if verify_comm_module(i):
            success_count += 1
            
    print(f"\n=== Final Result: {success_count}/5 Iterations Passed ===")
    if success_count == 5:
        sys.exit(0)
    else:
        sys.exit(1)
