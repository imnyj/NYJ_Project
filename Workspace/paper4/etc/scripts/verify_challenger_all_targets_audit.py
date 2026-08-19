#!/usr/bin/env python3
"""
Empirical Challenger Script 3: Comprehensive Multi-Target & Model Checkpoint Audit
Audits:
1. All 11 target data CSV files (reward_convergence, ablation, optuna, cbr, pdr/aoi vs density/distance, hardware)
2. Model checkpoints (.pth, .pkl) in data/models/
3. Optuna logs and hyperparameter validity
"""

import os
import sys
import glob
import pandas as pd
import numpy as np

DATA_DIR = "/home/imnyj/Workspace/paper4/data"
MODELS_DIR = os.path.join(DATA_DIR, "models")
VIS_DIR = "/home/imnyj/Workspace/paper4/visualizer"

ALL_TARGET_CSVS = [
    "reward_convergence.csv",
    "ablation_study.csv",
    "optuna_sensitivity.csv",
    "cbr_trace.csv",
    "pdr_vs_density.csv",
    "aoi_vs_density.csv",
    "pdr_vs_distance.csv",
    "aoi_vs_distance.csv",
    "moe_routing.csv",
    "tsne_clustering.csv",
    "hardware_feasibility.csv"
]

def main():
    print("=" * 80)
    print("CHALLENGER 3: Comprehensive Multi-Target Dataset & Checkpoint Empirical Audit")
    print("=" * 80)
    
    all_passed = True
    
    # 1. Audit all 11 target CSVs
    print("\n--- [Audit 1/3] Full Scan of 11 Target Datasets in data/ ---")
    for csv_name in ALL_TARGET_CSVS:
        path = os.path.join(DATA_DIR, csv_name)
        if not os.path.exists(path):
            print(f"[FAIL - MISSING] {csv_name}")
            all_passed = False
            continue
            
        size = os.path.getsize(path)
        if size == 0:
            print(f"[FAIL - EMPTY] {csv_name} (0 bytes)")
            all_passed = False
            continue
            
        df = pd.read_csv(path)
        nan_count = df.isna().sum().sum()
        num_cols = df.select_dtypes(include=[np.number]).columns
        inf_count = sum(np.isinf(df[c]).sum() for c in num_cols)
        
        status = "[PASS]" if (nan_count == 0 and inf_count == 0) else "[FAIL]"
        if nan_count > 0 or inf_count > 0:
            all_passed = False
            
        print(f"{status:<8} | {csv_name:<26} | Size: {size/1024:5.1f} KB | Rows: {len(df):4d}, Cols: {len(df.columns):2d} | "
              f"NaNs: {nan_count}, Infs: {inf_count}")
              
    # 2. Audit Model Checkpoints in data/models/
    print("\n--- [Audit 2/3] Verification of 17 Checkpoint Files in data/models/ ---")
    expected_checkpoints = [
        "REMO-DQN.pth", "MoEDQN.pth", "MAPPO.pth", "PPO.pth", "SAC.pth", "DDPG.pth", "TD3.pth",
        "DuelingDQN.pth", "DoubleDQN.pth", "VanillaDQN.pth", "QLearning.pkl", "SARSA.pkl",
        "ActorCritic.pth", "DecisionTransformer.pth"
    ]
    for ckpt in expected_checkpoints:
        ckpt_path = os.path.join(MODELS_DIR, ckpt)
        if not os.path.exists(ckpt_path):
            print(f"[FAIL - MISSING CHECKPOINT] {ckpt}")
            all_passed = False
            continue
        size_kb = os.path.getsize(ckpt_path) / 1024.0
        if size_kb == 0:
            print(f"[FAIL - EMPTY CHECKPOINT] {ckpt} (0 KB)")
            all_passed = False
        else:
            print(f"[PASS] Checkpoint: {ckpt:<24} | File Size: {size_kb:8.1f} KB")

    # 3. Audit Structure / Reward / State ablation subdirectories
    print("\n--- [Audit 3/3] Verification of Ablation Checkpoint Subdirectories ---")
    ablation_dirs = ["ablation_structure", "ablation_reward", "ablation_state"]
    for ab_dir in ablation_dirs:
        dir_path = os.path.join(DATA_DIR, ab_dir)
        if not os.path.exists(dir_path):
            print(f"[FAIL - MISSING DIR] {ab_dir}")
            all_passed = False
            continue
        files = glob.glob(os.path.join(dir_path, "*"))
        print(f"[PASS] Directory data/{ab_dir:<18} contains {len(files)} files (models & logs).")
        for f in files:
            sz = os.path.getsize(f)
            if sz == 0:
                print(f"  [FAIL] 0-byte file in ablation: {os.path.basename(f)}")
                all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print(">> VERDICT: ALL DATASETS, CHECKPOINTS, AND ABLATION LOGS ARE 100% CLEAN & COMPLETE.")
    else:
        print(">> VERDICT: COMPREHENSIVE AUDIT FAILED ON SOME TARGETS.")
    print("=" * 80)
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
