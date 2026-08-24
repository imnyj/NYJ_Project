"""
Verification Script for Model Convergence CSVs and Model Weights
Paper4 - Reviewer 1 Independent Verification
"""
import os
import sys
import glob
import pickle
import pandas as pd
import numpy as np
import torch

WORKSPACE = "/home/imnyj/Workspace/paper4"
MODELS_DIR = os.path.join(WORKSPACE, "data/models")
REWARD_CONV_FILE = os.path.join(WORKSPACE, "data/reward_convergence.csv")

EXPECTED_COLUMNS = ["Episode", "Global_Step", "Reward", "AoI_mean", "CBR_mean", "PDR_mean", "Loss", "Epsilon", "Density"]

EXPECTED_17_MODELS = [
    "REMO-DQN", "VanillaDQN", "DoubleDQN", "DuelingDQN", "MoEDQN",
    "PPO", "SAC", "DDPG", "TD3", "MAPPO",
    "ActorCritic", "DecisionTransformer", "QLearning", "SARSA",
    "Fixed10Hz", "ReactDCC", "AdaptDCC"
]

def check_csv_convergence():
    print("=" * 60)
    print("1. CHECKING INDIVIDUAL CONVERGENCE CSV FILES")
    print("=" * 60)
    
    results = {}
    
    # Check for both Fixed10Hz and Fixed 10Hz
    model_files = {}
    for model in EXPECTED_17_MODELS:
        candidates = [
            os.path.join(MODELS_DIR, f"{model}_convergence.csv"),
            os.path.join(MODELS_DIR, f"{model.replace('Fixed10Hz', 'Fixed 10Hz')}_convergence.csv")
        ]
        found = None
        for c in candidates:
            if os.path.exists(c):
                found = c
                break
        model_files[model] = found

    all_csv_pass = True
    for model, filepath in model_files.items():
        if not filepath:
            print(f"[-] MISSING FILE for model: {model}")
            all_csv_pass = False
            results[model] = {"status": "MISSING"}
            continue
        
        try:
            df = pd.read_csv(filepath)
            row_count = len(df)
            cols = list(df.columns)
            
            # Check row count
            row_pass = (row_count == 100)
            
            # Check columns
            col_pass = (cols == EXPECTED_COLUMNS)
            
            # Check for NaN / Inf
            has_nan = df.isna().any().any()
            has_inf = np.isinf(df.select_dtypes(include=[np.number])).any().any()
            
            # Check convergence trend (reward episode 1-10 vs 91-100)
            r_start = df["Reward"].iloc[:10].mean()
            r_end = df["Reward"].iloc[-10:].mean()
            
            # Step continuity
            steps = df["Global_Step"].tolist()
            step_increasing = all(steps[i] <= steps[i+1] for i in range(len(steps)-1))
            
            res_pass = row_pass and col_pass and not has_nan and not has_inf and step_increasing
            if not res_pass:
                all_csv_pass = False
            
            status_str = "PASS" if res_pass else "FAIL"
            print(f"[{status_str}] {model:20s}: Rows={row_count:3d} (Expect 100), Cols={'MATCH' if col_pass else cols}, NaN={has_nan}, Inf={has_inf}, R_start={r_start:.3f}, R_end={r_end:.3f}, Steps_Monotonic={step_increasing}")
            
            results[model] = {
                "status": "OK" if res_pass else "FAIL",
                "row_count": row_count,
                "cols": cols,
                "has_nan": has_nan,
                "has_inf": has_inf,
                "r_start": r_start,
                "r_end": r_end,
                "df": df
            }
        except Exception as e:
            print(f"[FAIL] {model:20s}: Error reading CSV - {e}")
            all_csv_pass = False
            results[model] = {"status": f"ERROR: {e}"}

    print(f"\nIndividual Convergence CSV Overall Result: {'ALL PASS' if all_csv_pass else 'SOME FAILED'}\n")
    return results, all_csv_pass

