import sys
import numpy as np
from sim_engine import SimulationRunner

# List of baseline method strings exactly as they are mapped in get_hook()
BASELINES = [
    "VanillaDQN", "DoubleDQN", "DuelingDQN", "QLearning", "SARSA", 
    "ActorCritic", "PPO", "DDPG", "DecisionTransformer", "SAC", 
    "MAPPO", "TD3", "MoEDQN"
]

def verify_baseline(method_name, iteration):
    print(f"\n--- Testing {method_name} (Iteration {iteration}/5) ---")
    try:
        # Run simulation using the correct method string
        # We use a short duration steps to verify it doesn't crash and tensors align
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=15, seed=200+iteration, method=method_name, duration_steps=50)
        
        # When we call runner.run(), it automatically uses the internal AI_DCC_Hook factory
        # Wait, run() usually trains if it's an RL agent. That's good enough to test implementation.
        metrics = runner.run()
        
        # We just need to check if it crashed. 
        # If it returned metrics, it means it completed the loop successfully.
        pdr = metrics.get('PDR_mean', -1)
        assert 0.0 <= pdr <= 100.0 or pdr == -1, f"PDR {pdr} out of bounds"
        print(f"PASSED {method_name} iteration {iteration}.")
        return True
    except Exception as e:
        print(f"FAILED {method_name} iteration {iteration} with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    total_failures = 0
    for method_name in BASELINES:
        successes = 0
        for i in range(1, 6):
            if verify_baseline(method_name, i):
                successes += 1
            else:
                total_failures += 1
        print(f"=== {method_name}: {successes}/5 iterations passed ===")
        
    if total_failures == 0:
        print("\nALL BASELINES VERIFIED SUCCESSFULLY.")
        sys.exit(0)
    else:
        print(f"\nTOTAL FAILURES DETECTED: {total_failures}")
        sys.exit(1)
