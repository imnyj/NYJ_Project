#!/usr/bin/env python3
"""
Inspect specific details of models, convergence csvs, and optuna params.
"""

import os
import json
import pickle
import torch
import pandas as pd

WORKSPACE_DIR = "/home/imnyj/Workspace/paper4"

print("--- Inspecting data/models/TD3.pth ---")
td3_path = os.path.join(WORKSPACE_DIR, "data", "models", "TD3.pth")
td3_data = torch.load(td3_path, map_location="cpu")
print("TD3.pth type:", type(td3_data))
if isinstance(td3_data, dict):
    print("TD3.pth keys:", list(td3_data.keys()))
    for k, v in td3_data.items():
        if isinstance(v, dict):
            print(f"  sub-dict {k}: {len(v)} keys -> {list(v.keys())[:4]}")
        elif torch.is_tensor(v):
            print(f"  tensor {k}: shape {v.shape}, mean {v.mean().item():.4f}")
        else:
            print(f"  other {k}: {type(v)}")

print("\n--- Inspecting data/models/SARSA.pkl & QLearning.pkl ---")
for pkl_name in ["SARSA.pkl", "QLearning.pkl"]:
    p_path = os.path.join(WORKSPACE_DIR, "data", "models", pkl_name)
    with open(p_path, "rb") as f:
        obj = pickle.load(f)
    print(f"{pkl_name}: type {type(obj)}")
    if isinstance(obj, dict):
        print(f"  dict len: {len(obj)}")
        first_keys = list(obj.keys())[:5]
        print(f"  sample keys: {first_keys}")
        for k in first_keys:
            print(f"    key {k}: {type(obj[k])}, len/val: {len(obj[k]) if hasattr(obj[k], '__len__') else obj[k]}")
    elif isinstance(obj, np.ndarray):
        print(f"  ndarray shape: {obj.shape}, mean: {obj.mean()}, non-zero: {np.count_nonzero(obj)}")

print("\n--- Inspecting data/models/ActorCritic_convergence.csv & REMO-DQN_convergence.csv ---")
for name in ["ActorCritic", "REMO-DQN", "DoubleDQN"]:
    csv_p = os.path.join(WORKSPACE_DIR, "data", "models", f"{name}_convergence.csv")
    df = pd.read_csv(csv_p)
    print(f"{name}_convergence.csv:")
    print(f"  columns: {list(df.columns)}")
    print(f"  head(2):\n{df.head(2)}")
    print(f"  tail(2):\n{df.tail(2)}")

print("\n--- Inspecting data/optuna/ ---")
optuna_files = os.listdir(os.path.join(WORKSPACE_DIR, "data", "optuna"))
print("optuna files:", optuna_files)
json_path = os.path.join(WORKSPACE_DIR, "data", "optuna", "all_best_params.json")
with open(json_path) as f:
    d = json.load(f)
print("all_best_params.json keys:", list(d.keys()))

