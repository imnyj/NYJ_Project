"""
Deep Inspection Script for Model Convergence and Weights
Paper4 - Reviewer 1 Independent Verification (Deep Dive)
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

EXPECTED_17_MODELS = [
    "REMO-DQN", "VanillaDQN", "DoubleDQN", "DuelingDQN", "MoEDQN",
    "PPO", "SAC", "DDPG", "TD3", "MAPPO",
    "ActorCritic", "DecisionTransformer", "QLearning", "SARSA",
    "Fixed10Hz", "ReactDCC", "AdaptDCC"
]

def detailed_csv_report():
    print("=" * 80)
    print("DETAILED 17-MODEL CONVERGENCE CSV AUDIT")
    print("=" * 80)
    
    rows = []
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
        
        if not found:
            print(f"[-] MISSING: {model}")
            continue
        
        df = pd.read_csv(found)
        row_cnt = len(df)
        cols = list(df.columns)
        
        # Check standard columns
        exp_cols = ["Episode", "Global_Step", "Reward", "AoI_mean", "CBR_mean", "PDR_mean", "Loss", "Epsilon", "Density"]
        cols_match = (cols == exp_cols)
        
        r_start = df["Reward"].iloc[:10].mean()
        r_end = df["Reward"].iloc[-10:].mean()
        r_min = df["Reward"].min()
        r_max = df["Reward"].max()
        r_gain = r_end - r_start
        
        pdr_start = df["PDR_mean"].iloc[:10].mean()
        pdr_end = df["PDR_mean"].iloc[-10:].mean()
        
        cbr_start = df["CBR_mean"].iloc[:10].mean()
        cbr_end = df["CBR_mean"].iloc[-10:].mean()
        
        aoi_start = df["AoI_mean"].iloc[:10].mean()
        aoi_end = df["AoI_mean"].iloc[-10:].mean()
        
        loss_start = df["Loss"].iloc[:10].mean()
        loss_end = df["Loss"].iloc[-10:].mean()
        
        eps_start = df["Epsilon"].iloc[0]
        eps_end = df["Epsilon"].iloc[-1]
        
        print(f"Model: {model:22s} | Rows: {row_cnt:3d} | Cols: {'OK' if cols_match else 'DIFF'} | R: [{r_start:6.2f} -> {r_end:6.2f}, Δ={r_gain:+6.2f}] | PDR: [{pdr_start:.3f} -> {pdr_end:.3f}] | CBR: [{cbr_start:.3f} -> {cbr_end:.3f}] | AoI: [{aoi_start:.3f} -> {aoi_end:.3f}] | Loss: [{loss_start:.4f} -> {loss_end:.4f}] | Eps: [{eps_start:.2f} -> {eps_end:.3f}]")

def inspect_all_weight_structures():
    print("\n" + "=" * 80)
    print("DETAILED WEIGHT FILE INTERNAL STRUCTURE INSPECTION")
    print("=" * 80)
    
    weight_files = sorted(glob.glob(os.path.join(MODELS_DIR, "*.pth")) + glob.glob(os.path.join(MODELS_DIR, "*.pkl")))
    
    for wf in weight_files:
        basename = os.path.basename(wf)
        size_kb = os.path.getsize(wf) / 1024
        print(f"\n--- File: {basename} ({size_kb:.1f} KB) ---")
        
        if wf.endswith(".pth"):
            try:
                ckpt = torch.load(wf, map_location="cpu")
                if isinstance(ckpt, dict):
                    print(f"Dict keys ({len(ckpt.keys())}): {list(ckpt.keys())[:10]}")
                    
                    # Inspect sub-dictionaries if actor/critic/etc
                    for k, v in ckpt.items():
                        if isinstance(v, dict):
                            sub_params = sum(t.numel() for t in v.values() if isinstance(t, torch.Tensor))
                            print(f"  Subdict '{k}': {len(v)} keys, total params = {sub_params:,}")
                        elif isinstance(v, torch.Tensor):
                            print(f"  Tensor '{k}': shape {list(v.shape)}, mean={v.float().mean():.4f}, std={v.float().std():.4f}")
                        elif isinstance(v, (int, float, str, bool)):
                            print(f"  Meta '{k}': {v}")
                        else:
                            print(f"  Item '{k}': type {type(v)}")
                elif isinstance(ckpt, torch.nn.Module):
                    total_p = sum(p.numel() for p in ckpt.parameters())
                    print(f"nn.Module object: {type(ckpt).__name__}, total params = {total_p:,}")
                else:
                    print(f"Unknown PyTorch object: {type(ckpt)}")
            except Exception as e:
                print(f"ERROR loading pth: {e}")
                
        elif wf.endswith(".pkl"):
            try:
                with open(wf, "rb") as f:
                    data = pickle.load(f)
                if isinstance(data, dict):
                    print(f"Dict with {len(data)} top keys: {list(data.keys())[:10]}")
                    for k in list(data.keys())[:5]:
                        v = data[k]
                        if isinstance(v, np.ndarray):
                            print(f"  Key '{k}': ndarray shape={v.shape}, dtype={v.dtype}, mean={v.mean():.4f}, std={v.std():.4f}")
                        elif isinstance(v, dict):
                            print(f"  Key '{k}': subdict with {len(v)} keys")
                            # sample sub-values
                            sample_items = list(v.items())[:3]
                            print(f"    Samples: {sample_items}")
                        else:
                            print(f"  Key '{k}': type={type(v)}, val={v}")
                else:
                    print(f"Object type: {type(data)}")
            except Exception as e:
                print(f"ERROR loading pkl: {e}")

if __name__ == "__main__":
    detailed_csv_report()
    inspect_all_weight_structures()
