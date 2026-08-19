import os
import glob
import pandas as pd

def scan_csvs(root_dir):
    csv_files = glob.glob(os.path.join(root_dir, "**/*.csv"), recursive=True)
    # Filter out .git, .agents
    csv_files = [f for f in csv_files if ".git" not in f and ".agents" not in f]
    csv_files.sort()
    
    print(f"Total CSV files found: {len(csv_files)}\n")
    
    results = []
    for f in csv_files:
        try:
            df = pd.read_csv(f)
            num_rows, num_cols = df.shape
            cols = list(df.columns)
            results.append({
                "path": os.path.relpath(f, root_dir),
                "full_path": f,
                "rows": num_rows,
                "cols": num_cols,
                "columns": cols,
                "size_bytes": os.path.getsize(f)
            })
            print(f"[{os.path.relpath(f, root_dir)}] Rows: {num_rows}, Cols: {num_cols}, Size: {os.path.getsize(f)} bytes")
            print(f"  Columns: {cols[:8]}{'...' if len(cols) > 8 else ''}")
        except Exception as e:
            print(f"[{os.path.relpath(f, root_dir)}] Error reading CSV: {e}")
            results.append({
                "path": os.path.relpath(f, root_dir),
                "full_path": f,
                "rows": -1,
                "cols": -1,
                "columns": [str(e)],
                "size_bytes": os.path.getsize(f)
            })

if __name__ == "__main__":
    scan_csvs("/home/imnyj/Workspace/paper4")
