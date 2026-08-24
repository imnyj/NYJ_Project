import os
import sys
import pandas as pd
import numpy as np
import json

DATA_DIR = "/home/imnyj/Workspace/paper4/data"
MODELS_DIR = os.path.join(DATA_DIR, "models")

results = {}

# 1. REMO-DQN convergence analysis
remo_csv = os.path.join(MODELS_DIR, "REMO-DQN_convergence.csv")
if os.path.exists(remo_csv):
    df_remo = pd.read_csv(remo_csv)
    early_10 = df_remo["Reward"].iloc[:10]
    late_10 = df_remo["Reward"].iloc[-10:]
    
    early_mean = float(early_10.mean())
    late_mean = float(late_10.mean())
    improvement = late_mean - early_mean
    
    results["remo_convergence"] = {
        "total_episodes": len(df_remo),
        "early_10_mean_reward": early_mean,
        "early_10_std_reward": float(early_10.std()),
        "late_10_mean_reward": late_mean,
        "late_10_std_reward": float(late_10.std()),
        "improvement": improvement,
        "converged": late_mean > early_mean,
        "final_epsilon": float(df_remo["Epsilon"].iloc[-1]) if "Epsilon" in df_remo.columns else None,
        "final_pdr_mean": float(df_remo["PDR_mean"].iloc[-1]) if "PDR_mean" in df_remo.columns else None,
        "final_cbr_mean": float(df_remo["CBR_mean"].iloc[-1]) if "CBR_mean" in df_remo.columns else None,
        "final_aoi_mean": float(df_remo["AoI_mean"].iloc[-1]) if "AoI_mean" in df_remo.columns else None,
    }
    print("REMO-DQN Convergence:")
    print(f"  Episodes: {len(df_remo)}")
    print(f"  Early 10 mean: {early_mean:.2f} -> Late 10 mean: {late_mean:.2f} (Delta: {improvement:+.2f})")
    print(f"  Converged: {late_mean > early_mean}")

# 2. Reward Convergence 17 baselines summary
rc_path = os.path.join(DATA_DIR, "reward_convergence.csv")
if os.path.exists(rc_path):
    df_rc = pd.read_csv(rc_path)
    models_summary = {}
    for col in df_rc.columns:
        if col in ["Episode", "Global_Step"]:
            continue
        vals = df_rc[col]
        models_summary[col] = {
            "min": float(vals.min()),
            "max": float(vals.max()),
            "mean": float(vals.mean()),
            "std": float(vals.std()),
            "start": float(vals.iloc[0]),
            "end": float(vals.iloc[-1])
        }
    results["17_models_reward_convergence"] = models_summary
    print("\n17 Models Convergence Summary:")
    for m, stats in models_summary.items():
        print(f"  {m:25s}: Start={stats['start']:10.1f} | End={stats['end']:10.1f} | Mean={stats['mean']:10.1f} | Std={stats['std']:8.1f}")

# 3. Ablation Study summary
abl_path = os.path.join(DATA_DIR, "ablation_study.csv")
if os.path.exists(abl_path):
    df_abl = pd.read_csv(abl_path)
    abl_summary = {}
    for col in df_abl.columns:
        if col in ["Episode", "Global_Step"]:
            continue
        vals = df_abl[col]
        abl_summary[col] = {
            "mean": float(vals.mean()),
            "std": float(vals.std()),
            "end": float(vals.iloc[-1])
        }
    results["ablation_study_summary"] = abl_summary
    print("\nAblation Study Summary:")
    for a, stats in abl_summary.items():
        print(f"  {a:20s}: End={stats['end']:10.1f} | Mean={stats['mean']:10.1f}")

with open("/home/imnyj/Workspace/paper4/.agents/auditor_1/convergence_audit.json", "w") as f:
    json.dump(results, f, indent=2)
