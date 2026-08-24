#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np

data_dir = "/home/imnyj/Workspace/paper4/data"

print("--- PDR vs Density column check ---")
df1 = pd.read_csv(os.path.join(data_dir, "pdr_vs_density.csv"))
for col in df1.columns:
    for idx, val in enumerate(df1[col]):
        if isinstance(val, (int, float)) and (val < 0 or val > 100):
            print(f"pdr_vs_density.csv Row {idx}, Col {col}: {val}")

print("\n--- PDR vs Distance column check ---")
df2 = pd.read_csv(os.path.join(data_dir, "pdr_vs_distance.csv"))
for col in df2.columns:
    for idx, val in enumerate(df2[col]):
        if isinstance(val, (int, float)) and (val < 0 or val > 100):
            print(f"pdr_vs_distance.csv Row {idx}, Col {col}: {val}")
