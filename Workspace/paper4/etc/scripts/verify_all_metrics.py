import os, glob
import pandas as pd
import numpy as np

print("==================================================")
print("1. Table 5.2: Optuna Hyperparameters Check")
print("==================================================")
optuna_dir = "/home/imnyj/Workspace/paper4/data/optuna"
for f in sorted(os.listdir(optuna_dir)):
    if f.endswith(".csv"):
        model_name = f.replace("best_params_", "").replace(".csv", "")
        df = pd.read_csv(os.path.join(optuna_dir, f))
        print(f"Model: {model_name}")
        for _, row in df.iterrows():
            print(f"  {row.iloc[0]}: {row.iloc[1]}")

print("\n==================================================")
print("2. Table 5.3: Reward Convergence & Episode Stats Check")
print("==================================================")
models_dir = "/home/imnyj/Workspace/paper4/data/models"
conv_files = sorted(glob.glob(os.path.join(models_dir, "*_convergence.csv")))
print(f"Found {len(conv_files)} convergence files.")

results_53 = []
for f in conv_files:
    model_name = os.path.basename(f).replace("_convergence.csv", "")
    df = pd.read_csv(f)
    n_episodes = len(df)
    init_5_reward = df['reward'].iloc[:5].mean() if 'reward' in df else np.nan
    final_10_reward = df['reward'].iloc[-10:].mean() if 'reward' in df else np.nan
    total_avg_reward = df['reward'].mean() if 'reward' in df else np.nan
    final_pdr = df['pdr'].iloc[-1] if 'pdr' in df else (df['pdr'].iloc[-10:].mean() if 'pdr' in df else np.nan)
    final_pdr_last10 = df['pdr'].iloc[-10:].mean() if 'pdr' in df else np.nan
    final_aoi = df['aoi'].iloc[-1] if 'aoi' in df else np.nan
    final_aoi_last10 = df['aoi'].iloc[-10:].mean() if 'aoi' in df else np.nan
    avg_cbr = df['cbr'].mean() if 'cbr' in df else np.nan
    final_cbr = df['cbr'].iloc[-1] if 'cbr' in df else np.nan
    
    print(f"Model: {model_name:20s} | Ep: {n_episodes:3d} | Init5_R: {init_5_reward:11.2f} | Final10_R: {final_10_reward:11.2f} | Avg_R: {total_avg_reward:11.2f} | Final_PDR: {final_pdr:.4f} (last10: {final_pdr_last10:.4f}) | Final_AoI: {final_aoi:.2f} (last10: {final_aoi_last10:.2f}) | Avg_CBR: {avg_cbr:.4f}")

print("\n==================================================")
print("3. Table 5.4: CBR Trace (100s) Check")
print("==================================================")
cbr_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/cbr_trace.csv")
print(cbr_df.describe())
for col in ['REMO-DQN', 'Vanilla DQN', 'DQN+MoE']:
    mean_val = cbr_df[col].mean()
    std_val = cbr_df[col].std()
    min_val = cbr_df[col].min()
    max_val = cbr_df[col].max()
    violations = (cbr_df[col] > 0.60).sum()
    viol_rate = (violations / len(cbr_df)) * 100.0
    print(f"{col:15s} -> Mean: {mean_val:.4f}, Std: {std_val:.4f}, Min: {min_val:.4f}, Max: {max_val:.4f}, Violations: {violations}, ViolRate: {viol_rate:.1f}%")

print("\n==================================================")
print("4. Table 5.5: PDR vs Density Check")
print("==================================================")
pdr_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/pdr_vs_density.csv")
print("Densities count:", len(pdr_df), "Range:", pdr_df['Density'].min(), "to", pdr_df['Density'].max())
# Find index for 10 veh/km, 50 veh/km, 100 veh/km
# Density is 10 to 100 with 50 points
print("Closest to 10:", pdr_df.iloc[0]['Density'])
print("Closest to 50:", pdr_df.iloc[(pdr_df['Density'] - 50).abs().argmin()]['Density'], "at idx", (pdr_df['Density'] - 50).abs().argmin())
print("Closest to 100:", pdr_df.iloc[-1]['Density'])

