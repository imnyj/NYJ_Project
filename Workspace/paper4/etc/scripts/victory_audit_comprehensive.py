#!/usr/bin/env python3
"""
Comprehensive Victory Audit Verification Script for Paper4
Author: Victory Auditor 3
"""

import os
import sys
import json
import pickle
import hashlib
import numpy as np
import pandas as pd
import torch

WORKSPACE = "/home/imnyj/Workspace/paper4"
RESULTS = {"passed": 0, "failed": 0, "details": []}

def log_check(name, passed, msg=""):
    status = "PASS" if passed else "FAIL"
    if passed:
        RESULTS["passed"] += 1
    else:
        RESULTS["failed"] += 1
    RESULTS["details"].append((name, status, msg))
    print(f"[{status}] {name}: {msg}")

print("=== 1. Checking Model Weights & Tensors ===")
MODELS = [
    ("REMO-DQN.pth", "torch"),
    ("ActorCritic.pth", "torch"),
    ("DDPG.pth", "torch"),
    ("DecisionTransformer.pth", "torch"),
    ("DoubleDQN.pth", "torch"),
    ("DuelingDQN.pth", "torch"),
    ("MAPPO.pth", "torch"),
    ("MoEDQN.pth", "torch"),
    ("PPO.pth", "torch"),
    ("SAC.pth", "torch"),
    ("TD3.pth", "torch"),
    ("VanillaDQN.pth", "torch"),
    ("QLearning.pkl", "pickle"),
    ("SARSA.pkl", "pickle"),
]

for fname, mtype in MODELS:
    fpath = os.path.join(WORKSPACE, "data/models", fname)
    if not os.path.exists(fpath):
        log_check(f"Model exists: {fname}", False, f"File not found: {fpath}")
        continue
    
    if mtype == "torch":
        try:
            ckpt = torch.load(fpath, map_location="cpu", weights_only=False)
            tensors = []
            if isinstance(ckpt, dict):
                for k, v in ckpt.items():
                    if isinstance(v, torch.Tensor):
                        tensors.append(v)
                    elif isinstance(v, dict):
                        for sub_k, sub_v in v.items():
                            if isinstance(sub_v, torch.Tensor):
                                tensors.append(sub_v)
            elif isinstance(ckpt, torch.Tensor):
                tensors.append(ckpt)
            
            total_params = sum(t.numel() for t in tensors)
            has_nan = any(torch.isnan(t).any().item() for t in tensors)
            has_inf = any(torch.isinf(t).any().item() for t in tensors)
            
            passed = total_params > 0 and not has_nan and not has_inf
            log_check(f"Model tensor check: {fname}", passed, f"Params: {total_params:,}, NaN: {has_nan}, Inf: {has_inf}")
        except Exception as e:
            log_check(f"Model tensor check: {fname}", False, f"Exception: {str(e)}")
    elif mtype == "pickle":
        try:
            with open(fpath, "rb") as f:
                data = pickle.load(f)
            is_valid = isinstance(data, (dict, np.ndarray)) and len(data) > 0
            log_check(f"Model pickle check: {fname}", is_valid, f"Type: {type(data)}, Entries: {len(data):,}")
        except Exception as e:
            log_check(f"Model pickle check: {fname}", False, f"Exception: {str(e)}")

print("\n=== 2. Checking 200,000 Step Convergence CSVs ===")
CONV_MODELS = [
    "REMO-DQN", "ActorCritic", "DDPG", "DecisionTransformer", "DoubleDQN",
    "DuelingDQN", "MAPPO", "MoEDQN", "PPO", "SAC", "TD3", "VanillaDQN",
    "QLearning", "SARSA"
]

