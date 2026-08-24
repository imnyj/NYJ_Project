#!/usr/bin/env python3
import os
import glob
import pandas as pd
import numpy as np
from scipy import stats

def inspect_all_data():
    project_root = "/home/imnyj/Workspace/paper4"
    data_dir = os.path.join(project_root, "data")
    models_dir = os.path.join(data_dir, "models")
    
    print("=== DATA FILES INSPECTION ===")
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    for f in sorted(csv_files):
        try:
            df = pd.read_csv(f)
            print(f"\n[File] {os.path.basename(f)} (Shape: {df.shape})")
            print(f"Columns: {list(df.columns)}")
            print(df.head(2))
        except Exception as e:
            print(f"[ERROR reading {f}]: {e}")

    print("\n=== MODELS CONVERGENCE FILES INSPECTION ===")
    conv_files = glob.glob(os.path.join(models_dir, "*_convergence.csv"))
    for f in sorted(conv_files):
        try:
            df = pd.read_csv(f)
            print(f"\n[Model Conv] {os.path.basename(f)} (Shape: {df.shape})")
            print(f"Columns: {list(df.columns)}")
            print(f"Episodes: {len(df)}, Epsilon range: [{df['Epsilon'].min() if 'Epsilon' in df.columns else 'N/A'}, {df['Epsilon'].max() if 'Epsilon' in df.columns else 'N/A'}]")
        except Exception as e:
            print(f"[ERROR reading {f}]: {e}")

if __name__ == "__main__":
    inspect_all_data()
