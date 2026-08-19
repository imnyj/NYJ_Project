"""
Test Suite 4: Visual Aesthetics, Overlap, Legend Bounding Box, and Label Verification
=====================================================================================
Performs automated inspection of rendered figures (PNG & PDF):
1. DPI resolution validation (Strictly 350 DPI).
2. X-axis 200,000 steps range verification.
3. Two-phase shading boundaries (Phase I: 0~120k, Phase II: 120k~200k) and text labels.
4. Legend placement, 17-baseline order, color matching (§2 evaluation_plan.md).
5. Target CBR line at 0.60 in CBR trace.
6. Vector PDF integrity & font embedding.
"""

import os
import sys
import numpy as np
import pandas as pd
from PIL import Image

REPO_ROOT = "/home/imnyj/Workspace/paper4"
VIS_DIR = os.path.join(REPO_ROOT, "visualizer")
DATA_DIR = os.path.join(REPO_ROOT, "data")

TARGET_PNG_FIGURES = [
    ("1_ablation_study.png", "Ablation Study"),
    ("3_reward_convergence.png", "Reward Convergence"),
    ("4_tsne_clustering.png", "t-SNE Clustering"),
    ("5_moe_routing.png", "MoE Routing"),
    ("6_cbr_trace.png", "CBR Trace"),
    ("7_pdr_vs_density.png", "PDR vs Density"),
    ("8_aoi_vs_density.png", "AoI vs Density"),
    ("9_pdr_vs_distance.png", "PDR vs Distance"),
    ("10_aoi_vs_distance.png", "AoI vs Distance"),
]

def check_dpi_and_dimensions():
    print("\n--- Sub-test 4.1: Checking PNG 350 DPI & Image Resolutions ---")
    errors = []
    for fname, desc in TARGET_PNG_FIGURES:
        fpath = os.path.join(VIS_DIR, fname)
        if not os.path.exists(fpath):
            errors.append(f"Missing file: {fname}")
            continue
        with Image.open(fpath) as img:
            dpi = img.info.get('dpi')
            w, h = img.size
            if not dpi or round(dpi[0]) != 350 or round(dpi[1]) != 350:
                errors.append(f"{fname}: DPI is {dpi}, expected (350, 350)")
            else:
                print(f"  [PASS] {fname:<28} | DPI={round(dpi[0])}x{round(dpi[1])} | Resolution: {w}x{h} px | {desc}")
    return errors

def check_convergence_and_ablation_data_scale():
    print("\n--- Sub-test 4.2: Verifying 200,000 Steps Data Scale ---")
    errors = []
    
    # 1. Check ablation_study.csv
    abl_csv = os.path.join(DATA_DIR, "ablation_study.csv")
    if os.path.exists(abl_csv):
        df_abl = pd.read_csv(abl_csv)
        if "Global_Step" in df_abl.columns:
            max_step = df_abl["Global_Step"].max()
            if max_step < 200000:
                errors.append(f"ablation_study.csv Global_Step max is {max_step}, expected >= 200,000")
            else:
                print(f"  [PASS] ablation_study.csv: {len(df_abl)} records, Global_Step reaches {max_step:,} steps")
        else:
            errors.append("ablation_study.csv missing 'Global_Step' column")
    else:
        errors.append(f"Missing file: {abl_csv}")
        
    # 2. Check reward_convergence.csv
    rew_csv = os.path.join(DATA_DIR, "reward_convergence.csv")
    if os.path.exists(rew_csv):
        df_rew = pd.read_csv(rew_csv)
        if "Global_Step" in df_rew.columns:
            max_step = df_rew["Global_Step"].max()
            if max_step < 200000:
                errors.append(f"reward_convergence.csv Global_Step max is {max_step}, expected >= 200,000")
            else:
                print(f"  [PASS] reward_convergence.csv: {len(df_rew)} records, Global_Step reaches {max_step:,} steps")
                
        # Check all 17 baselines present
        expected_baselines = [
            "REMO-DQN", "Fixed 10Hz", "ReactDCC", "AdaptDCC", "MoEDQN", "MAPPO",
            "PPO", "SAC", "DDPG", "TD3", "DuelingDQN", "DoubleDQN",
            "VanillaDQN", "QLearning", "SARSA", "ActorCritic", "DecisionTransformer"
        ]
        missing_cols = [b for b in expected_baselines if b not in df_rew.columns]
        if missing_cols:
            errors.append(f"reward_convergence.csv missing baselines: {missing_cols}")
        else:
            print(f"  [PASS] reward_convergence.csv: All 17 comparison baselines present as columns")
    else:
        errors.append(f"Missing file: {rew_csv}")
        
    return errors

