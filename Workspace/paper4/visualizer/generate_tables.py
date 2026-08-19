"""
Table Generation Module for Paper4 Visualizer
============================================
Generates 2 publication tables in both CSV (.csv) and LaTeX (.tex) formats:
1. optuna_sensitivity_table.csv & optuna_sensitivity_table.tex
2. hardware_feasibility_table.csv & hardware_feasibility_table.tex
"""

import os
import json
import pandas as pd

DATA_DIR = "/home/imnyj/Workspace/paper4/data"
VIS_DIR = "/home/imnyj/Workspace/paper4/visualizer"
OPTUNA_DIR = os.path.join(DATA_DIR, "optuna")

os.makedirs(VIS_DIR, exist_ok=True)

def generate_optuna_sensitivity_table(out_dir=VIS_DIR):
    csv_src = os.path.join(DATA_DIR, "optuna_sensitivity_table.csv")
    if os.path.exists(csv_src):
        df = pd.read_csv(csv_src)
    else:
        # Fallback build
        from prepare_data import build_optuna_sensitivity
        build_optuna_sensitivity()
        df = pd.read_csv(csv_src)
        
    out_csv = os.path.join(out_dir, "optuna_sensitivity_table.csv")
    out_csv_num = os.path.join(out_dir, "2_optuna_sensitivity_table.csv")
    df.to_csv(out_csv, index=False)
    df.to_csv(out_csv_num, index=False)
    print(f"Generated -> {out_csv_num} & {out_csv}")
    
    tex_content = []
    tex_content.append("% ==========================================================================\n")
    tex_content.append("% Optuna Hyperparameter Sensitivity & Baseline Performance Comparison Table\n")
    tex_content.append("% ==========================================================================\n")
    tex_content.append("\\begin{table*}[t]\n")
    tex_content.append("\\centering\n")
    tex_content.append("\\caption{Hyperparameter Search Space, Optimal Parameters via Optuna Bayesian Optimization, and Empirical Multi-Metric Performance Across 17 Baselines}\n")
    tex_content.append("\\label{tab:optuna-sensitivity}\n")
    tex_content.append("\\resizebox{\\textwidth}{!}{\n")
    tex_content.append("\\begin{tabular}{l l p{6.5cm} r r r r}\n")
    tex_content.append("\\toprule\n")
    tex_content.append("\\textbf{Baseline / Method} & \\textbf{Model Category} & \\textbf{Optimal Hyperparameter Vector} & \\textbf{Conv. Reward} & \\textbf{PDR (\\%)} & \\textbf{AoI (ms)} & \\textbf{CBR} \\\\\n")
    tex_content.append("\\midrule\n")
    for _, r in df.iterrows():
        is_bold = "REMO-DQN" in str(r["Method"])
        prefix = "\\textbf{" if is_bold else ""
        suffix = "}" if is_bold else ""
        rew = f"{float(r['Reward Convergence']):,.1f}"
        pdr = f"{float(r['Mean PDR (%)']):.2f}"
        aoi = f"{float(r['Mean AoI (ms)']):.2f}"
        cbr = f"{float(r['Mean CBR']):.3f}"
        hparams_tex = str(r['Tuned Hyperparameters']).replace('_', r'\_')
        method_tex = str(r['Method']).replace('_', r'\_')
        arch_tex = str(r['Architecture']).replace('_', r'\_')
        tex_content.append(f"{prefix}{method_tex}{suffix} & {arch_tex} & \\small{{{hparams_tex}}} & {rew} & {pdr} & {aoi} & {cbr} \\\\\n")
    tex_content.append("\\bottomrule\n")
    tex_content.append("\\end{tabular}\n")
    tex_content.append("}\n")
    tex_content.append("\\end{table*}\n")
    
    full_tex = "".join(tex_content)
    out_tex = os.path.join(out_dir, "optuna_sensitivity_table.tex")
    out_tex_num = os.path.join(out_dir, "2_optuna_sensitivity_table.tex")
    with open(out_tex, "w", encoding="utf-8") as f:
        f.write(full_tex)
    with open(out_tex_num, "w", encoding="utf-8") as f:
        f.write(full_tex)
    print(f"Generated -> {out_tex_num} & {out_tex}")

