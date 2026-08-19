import os
import pandas as pd
import numpy as np
import glob

print("=== Checking coder/data CSV files ===")
data_dir = "/home/imnyj/Workspace/paper4/coder/data"
for f in sorted(os.listdir(data_dir)):
    if f.endswith(".csv"):
        path = os.path.join(data_dir, f)
        df = pd.read_csv(path)
        print(f"\n--- {f} (shape: {df.shape}) ---")
        print("Columns:", list(df.columns))
        print(df.head(3))
        if len(df) > 3:
            print("Tail:")
            print(df.tail(2))
