import os
import glob
import pandas as pd

base = "/home/imnyj/Workspace/paper4/data"

print("=== Checking subdirectories in data ===")
for sub in ["ablation_structure", "ablation_reward", "ablation_state"]:
    p = os.path.join(base, sub)
    print(f"\n--- Subdir: {sub} ---")
    if not os.path.exists(p):
        print("Does not exist.")
        continue
    for f in sorted(os.listdir(p)):
        fp = os.path.join(p, f)
        if f.endswith(".csv"):
            df = pd.read_csv(fp)
            print(f"File: {f:30s} | Shape: {str(df.shape):10s} | Cols: {list(df.columns)}")
        elif f.endswith(".pth"):
            size = os.path.getsize(fp)
            print(f"Model: {f:30s} | Size: {size} bytes")

