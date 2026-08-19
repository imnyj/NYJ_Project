import os
import glob
import pandas as pd

print("=== Check code files related to evaluations and plots ===")
for p in sorted(glob.glob("/home/imnyj/Workspace/paper4/code/*plot*.py")):
    print(p)

for p in sorted(glob.glob("/home/imnyj/Workspace/paper4/code/*ablation*.py")):
    print(p)

for p in sorted(glob.glob("/home/imnyj/Workspace/paper4/code/*optuna*.py")):
    print(p)

print("\n=== Check evaluation/eval_density_results.csv ===")
df_dens = pd.read_csv("/home/imnyj/Workspace/paper4/data/evaluation/eval_density_results.csv")
print(df_dens.groupby('method')[['PDR_mean', 'AoI_mean', 'CBR_mean', 'energy_efficiency']].mean())

print("\n=== Check models convergence csvs ===")
for p in sorted(glob.glob("/home/imnyj/Workspace/paper4/data/models/*_convergence.csv")):
    df = pd.read_csv(p)
    name = os.path.basename(p).replace('_convergence.csv', '')
    print(f"Model {name:20s}: Episodes {len(df)}, Final Reward: {df['Reward'].iloc[-1]:.2f}, Final PDR: {df['PDR_mean'].iloc[-1]:.2f}, Final AoI: {df['AoI_mean'].iloc[-1]:.2f}")