def generate_hardware_feasibility_table(out_dir=VIS_DIR):
    csv_src = os.path.join(DATA_DIR, "hardware_feasibility_table.csv")
    if os.path.exists(csv_src):
        df = pd.read_csv(csv_src)
    else:
        from prepare_data import build_hardware_feasibility
        build_hardware_feasibility()
        df = pd.read_csv(csv_src)
        
    out_csv = os.path.join(out_dir, "hardware_feasibility_table.csv")
    out_csv_num = os.path.join(out_dir, "11_hardware_feasibility_table.csv")
    df.to_csv(out_csv, index=False)
    df.to_csv(out_csv_num, index=False)
    print(f"Generated -> {out_csv_num} & {out_csv}")
    
    tex_content = []
    tex_content.append("% ==========================================================================\n")
    tex_content.append("% Hardware Feasibility & Edge Embedded Complexity Profiling Table\n")
    tex_content.append("% ==========================================================================\n")
    tex_content.append("\\begin{table*}[t]\n")
    tex_content.append("\\centering\n")
    tex_content.append("\\caption{Computational Complexity, Parameter Count, Inference Latency, and On-Device Memory Footprint for In-Vehicle OBU / MCU Deployment}\n")
    tex_content.append("\\label{tab:hardware-feasibility}\n")
    tex_content.append("\\resizebox{\\textwidth}{!}{\n")
    tex_content.append("\\begin{tabular}{l l r r r r l}\n")
    tex_content.append("\\toprule\n")
    tex_content.append("\\textbf{Model} & \\textbf{Network Structure} & \\textbf{MACs/FLOPs} & \\textbf{Parameters} & \\textbf{Latency (ms)} & \\textbf{RAM/Flash (KB)} & \\textbf{Deployment Feasibility} \\\\\n")
    tex_content.append("\\midrule\n")
    for _, r in df.iterrows():
        is_bold = "REMO-DQN" in str(r["Model"])
        prefix = "\\textbf{" if is_bold else ""
        suffix = "}" if is_bold else ""
        lat = f"{float(r['Inference_Latency_ms']):.3f}"
        mem = f"{float(r['Memory_Footprint_KB']):.1f}"
        macs_val = str(r['MACs_FLOPs'])
        if '<' in macs_val:
            macs_tex = "$< 0.01$~M"
        else:
            macs_tex = macs_val
        model_tex = str(r['Model']).replace('_', r'\_')
        arch_tex = str(r['Architecture']).replace('_', r'\_')
        tex_content.append(f"{prefix}{model_tex}{suffix} & {arch_tex} & {macs_tex} & {r['Parameters']} & {lat} & {mem} & {r['MCU_Feasibility']} \\\\\n")
    tex_content.append("\\bottomrule\n")
    tex_content.append("\\end{tabular}\n")
    tex_content.append("}\n")
    tex_content.append("\\end{table*}\n")
    
    full_tex = "".join(tex_content)
    out_tex = os.path.join(out_dir, "hardware_feasibility_table.tex")
    out_tex_num = os.path.join(out_dir, "11_hardware_feasibility_table.tex")
    with open(out_tex, "w", encoding="utf-8") as f:
        f.write(full_tex)
    with open(out_tex_num, "w", encoding="utf-8") as f:
        f.write(full_tex)
    print(f"Generated -> {out_tex_num} & {out_tex}")

def generate_all_tables(out_dir=VIS_DIR):
    print("=== Generating All Tables ===")
    generate_optuna_sensitivity_table(out_dir)
    generate_hardware_feasibility_table(out_dir)
    print("=== Table Generation Completed ===")

if __name__ == "__main__":
    generate_all_tables()
