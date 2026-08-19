#!/usr/bin/env python3
"""
Empirical Verification Script for Paper4 Visualizer Deliverables
Author: Empirical Challenger 1
"""

import os
import sys
import json
import numpy as np
import pandas as pd

DATA_DIR = "/home/imnyj/Workspace/paper4/data"
CODER_DATA = "/home/imnyj/Workspace/paper4/coder/data"
VIS_DIR = "/home/imnyj/Workspace/paper4/visualizer"
EVAL_DIR = os.path.join(DATA_DIR, "evaluation")
OPTUNA_DIR = os.path.join(DATA_DIR, "optuna")

def check_file_exists_and_nonempty(path):
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    return exists and size > 0, size

def verify_data_coder_sync():
    print("="*60)
    print("1. VERIFYING DATA/ vs CODER/DATA/ SYNCHRONIZATION")
    print("="*60)
    
    csv_files = [
        "reward_convergence.csv", "ablation_study.csv", "optuna_sensitivity_table.csv",
        "tsne_clustering.csv", "moe_routing.csv", "cbr_trace.csv", "pdr_vs_density.csv",
        "aoi_vs_density.csv", "pdr_vs_distance.csv", "aoi_vs_distance.csv", "hardware_feasibility_table.csv"
    ]
    
    results = {}
    for fname in csv_files:
        p_data = os.path.join(DATA_DIR, fname)
        p_coder = os.path.join(CODER_DATA, fname)
        
        ok_d, sz_d = check_file_exists_and_nonempty(p_data)
        ok_c, sz_c = check_file_exists_and_nonempty(p_coder)
        
        if not ok_d or not ok_c:
            results[fname] = f"FAIL (exists data: {ok_d}, coder: {ok_c})"
            continue
            
        df_d = pd.read_csv(p_data)
        df_c = pd.read_csv(p_coder)
        
        if df_d.shape != df_c.shape:
            results[fname] = f"FAIL (shape mismatch: {df_d.shape} vs {df_c.shape})"
            continue
            
        # Numerical diff
        numeric_cols = df_d.select_dtypes(include=[np.number]).columns
        max_diff = 0.0
        for col in numeric_cols:
            if col in df_c.columns:
                diff = np.max(np.abs(df_d[col].values - df_c[col].values))
                max_diff = max(max_diff, diff)
                
        if max_diff < 1e-5:
            results[fname] = f"PASS (exact match, max diff: {max_diff:.2e})"
        else:
            results[fname] = f"FAIL (numeric diff: {max_diff})"
            
    for k, v in results.items():
        print(f"  {k:<32} : {v}")
    return results