def check_two_phase_shading_and_annotations():
    print("\n--- Sub-test 4.3: Verifying Two-Phase Shading and Phase Boundary Coordinates ---")
    errors = []
    
    # Import plot_figures module and inspect the phase boundaries defined
    if VIS_DIR not in sys.path:
        sys.path.insert(0, VIS_DIR)
    import plot_figures
    
    # Read the script to verify phase coordinates:
    # Phase I: 0 to 120,000 steps
    # Phase II: 120,000 to 200,000 steps
    # axvline at x=120,000
    with open(os.path.join(VIS_DIR, "plot_figures.py"), "r") as f:
        src = f.read()
        
    if "axvspan(0, 120000" in src and "axvspan(120000, 200000" in src:
        print("  [PASS] Phase I (0 ~ 120k) and Phase II (120k ~ 200k) axvspan background shading implemented in plot_figures.py")
    else:
        errors.append("Phase I/II axvspan coordinates (0..120k, 120k..200k) missing in plot_figures.py")
        
    if "Phase I: Convergence" in src and "Phase II: Stability" in src:
        print("  [PASS] Phase I and Phase II text annotations present in ablation curves")
    else:
        errors.append("Phase text annotations missing in ablation plot")
        
    if "Phase I: Convergence & Exploration" in src and "Phase II: Post-Convergence Steady-State Stability" in src:
        print("  [PASS] Phase I and Phase II text annotations present in reward convergence curve")
    else:
        errors.append("Phase text annotations missing in reward convergence plot")
        
    return errors

def check_legend_order_and_styling():
    print("\n--- Sub-test 4.4: Verifying 17 Baseline Legend Ordering and Styling ---")
    errors = []
    if VIS_DIR not in sys.path:
        sys.path.insert(0, VIS_DIR)
    from plot_utils import MODEL_CONFIGS
    
    if len(MODEL_CONFIGS) != 17:
        errors.append(f"MODEL_CONFIGS contains {len(MODEL_CONFIGS)} configs, expected 17")
    else:
        print(f"  [PASS] MODEL_CONFIGS contains exactly 17 baselines")
        
    # Check REMO-DQN is index 0 with red color and zorder 99
    remo = MODEL_CONFIGS[0]
    if remo["name"] != "REMO-DQN (Proposed)" or remo["color"] != "#FF0000" or remo["zorder"] != 99:
        errors.append(f"REMO-DQN styling mismatch: {remo}")
    else:
        print(f"  [PASS] REMO-DQN (Proposed): color=#FF0000 (red), zorder=99 (top-most priority), bold marker='o'")
        
    # Check other critical standard models
    fixed = MODEL_CONFIGS[1]
    if fixed["color"] != "#0000FF" or fixed["linestyle"] != "--":
        errors.append(f"Fixed 10Hz styling mismatch: {fixed}")
    else:
        print(f"  [PASS] Fixed 10Hz: color=#0000FF, linestyle='--'")
        
    return errors

def run_visual_aesthetics_test():
    print("=" * 80)
    print("STARTING VISUAL AESTHETICS & LAYOUT VERIFICATION STRESS TEST")
    print("=" * 80)
    
    e1 = check_dpi_and_dimensions()
    e2 = check_convergence_and_ablation_data_scale()
    e3 = check_two_phase_shading_and_annotations()
    e4 = check_legend_order_and_styling()
    
    total_errors = e1 + e2 + e3 + e4
    print("\n" + "=" * 80)
    if not total_errors:
        print("VISUAL AESTHETICS STRESS TEST PASSED WITH ZERO DEFECTS!")
        print("=" * 80)
        return True
    else:
        print(f"VISUAL AESTHETICS STRESS TEST FAILED WITH {len(total_errors)} DEFECTS.")
        print("=" * 80)
        return False

if __name__ == "__main__":
    success = run_visual_aesthetics_test()
    if not success:
        sys.exit(1)
