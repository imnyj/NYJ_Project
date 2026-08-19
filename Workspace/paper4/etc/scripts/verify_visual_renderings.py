#!/usr/bin/env python3
"""
Visual Artifacts & Style Integrity Verification Script
Author: Empirical Challenger 1
"""

import os
import sys
import pandas as pd

VIS_DIR = "/home/imnyj/Workspace/paper4/visualizer"
if VIS_DIR not in sys.path:
    sys.path.insert(0, VIS_DIR)

PLAN_PATH = os.path.join(VIS_DIR, "evaluation_plan.md")

EXPECTED_OUTPUTS = [
    ("ablation_study.pdf", "PDF", 10000),             # Target 1
    ("optuna_sensitivity_table.csv", "CSV", 500),     # Target 2
    ("optuna_sensitivity_table.tex", "TeX", 500),     # Target 2
    ("reward_convergence.pdf", "PDF", 10000),         # Target 3
    ("tsne_clustering.png", "PNG", 50000),            # Target 4
    ("moe_routing.pdf", "PDF", 10000),                # Target 5
    ("cbr_trace.pdf", "PDF", 10000),                  # Target 6
    ("pdr_vs_density.pdf", "PDF", 10000),             # Target 7
    ("aoi_vs_density.pdf", "PDF", 10000),             # Target 8
    ("pdr_vs_distance.pdf", "PDF", 10000),            # Target 9
    ("aoi_vs_distance.pdf", "PDF", 10000),            # Target 10
    ("hardware_feasibility_table.csv", "CSV", 300),   # Target 11
    ("hardware_feasibility_table.tex", "TeX", 500)    # Target 11
]

def verify_output_files():
    print("="*60)
    print("1. VERIFYING ALL TARGET DELIVERABLE ARTIFACTS")
    print("="*60)
    
    all_ok = True
    for fname, ftype, min_size in EXPECTED_OUTPUTS:
        fpath = os.path.join(VIS_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  [MISSING] {fname}")
            all_ok = False
            continue
        sz = os.path.getsize(fpath)
        if sz < min_size:
            print(f"  [SUSPICIOUS SIZE] {fname:<32} size: {sz} bytes (expected >= {min_size})")
            all_ok = False
        else:
            print(f"  [PASS] {fname:<32} ({ftype:<3}) size: {sz/1024.0:6.1f} KB")
            
    print(f"\nArtifact Verification Result: {'ALL PASS' if all_ok else 'FAIL'}")
    return all_ok

def verify_legend_and_color_mapping():
    print("\n" + "="*60)
    print("2. VERIFYING LEGEND ORDER & COLOR CODES VS EVALUATION_PLAN.MD")
    print("="*60)
    
    from plot_utils import MODEL_CONFIGS
    
    expected_order = [
        ("REMO-DQN (Proposed)", "#FF0000"),
        ("Fixed 10Hz", "#0000FF"),
        ("ReactDCC (ETSI Standard)", "#4D96FF"),
        ("AdaptDCC (ETSI Standard)", "#2A4B7C"),
        ("MoEDQN", "#9B5DE5"),
        ("MAPPO", "#D783FF"),
        ("PPO", "#7A49A5"),
        ("SAC", "#00FF00"),
        ("DDPG", "#6BCB77"),
        ("TD3", "#2E8B57"),
        ("DuelingDQN", "#FF9F1C"),
        ("DoubleDQN", "#FFD166"),
        ("VanillaDQN", "#D67229"),
        ("QLearning", "#1A1A1A"),
        ("SARSA", "#555555"),
        ("ActorCritic", "#888888"),
        ("DecisionTransformer", "#B5B5B5")
    ]
    
    mismatch = False
    for idx, (exp_name, exp_color) in enumerate(expected_order):
        actual_cfg = MODEL_CONFIGS[idx]
        act_name = actual_cfg["name"]
        act_color = actual_cfg["color"].upper()
        
        name_match = (exp_name == act_name)
        color_match = (exp_color.upper() == act_color)
        
        status = "PASS" if (name_match and color_match) else "MISMATCH"
        if status == "MISMATCH":
            mismatch = True
        print(f"  Index {idx+1:2d}: Expected ({exp_name}, {exp_color}) vs Actual ({act_name}, {act_color}) -> {status}")
        
    print(f"\nLegend Order & Color Mapping Result: {'ALL PASS' if not mismatch else 'FAIL'}")

def test_regenerate_pipeline():
    print("\n" + "="*60)
    print("3. TESTING FULL PIPELINE REPRODUCIBILITY (plot_all.py)")
    print("="*60)
    
    import subprocess
    cmd = ["python3", os.path.join(VIS_DIR, "plot_all.py")]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=VIS_DIR)
    
    if res.returncode == 0:
        print("  [PASS] Pipeline plot_all.py re-executed successfully with zero exit code.")
    else:
        print(f"  [FAIL] Pipeline execution failed (exit {res.returncode}):\nStdout: {res.stdout}\nStderr: {res.stderr}")

if __name__ == "__main__":
    verify_output_files()
    verify_legend_and_color_mapping()
    test_regenerate_pipeline()
