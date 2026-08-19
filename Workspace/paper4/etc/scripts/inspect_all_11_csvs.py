import os
import pandas as pd

DATA_DIR = "/home/imnyj/Workspace/paper4/data"

files = [
    "ablation_study.csv",
    "optuna_sensitivity.csv",
    "reward_convergence.csv",
    "tsne_clustering.csv",
    "moe_routing.csv",
    "cbr_trace.csv",
    "pdr_vs_density.csv",
    "aoi_vs_density.csv",
    "pdr_vs_distance.csv",
    "aoi_vs_distance.csv",
    "hardware_feasibility.csv"
]

print("=== INSPECTING ALL 11 TARGET CSV FILES IN data/ ===")
for fname in files:
    fpath = os.path.join(DATA_DIR, fname)
    if os.path.exists(fpath):
        df = pd.read_csv(fpath)
        print(f"\n[{fname}] Shape: {df.shape}")
        print("  Columns:", list(df.columns))
        print("  Head(2):\n", df.head(2))
    else:
        print(f"\n❌ MISSING: {fname}")

