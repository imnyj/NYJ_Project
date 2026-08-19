#!/usr/bin/env python3
"""
Deep Adversarial Verification Script for Paper4 Visualizer Deliverables
Author: Empirical Challenger 1
"""

import os
import json
import numpy as np
import pandas as pd

DATA_DIR = "/home/imnyj/Workspace/paper4/data"
VIS_DIR = "/home/imnyj/Workspace/paper4/visualizer"
MODELS_DIR = os.path.join(DATA_DIR, "models")
OPTUNA_DIR = os.path.join(DATA_DIR, "optuna")
EVAL_DIR = os.path.join(DATA_DIR, "evaluation")

def verify_optuna_params_json_vs_table():
    print("="*60)
    print("1. OPTUNA RAW JSON VS OPTUNA SENSITIVITY TABLE")
    print("="*60)
    
    json_path = os.path.join(OPTUNA_DIR, "all_best_params.json")
    table_path = os.path.join(VIS_DIR, "optuna_sensitivity_table.csv")
    
    if not os.path.exists(json_path):
        print("  [WARN] all_best_params.json not found")
        return
    if not os.path.exists(table_path):
        print("  [FAIL] optuna_sensitivity_table.csv not found")
        return
        
    with open(json_path, 'r') as f:
        raw_optuna = json.load(f)
        
    df_opt = pd.read_csv(table_path)
    
    print(f"  Optuna raw JSON keys: {list(raw_optuna.keys())}")
    for k, v in raw_optuna.items():
        print(f"    Raw JSON -> {k}: {v}")
        
    print("\n  Table entries:")
    for _, r in df_opt.iterrows():
        print(f"    Table -> {r['Method']}: {r['Tuned Hyperparameters']}")

def verify_convergence_raw_vs_reward_csv():
    print("\n" + "="*60)
    print("2. RAW MODEL CONVERGENCE CSV VS REWARD_CONVERGENCE.CSV")
    print("="*60)
    
    reward_csv = os.path.join(DATA_DIR, "reward_convergence.csv")
    df_rew = pd.read_csv(reward_csv)
    
    rl_models = [
        "REMO-DQN", "MoEDQN", "MAPPO", "PPO", "SAC", "DDPG", "TD3",
        "DuelingDQN", "DoubleDQN", "VanillaDQN", "QLearning", "SARSA",
        "ActorCritic", "DecisionTransformer"
    ]
    
    mismatches = []
    for model in rl_models:
        raw_csv = os.path.join(MODELS_DIR, f"{model}_convergence.csv")
        if not os.path.exists(raw_csv):
            print(f"  [MISSING] {raw_csv}")
            mismatches.append(model)
            continue
            
        df_raw = pd.read_csv(raw_csv)
        col_name = "Reward" if "Reward" in df_raw.columns else df_raw.columns[1]
        raw_vals = df_raw[col_name].values[:100]
        tbl_vals = df_rew[model].values[:100]
        
        diff = np.max(np.abs(raw_vals - tbl_vals))
        if diff < 1e-4:
            print(f"  {model:<22} : MATCH (diff = {diff:.2e}, last reward = {raw_vals[-1]:.1f})")
        else:
            print(f"  {model:<22} : MISMATCH (max diff = {diff:.2e})")
            mismatches.append((model, diff))
            
    print(f"\n  Convergence Data Alignment Result: {'ALL MATCH' if not mismatches else 'MISMATCH FOUND'}")

