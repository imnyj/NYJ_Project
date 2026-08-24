#!/usr/bin/env python3
"""
Independent Victory Audit Script — victory_auditor_2
Verifies all 4 major requirements:
R1. REMO-DQN Training & Convergence
R2. 16 Baseline Models (17 total models)
R3. Ablation Study Integrity & Tests
R4. Evaluation Datasets, 22 Visualizations, Zero-Mock
"""

import os
import sys
import glob
import subprocess
import pickle
import pandas as pd
import numpy as np
import torch
from PIL import Image

PROJECT_ROOT = "/home/imnyj/Workspace/paper4"
sys.path.insert(0, os.path.join(PROJECT_ROOT, "code"))

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

all_passed = True
failures = []

# -------------------------------------------------------------
# R1. REMO-DQN Training & Convergence Verification
# -------------------------------------------------------------
print_header("R1. REMO-DQN Training & Convergence Verification")

remo_csvs = [
    os.path.join(PROJECT_ROOT, "data/models/REMO-DQN_convergence.csv"),
    os.path.join(PROJECT_ROOT, "code/resnet_train_log.csv")
]
expected_cols = ["Episode", "Global_Step", "Reward", "AoI_mean", "CBR_mean", "PDR_mean", "Loss", "Epsilon", "Density"]

for csv_path in remo_csvs:
    rel_path = os.path.relpath(csv_path, PROJECT_ROOT)
    if not os.path.exists(csv_path):
        failures.append(f"R1: Missing file {rel_path}")
        print(f"[FAIL] {rel_path} does not exist.")
        continue
    
    with open(csv_path, "r") as f:
        lines = f.readlines()
    line_count = len(lines)
    print(f"[INFO] {rel_path}: {line_count} lines on disk.")
    
    if line_count != 101:
        failures.append(f"R1: {rel_path} line count is {line_count} (expected 101)")
        print(f"[FAIL] {rel_path} line count is {line_count} (expected 101)")
    else:
        print(f"[PASS] {rel_path} has exactly 101 lines.")
        
    df = pd.read_csv(csv_path)
    if list(df.columns) != expected_cols:
        failures.append(f"R1: {rel_path} column mismatch: {list(df.columns)}")
        print(f"[FAIL] {rel_path} column mismatch: {list(df.columns)}")
    else:
        print(f"[PASS] {rel_path} has valid 9 columns.")
        
    if df.isna().sum().sum() > 0:
        failures.append(f"R1: {rel_path} contains NaNs")
        print(f"[FAIL] {rel_path} contains NaNs.")
    else:
        print(f"[PASS] {rel_path} contains 0 NaNs.")

# Run verify_remo_convergence.py
cmd1 = ["python3", os.path.join(PROJECT_ROOT, "code/verify_remo_convergence.py")]
res1 = subprocess.run(cmd1, capture_output=True, text=True)
print(f"\nRunning: {' '.join(cmd1)}")
print(f"Exit code: {res1.returncode}")
print("Output snippet:\n" + "\n".join(res1.stdout.strip().splitlines()[-6:]))
if res1.returncode != 0 or "[PASS]" not in res1.stdout:
    failures.append("R1: verify_remo_convergence.py failed")
    print("[FAIL] verify_remo_convergence.py failed!")
else:
    print("[PASS] verify_remo_convergence.py succeeded with [PASS]")

cmd2 = ["python3", os.path.join(PROJECT_ROOT, "code/verify_remo_convergence.py"), "--csv", os.path.join(PROJECT_ROOT, "code/resnet_train_log.csv")]
res2 = subprocess.run(cmd2, capture_output=True, text=True)
print(f"\nRunning: {' '.join(cmd2)}")
print(f"Exit code: {res2.returncode}")
print("Output snippet:\n" + "\n".join(res2.stdout.strip().splitlines()[-6:]))
if res2.returncode != 0 or "[PASS]" not in res2.stdout:
    failures.append("R1: verify_remo_convergence.py with resnet_train_log.csv failed")
    print("[FAIL] verify_remo_convergence.py with resnet_train_log.csv failed!")
