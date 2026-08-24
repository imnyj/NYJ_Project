#!/usr/bin/env python3
import os
import glob
import json
import pandas as pd
import numpy as np
from scipy import stats

def run_comprehensive_empirical_validation():
    project_root = "/home/imnyj/Workspace/paper4"
    data_dir = os.path.join(project_root, "data")
    models_dir = os.path.join(data_dir, "models")
    
    results = {
        "convergence_test": {},
        "boundary_test": {},
        "density_consistency": {},
        "ablation_test": {}
    }
    
    print("=" * 80)
    print("1. MODEL CONVERGENCE & STATISTICAL SIGNIFICANCE STRESS TEST (17 MODELS)")
    print("=" * 80)
    
    model_files = sorted(glob.glob(os.path.join(models_dir, "*_convergence.csv")))
    # Normalize duplicate Fixed 10Hz if exists
    unique_models = {}
    for f in model_files:
        basename = os.path.basename(f)
        mname = basename.replace("_convergence.csv", "")
        if mname == "Fixed 10Hz":
            continue # duplicate with Fixed10Hz
        unique_models[mname] = f
        
    print(f"Total Unique Models found in data/models: {len(unique_models)}")
    
    table_rows = []
    
    for mname, fpath in unique_models.items():
        df = pd.read_csv(fpath)
        episodes = len(df)
        init_df = df.iloc[:10]
        final_df = df.iloc[-10:]
        
        init_r = init_df['Reward'].values
        final_r = final_df['Reward'].values
        mean_init_r = float(np.mean(init_r))
        mean_final_r = float(np.mean(final_r))
        std_init_r = float(np.std(init_r))
        std_final_r = float(np.std(final_r))
        delta_r = mean_final_r - mean_init_r
        
        # t-test
        t_stat, p_val_two = stats.ttest_ind(final_r, init_r, equal_var=False)
        if np.isnan(t_stat) or (std_init_r == 0 and std_final_r == 0):
            p_val_one = 1.0 if delta_r <= 0 else 0.0
            t_stat = 0.0
        else:
            p_val_one = p_val_two / 2.0 if t_stat > 0 else 1.0 - (p_val_two / 2.0)
            
        final_eps = float(df['Epsilon'].iloc[-1]) if 'Epsilon' in df.columns else 0.0
        start_eps = float(df['Epsilon'].iloc[0]) if 'Epsilon' in df.columns else 0.0
        uses_eps = (start_eps > 0.0)
        
        eps_pass = (final_eps <= 0.015) if uses_eps else True
        r_pass = (mean_final_r > mean_init_r)
        stat_pass = (p_val_one < 0.05) if r_pass else False
        
        # Density distribution in training
        if 'Density' in df.columns:
            densities = df['Density'].unique().tolist()
            init_dens = init_df['Density'].mean()
            final_dens = final_df['Density'].mean()
        else:
            densities = []
            init_dens = np.nan
            final_dens = np.nan
            
        init_pdr = float(init_df['PDR_mean'].mean()) if 'PDR_mean' in init_df.columns else np.nan
        final_pdr = float(final_df['PDR_mean'].mean()) if 'PDR_mean' in final_df.columns else np.nan
        init_aoi = float(init_df['AoI_mean'].mean()) if 'AoI_mean' in init_df.columns else np.nan
        final_aoi = float(final_df['AoI_mean'].mean()) if 'AoI_mean' in final_df.columns else np.nan
        init_cbr = float(init_df['CBR_mean'].mean()) if 'CBR_mean' in init_df.columns else np.nan
        final_cbr = float(final_df['CBR_mean'].mean()) if 'CBR_mean' in final_df.columns else np.nan
        
        results["convergence_test"][mname] = {
            "episodes": episodes,
            "mean_init_r": mean_init_r,
            "mean_final_r": mean_final_r,
            "delta_r": delta_r,
            "t_stat": float(t_stat),
            "p_val_one_tailed": float(p_val_one),
            "final_epsilon": final_eps,
            "eps_pass": eps_pass,
            "r_pass": r_pass,
            "stat_pass": stat_pass,
            "init_pdr": init_pdr,
            "final_pdr": final_pdr,
            "init_aoi": init_aoi,
            "final_aoi": final_aoi,
            "init_cbr": init_cbr,
            "final_cbr": final_cbr,
            "init_dens_mean": float(init_dens),
            "final_dens_mean": float(final_dens)
        }
        
        print(f"[{mname:20s}] Ep:{episodes:3d} | InitR:{mean_init_r:11.1f} -> FinalR:{mean_final_r:11.1f} | Delta:{delta_r:+11.1f} | p-val:{p_val_one:.4e} | Eps:{final_eps:.4f} | R_inc:{'PASS' if r_pass else 'FAIL'} | Eps_conv:{'PASS' if eps_pass else 'FAIL'}")

    print("\n" + "=" * 80)
    print("2. REWARD_CONVERGENCE.CSV CONVERGENCE CHECK (17 MODELS MERGED)")
    print("=" * 80)
    rc_path = os.path.join(data_dir, "reward_convergence.csv")
    if os.path.exists(rc_path):
        rc_df = pd.read_csv(rc_path)
        print(f"reward_convergence.csv shape: {rc_df.shape}, Episodes: {len(rc_df)}")
        for col in rc_df.columns:
            if col in ['Episode', 'Global_Step']:
                continue
            init_val = rc_df[col].iloc[:10].mean()
            final_val = rc_df[col].iloc[-10:].mean()
            delta = final_val - init_val
            t_s, p_2 = stats.ttest_ind(rc_df[col].iloc[-10:], rc_df[col].iloc[:10], equal_var=False)
            p_1 = p_2 / 2.0 if t_s > 0 else 1.0 - (p_2 / 2.0)
            print(f"  Col: {col:20s} | Init:{init_val:11.1f} -> Final:{final_val:11.1f} | Delta:{delta:+11.1f} | p:{p_1:.4e} | {'PASS' if delta > 0 else 'FAIL'}")

    print("\n" + "=" * 80)
    print("3. PHYSICAL & DOMAIN CONSTRAINT BOUNDARY CHECKS (ALL CSV FILES)")
    print("=" * 80)
    
    all_csvs = glob.glob(os.path.join(data_dir, "*.csv")) + glob.glob(os.path.join(models_dir, "*.csv"))
    
    for f in sorted(all_csvs):
        rel_f = os.path.relpath(f, project_root)
        try:
            df = pd.read_csv(f)
        except Exception as e:
            print(f"[ERROR reading {rel_f}]: {e}")
            continue
            
        nan_count = df.isna().sum().sum()
        inf_count = np.isinf(df.select_dtypes(include=np.number)).sum().sum()
        
        # Check boundary rules per column type
        pdr_violations = 0
        cbr_violations = 0
        aoi_violations = 0
        
        num_cols = df.select_dtypes(include=np.number).columns
        
        for c in num_cols:
            c_lower = c.lower()
            vals = df[c].dropna().values
            if len(vals) == 0:
                continue
                
            # PDR checks
            if 'pdr' in c_lower or 'pdr_mean' in c_lower or 'pdr_vs' in rel_f.lower():
                # check if values are within [0, 100] (or [0, 1.0])
                if np.any(vals < 0.0) or np.any(vals > 100.0):
                    pdr_violations += int(np.sum((vals < 0.0) | (vals > 100.0)))
            
            # CBR checks
            if 'cbr' in c_lower or 'cbr_mean' in c_lower or 'cbr_vs' in rel_f.lower() or 'cbr_trace' in rel_f.lower():
                if np.any(vals < 0.0) or np.any(vals > 1.0):
                    cbr_violations += int(np.sum((vals < 0.0) | (vals > 1.0)))
                    
            # AoI checks
            if 'aoi' in c_lower or 'aoi_mean' in c_lower or 'aoi_vs' in rel_f.lower():
                if np.any(vals <= 0.0):
                    aoi_violations += int(np.sum(vals <= 0.0))
                    
        has_error = (nan_count > 0 or inf_count > 0 or pdr_violations > 0 or cbr_violations > 0 or aoi_violations > 0)
        status_str = "[FAIL]" if has_error else "[PASS]"
        print(f"{status_str} {rel_f:45s} | Shape:{str(df.shape):10s} | NaN:{nan_count} | Inf:{inf_count} | PDR_viol:{pdr_violations} | CBR_viol:{cbr_violations} | AoI_viol:{aoi_violations}")

    print("\n" + "=" * 80)
    print("4. DENSITY CONSISTENCY CHECK (DENSITY 30, 50, 100 AND FULL SWEEP)")
    print("=" * 80)
    # Check pdr_vs_density, cbr_vs_density, aoi_vs_density
    for metric, filename in [("PDR", "pdr_vs_density.csv"), ("CBR", "cbr_vs_density.csv"), ("AoI", "aoi_vs_density.csv"), ("Throughput", "throughput_vs_density.csv")]:
        fpath = os.path.join(data_dir, filename)
        if os.path.exists(fpath):
            df = pd.read_csv(fpath)
            print(f"\n--- {metric} vs Density ---")
            print(df[['Density', 'REMO-DQN', 'Fixed 10Hz', 'ReactDCC', 'AdaptDCC', 'MoEDQN']].to_string())
            
            # Check physical consistency:
            # As density increases:
            # - CBR should generally increase or stay bounded
            # - PDR should generally decrease or stay controlled
            # - AoI should increase or stay controlled
            densities = df['Density'].values
            remo_vals = df['REMO-DQN'].values
            print(f"REMO-DQN {metric} trend with Density {densities}: {remo_vals}")

    print("\n" + "=" * 80)
    print("5. ABLATION STUDIES CONVERGENCE & INTEGRITY CHECK")
    print("=" * 80)
    for ab_name in ["ablation_structure.csv", "ablation_reward.csv", "ablation_study.csv"]:
        ab_path = os.path.join(data_dir, ab_name)
        if os.path.exists(ab_path):
            df = pd.read_csv(ab_path)
            print(f"\n[Ablation] {ab_name} (Shape: {df.shape})")
            print(f"Columns: {list(df.columns)}")
            for col in df.columns:
                if col in ['Episode', 'Global_Step']:
                    continue
                init_v = df[col].iloc[:10].mean()
                final_v = df[col].iloc[-10:].mean()
                delta = final_v - init_v
                print(f"  Variant: {col:25s} | Init:{init_v:11.1f} -> Final:{final_v:11.1f} | Delta:{delta:+11.1f} | {'PASS' if delta > 0 else 'FAIL'}")

if __name__ == "__main__":
    run_comprehensive_empirical_validation()