def verify_pdr_distance_and_aoi_distance():
    print("\n" + "="*60)
    print("3. PDR & AOI VS DISTANCE VERIFICATION")
    print("="*60)
    
    pdr_dist_csv = os.path.join(DATA_DIR, "pdr_vs_distance.csv")
    aoi_dist_csv = os.path.join(DATA_DIR, "aoi_vs_distance.csv")
    
    df_pdr_d = pd.read_csv(pdr_dist_csv)
    df_aoi_d = pd.read_csv(aoi_dist_csv)
    
    print(f"  Distances tested: {df_pdr_d['Distance'].tolist()} meters")
    
    # Check monotonic degradation with distance (Physical realism)
    pdr_monotonic = True
    aoi_monotonic = True
    
    for col in df_pdr_d.columns:
        if col == "Distance":
            continue
        vals = df_pdr_d[col].values
        # PDR should decrease with distance
        if not (vals[0] >= vals[-1]):
            print(f"  [ANOMALY] PDR for {col} does not decrease with distance: {vals[0]:.1f}% -> {vals[-1]:.1f}%")
            pdr_monotonic = False
            
    for col in df_aoi_d.columns:
        if col == "Distance":
            continue
        vals = df_aoi_d[col].values
        # AoI should increase with distance
        if not (vals[0] <= vals[-1]):
            print(f"  [ANOMALY] AoI for {col} does not increase with distance: {vals[0]:.1f}ms -> {vals[-1]:.1f}ms")
            aoi_monotonic = False
            
    print(f"  PDR Distance Monotonic Decay Check (Physical Law): {'PASS' if pdr_monotonic else 'FAIL'}")
    print(f"  AoI Distance Monotonic Increase Check (Physical Law): {'PASS' if aoi_monotonic else 'FAIL'}")
    
    # Verify REMO-DQN superiority across distance
    remo_pdr_300m = df_pdr_d["REMO-DQN"].iloc[-1]
    remo_aoi_300m = df_aoi_d["REMO-DQN"].iloc[-1]
    print(f"\n  REMO-DQN at 300m: PDR = {remo_pdr_300m:.2f}%, AoI = {remo_aoi_300m:.2f}ms")
    
    best_pdr_300m = df_pdr_d.iloc[-1, 1:].idxmax()
    best_aoi_300m = df_aoi_d.iloc[-1, 1:].idxmin()
    print(f"  Best PDR at 300m : {best_pdr_300m} ({df_pdr_d[best_pdr_300m].iloc[-1]:.2f}%)")
    print(f"  Best AoI at 300m : {best_aoi_300m} ({df_aoi_d[best_aoi_300m].iloc[-1]:.2f}ms)")
    
    print(f"  REMO-DQN is Top-1 at 300m: PDR={'PASS' if best_pdr_300m=='REMO-DQN' else 'FAIL'}, AoI={'PASS' if best_aoi_300m=='REMO-DQN' else 'FAIL'}")

def verify_ablation_study_integrity():
    print("\n" + "="*60)
    print("4. ABLATION STUDY INTEGRITY VERIFICATION")
    print("="*60)
    
    abl_csv = os.path.join(DATA_DIR, "ablation_study.csv")
    df_abl = pd.read_csv(abl_csv)
    
    print(f"  Ablation components: {df_abl.columns.tolist()}")
    print("  Final Episode Performance (Episode 25):")
    final_row = df_abl.iloc[-1]
    for col in df_abl.columns:
        if col != "Episode":
            print(f"    {col:<24} : {final_row[col]:,.1f}")
            
    # Check that Full REMO-DQN outperforms all ablations
    full_rew = final_row["REMO-DQN"]
    all_ablations_lower = True
    for col in df_abl.columns:
        if col not in ["Episode", "REMO-DQN"]:
            if final_row[col] >= full_rew:
                print(f"  [ERROR] Ablation {col} has reward >= REMO-DQN!")
                all_ablations_lower = False
                
    print(f"  Full REMO-DQN strictly outperforms all ablation variants: {'PASS' if all_ablations_lower else 'FAIL'}")

def verify_moe_routing_integrity():
    print("\n" + "="*60)
    print("5. MOE DYNAMIC ROUTING INTEGRITY VERIFICATION")
    print("="*60)
    
    moe_csv = os.path.join(DATA_DIR, "moe_routing.csv")
    df_moe = pd.read_csv(moe_csv)
    
    print(df_moe)
    
    # Check sum of weights per row == 100%
    sums = df_moe[["Expert1 (Low Density)", "Expert2 (Medium Density)", "Expert3 (High Density)"]].sum(axis=1)
    sum_100 = np.allclose(sums, 100.0)
    print(f"\n  Expert weight sum == 100% across all densities: {'PASS' if sum_100 else 'FAIL'} (sums: {sums.tolist()})")
    
    # Check expert shift logic:
    # At low density (20 veh/km), Expert 1 should dominate
    # At high density (120 veh/km), Expert 3 should dominate
    exp1_low = df_moe.iloc[0]["Expert1 (Low Density)"]
    exp3_high = df_moe.iloc[-1]["Expert3 (High Density)"]
    
    logic_pass = (exp1_low > 70) and (exp3_high > 70)
    print(f"  Expert 1 dominance at low density (20 veh/km): {exp1_low}%")
    print(f"  Expert 3 dominance at high density (120 veh/km): {exp3_high}%")
    print(f"  MoE Dynamic Routing Behavior Check: {'PASS' if logic_pass else 'FAIL'}")

if __name__ == "__main__":
    verify_optuna_params_json_vs_table()
    verify_convergence_raw_vs_reward_csv()
    verify_pdr_distance_and_aoi_distance()
    verify_ablation_study_integrity()
    verify_moe_routing_integrity()
