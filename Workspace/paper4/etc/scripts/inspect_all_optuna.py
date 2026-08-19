import os
import glob
import json
import pandas as pd

print("=== Optuna JSON ===")
with open("/home/imnyj/Workspace/paper4/data/optuna/all_best_params.json") as f:
    data = json.load(f)
    for k, v in data.items():
        print(f"Model: {k:20s} -> {v}")

print("\n=== Optuna CSVs ===")
for p in sorted(glob.glob("/home/imnyj/Workspace/paper4/data/optuna/*.csv")):
    df = pd.read_csv(p)
    print(f"--- {os.path.basename(p)} ---")
    print(df)