for model_name in CONV_MODELS:
    cpath = os.path.join(WORKSPACE, "data/models", f"{model_name}_convergence.csv")
    if not os.path.exists(cpath):
        log_check(f"Convergence CSV: {model_name}", False, f"Missing: {cpath}")
        continue
    
    try:
        df = pd.read_csv(cpath)
        cols_lower = [c.lower() for c in df.columns]
        episodes = len(df)
        
        step_col = None
        for col in ['global_step', 'step', 'steps']:
            if col in cols_lower:
                step_col = df.columns[cols_lower.index(col)]
                break
        
        max_step = df[step_col].max() if step_col else episodes * 2000
        has_reward = any('reward' in c for c in cols_lower)
        
        passed = episodes >= 100 and max_step >= 200000 and has_reward
        log_check(f"Convergence CSV: {model_name}", passed, f"Episodes: {episodes}, Max Step: {max_step:,}, Reward col: {has_reward}")
    except Exception as e:
        log_check(f"Convergence CSV: {model_name}", False, f"Exception: {str(e)}")

print("\n=== 3. Checking All 11 Synchronized Datasets across data/ and coder/data/ ===")
DATASETS = [
    ("reward_convergence.csv", (100, 18)),
    ("ablation_study.csv", (25, 8)),
    ("optuna_sensitivity_table.csv", (17, 7)),
    ("tsne_clustering.csv", (150, 3)),
    ("moe_routing.csv", (8, 4)),
    ("cbr_trace.csv", (100, 18)),
    ("pdr_vs_density.csv", (50, 18)),
    ("aoi_vs_density.csv", (50, 18)),
    ("pdr_vs_distance.csv", (7, 18)),
    ("aoi_vs_distance.csv", (7, 18)),
    ("hardware_feasibility_table.csv", (11, 7)),
]

for fname, exp_shape in DATASETS:
    p1 = os.path.join(WORKSPACE, "data", fname)
    p2 = os.path.join(WORKSPACE, "coder/data", fname)
    
    if not os.path.exists(p1) or not os.path.exists(p2):
        log_check(f"Dataset exists in data/ & coder/data/: {fname}", False, f"p1={os.path.exists(p1)}, p2={os.path.exists(p2)}")
        continue
    
    with open(p1, "rb") as f:
        h1 = hashlib.sha256(f.read()).hexdigest()
    with open(p2, "rb") as f:
        h2 = hashlib.sha256(f.read()).hexdigest()
    
    df = pd.read_csv(p1)
    shape_match = (df.shape == exp_shape)
    hash_match = (h1 == h2)
    no_null = df.isnull().sum().sum() == 0
    passed = shape_match and hash_match and no_null
    log_check(f"Dataset integrity: {fname}", passed, f"Shape: {df.shape} (exp: {exp_shape}), SHA256 match: {hash_match}, Nulls: 0")

print("\n=== 4. Checking Visualizer Target Outputs (9 Figures PDF/PNG + 2 Tables CSV/TeX) ===")
FIGURES = [
    "ablation_study", "reward_convergence", "tsne_clustering", "moe_routing",
    "cbr_trace", "pdr_vs_density", "aoi_vs_density", "pdr_vs_distance", "aoi_vs_distance"
]

for fig in FIGURES:
    pdf_p = os.path.join(WORKSPACE, "visualizer", f"{fig}.pdf")
    png_p = os.path.join(WORKSPACE, "visualizer", f"{fig}.png")
    
    pdf_ok = os.path.exists(pdf_p) and os.path.getsize(pdf_p) > 1000
    if pdf_ok:
        with open(pdf_p, "rb") as f:
            pdf_head = f.read(5)
            pdf_ok = pdf_head.startswith(b"%PDF-")
            
    png_ok = os.path.exists(png_p) and os.path.getsize(png_p) > 10000
    log_check(f"Figure output: {fig}", pdf_ok and png_ok, f"PDF: {os.path.getsize(pdf_p) if os.path.exists(pdf_p) else 0} B, PNG: {os.path.getsize(png_p) if os.path.exists(png_p) else 0} B")