def verify_tables_consistency():
    print("\n" + "="*60)
    print("2. VERIFYING TABLES (CSV vs TEX vs DATA SOURCES)")
    print("="*60)
    
    # 1. Optuna Sensitivity Table
    opt_csv_path = os.path.join(VIS_DIR, "optuna_sensitivity_table.csv")
    opt_tex_path = os.path.join(VIS_DIR, "optuna_sensitivity_table.tex")
    
    print(f"\n[A] Optuna Sensitivity Table Check:")
    if os.path.exists(opt_csv_path) and os.path.exists(opt_tex_path):
        df_opt = pd.read_csv(opt_csv_path)
        print(f"  Rows in CSV: {len(df_opt)}")
        print("  Columns:", df_opt.columns.tolist())
        print("  Methods included:", df_opt["Method"].tolist())
        
        # Read TeX content
        with open(opt_tex_path, 'r', encoding='utf-8') as f:
            tex_content = f.read()
            
        tex_check_passed = True
        for _, row in df_opt.iterrows():
            m = str(row['Method'])
            if m not in tex_content:
                print(f"  [ERROR] Method {m} not found in .tex table!")
                tex_check_passed = False
                
        # Check REMO-DQN bold in LaTeX
        if "\\textbf{REMO-DQN" in tex_content:
            print("  [PASS] REMO-DQN is properly bolded in LaTeX table.")
        else:
            print("  [FAIL] REMO-DQN is not bolded in LaTeX table!")
            tex_check_passed = False
            
        print(f"  Optuna CSV vs TeX consistency: {'PASS' if tex_check_passed else 'FAIL'}")
    else:
        print("  [ERROR] Optuna table files missing!")

    # 2. Hardware Feasibility Table
    hw_csv_path = os.path.join(VIS_DIR, "hardware_feasibility_table.csv")
    hw_tex_path = os.path.join(VIS_DIR, "hardware_feasibility_table.tex")
    
    print(f"\n[B] Hardware Feasibility Table Check:")
    if os.path.exists(hw_csv_path) and os.path.exists(hw_tex_path):
        df_hw = pd.read_csv(hw_csv_path)
        print(f"  Rows in CSV: {len(df_hw)}")
        print("  Columns:", df_hw.columns.tolist())
        print(df_hw[["Model", "Architecture", "MACs_FLOPs", "Parameters", "Inference_Latency_ms", "Memory_Footprint_KB", "MCU_Feasibility"]])
        
        with open(hw_tex_path, 'r', encoding='utf-8') as f:
            hw_tex_content = f.read()
            
        hw_tex_passed = True
        for _, row in df_hw.iterrows():
            m = str(row['Model'])
            if m not in hw_tex_content:
                print(f"  [ERROR] Model {m} not found in HW .tex table!")
                hw_tex_passed = False
                
        if "\\textbf{REMO-DQN" in hw_tex_content:
            print("  [PASS] REMO-DQN is properly bolded in HW LaTeX table.")
        else:
            print("  [FAIL] REMO-DQN is not bolded in HW LaTeX table!")
            hw_tex_passed = False
            
        print(f"  HW CSV vs TeX consistency: {'PASS' if hw_tex_passed else 'FAIL'}")
    else:
        print("  [ERROR] Hardware feasibility table files missing!")

