#!/usr/bin/env python3
"""
run_all_ablations.py
====================
Master orchestrator to run full 100-episode x 2000-step training for:
  - 4 Structure Ablation variants (REMO-DQN, wo_ResNet, wo_MoE, wo_Dueling)
  - 4 Reward Ablation variants (REMO-DQN, wo_R1, wo_R2, wo_R3)
Runs on GPU 3 in parallel (8 concurrent processes).
"""

import os
import sys
import time
import subprocess
import csv
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODE_DIR = os.path.join(PROJECT_ROOT, "code")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
STRUCT_DIR = os.path.join(DATA_DIR, "ablation_structure")
REWARD_DIR = os.path.join(DATA_DIR, "ablation_reward")

os.makedirs(STRUCT_DIR, exist_ok=True)
os.makedirs(REWARD_DIR, exist_ok=True)

def run_cmd(cmd, log_file):
    with open(log_file, "w") as out:
        p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, cwd=PROJECT_ROOT)
    return p

def main():
    t0 = time.time()
    print("=" * 80)
    print("STARTING FULL 100-EPISODE ABLATION RUNS (STRUCTURE & REWARD) ON GPU 3")
    print("=" * 80)

    # 1. Structure Ablations (4 variants)
    struct_variants = ["REMO-DQN", "wo_ResNet", "wo_MoE", "wo_Dueling"]
    procs = {}
    for var in struct_variants:
        log_out = os.path.join(PROJECT_ROOT, "etc", f"log_struct_{var}.txt")
        cmd = [
            sys.executable,
            os.path.join(CODE_DIR, "run_ablation_structure.py"),
            "--variant", var,
            "--episodes", "100",
            "--duration_steps", "2000",
            "--device", "cuda:3"
        ]
        procs[f"struct_{var}"] = (run_cmd(cmd, log_out), log_out)
        print(f"  -> Spawned Structure Variant: {var} (Log: {log_out})")

    # 2. Reward Ablations (4 variants)
    reward_variants = ["REMO-DQN", "wo_R1", "wo_R2", "wo_R3"]
    for var in reward_variants:
        log_out = os.path.join(PROJECT_ROOT, "etc", f"log_reward_{var}.txt")
        cmd = [
            sys.executable,
            os.path.join(CODE_DIR, "run_ablation_reward.py"),
            "--variant", var,
            "--episodes", "100",
            "--duration_steps", "2000",
            "--device", "cuda:3"
        ]
        procs[f"reward_{var}"] = (run_cmd(cmd, log_out), log_out)
        print(f"  -> Spawned Reward Variant: {var} (Log: {log_out})")

    # Monitor all 8 processes
    total_count = len(procs)
    while procs:
        time.sleep(15)
        done_keys = []
        for key, (p, lfile) in procs.items():
            ret = p.poll()
            if ret is not None:
                elapsed = time.time() - t0
                print(f"[Done] {key} completed with return code {ret} at {elapsed/60:.2f}m")
                done_keys.append(key)
        for dk in done_keys:
            del procs[dk]
        remaining = len(procs)
        if remaining > 0:
            print(f"[{time.strftime("%H:%M:%S")}] {total_count - remaining}/{total_count} tasks completed. {remaining} in progress...")

    print("\nAll 8 training runs complete! Merging datasets...")
    # Merge structure CSV
    subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, \"code\"); from run_ablation_structure import merge_structure_ablation_csv; merge_structure_ablation_csv()"], cwd=PROJECT_ROOT)
    # Merge reward CSV
    subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, \"code\"); from run_ablation_reward import merge_reward_ablation_csv; merge_reward_ablation_csv()"], cwd=PROJECT_ROOT)
    # Build unified ablation_study.csv
    build_unified_ablation_study()

    elapsed = time.time() - t0
    print(f"\nALL ABLATION RUNS & DATASETS COMPLETED in {elapsed/60:.2f} minutes!")

def build_unified_ablation_study():
    remo_log = os.path.join(STRUCT_DIR, "REMO-DQN_train_log.csv")
    wo_resnet_log = os.path.join(STRUCT_DIR, "wo_ResNet_train_log.csv")
    wo_moe_log = os.path.join(STRUCT_DIR, "wo_MoE_train_log.csv")
    wo_dueling_log = os.path.join(STRUCT_DIR, "wo_Dueling_train_log.csv")

    wo_r1_log = os.path.join(REWARD_DIR, "wo_R1_train_log.csv")
    wo_r2_log = os.path.join(REWARD_DIR, "wo_R2_train_log.csv")
    wo_r3_log = os.path.join(REWARD_DIR, "wo_R3_train_log.csv")

    df_remo = pd.read_csv(remo_log)
    df_wo_res = pd.read_csv(wo_resnet_log)
    df_wo_moe = pd.read_csv(wo_moe_log)
    df_wo_duel = pd.read_csv(wo_dueling_log)

    df_wo_r1 = pd.read_csv(wo_r1_log)
    df_wo_r2 = pd.read_csv(wo_r2_log)
    df_wo_r3 = pd.read_csv(wo_r3_log)

    n_episodes = len(df_remo)

    df_unified = pd.DataFrame({
        "Episode": df_remo["Episode"],
        "Global_Step": df_remo["Global_Step"],
        "REMO-DQN": df_remo["Reward"],
        "w/o ResNet": df_wo_res["Reward"].values[:n_episodes],
        "w/o MoE": df_wo_moe["Reward"].values[:n_episodes],
        "w/o Dueling": df_wo_duel["Reward"].values[:n_episodes],
        "w/o R1": df_wo_r1["Reward"].values[:n_episodes],
        "w/o R2": df_wo_r2["Reward"].values[:n_episodes],
        "w/o R3": df_wo_r3["Reward"].values[:n_episodes],
    })

    out_path = os.path.join(DATA_DIR, "ablation_study.csv")
    df_unified.to_csv(out_path, index=False)
    print(f"Saved {out_path} with {len(df_unified)} rows and columns: {list(df_unified.columns)}")

if __name__ == "__main__":
    main()
