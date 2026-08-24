import os
import pandas as pd
import numpy as np

base_dir = "/home/imnyj/Workspace/paper4"
data_dir = os.path.join(base_dir, "data")

print("=== DEEP INTEGRITY & CONSISTENCY CHECK ===")

# 1. Check consistency between ablation_study.csv vs ablation_structure.csv vs ablation_reward.csv
df_study = pd.read_csv(os.path.join(data_dir, "ablation_study.csv"))
df_struct = pd.read_csv(os.path.join(data_dir, "ablation_structure.csv"))
df_rew = pd.read_csv(os.path.join(data_dir, "ablation_reward.csv"))
df_conv = pd.read_csv(os.path.join(data_dir, "reward_convergence.csv"))

print("\n1. Ablation Cross-Consistency:")
diff_remo_struct = np.max(np.abs(df_study["REMO-DQN"] - df_struct["REMO-DQN"]))
diff_remo_rew = np.max(np.abs(df_study["REMO-DQN"] - df_rew["REMO-DQN"]))
diff_remo_conv = np.max(np.abs(df_study["REMO-DQN"] - df_conv["REMO-DQN"]))
print(f"Max Diff (study vs struct REMO-DQN): {diff_remo_struct}")
print(f"Max Diff (study vs rew REMO-DQN): {diff_remo_rew}")
print(f"Max Diff (study vs conv REMO-DQN): {diff_remo_conv}")

diff_resnet = np.max(np.abs(df_study["w/o ResNet"] - df_struct["wo_ResNet"]))
diff_moe = np.max(np.abs(df_study["w/o MoE"] - df_struct["wo_MoE"]))
diff_dueling = np.max(np.abs(df_study["w/o Dueling"] - df_struct["wo_Dueling"]))
print(f"Max Diff (study vs struct w/o ResNet): {diff_resnet}")
print(f"Max Diff (study vs struct w/o MoE): {diff_moe}")
print(f"Max Diff (study vs struct w/o Dueling): {diff_dueling}")

diff_r1 = np.max(np.abs(df_study["w/o R1"] - df_rew["wo_R1"]))
diff_r2 = np.max(np.abs(df_study["w/o R2"] - df_rew["wo_R2"]))
diff_r3 = np.max(np.abs(df_study["w/o R3"] - df_rew["wo_R3"]))
print(f"Max Diff (study vs rew w/o R1): {diff_r1}")
print(f"Max Diff (study vs rew w/o R2): {diff_r2}")
print(f"Max Diff (study vs rew w/o R3): {diff_r3}")

# 2. Convergence Analysis (First 10 episodes vs Last 10 episodes)
print("\n2. Convergence Trend Analysis (Initial vs Final Mean Reward):")
cols_to_check = ['REMO-DQN', 'w/o ResNet', 'w/o MoE', 'w/o Dueling', 'w/o R1', 'w/o R2', 'w/o R3']
for c in cols_to_check:
    first_10 = df_study[c].iloc[:10].mean()
    last_10 = df_study[c].iloc[-10:].mean()
    gain = last_10 - first_10
    print(f"  {c:15s} | First 10: {first_10:11.2f} | Last 10: {last_10:11.2f} | Gain: {gain:+10.2f}")

# 3. Baseline Comparisons across Density
print("\n3. Density Sweeps (PDR, AoI, CBR across models):")
df_pdr = pd.read_csv(os.path.join(data_dir, "pdr_vs_density.csv"))
df_aoi = pd.read_csv(os.path.join(data_dir, "aoi_vs_density.csv"))
df_cbr = pd.read_csv(os.path.join(data_dir, "cbr_vs_density.csv"))

print("PDR vs Density (Proposed vs Fixed 10Hz vs AdaptDCC):")
print(df_pdr[['Density', 'REMO-DQN', 'Fixed 10Hz', 'AdaptDCC', 'ReactDCC']])

print("\nAoI vs Density (Proposed vs Fixed 10Hz vs AdaptDCC):")
print(df_aoi[['Density', 'REMO-DQN', 'Fixed 10Hz', 'AdaptDCC', 'ReactDCC']])

print("\nCBR vs Density (Proposed vs Fixed 10Hz vs AdaptDCC):")
print(df_cbr[['Density', 'REMO-DQN', 'Fixed 10Hz', 'AdaptDCC', 'ReactDCC']])

# 4. Check for Integrity Violations / Constant Arrays / Fake Linear Functions
print("\n4. Hardcoding & Artificial Linear Pattern Detection:")
for c in cols_to_check:
    diffs = np.diff(df_study[c].values)
    is_constant_diff = np.allclose(diffs, diffs[0])
    std_val = np.std(df_study[c].values)
    print(f"  {c:15s} | Linear: {is_constant_diff} | Std: {std_val:8.2f} | Unique values: {len(np.unique(df_study[c].values))}")