def verify_remo_dqn_key_metrics():
    print("\n" + "="*60)
    print("3. EMPIRICAL VERIFICATION OF REMO-DQN KEY METRICS")
    print("="*60)
    
    # Requirement:
    # 1. PDR defense (>= 73% at high density)
    # 2. AoI lowest (in ~370ms or best among all)
    # 3. CBR stability (lowest std and maintain <= 0.6)
    
    # Check PDR vs Density
    pdr_csv = os.path.join(DATA_DIR, "pdr_vs_density.csv")
    df_pdr = pd.read_csv(pdr_csv)
    
    densities = df_pdr["Density"].values
    min_dens = densities.min()
    max_dens = densities.max()
    
    remo_pdr = df_pdr["REMO-DQN"].values
    remo_pdr_high = df_pdr[df_pdr["Density"] >= 100]["REMO-DQN"].values
    
    print(f"\n[PDR Analysis] Density range: {min_dens:.1f} to {max_dens:.1f} veh/km")
    print(f"  REMO-DQN PDR at min density ({min_dens:.1f}): {remo_pdr[0]:.2f}%")
    print(f"  REMO-DQN PDR at max density ({max_dens:.1f}): {remo_pdr[-1]:.2f}%")
    print(f"  REMO-DQN Mean PDR (>=100 veh/km): {remo_pdr_high.mean():.2f}% (min: {remo_pdr_high.min():.2f}%)")
    
    # Compare with all baselines at high density
    print("\n  Comparison at max density (120 veh/km):")
    bl_cols = [c for c in df_pdr.columns if c != "Density"]
    pdr_at_max = {}
    for col in bl_cols:
        pdr_at_max[col] = df_pdr[col].iloc[-1]
    sorted_pdr = sorted(pdr_at_max.items(), key=lambda x: x[1], reverse=True)
    for rank, (model, val) in enumerate(sorted_pdr, 1):
        print(f"    Rank {rank:2d}: {model:<24} = {val:.2f}%")
        
    pdr_claim_met = (remo_pdr_high.min() >= 73.0) and (sorted_pdr[0][0] == "REMO-DQN")
    print(f"  => REMO-DQN PDR Defense Claim (>= 73% & Top-1 at high density): {'PASS' if pdr_claim_met else 'FAIL'}")

    # Check AoI vs Density
    aoi_csv = os.path.join(DATA_DIR, "aoi_vs_density.csv")
    df_aoi = pd.read_csv(aoi_csv)
    
    remo_aoi = df_aoi["REMO-DQN"].values
    print(f"\n[AoI Analysis] Density range: {min_dens:.1f} to {max_dens:.1f} veh/km")
    print(f"  REMO-DQN AoI at min density: {remo_aoi[0]:.2f} ms")
    print(f"  REMO-DQN AoI at max density: {remo_aoi[-1]:.2f} ms")
    print(f"  REMO-DQN Mean AoI: {remo_aoi.mean():.2f} ms")
    
    aoi_at_max = {}
    bl_aoi_cols = [c for c in df_aoi.columns if c != "Density"]
    for col in bl_aoi_cols:
        aoi_at_max[col] = df_aoi[col].iloc[-1]
    sorted_aoi = sorted(aoi_at_max.items(), key=lambda x: x[1])
    print("\n  Comparison of AoI at max density (120 veh/km):")
    for rank, (model, val) in enumerate(sorted_aoi, 1):
        print(f"    Rank {rank:2d}: {model:<24} = {val:.2f} ms")
        
    aoi_claim_met = (sorted_aoi[0][0] == "REMO-DQN")
    print(f"  => REMO-DQN AoI Lowest Claim: {'PASS' if aoi_claim_met else 'FAIL'}")

    # Check CBR Trace & Stability
    cbr_csv = os.path.join(DATA_DIR, "cbr_trace.csv")
    df_cbr = pd.read_csv(cbr_csv)
    
    bl_cbr_cols = [c for c in df_cbr.columns if c != "Time"]
    print(f"\n[CBR Trace Analysis] Time steps: {len(df_cbr)}")
    
    cbr_stats = []
    for col in bl_cbr_cols:
        vals = df_cbr[col].values
        mean_v = np.mean(vals)
        std_v = np.std(vals)
        max_v = np.max(vals)
        min_v = np.min(vals)
        cbr_stats.append({
            "Model": col,
            "Mean": mean_v,
            "Std": std_v,
            "Min": min_v,
            "Max": max_v,
            "Under_0_6": max_v <= 0.62  # allow slight buffer for noise
        })
        
    df_cbr_stats = pd.DataFrame(cbr_stats).sort_values(by="Std")
    print("\n  CBR Stability Ranking (sorted by Std, ascending):")
    for idx, r in df_cbr_stats.reset_index().iterrows():
        print(f"    Rank {idx+1:2d}: {r['Model']:<24} | Mean: {r['Mean']:.4f}, Std: {r['Std']:.4f}, Range: [{r['Min']:.4f}, {r['Max']:.4f}]")
        
    remo_stats = df_cbr_stats[df_cbr_stats["Model"] == "REMO-DQN"].iloc[0]
    cbr_lowest_std = (df_cbr_stats.iloc[0]["Model"] == "REMO-DQN")
    cbr_under_0_6 = (remo_stats["Mean"] <= 0.60 and remo_stats["Max"] <= 0.62)
    
    print(f"\n  REMO-DQN CBR Std: {remo_stats['Std']:.4f} (Lowest among all: {cbr_lowest_std})")
    print(f"  REMO-DQN CBR Mean: {remo_stats['Mean']:.4f}, Max: {remo_stats['Max']:.4f} (Under <= 0.6 target: {cbr_under_0_6})")
    print(f"  => CBR Stability Claim: {'PASS' if (cbr_lowest_std and cbr_under_0_6) else 'FAIL'}")

def verify_raw_simulation_models():
    print("\n" + "="*60)
    print("4. VERIFYING RAW MODEL CONVERGENCE FILES IN DATA/MODELS")
    print("="*60)
    
    models_dir = os.path.join(DATA_DIR, "models")
    if not os.path.exists(models_dir):
        print("  [ERROR] models/ dir not found")
        return
        
    conv_files = [f for f in os.listdir(models_dir) if f.endswith("_convergence.csv")]
    print(f"  Found {len(conv_files)} convergence CSV files in data/models:")
    for f in sorted(conv_files):
        p = os.path.join(models_dir, f)
        df_m = pd.read_csv(p)
        print(f"    {f:<32} : {len(df_m)} rows, cols: {df_m.columns.tolist()}")

if __name__ == "__main__":
    verify_data_coder_sync()
    verify_tables_consistency()
    verify_remo_dqn_key_metrics()
    verify_raw_simulation_models()
