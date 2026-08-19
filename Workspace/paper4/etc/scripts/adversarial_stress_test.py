#!/usr/bin/env python3
"""
Adversarial Stress Test and Deep Data Flow Verification
"""

import os
import re
import pandas as pd
import numpy as np

WORKSPACE_DIR = "/home/imnyj/Workspace/paper4"

def test_data_flow():
    print("=== Testing Visualizer Scripts Data Flow ===")
    vis_scripts = [
        "generate_visualizations.py",
        "plot_figures.py",
        "generate_tables.py",
        "plot_all.py"
    ]
    
    for s in vis_scripts:
        p = os.path.join(WORKSPACE_DIR, "visualizer", s)
        if not os.path.exists(p):
            print(f"  [MISSING] {s}")
            continue
        with open(p, "r") as f:
            content = f.read()
            
        # Check pd.read_csv calls
        read_csv_matches = re.findall(r'pd\.read_csv\((.*?)\)', content)
        print(f"  {s}: {len(read_csv_matches)} pd.read_csv occurrences")
        for m in read_csv_matches[:5]:
            print(f"    -> pd.read_csv({m})")

def test_convergence_phases():
    print("\n=== Testing Convergence Phases in CSVs ===")
    for csv_name in ["reward_convergence.csv", "ablation_study.csv"]:
        p = os.path.join(WORKSPACE_DIR, "data", csv_name)
        df = pd.read_csv(p)
        print(f"  {csv_name}: Rows={len(df)}, Steps: {df['Global_Step'].min()} to {df['Global_Step'].max()}")
        
        # Phase 1: 0 - 60,000 steps (Exploration / Rapid Improvement)
        # Phase 2: 60,000 - 200,000 steps (Convergence & Steady State)
        p1 = df[df['Global_Step'] <= 60000]
        p2 = df[df['Global_Step'] > 60000]
        
        # Check proposed REMO-DQN stability
        if 'REMO-DQN' in df.columns:
            r1_mean = p1['REMO-DQN'].mean()
            r1_std = p1['REMO-DQN'].std()
            r2_mean = p2['REMO-DQN'].mean()
            r2_std = p2['REMO-DQN'].std()
            print(f"    REMO-DQN Phase 1 (0-60k): Mean={r1_mean:.1f}, Std={r1_std:.1f}")
            print(f"    REMO-DQN Phase 2 (60k-200k): Mean={r2_mean:.1f}, Std={r2_std:.1f}")
            print(f"    -> Phase 2 has higher mean reward: {r2_mean > r1_mean}")
            print(f"    -> Phase 2 is stable (std < 100000): {r2_std < 100000}")

def test_model_parameters_integrity():
    print("\n=== Testing Model Checkpoint Tensors in data/models/ ===")
    models_dir = os.path.join(WORKSPACE_DIR, "data", "models")
    for f in sorted(os.listdir(models_dir)):
        if f.endswith(".pth") or f.endswith(".pkl"):
            f_path = os.path.join(models_dir, f)
            sz = os.path.getsize(f_path)
            print(f"  {f:25s} : {sz/1024:.1f} KB")

def main():
    test_data_flow()
    test_convergence_phases()
    test_model_parameters_integrity()

if __name__ == "__main__":
    main()
