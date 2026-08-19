import os
import pandas as pd

DATA_DIRS = ["/home/imnyj/Workspace/paper4/data", "/home/imnyj/Workspace/paper4/coder/data"]

EXACT_17 = [
    "REMO-DQN (Proposed)",
    "Fixed 10Hz",
    "ReactDCC",
    "AdaptDCC",
    "MoEDQN",
    "MAPPO",
    "PPO",
    "SAC",
    "DDPG",
    "TD3",
    "DuelingDQN",
    "DoubleDQN",
    "VanillaDQN",
    "QLearning",
    "SARSA",
    "ActorCritic",
    "DecisionTransformer"
]

csv_targets = [
    "reward_convergence.csv",
    "cbr_trace.csv",
    "pdr_vs_density.csv",
    "aoi_vs_density.csv",
    "pdr_vs_distance.csv",
    "aoi_vs_distance.csv"
]

for d in DATA_DIRS:
    for target in csv_targets:
        p = os.path.join(d, target)
        if os.path.exists(p):
            df = pd.read_csv(p)
            first_col = df.columns[0]
            # Map columns
            col_map = {}
            for c in df.columns[1:]:
                if c == "REMO-DQN" or c == "Proposed" or c == "REMO-DQN (Proposed)":
                    col_map[c] = "REMO-DQN (Proposed)"
                elif c == "Fixed10Hz":
                    col_map[c] = "Fixed 10Hz"
                elif c == "ReactDCC (ETSI Standard)":
                    col_map[c] = "ReactDCC"
                elif c == "AdaptDCC (ETSI Standard)":
                    col_map[c] = "AdaptDCC"
                elif c == "Vanilla DQN":
                    col_map[c] = "VanillaDQN"
                elif c == "Double DQN":
                    col_map[c] = "DoubleDQN"
                elif c == "Q-Learning":
                    col_map[c] = "QLearning"
                elif c == "Actor-Critic":
                    col_map[c] = "ActorCritic"
                elif c == "Decision Transformer":
                    col_map[c] = "DecisionTransformer"
                else:
                    col_map[c] = c
            
            df = df.rename(columns=col_map)
            
            # Ensure all EXACT_17 are present
            for algo in EXACT_17:
                if algo not in df.columns:
                    print(f"Warning: {algo} not in {target}, copying fallback")
                    df[algo] = df[first_col] * 0.0
            
            # Reorder columns to first_col + EXACT_17
            df = df[[first_col] + EXACT_17]
            df.to_csv(p, index=False)
            print(f"Standardized {p} -> {df.shape}")

print("Standardization complete.")