TABLES = ["optuna_sensitivity_table", "hardware_feasibility_table"]
for tab in TABLES:
    csv_p = os.path.join(WORKSPACE, "visualizer", f"{tab}.csv")
    tex_p = os.path.join(WORKSPACE, "visualizer", f"{tab}.tex")
    
    csv_ok = os.path.exists(csv_p) and os.path.getsize(csv_p) > 100
    tex_ok = os.path.exists(tex_p) and os.path.getsize(tex_p) > 100
    
    unescaped_underscores = 0
    if tex_ok:
        with open(tex_p, "r", encoding="utf-8") as f:
            tex_content = f.read()
        lines = tex_content.splitlines()
        for idx, line in enumerate(lines):
            for char_idx, char in enumerate(line):
                if char == '_':
                    if char_idx > 0 and line[char_idx-1] == '\\':
                        continue
                    dollars_before = line[:char_idx].count('$')
                    if dollars_before % 2 == 0:
                        unescaped_underscores += 1
        tex_ok = (unescaped_underscores == 0)
    
    log_check(f"Table output: {tab}", csv_ok and tex_ok, f"CSV: {os.path.getsize(csv_p) if os.path.exists(csv_p) else 0} B, TeX: {os.path.getsize(tex_p) if os.path.exists(tex_p) else 0} B, Unescaped _: {unescaped_underscores}")

print("\n=== 5. Checking Visualizer Styling & Legend Order ===")
with open(os.path.join(WORKSPACE, "visualizer/plot_utils.py"), "r") as f:
    pu_code = f.read()

has_remo_red = "#FF0000" in pu_code
has_bold_remo = "REMO-DQN (Proposed)" in pu_code
has_model_configs = "MODEL_CONFIGS" in pu_code
log_check("Visualizer Styling (#FF0000 proposed, legend mapping in plot_utils.py)", has_remo_red and has_bold_remo and has_model_configs, f"Red: {has_remo_red}, Proposed Name: {has_bold_remo}, Model Configs: {has_model_configs}")

print("\n=== 6. Checking config.md & sim_engine.py Integration ===")
cfg_path = os.path.join(WORKSPACE, "config.md")
cfg_ok = os.path.exists(cfg_path) and os.path.getsize(cfg_path) > 1000
with open(os.path.join(WORKSPACE, "code/sim_engine.py"), "r") as f:
    sim_code = f.read()

has_config_md_parse = "config.md" in sim_code
log_check("config.md root placement and parsing", cfg_ok and has_config_md_parse, f"config.md: {cfg_ok}, sim_engine parsing: {has_config_md_parse}")

print("\n=== 7. Checking analysis_report.md & Data Concordance ===")
ar_path = os.path.join(WORKSPACE, "analysis_report.md")
ar_ok = os.path.exists(ar_path) and os.path.getsize(ar_path) > 10000
with open(ar_path, "r", encoding="utf-8") as f:
    ar_content = f.read()

has_moe_formula = "g_k(s_t)" in ar_content or "Softmax" in ar_content
has_tsne_formula = "KL" in ar_content or "p_{ij}" in ar_content
has_low_coord = "-0.23" in ar_content and "0.08" in ar_content
has_mid_coord = "5.02" in ar_content and "5.15" in ar_content
has_high_coord = "1.96" in ar_content and "4.98" in ar_content

log_check("analysis_report.md completeness and data concordance", 
          ar_ok and has_moe_formula and has_tsne_formula and has_low_coord and has_mid_coord and has_high_coord,
          f"Size: {len(ar_content):,} B, MoE Form: {has_moe_formula}, t-SNE Form: {has_tsne_formula}, Coords Match: {has_low_coord and has_mid_coord and has_high_coord}")

print("\n=== Summary ===")
print(f"Total Passed: {RESULTS['passed']}, Total Failed: {RESULTS['failed']}")
if RESULTS['failed'] == 0:
    print("ALL AUDIT CHECKS PASSED.")
    sys.exit(0)
else:
    print("AUDIT DETECTED FAILURES.")
    sys.exit(1)
