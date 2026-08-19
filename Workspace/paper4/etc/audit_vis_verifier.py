#!/usr/bin/env python3
"""
Forensic Audit Verification Script for Paper4 Visualizer
========================================================
Runs empirical integrity, format, and specification checks on all visualizer outputs.
"""

import os
import sys
import pandas as pd
from PIL import Image

VIS_DIR = "/home/imnyj/Workspace/paper4/visualizer"
DATA_DIR = "/home/imnyj/Workspace/paper4/data"

if VIS_DIR not in sys.path:
    sys.path.insert(0, VIS_DIR)

REQUIRED_FILES = [
    ("ablation_study.pdf", "PDF", 10000),
    ("optuna_sensitivity_table.csv", "CSV", 1000),
    ("optuna_sensitivity_table.tex", "TEX", 1500),
    ("reward_convergence.pdf", "PDF", 10000),
    ("tsne_clustering.png", "PNG", 50000),
    ("moe_routing.pdf", "PDF", 10000),
    ("cbr_trace.pdf", "PDF", 10000),
    ("pdr_vs_density.pdf", "PDF", 10000),
    ("aoi_vs_density.pdf", "PDF", 10000),
    ("pdr_vs_distance.pdf", "PDF", 10000),
    ("aoi_vs_distance.pdf", "PDF", 10000),
    ("hardware_feasibility_table.csv", "CSV", 500),
    ("hardware_feasibility_table.tex", "TEX", 1000),
]

EXPECTED_BASELINES = [
    ("REMO-DQN (Proposed)", "#FF0000", 1.0),
    ("Fixed 10Hz", "#0000FF", 0.6),
    ("ReactDCC (ETSI Standard)", "#4D96FF", 0.6),
    ("AdaptDCC (ETSI Standard)", "#2A4B7C", 0.6),
    ("MoEDQN", "#9B5DE5", 0.6),
    ("MAPPO", "#D783FF", 0.6),
    ("PPO", "#7A49A5", 0.6),
    ("SAC", "#00FF00", 0.6),
    ("DDPG", "#6BCB77", 0.6),
    ("TD3", "#2E8B57", 0.6),
    ("DuelingDQN", "#FF9F1C", 0.6),
    ("DoubleDQN", "#FFD166", 0.6),
    ("VanillaDQN", "#D67229", 0.6),
    ("QLearning", "#1A1A1A", 0.6),
    ("SARSA", "#555555", 0.6),
    ("ActorCritic", "#888888", 0.6),
    ("DecisionTransformer", "#B5B5B5", 0.6),
]

