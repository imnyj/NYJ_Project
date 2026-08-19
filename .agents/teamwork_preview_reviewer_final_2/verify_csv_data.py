import re
import os
import pandas as pd
import numpy as np

# Verify Table V (Table 5.3) values
conv_csv = "/home/imnyj/Workspace/paper4/coder/data/reward_convergence.csv"
if os.path.exists(conv_csv):
    df_conv = pd.read_csv(conv_csv)
    print("Found reward_convergence.csv with shape:", df_conv.shape)

# Verify Table VI (Table 5.4) values
cbr_csv = "/home/imnyj/Workspace/paper4/coder/data/cbr_trace.csv"
if os.path.exists(cbr_csv):
    df_cbr = pd.read_csv(cbr_csv)
    print("Found cbr_trace.csv with shape:", df_cbr.shape)
    for col in df_cbr.columns:
        if col != 'time':
            print(f"  {col}: mean={df_cbr[col].mean():.4f}, std={df_cbr[col].std():.4f}, min={df_cbr[col].min():.4f}, max={df_cbr[col].max():.4f}")

# Verify Table VII (Table 5.5) values
pdr_csv = "/home/imnyj/Workspace/paper4/coder/data/pdr_vs_density.csv"
if os.path.exists(pdr_csv):
    df_pdr = pd.read_csv(pdr_csv)
    print("Found pdr_vs_density.csv with shape:", df_pdr.shape)
    for col in ['REMO-DQN', 'Fixed 10Hz', 'AdaptDCC', 'Vanilla DQN']:
        if col in df_pdr.columns:
            low = df_pdr[col].iloc[0] * 100 if df_pdr[col].iloc[0] <= 1.0 else df_pdr[col].iloc[0]
            high = df_pdr[col].iloc[-1] * 100 if df_pdr[col].iloc[-1] <= 1.0 else df_pdr[col].iloc[-1]
            mean = df_pdr[col].mean() * 100 if df_pdr[col].mean() <= 1.0 else df_pdr[col].mean()
            print(f"  {col}: low={low:.2f}%, high={high:.2f}%, mean={mean:.2f}%")

# Verify Table IX (Table 5.7) values
aoi_csv = "/home/imnyj/Workspace/paper4/coder/data/aoi_vs_density.csv"
if os.path.exists(aoi_csv):
    df_aoi = pd.read_csv(aoi_csv)
    print("Found aoi_vs_density.csv with shape:", df_aoi.shape)
    for col in ['REMO-DQN', 'Fixed 10Hz', 'AdaptDCC', 'Vanilla DQN']:
        if col in df_aoi.columns:
            low = df_aoi[col].iloc[0]
            high = df_aoi[col].iloc[-1]
            mean = df_aoi[col].mean()
            print(f"  {col}: low={low:.2f} ms, high={high:.2f} ms, mean={mean:.2f} ms")

# Verify Table X (Table 5.8) values
dist_csv = "/home/imnyj/Workspace/paper4/coder/data/pdr_vs_distance.csv"
if os.path.exists(dist_csv):
    df_dist = pd.read_csv(dist_csv)
    print("Found pdr_vs_distance.csv with shape:", df_dist.shape)
    print(df_dist)

# Verify Table XI (Table 5.9) values
hw_csv = "/home/imnyj/Workspace/paper4/coder/data/hardware_feasibility.csv"
if os.path.exists(hw_csv):
    df_hw = pd.read_csv(hw_csv)
    print("Found hardware_feasibility.csv with shape:", df_hw.shape)
    print(df_hw)

# Verify Table XII (Table 5.10) values
abl_csv = "/home/imnyj/Workspace/paper4/coder/data/ablation_study.csv"
if os.path.exists(abl_csv):
    df_abl = pd.read_csv(abl_csv)
    print("Found ablation_study.csv with shape:", df_abl.shape)
    print(df_abl)

# Verify Table XIII (Table 5.11) values
moe_csv = "/home/imnyj/Workspace/paper4/coder/data/moe_routing.csv"
if os.path.exists(moe_csv):
    df_moe = pd.read_csv(moe_csv)
    print("Found moe_routing.csv with shape:", df_moe.shape)
    print(df_moe)

# Verify Table XIV (Table 5.12) values
tsne_csv = "/home/imnyj/Workspace/paper4/coder/data/tsne_clustering.csv"
if os.path.exists(tsne_csv):
    df_tsne = pd.read_csv(tsne_csv)
    print("Found tsne_clustering.csv with shape:", df_tsne.shape)
    for c in df_tsne['cluster'].unique():
        sub = df_tsne[df_tsne['cluster'] == c]
        print(f"  Cluster {c}: samples={len(sub)}, mean_x={sub['x'].mean():.3f}, std_x={sub['x'].std():.3f}, mean_y={sub['y'].mean():.3f}, std_y={sub['y'].std():.3f}")