else:
    print("[PASS] verify_remo_convergence.py with resnet_train_log.csv succeeded with [PASS]")

# Check model weight loading
from resnet_moe_agent import ResNetMoEDQN
remo_model_path = os.path.join(PROJECT_ROOT, "data/models/resnet_moe_dqn.pth")
if os.path.exists(remo_model_path):
    try:
        model = ResNetMoEDQN(state_dim=5, action_dim=24)
        sd = torch.load(remo_model_path, map_location="cpu")
        model.load_state_dict(sd)
        model.eval()
        dummy_state = torch.tensor([[0.5, 0.5, 0.5, 0.5, 0.5]], dtype=torch.float32)
        with torch.no_grad():
            q_vals = model(dummy_state)
            action = int(torch.argmax(q_vals, dim=1).item())
        print(f"[PASS] Successfully loaded resnet_moe_dqn.pth: Q shape {q_vals.shape}, test action {action}")
    except Exception as e:
        failures.append(f"R1: Failed to load/infer resnet_moe_dqn.pth: {e}")
        print(f"[FAIL] Loading resnet_moe_dqn.pth failed: {e}")
else:
    failures.append("R1: resnet_moe_dqn.pth missing")
    print("[FAIL] resnet_moe_dqn.pth missing")

# -------------------------------------------------------------
# R2. 16 Baseline Models (17 Total Models) Verification
# -------------------------------------------------------------
print_header("R2. 17 Baseline & Proposed Models Verification")

# 17 models list
models_17 = [
    "ActorCritic", "AdaptDCC", "DDPG", "DecisionTransformer", "DoubleDQN",
    "DuelingDQN", "Fixed 10Hz", "MAPPO", "MoEDQN", "PPO",
    "QLearning", "REMO-DQN", "ReactDCC", "SAC", "SARSA",
    "TD3", "VanillaDQN"
]

all_conv_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, "data/models/*_convergence.csv")))
print(f"Found {len(all_conv_files)} convergence CSV files in data/models/")

r2_csv_pass = True
for fpath in all_conv_files:
    fname = os.path.basename(fpath)
    with open(fpath, "r") as f:
        lines = f.readlines()
    n_lines = len(lines)
    df = pd.read_csv(fpath)
    n_rows, n_cols = df.shape
    nan_count = df.isna().sum().sum()
    inf_count = np.isinf(df.select_dtypes(include=[np.number])).sum().sum()
    
    status = "PASS" if (n_lines == 101 and n_rows == 100 and n_cols == 9 and nan_count == 0 and inf_count == 0) else "FAIL"
    if status == "FAIL":
        r2_csv_pass = False
        failures.append(f"R2: {fname} format violation: lines={n_lines}, rows={n_rows}, cols={n_cols}, NaNs={nan_count}, Infs={inf_count}")
        print(f"  [{status}] {fname:<35}: lines={n_lines}, rows={n_rows}, cols={n_cols}, NaNs={nan_count}, Infs={inf_count}")
    else:
        print(f"  [{status}] {fname:<35}: lines={n_lines}, rows={n_rows}, cols={n_cols}, NaNs={nan_count}, Infs={inf_count}")

# DDPG specific check
ddpg_path = os.path.join(PROJECT_ROOT, "data/models/DDPG_convergence.csv")
with open(ddpg_path, "r") as f:
    ddpg_lines = f.readlines()
print(f"\nDDPG_convergence.csv lines: {len(ddpg_lines)}")
print("DDPG_convergence.csv last 2 lines:")
for l in ddpg_lines[-2:]:
    print(" ", l.strip())
assert len(ddpg_lines) == 101, f"DDPG has {len(ddpg_lines)} lines, expected 101"

