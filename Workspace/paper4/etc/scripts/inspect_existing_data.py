import os
import pandas as pd
import glob

print("=== Checking coder/data CSVs ===")
coder_csvs = glob.glob("/home/imnyj/Workspace/paper4/coder/data/*.csv")
for f in sorted(coder_csvs):
    try:
        df = pd.read_csv(f)
        print(f"File: {os.path.basename(f)}, Shape: {df.shape}")
        print("  Columns:", list(df.columns))
        print("  Head(2):\n", df.head(2))
        print("-" * 50)
    except Exception as e:
        print(f"File: {os.path.basename(f)}, Error: {e}")

print("\n=== Checking data/ CSVs ===")
data_csvs = glob.glob("/home/imnyj/Workspace/paper4/data/**/*.csv", recursive=True)
for f in sorted(data_csvs):
    try:
        df = pd.read_csv(f)
        print(f"File: {f.replace('/home/imnyj/Workspace/paper4/data/', '')}, Shape: {df.shape}")
        print("  Columns:", list(df.columns)[:10])
        print("-" * 50)
    except Exception as e:
        print(f"File: {f}, Error: {e}")

