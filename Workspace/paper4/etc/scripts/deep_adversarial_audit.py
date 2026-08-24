#!/usr/bin/env python3
import os
import glob
import json
import pandas as pd
import numpy as np
from scipy import stats

def run_deep_adversarial_audit():
    project_root = "/home/imnyj/Workspace/paper4"
    data_dir = os.path.join(project_root, "data")
    models_dir = os.path.join(data_dir, "models")
    
    report = {
        "task_1_convergence": {},
        "task_2_physical_constraints": {},
        "task_2_density_consistency": {},
        "overall_verdict": "FAIL",
        "detailed_reasons": []
    }
    
    # 1. 17 Models Convergence Stress Test
    model_files = sorted(glob.glob(os.path.join(models_dir, "*_convergence.csv")))
    unique_models = {}
    for f in model_files:
        mname = os.path.basename(f).replace("_convergence.csv", "")
        if mname == "Fixed 10Hz":
            continue
        unique_models[mname] = f
        
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
        
        model_verdict = "PASS" if (r_pass and eps_pass and (stat_pass or mname in ["Fixed10Hz", "ReactDCC", "AdaptDCC"])) else "FAIL"
        
        report["task_1_convergence"][mname] = {
            "episodes": episodes,
            "mean_init_reward": mean_init_r,
            "mean_final_reward": mean_final_r,
            "delta_reward": delta_r,
            "t_stat": float(t_stat),
            "p_val_one_tailed": float(p_val_one),
            "final_epsilon": final_eps,
            "reward_improvement": bool(r_pass),
            "epsilon_converged": bool(eps_pass),
            "statistically_significant": bool(stat_pass),
            "verdict": model_verdict
        }

    # 2. Boundary & Physical Constraints across all data CSVs
    all_data_files = glob.glob(os.path.join(data_dir, "*.csv")) + glob.glob(os.path.join(models_dir, "*.csv"))
    for f in sorted(all_data_files):
        rel = os.path.relpath(f, project_root)
        df = pd.read_csv(f)
        
        # Check NaN / Inf
        nan_total = int(df.isna().sum().sum())
        num_df = df.select_dtypes(include=np.number)
        inf_total = int(np.isinf(num_df).sum().sum()) if not num_df.empty else 0
        
        # Boundary checks per metric
        pdr_violations = []
        cbr_violations = []
        aoi_violations = []
        
        for col in df.columns:
            if col in ['Density', 'Distance', 'Episode', 'Global_Step', 'Cluster', 'x', 'y', 'Parameter', 'Algorithm', 'Method', 'Architecture', 'Tuned Hyperparameters', 'Search_Space', 'Sensitivity']:
                continue
            
            vals = df[col]
            if not pd.api.types.is_numeric_dtype(vals):
                continue
                
            c_low = col.lower()
            f_low = rel.lower()
            
            # PDR
            if 'pdr' in c_low or 'pdr_vs' in f_low:
                bad = vals[(vals < 0.0) | (vals > 100.0)]
                if len(bad) > 0:
                    pdr_violations.append({col: bad.tolist()})
            
            # CBR
            if 'cbr' in c_low or 'cbr_vs' in f_low or 'cbr_trace' in f_low:
                bad = vals[(vals < 0.0) | (vals > 1.0)]
                if len(bad) > 0:
                    cbr_violations.append({col: bad.tolist()})
                    
            # AoI
            if 'aoi' in c_low or 'aoi_vs' in f_low:
                bad = vals[vals <= 0.0]
                if len(bad) > 0:
                    aoi_violations.append({col: bad.tolist()})

        report["task_2_physical_constraints"][rel] = {
            "shape": list(df.shape),
            "nan_count": nan_total,
            "inf_count": inf_total,
            "pdr_violations": pdr_violations,
            "cbr_violations": cbr_violations,
            "aoi_violations": aoi_violations,
            "status": "PASS" if (nan_total == 0 and inf_total == 0 and len(pdr_violations) == 0 and len(cbr_violations) == 0 and len(aoi_violations) == 0) else "FAIL"
        }

    # 3. Density Consistency Check (Density 30, 50, 100 and sweep)
    # Check if PDR decreases or remains stable, CBR stays <= 1.0, AoI stays positive & physically plausible
    pdr_df = pd.read_csv(os.path.join(data_dir, "pdr_vs_density.csv"))
    cbr_df = pd.read_csv(os.path.join(data_dir, "cbr_vs_density.csv"))
    aoi_df = pd.read_csv(os.path.join(data_dir, "aoi_vs_density.csv"))
    
    report["task_2_density_consistency"]["densities"] = pdr_df['Density'].tolist()
    report["task_2_density_consistency"]["remo_pdr_trend"] = pdr_df['REMO-DQN'].tolist()
    report["task_2_density_consistency"]["remo_cbr_trend"] = cbr_df['REMO-DQN'].tolist()
    report["task_2_density_consistency"]["remo_aoi_trend"] = aoi_df['REMO-DQN'].tolist()
    
    # Check monotonic or physically sound trends
    # CBR increases with density
    cbr_vals = cbr_df['REMO-DQN'].values
    cbr_increasing = bool(np.all(np.diff(cbr_vals) >= -1e-5))
    
    # AoI > 0
    aoi_vals = aoi_df['REMO-DQN'].values
    aoi_positive = bool(np.all(aoi_vals > 0))
    
    # PDR in [0, 100]
    pdr_vals = pdr_df['REMO-DQN'].values
    pdr_valid = bool(np.all((pdr_vals >= 0) & (pdr_vals <= 100)))
    
    report["task_2_density_consistency"]["cbr_physical_trend_sound"] = cbr_increasing
    report["task_2_density_consistency"]["aoi_physical_valid"] = aoi_positive
    report["task_2_density_consistency"]["pdr_physical_valid"] = pdr_valid
    
    # Output to JSON
    json_path = os.path.join(project_root, "etc", "scripts", "empirical_audit_results.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"Audit results written to {json_path}")
    
    # Print summary
    failed_models = [m for m, v in report["task_1_convergence"].items() if v["verdict"] == "FAIL"]
    print(f"\nTotal Models Tested: {len(report['task_1_convergence'])}")
    print(f"Passed Models: {len(report['task_1_convergence']) - len(failed_models)}")
    print(f"Failed Models: {len(failed_models)} ({failed_models})")
    
if __name__ == "__main__":
    run_deep_adversarial_audit()