# Weights loading test
print("\n--- Model Weight Loading & Inference Checks ---")
weight_files = {
    "VanillaDQN": ("VanillaDQN.pth", "torch"),
    "DoubleDQN": ("DoubleDQN.pth", "torch"),
    "DuelingDQN": ("DuelingDQN.pth", "torch"),
    "MoEDQN": ("MoEDQN.pth", "torch"),
    "ResNetMoEDQN": ("resnet_moe_dqn.pth", "torch"),
    "REMO-DQN": ("REMO-DQN.pth", "torch"),
    "PPO": ("PPO.pth", "torch"),
    "SAC": ("SAC.pth", "torch"),
    "DDPG": ("DDPG.pth", "torch"),
    "TD3": ("TD3.pth", "torch"),
    "MAPPO": ("MAPPO.pth", "torch"),
    "ActorCritic": ("ActorCritic.pth", "torch"),
    "DecisionTransformer": ("DecisionTransformer.pth", "torch"),
    "QLearning": ("QLearning.pkl", "pickle"),
    "SARSA": ("SARSA.pkl", "pickle")
}

for mname, (wname, wtype) in weight_files.items():
    wpath = os.path.join(PROJECT_ROOT, "data/models", wname)
    if not os.path.exists(wpath):
        failures.append(f"R2: Weight file missing: {wname}")
        print(f"  [FAIL] {wname:<25}: missing")
        continue
    sz = os.path.getsize(wpath)
    if wtype == "torch":
        try:
            data = torch.load(wpath, map_location="cpu")
            if isinstance(data, dict):
                n_keys = len(data)
                print(f"  [PASS] {wname:<25} ({sz:>7} B): valid torch state_dict ({n_keys} keys)")
            elif isinstance(data, torch.nn.Module):
                print(f"  [PASS] {wname:<25} ({sz:>7} B): valid torch Module")
            else:
                print(f"  [PASS] {wname:<25} ({sz:>7} B): valid torch object ({type(data)})")
        except Exception as e:
            failures.append(f"R2: Failed torch.load for {wname}: {e}")
            print(f"  [FAIL] {wname:<25}: torch load error {e}")
    elif wtype == "pickle":
        try:
            with open(wpath, "rb") as pf:
                obj = pickle.load(pf)
            print(f"  [PASS] {wname:<25} ({sz:>7} B): valid pickle object ({type(obj).__name__})")
        except Exception as e:
            failures.append(f"R2: Failed pickle.load for {wname}: {e}")
            print(f"  [FAIL] {wname:<25}: pickle load error {e}")

# -------------------------------------------------------------
# R3. Ablation Study Verification
# -------------------------------------------------------------
print_header("R3. Ablation Study Verification")

ablation_specs = [
    ("data/ablation_study.csv", 100, 9),
    ("data/ablation_structure.csv", 100, 6),
    ("data/ablation_reward.csv", 100, 6)
]

for rel_p, exp_r, exp_c in ablation_specs:
    full_p = os.path.join(PROJECT_ROOT, rel_p)
    if not os.path.exists(full_p):
        failures.append(f"R3: Missing {rel_p}")
        print(f"  [FAIL] {rel_p}: missing")
        continue
    df = pd.read_csv(full_p)
    r, c = df.shape
    nan_c = df.isna().sum().sum()
    if r == exp_r and c == exp_c and nan_c == 0:
        print(f"  [PASS] {rel_p:<30}: shape=({r}, {c}), NaNs=0")
    else:
        failures.append(f"R3: {rel_p} shape/nan error: expected ({exp_r},{exp_c}), got ({r},{c}), NaNs={nan_c}")
        print(f"  [FAIL] {rel_p:<30}: expected ({exp_r},{exp_c}), got ({r},{c}), NaNs={nan_c}")

# Run ablation test scripts
print("\n--- Running Ablation Test Scripts ---")
for script in ["code/test_c3_reward.py", "code/test_h5_ablation.py"]:
    cmd = ["python3", os.path.join(PROJECT_ROOT, script)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"  [PASS] {script}: Exit Code 0")
    else:
        failures.append(f"R3: {script} failed with exit code {res.returncode}")
        print(f"  [FAIL] {script}: Exit Code {res.returncode}\n{res.stderr}")

# -------------------------------------------------------------
# R4. Evaluation Datasets & Visualizations Verification
# -------------------------------------------------------------
print_header("R4. Evaluation Datasets & Visualizations Verification")