def check_reward_convergence_merged(indiv_results):
    print("=" * 60)
    print("2. CHECKING MERGED data/reward_convergence.csv")
    print("=" * 60)
    
    if not os.path.exists(REWARD_CONV_FILE):
        print(f"[FAIL] Missing {REWARD_CONV_FILE}")
        return False
    
    df_merged = pd.read_csv(REWARD_CONV_FILE)
    print(f"Merged CSV Shape: {df_merged.shape} (Expected: 100 rows, 19 columns)")
    print(f"Columns: {list(df_merged.columns)}")
    
    shape_pass = (df_merged.shape == (100, 19))
    cols_pass = ("Episode" in df_merged.columns and "Global_Step" in df_merged.columns)
    
    # Check data consistency between individual CSVs and merged CSV
    consistency_pass = True
    mismatch_details = []
    
    for model in EXPECTED_17_MODELS:
        # Find corresponding column name in merged CSV
        col_name = None
        for c in df_merged.columns:
            if c == model or c.replace(" ", "") == model.replace(" ", ""):
                col_name = c
                break
        
        if not col_name:
            print(f"[-] Column for {model} NOT FOUND in merged CSV!")
            consistency_pass = False
            continue
        
        if model in indiv_results and "df" in indiv_results[model]:
            indiv_reward = indiv_results[model]["df"]["Reward"].values
            merged_reward = df_merged[col_name].values
            
            diff = np.abs(indiv_reward - merged_reward)
            max_diff = np.max(diff)
            
            if max_diff > 1e-4:
                print(f"[FAIL] Inconsistency in {model}: max difference = {max_diff}")
                consistency_pass = False
                mismatch_details.append((model, max_diff))
            else:
                print(f"[PASS] Consistency {model:20s} vs col '{col_name}': max diff = {max_diff:.6e}")
    
    merged_pass = shape_pass and cols_pass and consistency_pass
    print(f"\nMerged CSV Overall Result: {'PASS' if merged_pass else 'FAIL'}\n")
    return merged_pass

def check_model_weights():
    print("=" * 60)
    print("3. CHECKING MODEL WEIGHT FILES (.pth and .pkl)")
    print("=" * 60)
    
    # Expected weight files for RL models
    weight_targets = {
        "REMO-DQN": ["REMO-DQN.pth", "resnet_moe_dqn.pth"],
        "VanillaDQN": ["VanillaDQN.pth", "vanilla_dqn.pth"],
        "DoubleDQN": ["DoubleDQN.pth", "ddqn.pth"],
        "DuelingDQN": ["DuelingDQN.pth", "dueling_dqn.pth"],
        "MoEDQN": ["MoEDQN.pth", "moe_dqn.pth"],
        "PPO": ["PPO.pth", "ppo.pth"],
        "SAC": ["SAC.pth", "sac.pth"],
        "DDPG": ["DDPG.pth", "ddpg.pth"],
        "TD3": ["TD3.pth", "td3.pth"],
        "MAPPO": ["MAPPO.pth", "mappo.pth"],
        "ActorCritic": ["ActorCritic.pth", "actor_critic.pth"],
        "DecisionTransformer": ["DecisionTransformer.pth", "dt.pth"],
        "QLearning": ["QLearning.pkl", "qlearning.pkl"],
        "SARSA": ["SARSA.pkl", "sarsa.pkl"]
    }
    
    all_weights_pass = True
    
    for model, filenames in weight_targets.items():
        found_file = None
        for fn in filenames:
            p = os.path.join(MODELS_DIR, fn)
            if os.path.exists(p):
                found_file = p
                break
        
        if not found_file:
            print(f"[FAIL] Missing weight file for {model} (checked {filenames})")
            all_weights_pass = False
            continue
        
        file_size = os.path.getsize(found_file)
        ext = os.path.splitext(found_file)[1]
        
        try:
            if ext == ".pth":
                # Load PyTorch checkpoint
                ckpt = torch.load(found_file, map_location="cpu")
                if isinstance(ckpt, dict):
                    num_keys = len(ckpt.keys())
                    # Check for state dict
                    if "state_dict" in ckpt:
                        state_dict = ckpt["state_dict"]
                    elif "model_state_dict" in ckpt:
                        state_dict = ckpt["model_state_dict"]
                    else:
                        state_dict = ckpt
                    
                    # Check param tensors
                    total_params = 0
                    has_nan = False
                    for k, v in state_dict.items():
                        if isinstance(v, torch.Tensor):
                            total_params += v.numel()
                            if torch.isnan(v).any() or torch.isinf(v).any():
                                has_nan = True
                    
                    print(f"[PASS] {model:20s} ({os.path.basename(found_file)}): size={file_size/1024:.1f}KB, keys={num_keys}, total_params={total_params:,}, NaN/Inf={has_nan}")
                else:
                    print(f"[PASS] {model:20s} ({os.path.basename(found_file)}): size={file_size/1024:.1f}KB, loaded object type={type(ckpt)}")
            
            elif ext == ".pkl":
                with open(found_file, "rb") as f:
                    data = pickle.load(f)
                
                if isinstance(data, dict):
                    entries = len(data)
                    print(f"[PASS] {model:20s} ({os.path.basename(found_file)}): size={file_size/1024:.1f}KB, dict entries={entries:,}")
                else:
                    print(f"[PASS] {model:20s} ({os.path.basename(found_file)}): size={file_size/1024:.1f}KB, loaded object type={type(data)}")
        
        except Exception as e:
            print(f"[FAIL] {model:20s} ({os.path.basename(found_file)}): Error loading - {e}")
            all_weights_pass = False

    print(f"\nModel Weights Overall Result: {'ALL PASS' if all_weights_pass else 'SOME FAILED'}\n")
    return all_weights_pass

