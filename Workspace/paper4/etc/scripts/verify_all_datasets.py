import os
import pandas as pd
import numpy as np

DATA_DIR = "/home/imnyj/Workspace/paper4/data"

TARGET_FILES = [
    "ablation_study.csv",
    "optuna_sensitivity.csv",
    "reward_convergence.csv",
    "tsne_clustering.csv",
    "moe_routing.csv",
    "cbr_trace.csv",
    "pdr_vs_density.csv",
    "aoi_vs_density.csv",
    "pdr_vs_distance.csv",
    "aoi_vs_distance.csv",
    "hardware_feasibility.csv"
]

ALGORITHMS_17 = [
    "REMO-DQN (Proposed)",
    "Fixed 10Hz",
    "ReactDCC",
    "AdaptDCC",
    "MoEDQN",
    "MAPPO",
    "PPO",
    "SAC",
    "DDPG",
    "TD3",
    "DuelingDQN",
    "DoubleDQN",
    "VanillaDQN",
    "QLearning",
    "SARSA",
    "ActorCritic",
    "DecisionTransformer"
]

print("=" * 70)
print("COMPREHENSIVE DATA INTEGRITY & SANITY VERIFICATION")
print("=" * 70)

all_passed = True

# 1. Existence and non-emptiness check
print("\n[Check 1] 11 Target Files Existence & Shape Check:")
for fname in TARGET_FILES:
    fpath = os.path.join(DATA_DIR, fname)
    if not os.path.exists(fpath):
        print(f"❌ FAIL: Missing {fname}")
        all_passed = False
        continue
    df = pd.read_csv(fpath)
    if len(df) == 0:
        print(f"❌ FAIL: {fname} is empty")
        all_passed = False
    else:
        print(f"✅ PASS: {fname:<25s} | Shape: {df.shape} | Nulls: {df.isnull().sum().sum()}")

# 2. 17 Algorithms check for multi-model CSVs
MULTI_MODEL_CSVS = [
    "reward_convergence.csv",
    "cbr_trace.csv",
    "pdr_vs_density.csv",
    "aoi_vs_density.csv",
    "pdr_vs_distance.csv",
    "aoi_vs_distance.csv"
]

print("\n[Check 2] 17 Algorithms Exact Naming & Column Order Check:")
for fname in MULTI_MODEL_CSVS:
    fpath = os.path.join(DATA_DIR, fname)
    df = pd.read_csv(fpath)
    cols = list(df.columns)
    first_col = cols[0]
    algo_cols = cols[1:]
    
    mismatches = []
    for expected, actual in zip(ALGORITHMS_17, algo_cols):
        if expected != actual:
            mismatches.append((expected, actual))
            
    if mismatches or len(algo_cols) != 17:
        print(f"❌ FAIL: {fname} column mismatch! Len={len(algo_cols)}, Mismatches={mismatches}")
        all_passed = False
    else:
        print(f"✅ PASS: {fname:<25s} | First col: {first_col:<10s} | Exactly 17 algorithms matched!")

# 3. Value domain sanity check
print("\n[Check 3] Value Domain & Physical Bounds Sanity Check:")
df_pdr_dens = pd.read_csv(os.path.join(DATA_DIR, "pdr_vs_density.csv"))
pdr_vals = df_pdr_dens[ALGORITHMS_17].values
if (pdr_vals < 0).any() or (pdr_vals > 100.0).any():
    print("❌ FAIL: PDR values out of bounds [0, 100]")
    all_passed = False
else:
    print(f"✅ PASS: pdr_vs_density values in [0, 100]% (Min: {pdr_vals.min():.2f}%, Max: {pdr_vals.max():.2f}%)")

df_pdr_dist = pd.read_csv(os.path.join(DATA_DIR, "pdr_vs_distance.csv"))
pdr_dist_vals = df_pdr_dist[ALGORITHMS_17].values
if (pdr_dist_vals < 0).any() or (pdr_dist_vals > 100.0).any():
    print("❌ FAIL: PDR distance values out of bounds [0, 100]")
    all_passed = False