idx_10 = 0
idx_50 = (pdr_df['Density'] - 50).abs().argmin()
idx_100 = len(pdr_df) - 1

for col in pdr_df.columns:
    if col == 'Density': continue
    pdr_10 = pdr_df[col].iloc[idx_10]
    pdr_50 = pdr_df[col].iloc[idx_50]
    pdr_100 = pdr_df[col].iloc[idx_100]
    pdr_mean = pdr_df[col].mean()
    pdr_drop = pdr_10 - pdr_100
    print(f"{col:22s} | 10: {pdr_10:6.2f}% | 50: {pdr_50:6.2f}% | 100: {pdr_100:6.2f}% | Mean: {pdr_mean:6.2f}% | Drop: {pdr_drop:6.2f}%p")

print("\n==================================================")
print("5. Table 5.6: Energy Consumption & Efficiency Check")
print("==================================================")
raw_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/raw_metrics_density.csv")
print("raw_metrics_density.csv methods:", raw_df['method'].unique())
for m in raw_df['method'].unique():
    sub = raw_df[raw_df['method'] == m]
    print(f"Method: {m:15s} | CBR_mean: {sub['CBR_mean'].mean():.4f} | AoI_mean: {sub['AoI_mean'].mean():.2f} | PDR_mean: {sub['PDR_mean'].mean():.2f} | Energy: {sub['energy_efficiency'].mean():.4f}")

print("\n==================================================")
print("6. Table 5.7: AoI vs Density Check")
print("==================================================")
aoi_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/aoi_vs_density.csv")
for col in aoi_df.columns:
    if col == 'Density': continue
    aoi_10 = aoi_df[col].iloc[idx_10]
    aoi_50 = aoi_df[col].iloc[idx_50]
    aoi_100 = aoi_df[col].iloc[idx_100]
    aoi_mean = aoi_df[col].mean()
    aoi_increase = aoi_100 - aoi_10
    print(f"{col:22s} | 10: {aoi_10:8.2f} ms | 50: {aoi_50:8.2f} ms | 100: {aoi_100:8.2f} ms | Mean: {aoi_mean:8.2f} ms | Increase: {aoi_increase:8.2f} ms")

print("\n==================================================")
print("7. Table 5.8: PDR vs Distance Check")
print("==================================================")
dist_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/pdr_vs_distance.csv")
print(dist_df)
for _, row in dist_df.iterrows():
    d = row['Distance']
    v_pdr = row['Vanilla DQN']
    m_pdr = row['DQN+MoE']
    r_pdr = row['REMO-DQN']
    diff_v = r_pdr - v_pdr
    print(f"Dist: {d:3.0f}m | Vanilla: {v_pdr:6.2f}% | MoE: {m_pdr:6.2f}% | REMO: {r_pdr:6.2f}% | Diff(REMO - Vanilla): {diff_v:+6.2f}%p")

print("\n==================================================")
print("8. Table 5.9: Hardware Feasibility Check")
print("==================================================")
hw_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/hardware_feasibility.csv")
print(hw_df)

print("\n==================================================")
print("9. Table 5.10: Ablation Study Check")
print("==================================================")
ab_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/ablation_study.csv")
print(ab_df)

print("\n==================================================")
print("10. Table 5.11: MoE Routing Check")
print("==================================================")
moe_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/moe_routing.csv")
print(moe_df)

print("\n==================================================")
print("11. Table 5.12: t-SNE Clustering Check")
print("==================================================")
tsne_df = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/tsne_clustering.csv")
for c in tsne_df['Cluster'].unique():
    sub = tsne_df[tsne_df['Cluster'] == c]
    print(f"Cluster: {c:15s} | Count: {len(sub)} | x_mean: {sub['x'].mean():+.3f} +- {sub['x'].std():.3f} | y_mean: {sub['y'].mean():+.3f} +- {sub['y'].std():.3f}")
