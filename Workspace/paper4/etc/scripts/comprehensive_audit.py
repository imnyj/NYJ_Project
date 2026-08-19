import os
import glob
import pandas as pd
import numpy as np
import torch
import json

def safe_val(val):
    if pd.isna(val):
        return None
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        return float(val)
    return str(val)

def analyze_all():
    summary = {}
    
    # 1. Models & Convergence Analysis in data/models/
    print("=== 1. Checking data/models/ ===")
    models_dir = "/home/imnyj/Workspace/paper4/data/models"
    model_files = sorted(os.listdir(models_dir)) if os.path.exists(models_dir) else []
    summary['data_models'] = {}
    for mf in model_files:
        fpath = os.path.join(models_dir, mf)
        if mf.endswith(".csv"):
            df = pd.read_csv(fpath)
            if len(df) == 0:
                summary['data_models'][mf] = {"rows": 0, "columns": list(df.columns)}
                continue
            max_step = df['Global_Step'].max() if 'Global_Step' in df.columns else None
            max_ep = df['Episode'].max() if 'Episode' in df.columns else None
            r_start = df['Reward'].iloc[0] if 'Reward' in df.columns else None
            r_end = df['Reward'].iloc[-1] if 'Reward' in df.columns else None
            r_mean_last10 = df['Reward'].tail(10).mean() if 'Reward' in df.columns else None
            r_mean_first10 = df['Reward'].head(10).mean() if 'Reward' in df.columns else None
            summary['data_models'][mf] = {
                "rows": len(df),
                "columns": list(df.columns),
                "max_ep": safe_val(max_ep),
                "max_step": safe_val(max_step),
                "r_start": safe_val(r_start),
                "r_end": safe_val(r_end),
                "r_mean_first10": safe_val(r_mean_first10),
                "r_mean_last10": safe_val(r_mean_last10),
                "is_converged": bool(r_mean_last10 > r_mean_first10) if (r_mean_last10 is not None and r_mean_first10 is not None) else None
            }
        elif mf.endswith(".pth") or mf.endswith(".pt") or mf.endswith(".pkl"):
            size = os.path.getsize(fpath)
            pth_info = {"size_bytes": size}
            if mf.endswith(".pth") or mf.endswith(".pt"):
                try:
                    ckpt = torch.load(fpath, map_location="cpu")
                    if isinstance(ckpt, dict):
                        pth_info["keys"] = list(ckpt.keys())[:10]
                        pth_info["num_keys"] = len(ckpt.keys())
                        pth_info["type"] = "dict"
                    elif hasattr(ckpt, 'state_dict'):
                        pth_info["type"] = "nn.Module"
                        pth_info["keys"] = list(ckpt.state_dict().keys())[:10]
                    else:
                        pth_info["type"] = str(type(ckpt))
                except Exception as e:
                    pth_info["load_error"] = str(e)
            summary['data_models'][mf] = pth_info

    # 2. Check code/ train logs and models
    print("=== 2. Checking code/ train logs ===")
    code_dir = "/home/imnyj/Workspace/paper4/code"
    code_csvs = sorted(glob.glob(os.path.join(code_dir, "*_train_log.csv")))
    summary['code_train_logs'] = {}
    for c_csv in code_csvs:
        fname = os.path.basename(c_csv)
        df = pd.read_csv(c_csv)
        if len(df) == 0:
            summary['code_train_logs'][fname] = {"rows": 0, "columns": list(df.columns)}
            continue
        step_col = [c for c in df.columns if 'step' in c.lower()]
        ep_col = [c for c in df.columns if 'ep' in c.lower()]
        r_col = [c for c in df.columns if 'reward' in c.lower()]
        summary['code_train_logs'][fname] = {
            "rows": len(df),
            "columns": list(df.columns),
            "max_step": safe_val(df[step_col[0]].max()) if step_col else None,
            "max_ep": safe_val(df[ep_col[0]].max()) if ep_col else None,
            "r_start": safe_val(df[r_col[0]].iloc[0]) if (r_col and len(df) > 0) else None,
            "r_end": safe_val(df[r_col[0]].iloc[-1]) if (r_col and len(df) > 0) else None
        }

    # 3. Check reward_convergence.csv in data/ and coder/data/
    print("=== 3. Checking reward_convergence.csv ===")
    summary['reward_convergence'] = {}
    for rc_path in ["/home/imnyj/Workspace/paper4/data/reward_convergence.csv",
                    "/home/imnyj/Workspace/paper4/coder/data/reward_convergence.csv"]:
        if os.path.exists(rc_path):
            df = pd.read_csv(rc_path)
            summary['reward_convergence'][rc_path] = {
                "rows": len(df),
                "columns": list(df.columns),
                "head": df.head(2).map(safe_val).to_dict(orient='records'),
                "tail": df.tail(2).map(safe_val).to_dict(orient='records'),
                "summary_stats": df.describe().map(safe_val).to_dict()
            }

    # 4. Check Ablation Studies (Structure, Reward, State)
    print("=== 4. Checking Ablations ===")
    summary['ablations'] = {}
    for ab_type in ['ablation_structure', 'ablation_reward', 'ablation_state']:
        ab_dir = os.path.join("/home/imnyj/Workspace/paper4/data", ab_type)
        files = sorted(os.listdir(ab_dir)) if os.path.exists(ab_dir) else []
        summary['ablations'][ab_type] = {}
        for f in files:
            fpath = os.path.join(ab_dir, f)
            if f.endswith(".csv"):
                df = pd.read_csv(fpath)
                summary['ablations'][ab_type][f] = {
                    "rows": len(df),
                    "columns": list(df.columns),
                    "head": df.head(1).map(safe_val).to_dict(orient='records') if len(df) > 0 else [],
                    "tail": df.tail(1).map(safe_val).to_dict(orient='records') if len(df) > 0 else []
                }
            elif f.endswith(".pth") or f.endswith(".pt") or f.endswith(".pkl"):
                summary['ablations'][ab_type][f] = {"size_bytes": os.path.getsize(fpath)}
    
    # Check data/ablation_study.csv and coder/data/ablation_study.csv
    for ab_csv in ["/home/imnyj/Workspace/paper4/data/ablation_study.csv",
                   "/home/imnyj/Workspace/paper4/coder/data/ablation_study.csv"]:
        if os.path.exists(ab_csv):
            df = pd.read_csv(ab_csv)
            summary['ablations'][ab_csv] = {
                "rows": len(df),
                "columns": list(df.columns),
                "content": df.map(safe_val).to_dict(orient='records')
            }

    # 5. Check Optuna
    print("=== 5. Checking Optuna ===")
    optuna_dir = "/home/imnyj/Workspace/paper4/data/optuna"
    opt_files = sorted(os.listdir(optuna_dir)) if os.path.exists(optuna_dir) else []
    summary['optuna_files'] = {}
    for of in opt_files:
        fpath = os.path.join(optuna_dir, of)
        if of.endswith(".csv"):
            df = pd.read_csv(fpath)
            summary['optuna_files'][of] = df.map(safe_val).to_dict(orient='records')
        elif of.endswith(".json"):
            with open(fpath, "r") as jf:
                summary['optuna_files'][of] = json.load(jf)
    
    for opt_table in ["/home/imnyj/Workspace/paper4/data/optuna_sensitivity_table.csv",
                      "/home/imnyj/Workspace/paper4/data/optuna_sensitivity.csv",
                      "/home/imnyj/Workspace/paper4/visualizer/optuna_sensitivity_table.csv"]:
        if os.path.exists(opt_table):
            df = pd.read_csv(opt_table)
            summary['optuna_files'][opt_table] = {
                "rows": len(df),
                "columns": list(df.columns),
                "content": df.map(safe_val).to_dict(orient='records')
            }

    # 6. Check Time & Environment metrics
    print("=== 6. Checking Time & Environment Metrics ===")
    eval_csvs = [
        "/home/imnyj/Workspace/paper4/data/cbr_trace.csv",
        "/home/imnyj/Workspace/paper4/data/pdr_vs_density.csv",
        "/home/imnyj/Workspace/paper4/data/aoi_vs_density.csv",
        "/home/imnyj/Workspace/paper4/data/pdr_vs_distance.csv",
        "/home/imnyj/Workspace/paper4/data/aoi_vs_distance.csv",
        "/home/imnyj/Workspace/paper4/data/evaluation/eval_speed_results.csv",
        "/home/imnyj/Workspace/paper4/data/evaluation/eval_density_results.csv",
        "/home/imnyj/Workspace/paper4/data/moe_routing.csv",
        "/home/imnyj/Workspace/paper4/data/tsne_clustering.csv",
        "/home/imnyj/Workspace/paper4/data/hardware_feasibility_table.csv",
        "/home/imnyj/Workspace/paper4/data/hardware_feasibility.csv"
    ]
    summary['eval_metrics'] = {}
    for ec in eval_csvs:
        if os.path.exists(ec):
            df = pd.read_csv(ec)
            summary['eval_metrics'][ec] = {
                "rows": len(df),
                "columns": list(df.columns),
                "head": df.head(3).map(safe_val).to_dict(orient='records') if len(df) > 0 else [],
                "tail": df.tail(2).map(safe_val).to_dict(orient='records') if len(df) > 0 else []
            }

    # Save complete JSON summary
    out_json = "/home/imnyj/Workspace/paper4/etc/temp/audit_summary.json"
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nAudit complete! Saved to {out_json}")

if __name__ == "__main__":
    analyze_all()