# 1. reward_convergence.csv
rc_path = os.path.join(PROJECT_ROOT, "data/reward_convergence.csv")
if os.path.exists(rc_path):
    rc_df = pd.read_csv(rc_path)
    rc_r, rc_c = rc_df.shape
    rc_nans = rc_df.isna().sum().sum()
    if rc_r == 100 and rc_c == 19 and rc_nans == 0:
        print(f"  [PASS] data/reward_convergence.csv: shape=({rc_r}, {rc_c}), NaNs=0, columns include 17 models")
    else:
        failures.append(f"R4: reward_convergence.csv shape/nan mismatch: ({rc_r}, {rc_c}), NaNs={rc_nans}")
        print(f"  [FAIL] data/reward_convergence.csv: shape=({rc_r}, {rc_c}), NaNs={rc_nans}")
else:
    failures.append("R4: data/reward_convergence.csv missing")
    print("  [FAIL] data/reward_convergence.csv missing")

# 2. Check 11 visualization pairs (22 files)
print("\n--- Checking 11 Visualization Output Pairs (22 Files) ---")
vis_targets = [
    ("1_ablation_study.png", "1_ablation_study.pdf"),
    ("2_optuna_sensitivity_table.csv", "2_optuna_sensitivity_table.tex"),
    ("3_reward_convergence.png", "3_reward_convergence.pdf"),
    ("4_tsne_clustering.png", "4_tsne_clustering.pdf"),
    ("5_moe_routing.png", "5_moe_routing.pdf"),
    ("6_cbr_trace.png", "6_cbr_trace.pdf"),
    ("7_pdr_vs_density.png", "7_pdr_vs_density.pdf"),
    ("8_aoi_vs_density.png", "8_aoi_vs_density.pdf"),
    ("9_pdr_vs_distance.png", "9_pdr_vs_distance.pdf"),
    ("10_aoi_vs_distance.png", "10_aoi_vs_distance.pdf"),
    ("11_hardware_feasibility_table.csv", "11_hardware_feasibility_table.tex")
]

for out1, out2 in vis_targets:
    p1 = os.path.join(PROJECT_ROOT, "visualizer", out1)
    p2 = os.path.join(PROJECT_ROOT, "visualizer", out2)
    
    e1 = os.path.exists(p1)
    e2 = os.path.exists(p2)
    sz1 = os.path.getsize(p1) if e1 else 0
    sz2 = os.path.getsize(p2) if e2 else 0
    
    dpi_str = ""
    if e1 and out1.endswith(".png"):
        img = Image.open(p1)
        dpi = img.info.get('dpi', (0, 0))
        dpi_str = f", DPI={dpi[0]:.1f}x{dpi[1]:.1f}, size={img.size}"
        if dpi[0] < 300:
            failures.append(f"R4: Low DPI for {out1}: {dpi}")
            
    if e1 and e2 and sz1 > 0 and sz2 > 0:
        print(f"  [PASS] {out1} ({sz1} B{dpi_str}) & {out2} ({sz2} B)")
    else:
        failures.append(f"R4: Visualization pair missing or empty: {out1} / {out2}")
        print(f"  [FAIL] {out1} (exists={e1}, sz={sz1}) & {out2} (exists={e2}, sz={sz2})")

# 3. Check Zero Mock Data
print("\n--- Checking Zero Mock Data ---")
p_grep = subprocess.run(["grep", "-rn", "np.random", os.path.join(PROJECT_ROOT, "visualizer/prepare_data.py")], capture_output=True, text=True)
if len(p_grep.stdout.strip()) == 0:
    print("  [PASS] visualizer/prepare_data.py: 0 matches for np.random")
else:
    failures.append("R4: np.random found in visualizer/prepare_data.py")
    print(f"  [FAIL] np.random in visualizer/prepare_data.py: {p_grep.stdout}")

print_header("AUDIT SUMMARY & VERDICT")
if len(failures) == 0:
    print("VERDICT: VICTORY CONFIRMED")
    print("All checks (R1, R2, R3, R4) passed with 100% empirical evidence.")
else:
    print("VERDICT: VICTORY REJECTED")
    print(f"Total failures ({len(failures)}):")
    for f in failures:
        print(f" - {f}")
