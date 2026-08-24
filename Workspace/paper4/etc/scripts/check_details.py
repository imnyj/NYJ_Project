#!/usr/bin/env python3
import os
import glob
import pandas as pd
import numpy as np

def check_details():
    project_root = "/home/imnyj/Workspace/paper4"
    data_dir = os.path.join(project_root, "data")
    models_dir = os.path.join(data_dir, "models")
    
    print("=== PDR VIOLATIONS IN pdr_vs_density.csv ===")
    df_pdr_dens = pd.read_csv(os.path.join(data_dir, "pdr_vs_density.csv"))
    print(df_pdr_dens)
    for col in df_pdr_dens.columns:
        if col == "Density":
            continue
        vals = df_pdr_dens[col].values
        bad = vals[(vals < 0) | (vals > 100)]
        if len(bad) > 0:
            print(f"Violation in {col}: {bad}")

    print("\n=== PDR VIOLATIONS IN pdr_vs_distance.csv ===")
    df_pdr_dist = pd.read_csv(os.path.join(data_dir, "pdr_vs_distance.csv"))
    print(df_pdr_dist)
    for col in df_pdr_dist.columns:
        if col == "Distance":
            continue
        vals = df_pdr_dist[col].values
        bad = vals[(vals < 0) | (vals > 100)]
        if len(bad) > 0:
            print(f"Violation in {col}: {bad}")

    print("\n=== 17 MODELS INDIVIDUAL CONVERGENCE SUMMARY ===")
    conv_files = sorted(glob.glob(os.path.join(models_dir, "*_convergence.csv")))
    for f in conv_files:
        mname = os.path.basename(f).replace("_convergence.csv", "")
        df = pd.read_csv(f)
        init_r = df['Reward'].iloc[:10].values
        final_r = df['Reward'].iloc[-10:].values
        mean_init = np.mean(init_r)
        mean_final = np.mean(final_r)
        delta = mean_final - mean_init
        
        # Density distribution
        dens_col = df['Density'] if 'Density' in df.columns else None
        init_dens = dens_col.iloc[:10].tolist() if dens_col is not None else []
        final_dens = dens_col.iloc[-10:].tolist() if dens_col is not None else []
        
        eps_final = df['Epsilon'].iloc[-1] if 'Epsilon' in df.columns else 'N/A'
        
        print(f"Model: {mname:<20s} | InitR: {mean_init:10.1f} | FinalR: {mean_final:10.1f} | Delta: {delta:+10.1f} | FinalEps: {eps_final} | InitDensMean: {np.mean(init_dens):.1f} | FinalDensMean: {np.mean(final_dens):.1f}")

if __name__ == "__main__":
    check_details()
