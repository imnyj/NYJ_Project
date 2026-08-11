import os
import glob
import pandas as pd
import numpy as np
import json

MODELS_DIR = "/home/imnyj/Workspace/paper4/data/models"

EXPECTED_MODELS = [
    "QLearning", "SARSA", "ActorCritic", "VanillaDQN", "DoubleDQN",
    "DuelingDQN", "DDPG", "PPO", "SAC", "TD3",
    "DecisionTransformer", "MAPPO", "MoEDQN", "REMO-DQN"
]

EXPECTED_EPISODES = 100

def verify_all():
    report = {
        "total_expected_models": len(EXPECTED_MODELS),
        "missing_csv_files": [],
        "present_csv_files": [],
        "details": {},
        "overall_pass": True
    }
    
    print("=== Paper4 M1 Convergence CSV & Model Weights Integrity Verification ===")
    print(f"Target Directory: {MODELS_DIR}\n")
    
    for model in EXPECTED_MODELS:
        csv_name = f"{model}_convergence.csv"
        csv_path = os.path.join(MODELS_DIR, csv_name)
        pth_path = os.path.join(MODELS_DIR, f"{model}.pth")
        pkl_path = os.path.join(MODELS_DIR, f"{model}.pkl")
        
        weight_exists = os.path.exists(pth_path) or os.path.exists(pkl_path)
        weight_file = pth_path if os.path.exists(pth_path) else (pkl_path if os.path.exists(pkl_path) else None)
        weight_size = os.path.getsize(weight_file) if weight_exists else 0
        
        model_res = {
            "model": model,
            "csv_exists": os.path.exists(csv_path),
            "weight_exists": weight_exists,
            "weight_file": os.path.basename(weight_file) if weight_file else None,
            "weight_size_bytes": weight_size,
            "header_valid": False,
            "row_count": 0,
            "episode_min": None,
            "episode_max": None,
            "episode_continuous": False,
            "missing_episodes": [],
            "duplicate_episodes": [],
            "null_count": 0,
            "nan_count": 0,
            "inf_count": 0,
            "reward_min": None,
            "reward_max": None,
            "reward_mean": None,
            "passed_all_checks": False,
            "failure_reasons": []
        }
        
        if not os.path.exists(csv_path):
            report["missing_csv_files"].append(csv_name)
            model_res["failure_reasons"].append(f"CSV file missing: {csv_name}")
            report["details"][model] = model_res
            report["overall_pass"] = False
            print(f"❌ [{model:20s}] Missing CSV: {csv_name}")
            continue
            
        report["present_csv_files"].append(csv_name)
        
        try:
            df = pd.read_csv(csv_path)
            model_res["row_count"] = len(df)
            
            # Check header
            if "Episode" not in df.columns or "Reward" not in df.columns:
                model_res["failure_reasons"].append(f"Header missing required columns ('Episode', 'Reward'). Found: {list(df.columns)}")
            else:
                model_res["header_valid"] = True
                
            # Check Null/NaN/Inf across all columns
            null_cnt = int(df.isnull().sum().sum())
            nan_cnt = int(df.isna().sum().sum())
            
            # Numeric columns Inf check
            numeric_df = df.select_dtypes(include=[np.number])
            inf_cnt = int(np.isinf(numeric_df).sum().sum())
            
            model_res["null_count"] = null_cnt
            model_res["nan_count"] = nan_cnt
            model_res["inf_count"] = inf_cnt
            
            if null_cnt > 0:
                model_res["failure_reasons"].append(f"Contains {null_cnt} Null values")
            if nan_cnt > 0:
                model_res["failure_reasons"].append(f"Contains {nan_cnt} NaN values")
            if inf_cnt > 0:
                model_res["failure_reasons"].append(f"Contains {inf_cnt} Inf values")
                
            if model_res["header_valid"]:
                episodes = df["Episode"].tolist()
                model_res["episode_min"] = int(df["Episode"].min()) if len(df) > 0 else None
                model_res["episode_max"] = int(df["Episode"].max()) if len(df) > 0 else None
                
                # Check episode range & continuity 1..100
                expected_set = set(range(1, EXPECTED_EPISODES + 1))
                actual_set = set(episodes)
                
                missing_eps = sorted(list(expected_set - actual_set))
                model_res["missing_episodes"] = missing_eps
                
                # Duplicates
                dups = df[df.duplicated(subset=["Episode"], keep=False)]["Episode"].unique().tolist()
                model_res["duplicate_episodes"] = dups
                if len(dups) > 0:
                    model_res["failure_reasons"].append(f"Duplicate episodes found: {dups}")
                    
                if len(missing_eps) > 0:
                    model_res["failure_reasons"].append(f"Missing episodes: count={len(missing_eps)}, range=[{missing_eps[0]}..{missing_eps[-1]}]")
                else:
                    if episodes == list(range(1, EXPECTED_EPISODES + 1)):
                        model_res["episode_continuous"] = True
                    else:
                        model_res["failure_reasons"].append("Episodes are not strictly in order 1..100")
                        
                # Check Rewards
                rewards = df["Reward"].dropna()
                if len(rewards) > 0:
                    model_res["reward_min"] = float(rewards.min())
                    model_res["reward_max"] = float(rewards.max())
                    model_res["reward_mean"] = float(rewards.mean())
                    
                    # Reward range sanity check (e.g. check for extreme/broken values)
                    if np.isinf(rewards).any() or np.isnan(rewards).any():
                        model_res["failure_reasons"].append("Reward column contains non-finite values (NaN/Inf)")
                else:
                    model_res["failure_reasons"].append("Reward column is empty")
                    
            if not weight_exists:
                model_res["failure_reasons"].append("Weight checkpoint file (.pth or .pkl) missing")
            elif weight_size == 0:
                model_res["failure_reasons"].append("Weight checkpoint file is 0 bytes")
                
            if len(model_res["failure_reasons"]) == 0:
                model_res["passed_all_checks"] = True
                print(f"✅ [{model:20s}] PASSED | Ep count: {model_res['row_count']} | Ep range: {model_res['episode_min']}..{model_res['episode_max']} | Reward mean: {model_res['reward_mean']:.2f}")
            else:
                report["overall_pass"] = False
                reasons_str = "; ".join(model_res["failure_reasons"])
                print(f"❌ [{model:20s}] FAILED | Rows: {model_res['row_count']} | Failures: {reasons_str}")
                
        except Exception as e:
            model_res["failure_reasons"].append(f"Exception reading CSV: {str(e)}")
            report["overall_pass"] = False
            print(f"❌ [{model:20s}] Exception: {str(e)}")
            
        report["details"][model] = model_res

    print("\n================ SUMMARY ================")
    print(f"Total expected models: {report['total_expected_models']}")
    print(f"Present CSV files: {len(report['present_csv_files'])}")
    print(f"Missing CSV files: {len(report['missing_csv_files'])}")
    print(f"Overall Decision: {'APPROVE' if report['overall_pass'] else 'REJECT'}")
    
    with open("/home/imnyj/Workspace/paper4/.agents/challenger_m1_2/verification_result.json", "w") as f:
        json.dump(report, f, indent=2)
        
    return report

if __name__ == "__main__":
    verify_all()