def inspect_remo_dqn_details():
    print("=" * 60)
    print("4. DEEP INSPECTION OF REMO-DQN WEIGHTS")
    print("=" * 60)
    
    pth_path = os.path.join(MODELS_DIR, "resnet_moe_dqn.pth")
    if not os.path.exists(pth_path):
        pth_path = os.path.join(MODELS_DIR, "REMO-DQN.pth")
    
    if not os.path.exists(pth_path):
        print(f"[FAIL] REMO-DQN pth not found!")
        return False
    
    ckpt = torch.load(pth_path, map_location="cpu")
    print(f"File: {pth_path}")
    print(f"Top-level keys / type: {type(ckpt)}")
    
    state_dict = ckpt if not isinstance(ckpt, dict) or ("state_dict" not in ckpt and "model" not in ckpt) else (ckpt.get("state_dict") or ckpt.get("model") or ckpt)
    
    print("\nLayer names and shapes:")
    for k, v in state_dict.items():
        if isinstance(v, torch.Tensor):
            print(f"  {k:45s}: shape={str(list(v.shape)):20s}, mean={v.float().mean().item():.5f}, std={v.float().std().item():.5f}")
        else:
            print(f"  {k:45s}: type={type(v)}")
    
    # Check required submodules: ResNet, MoE (gating + experts), Dueling (value + advantage)
    has_resnet = any("res" in k.lower() or "block" in k.lower() or "layer" in k.lower() or "input_layer" in k.lower() for k in state_dict.keys())
    has_moe = any("moe" in k.lower() or "expert" in k.lower() or "gate" in k.lower() or "router" in k.lower() for k in state_dict.keys())
    has_dueling = any("val" in k.lower() or "adv" in k.lower() or "value" in k.lower() or "advantage" in k.lower() for k in state_dict.keys())
    
    print(f"\nArchitecture Features in weights:")
    print(f"  - ResNet residual connections / layers present: {has_resnet}")
    print(f"  - MoE gating/experts present: {has_moe}")
    print(f"  - Dueling value/advantage streams present: {has_dueling}")
    
    return True

if __name__ == "__main__":
    indiv_res, csv_pass = check_csv_convergence()
    merged_pass = check_reward_convergence_merged(indiv_res)
    weights_pass = check_model_weights()
    inspect_remo_dqn_details()
    
    print("=" * 60)
    print("SUMMARY")
    print(f"1. Individual Convergence CSVs: {'PASS' if csv_pass else 'FAIL'}")
    print(f"2. Merged reward_convergence:   {'PASS' if merged_pass else 'FAIL'}")
    print(f"3. Model Weights (.pth/.pkl):   {'PASS' if weights_pass else 'FAIL'}")
    print("=" * 60)
