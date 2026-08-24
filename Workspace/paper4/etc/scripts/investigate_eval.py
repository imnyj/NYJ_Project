import os
import pandas as pd
import numpy as np

base_dir = "/home/imnyj/Workspace/paper4"
data_dir = os.path.join(base_dir, "data")

print("=== INVESTIGATION 1: REMO-DQN in reward_convergence vs ablation_study ===")
df_conv = pd.read_csv(os.path.join(data_dir, "reward_convergence.csv"))
df_study = pd.read_csv(os.path.join(data_dir, "ablation_study.csv"))

print("reward_convergence.csv Head:")
print(df_conv[["Episode", "Global_Step", "REMO-DQN", "Fixed 10Hz", "ReactDCC", "AdaptDCC", "MoEDQN"]].head(5))
print("reward_convergence.csv Tail:")
print(df_conv[["Episode", "Global_Step", "REMO-DQN", "Fixed 10Hz", "ReactDCC", "AdaptDCC", "MoEDQN"]].tail(5))

print("\nablation_study.csv Head:")
print(df_study[["Episode", "Global_Step", "REMO-DQN", "w/o ResNet", "w/o MoE", "w/o Dueling"]].head(5))
print("ablation_study.csv Tail:")
print(df_study[["Episode", "Global_Step", "REMO-DQN", "w/o ResNet", "w/o MoE", "w/o Dueling"]].tail(5))

print("\n=== INVESTIGATION 2: eval_density_results.csv ===")
eval_path = os.path.join(data_dir, "evaluation", "eval_density_results.csv")
if os.path.exists(eval_path):
    df_eval = pd.read_csv(eval_path)
    print(f"eval_density_results.csv Shape: {df_eval.shape}")
    print(f"Columns: {list(df_eval.columns)}")
    print(f"Methods: {df_eval['method'].unique()}")
    print(f"Densities: {df_eval['density'].unique()}")
    print("\nSample rows:")
    print(df_eval.head(10))
else:
    print(f"File not found: {eval_path}")

