import os
import pandas as pd
import numpy as np

base_dir = "/home/imnyj/Workspace/paper4"

print("=== 1. Ablation Study Files Inspection ===")

files = {
    "ablation_study": os.path.join(base_dir, "data/ablation_study.csv"),
    "ablation_structure": os.path.join(base_dir, "data/ablation_structure.csv"),
    "ablation_reward": os.path.join(base_dir, "data/ablation_reward.csv")
}

for name, path in files.items():
    if not os.path.exists(path):
        print(f"[FAIL] {name} does not exist at {path}")
        continue
    df = pd.read_csv(path)
    print(f"\n--- {name} ---")
    print(f"Shape: {df.shape} (Rows: {df.shape[0]}, Cols: {df.shape[1]})")
    print(f"Columns: {list(df.columns)}")
    print(f"Null count:\n{df.isnull().sum()}")
    print("Summary Stats (First 3 columns / numeric):")
    print(df.describe())
    print("Head (3 rows):")
    print(df.head(3))
    print("Tail (3 rows):")
    print(df.tail(3))