def run_audit():
    print("="*80)
    print(" FORENSIC INTEGRITY AUDIT: PAPER4 VISUALIZATION & EVALUATION ARTIFACTS")
    print("="*80)
    
    results = {}
    
    # 1. File existence and size check
    print("\n--- [Check 1] Artifact Existence & File Size Verification ---")
    all_files_ok = True
    for fname, ftype, min_size in REQUIRED_FILES:
        fpath = os.path.join(VIS_DIR, fname)
        if not os.path.exists(fpath):
            print(f"[-] MISSING: {fname}")
            all_files_ok = False
            continue
        size = os.path.getsize(fpath)
        if size < min_size:
            print(f"[-] TOO SMALL ({size} bytes < {min_size} bytes): {fname}")
            all_files_ok = False
        else:
            print(f"[+] VALID ({size:>7} bytes): {fname}")
            
    results["Files_Check"] = all_files_ok
    
    # 2. PNG DPI and dimensions check
    print("\n--- [Check 2] Image Resolution Verification (tsne_clustering.png) ---")
    img_path = os.path.join(VIS_DIR, "tsne_clustering.png")
    img_ok = False
    if os.path.exists(img_path):
        with Image.open(img_path) as img:
            w, h = img.size
            dpi = img.info.get('dpi', (300, 300))
            print(f"[+] Image Dimensions: {w} x {h}, DPI: {dpi}")
            if w >= 2000 and h >= 1500:
                img_ok = True
                print("[+] Resolution is publication quality (300+ DPI equivalent).")
            else:
                print("[-] Image dimensions below publication threshold.")
    results["Image_Check"] = img_ok
    
    # 3. CSV Schema & Row Count Verification
    print("\n--- [Check 3] CSV Schema & Data Structure Verification ---")
    csv_ok = True
    
    df_opt = pd.read_csv(os.path.join(VIS_DIR, "optuna_sensitivity_table.csv"))
    print(f"[+] optuna_sensitivity_table.csv shape: {df_opt.shape} (Expected 17 rows, 7 cols)")
    if df_opt.shape[0] != 17 or df_opt.shape[1] != 7:
        csv_ok = False
        print("[-] optuna_sensitivity_table.csv shape mismatch!")
        
    df_hw = pd.read_csv(os.path.join(VIS_DIR, "hardware_feasibility_table.csv"))
    print(f"[+] hardware_feasibility_table.csv shape: {df_hw.shape} (Expected 11 rows, 7 cols)")
    if df_hw.shape[0] != 11 or df_hw.shape[1] != 7:
        csv_ok = False
        print("[-] hardware_feasibility_table.csv shape mismatch!")
        
    df_cbr = pd.read_csv(os.path.join(DATA_DIR, "cbr_trace.csv"))
    print(f"[+] cbr_trace.csv shape: {df_cbr.shape} (Expected 100 rows, 18 cols)")
    if df_cbr.shape[0] != 100 or df_cbr.shape[1] != 18:
        csv_ok = False
        print("[-] cbr_trace.csv shape mismatch!")
        
    df_rew = pd.read_csv(os.path.join(DATA_DIR, "reward_convergence.csv"))
    print(f"[+] reward_convergence.csv shape: {df_rew.shape} (Expected 100 rows, 18 cols)")
    if df_rew.shape[0] != 100 or df_rew.shape[1] != 18:
        csv_ok = False
        print("[-] reward_convergence.csv shape mismatch!")

    results["CSV_Check"] = csv_ok
    
    # 4. LaTeX Table Syntax Verification
    print("\n--- [Check 4] LaTeX Table Syntax & Structure Verification ---")
    tex_ok = True
    for tex_name in ["optuna_sensitivity_table.tex", "hardware_feasibility_table.tex"]:
        tpath = os.path.join(VIS_DIR, tex_name)
        with open(tpath, "r", encoding="utf-8") as f:
            content = f.read()
            if "\\begin{table*}" in content and "\\end{table*}" in content and "\\begin{tabular}" in content and "\\end{tabular}" in content:
                print(f"[+] LaTeX Table Syntax Valid: {tex_name}")
            else:
                print(f"[-] Invalid LaTeX structure: {tex_name}")
                tex_ok = False
    results["LaTeX_Check"] = tex_ok
    
    # 5. Color & Style Specification Verification in Scripts
    print("\n--- [Check 5] Color Specification and Legend Order Verification ---")
    from plot_utils import MODEL_CONFIGS
    spec_ok = True
    if len(MODEL_CONFIGS) != 17:
        print(f"[-] MODEL_CONFIGS count mismatch: {len(MODEL_CONFIGS)} != 17")
        spec_ok = False
    else:
        print(f"[+] Exactly 17 baseline configurations defined.")
        
    for i, (exp_name, exp_color, exp_alpha) in enumerate(EXPECTED_BASELINES):
        actual_cfg = MODEL_CONFIGS[i]
        if actual_cfg["name"] != exp_name:
            print(f"[-] Order mismatch at #{i+1}: expected '{exp_name}', got '{actual_cfg['name']}'")
            spec_ok = False
        elif actual_cfg["color"] != exp_color:
            print(f"[-] Color mismatch for '{exp_name}': expected {exp_color}, got {actual_cfg['color']}")
            spec_ok = False
        elif actual_cfg["alpha"] != exp_alpha:
            print(f"[-] Alpha mismatch for '{exp_name}': expected {exp_alpha}, got {actual_cfg['alpha']}")
            spec_ok = False
        else:
            print(f"[+] #{i+1:02d} {exp_name:<26} Color: {exp_color} Alpha: {exp_alpha}")
            
    results["Spec_Check"] = spec_ok
    
    print("\n" + "="*80)
    print(" SUMMARY OF FORENSIC AUDIT CHECKS")
    print("="*80)
    all_passed = all(results.values())
    for k, v in results.items():
        status_str = "PASS" if v else "FAIL"
        print(f"{k:<25}: {status_str}")
        
    print("="*80)
    if all_passed:
        print("FINAL VERDICT: CLEAN")
    else:
        print("FINAL VERDICT: INTEGRITY VIOLATION")
    print("="*80)
    return all_passed

if __name__ == "__main__":
    success = run_audit()
    sys.exit(0 if success else 1)