else:
    print(f"✅ PASS: pdr_vs_distance values in [0, 100]% (Min: {pdr_dist_vals.min():.2f}%, Max: {pdr_dist_vals.max():.2f}%)")

df_cbr = pd.read_csv(os.path.join(DATA_DIR, "cbr_trace.csv"))
cbr_vals = df_cbr[ALGORITHMS_17].values
if (cbr_vals < 0).any() or (cbr_vals > 1.0).any():
    print("❌ FAIL: CBR values out of bounds [0, 1]")
    all_passed = False
else:
    print(f"✅ PASS: cbr_trace values in [0, 1] (Min: {cbr_vals.min():.4f}, Max: {cbr_vals.max():.4f})")

df_aoi_dens = pd.read_csv(os.path.join(DATA_DIR, "aoi_vs_density.csv"))
aoi_vals = df_aoi_dens[ALGORITHMS_17].values
if (aoi_vals < 0).any():
    print("❌ FAIL: Negative AoI values detected")
    all_passed = False
else:
    print(f"✅ PASS: aoi_vs_density values positive (Min: {aoi_vals.min():.2f} ms, Max: {aoi_vals.max():.2f} ms)")

df_moe = pd.read_csv(os.path.join(DATA_DIR, "moe_routing.csv"))
weight_sums = df_moe[['Expert1 (Low Density)', 'Expert2 (Medium Density)', 'Expert3 (High Density)']].sum(axis=1)
if not (weight_sums == 100).all():
    print(f"❌ FAIL: MoE routing weights do not sum to 100: {weight_sums.values}")
    all_passed = False
else:
    print(f"✅ PASS: moe_routing weights sum to 100% across all {len(df_moe)} density points.")

df_tsne = pd.read_csv(os.path.join(DATA_DIR, "tsne_clustering.csv"))
clusters = df_tsne['Cluster'].unique()
if set(clusters) != {'Low Traffic', 'Medium Traffic', 'High Traffic'}:
    print(f"❌ FAIL: t-SNE clusters unexpected: {clusters}")
    all_passed = False
else:
    print(f"✅ PASS: tsne_clustering contains 3 distinct clusters: {list(clusters)}")

df_hw = pd.read_csv(os.path.join(DATA_DIR, "hardware_feasibility.csv"))
if 'REMO-DQN (Proposed)' not in df_hw['Method'].values:
    print("❌ FAIL: REMO-DQN missing in hardware_feasibility.csv")
    all_passed = False
else:
    print(f"✅ PASS: hardware_feasibility contains {len(df_hw)} methods including REMO-DQN (Proposed).")

# Visualizer directory check
legacy_backup = "/home/imnyj/Workspace/paper4/visualizer/backup/legacy_20260819_pre_critic"
print(f"\n[Check 4] Visualizer Directory Quarantine Status:")
if not os.path.exists(legacy_backup):
    print("❌ FAIL: legacy backup directory missing")
    all_passed = False
else:
    legacy_files = os.listdir(legacy_backup)
    print(f"✅ PASS: legacy backup directory exists with {len(legacy_files)} quarantined legacy files.")

vis_files = os.listdir("/home/imnyj/Workspace/paper4/visualizer")
print(f"Active items in visualizer/: {vis_files}")
legacy_names = ['1_reward_convergence.png', '2_ablation_study.png', '3_moe_routing.png', '4_tsne_clustering.png',
                '5_hardware_feasibility.png', '7_cbr_trace.png', '8_pdr_vs_density.png', '9_aoi_vs_density.png',
                '10_pdr_vs_distance.png', 'convergence.png', 'line_density.png', 'config.md']
legacy_in_root = [f for f in vis_files if f in legacy_names]
if legacy_in_root:
    print(f"❌ FAIL: Legacy files found in root: {legacy_in_root}")
    all_passed = False
else:
    print("✅ PASS: All legacy files successfully quarantined. Only fresh target outputs and scripts present.")

print("\n" + "=" * 70)
if all_passed:
    print("🎉 ALL DATA INTEGRITY & WORKSPACE CHECKS PASSED WITH 100% PERFECTION!")
else:
    print("⚠️ SOME CHECKS FAILED! Please review logs.")
print("=" * 70)
