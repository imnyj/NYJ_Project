"""
Print clear table of all 17 models convergence metrics
"""
import os
import glob
import pandas as pd
import numpy as np

WORKSPACE = "/home/imnyj/Workspace/paper4"
MODELS_DIR = os.path.join(WORKSPACE, "data/models")

EXPECTED_17_MODELS = [
    "REMO-DQN", "VanillaDQN", "DoubleDQN", "DuelingDQN", "MoEDQN",
    "PPO", "SAC", "DDPG", "TD3", "MAPPO",
    "ActorCritic", "DecisionTransformer", "QLearning", "SARSA",
    "Fixed10Hz", "ReactDCC", "AdaptDCC"
]

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
    
    exp_cols = ["Episode", "Global_Step", "Reward", "AoI_mean", "CBR_mean", "PDR_mean", "Loss", "Epsilon", "Density"]
    cols_match = (cols == exp_cols)
    
    r_start = df["Reward"].iloc[:10].mean()
    r_end = df["Reward"].iloc[-10:].mean()
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
    
    steps_total = df["Global_Step"].iloc[-1]
    
    rows.append({
        "Model": model,
        "Rows": row_cnt,
        "Cols_Match": cols_match,
        "Steps_End": steps_total,
        "R_start(1-10)": round(r_start, 2),
        "R_end(91-100)": round(r_end, 2),
        "R_gain": round(r_gain, 2),
        "PDR_start": round(pdr_start, 3),
        "PDR_end": round(pdr_end, 3),
        "CBR_start": round(cbr_start, 3),
        "CBR_end": round(cbr_end, 3),
        "AoI_start": round(aoi_start, 3),
        "AoI_end": round(aoi_end, 3),
        "Loss_end": round(loss_end, 4),
        "Eps_end": round(eps_end, 3)
    })

res_df = pd.DataFrame(rows)
print(res_df.to_string(index=False))
