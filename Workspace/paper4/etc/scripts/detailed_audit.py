import os
import glob
import pandas as pd
import numpy as np
import json
import torch

def detailed_audit():
    print("=================================================================")
    print("DETAILED SCIENTIFIC AUDIT OF PAPER4 DATA AND MODELS")
    print("=================================================================\n")
    
    # 1. Inspect data/evaluation/
    print("--- [1] data/evaluation/ Check ---")
    dens_csv = "/home/imnyj/Workspace/paper4/data/evaluation/eval_density_results.csv"
    speed_csv = "/home/imnyj/Workspace/paper4/data/evaluation/eval_speed_results.csv"
    if os.path.exists(dens_csv):
        df_d = pd.read_csv(dens_csv)
        print(f"eval_density_results.csv: {len(df_d)} rows")
        print(f"  Methods ({df_d['method'].nunique()}): {df_d['method'].unique()}")
        print(f"  Densities ({df_d['density'].nunique()}): {sorted(df_d['density'].unique())}")
        print(f"  Seeds ({df_d['seed'].nunique()}): {df_d['seed'].unique()}")
        print("  Sample stats by method (PDR_mean, AoI_mean, CBR_mean):")
        print(df_d.groupby('method')[['PDR_mean', 'AoI_mean', 'CBR_mean']].mean().round(2).head(6))
        
    if os.path.exists(speed_csv):
        df_s = pd.read_csv(speed_csv)
        print(f"\neval_speed_results.csv: {len(df_s)} rows")
        print(f"  Methods ({df_s['method'].nunique()}): {df_s['method'].unique()}")
        print(f"  Speeds ({df_s['speed'].nunique()}): {sorted(df_s['speed'].unique())}")
        print(f"  Seeds ({df_s['seed'].nunique()}): {df_s['seed'].unique()}")

    # 2. Inspect coder/data/raw_metrics_density.csv
    print("\n--- [2] coder/data/raw_metrics_density.csv Check ---")
    raw_dens_csv = "/home/imnyj/Workspace/paper4/coder/data/raw_metrics_density.csv"
    if os.path.exists(raw_dens_csv):
        df_rd = pd.read_csv(raw_dens_csv)
        print(f"raw_metrics_density.csv: {len(df_rd)} rows")
        print(f"  Methods ({df_rd['method'].nunique()}): {df_rd['method'].unique()}")
        print(f"  Vehicle count range: {df_rd['n_vehicles'].min()} ~ {df_rd['n_vehicles'].max()}")
        print(df_rd.groupby('method')[['PDR_mean', 'AoI_mean', 'CBR_mean']].mean().round(2).head(6))

    # 3. Inspect .pth Checkpoint Validity
    print("\n--- [3] Checkpoint Structure & Weight Inspection ---")
    models_dir = "/home/imnyj/Workspace/paper4/data/models"
    for mf in sorted(os.listdir(models_dir)):
        fpath = os.path.join(models_dir, mf)
        if mf.endswith(".pth"):
            try:
                ckpt = torch.load(fpath, map_location="cpu")
                if isinstance(ckpt, dict):
                    num_params = sum([v.numel() for v in ckpt.values() if isinstance(v, torch.Tensor)])
                    print(f"[{mf}] PyTorch state_dict | Total tensors: {len(ckpt)} | Total scalar params: {num_params:,} | Size: {os.path.getsize(fpath):,} B")
                else:
                    print(f"[{mf}] PyTorch Object: {type(ckpt)} | Size: {os.path.getsize(fpath):,} B")
            except Exception as e:
                print(f"[{mf}] Error loading: {e}")
        elif mf.endswith(".pkl"):
            print(f"[{mf}] Pickle Model | Size: {os.path.getsize(fpath):,} B")

    # 4. Check All Optuna Files
    print("\n--- [4] Optuna Files & Parameters Check ---")
    optuna_dir = "/home/imnyj/Workspace/paper4/data/optuna"
    json_path = os.path.join(optuna_dir, "all_best_params.json")
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            jdata = json.load(f)
        print(f"all_best_params.json keys ({len(jdata)}): {list(jdata.keys())}")
        print("Sample Optuna best params for REMO-DQN / ResNetMoEDQN:")
        for k in ['REMO-DQN', 'ResNetMoEDQN', 'MoEDQN', 'PPO', 'SAC']:
            if k in jdata:
                print(f"  {k}: {jdata[k]}")

    # 5. Check Structure / Reward / State Ablation Directories
    print("\n--- [5] Ablation Detail Check ---")
    for ab_name in ['ablation_structure', 'ablation_reward', 'ablation_state']:
        p = os.path.join("/home/imnyj/Workspace/paper4/data", ab_name)
        flist = sorted(os.listdir(p)) if os.path.exists(p) else []
        print(f"\n{ab_name} directory contains {len(flist)} files:")
        for f in flist:
            fp = os.path.join(p, f)
            if f.endswith(".csv"):
                df_ab = pd.read_csv(fp)
                print(f"  {f} ({len(df_ab)} rows) -> cols: {list(df_ab.columns)}")
                if len(df_ab) > 0:
                    print(f"    first row: {df_ab.iloc[0].to_dict()}")
            elif f.endswith(".pth"):
                print(f"  {f} ({os.path.getsize(fp):,} B)")

    # 6. Check Coder vs Data vs Visualizer CSV Alignment
    print("\n--- [6] Cross-Directory CSV Alignment Check ---")
    target_files = [
        "reward_convergence.csv", "ablation_study.csv", "optuna_sensitivity_table.csv",
        "cbr_trace.csv", "pdr_vs_density.csv", "aoi_vs_density.csv",
        "pdr_vs_distance.csv", "aoi_vs_distance.csv", "moe_routing.csv",
        "tsne_clustering.csv", "hardware_feasibility_table.csv"
    ]
    for tf in target_files:
        p_data = os.path.join("/home/imnyj/Workspace/paper4/data", tf)
        p_coder = os.path.join("/home/imnyj/Workspace/paper4/coder/data", tf)
        p_vis = os.path.join("/home/imnyj/Workspace/paper4/visualizer", tf)
        
        e_data = os.path.exists(p_data)
        e_coder = os.path.exists(p_coder)
        e_vis = os.path.exists(p_vis)
        
        same_dc = False
        if e_data and e_coder:
            same_dc = (open(p_data, 'rb').read() == open(p_coder, 'rb').read())
            
        print(f"{tf:<30} | data: {e_data} | coder: {e_coder} | vis: {e_vis} | data==coder: {same_dc}")

if __name__ == "__main__":
    detailed_audit()
