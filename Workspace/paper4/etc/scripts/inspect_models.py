import os
import glob
import pandas as pd
import json

def inspect_models_and_convergence():
    models_dir = "/home/imnyj/Workspace/paper4/data/models"
    files = sorted(os.listdir(models_dir))
    
    print("=== DATA/MODELS/ FILE INVENTORY ===")
    csv_models = [f for f in files if f.endswith(".csv")]
    pth_models = [f for f in files if f.endswith(".pth") or f.endswith(".pkl")]
    
    print(f"Total CSVs: {len(csv_models)}, Total Model Checkpoints: {len(pth_models)}\n")
    
    table = []
    for csv_file in csv_models:
        model_name = csv_file.replace("_convergence.csv", "")
        csv_path = os.path.join(models_dir, csv_file)
        df = pd.read_csv(csv_path)
        
        # Check matching checkpoint
        pth_match = None
        for pf in pth_models:
            if pf.startswith(model_name):
                pth_match = pf
                break
        
        pth_path = os.path.join(models_dir, pth_match) if pth_match else None
        pth_size = os.path.getsize(pth_path) if (pth_path and os.path.exists(pth_path)) else 0
        
        rows = len(df)
        max_ep = df['Episode'].max() if 'Episode' in df.columns else None
        min_step = df['Global_Step'].min() if 'Global_Step' in df.columns else None
        max_step = df['Global_Step'].max() if 'Global_Step' in df.columns else None
        step_diff = df['Global_Step'].diff().iloc[1] if ('Global_Step' in df.columns and len(df) > 1) else None
        r_start = df['Reward'].iloc[0] if 'Reward' in df.columns else None
        r_end = df['Reward'].iloc[-1] if 'Reward' in df.columns else None
        r_max = df['Reward'].max() if 'Reward' in df.columns else None
        r_min = df['Reward'].min() if 'Reward' in df.columns else None
        r_mean_first10 = df['Reward'].head(10).mean() if 'Reward' in df.columns else None
        r_mean_last10 = df['Reward'].tail(10).mean() if 'Reward' in df.columns else None
        
        table.append({
            "model": model_name,
            "csv_rows": rows,
            "max_episode": max_ep,
            "min_global_step": min_step,
            "max_global_step": max_step,
            "step_interval": step_diff,
            "reward_start": round(r_start, 3) if r_start is not None else None,
            "reward_end": round(r_end, 3) if r_end is not None else None,
            "reward_first10_mean": round(r_mean_first10, 3) if r_mean_first10 is not None else None,
            "reward_last10_mean": round(r_mean_last10, 3) if r_mean_last10 is not None else None,
            "checkpoint_file": pth_match,
            "checkpoint_size_bytes": pth_size
        })
        
    df_summary = pd.DataFrame(table)
    print(df_summary.to_string(index=False))
    
    print("\n=== REWARD_CONVERGENCE.CSV IN DATA/ ===")
    rc_path = "/home/imnyj/Workspace/paper4/data/reward_convergence.csv"
    if os.path.exists(rc_path):
        df_rc = pd.read_csv(rc_path)
        print(f"Shape: {df_rc.shape}")
        print("Columns:", list(df_rc.columns))
        print("Head 3 rows:")
        print(df_rc.head(3))
        print("Tail 3 rows:")
        print(df_rc.tail(3))
        
    print("\n=== CODE/ DIRECTORY TRAIN LOGS ===")
    code_csvs = sorted(glob.glob("/home/imnyj/Workspace/paper4/code/*_train_log.csv"))
    for c_csv in code_csvs:
        df_c = pd.read_csv(c_csv)
        print(f"[{os.path.basename(c_csv)}] Rows: {len(df_c)}, Cols: {list(df_c.columns)}")
        if len(df_c) > 0:
            print(f"   First row: {df_c.iloc[0].to_dict()}")
            print(f"   Last row:  {df_c.iloc[-1].to_dict()}")

if __name__ == "__main__":
    inspect_models_and_convergence()
