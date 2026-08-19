import pandas as pd
import numpy as np
import glob
import os

print("=== Checking data/models/*_convergence.csv ===")
models_data = {}
for p in sorted(glob.glob("/home/imnyj/Workspace/paper4/data/models/*_convergence.csv")):
    m_name = os.path.basename(p).replace("_convergence.csv", "")
    df = pd.read_csv(p)
    models_data[m_name] = df
    print(f"Loaded {m_name}: shape={df.shape}, cols={list(df.columns)}")

print(f"Total models loaded: {len(models_data)}")

print("\n=== Checking coder/data/*.csv ===")
for p in sorted(glob.glob("/home/imnyj/Workspace/paper4/coder/data/*.csv")):
    df = pd.read_csv(p)
    print(f"File {os.path.basename(p)}: shape={df.shape}, cols={list(df.columns)}")

