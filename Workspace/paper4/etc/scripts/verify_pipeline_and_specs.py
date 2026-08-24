#!/usr/bin/env python3
"""
Empirical Verification Harness for Paper4 Data Pipeline & Visualization Reproducibility
Author: Challenger 2 (Empirical Challenger)
"""

import os
import sys
import time
import subprocess
import json
import pandas as pd
import numpy as np
from PIL import Image

PROJECT_ROOT = "/home/imnyj/Workspace/paper4"
VIS_DIR = os.path.join(PROJECT_ROOT, "visualizer")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

EXPECTED_11_TARGETS = [
    {
        "id": 1,
        "name": "Ablation Study Curves",
        "png": "1_ablation_study.png",
        "pdf": "1_ablation_study.pdf",
        "csv": "ablation_study.csv",
        "type": "plot"
    },
    {
        "id": 2,
        "name": "Optuna Sensitivity Table",
        "csv": "2_optuna_sensitivity_table.csv",
        "tex": "2_optuna_sensitivity_table.tex",
        "type": "table"
    },
    {
        "id": 3,
        "name": "Reward Convergence Curves",
        "png": "3_reward_convergence.png",
        "pdf": "3_reward_convergence.pdf",
        "csv": "reward_convergence.csv",
        "type": "plot"
    },
    {
        "id": 4,
        "name": "t-SNE Clustering",
        "png": "4_tsne_clustering.png",
        "pdf": "4_tsne_clustering.pdf",
        "csv": "tsne_clustering.csv",
        "type": "plot"
    },
    {
        "id": 5,
        "name": "MoE Routing Distribution",
        "png": "5_moe_routing.png",
        "pdf": "5_moe_routing.pdf",
        "csv": "moe_routing.csv",
        "type": "plot"
    },
    {
        "id": 6,
        "name": "CBR Trace",
        "png": "6_cbr_trace.png",
        "pdf": "6_cbr_trace.pdf",
        "csv": "cbr_trace.csv",
        "type": "plot"
    },
    {
        "id": 7,
        "name": "PDR vs Density",
        "png": "7_pdr_vs_density.png",
        "pdf": "7_pdr_vs_density.pdf",
        "csv": "pdr_vs_density.csv",
        "type": "plot"
    },
    {
        "id": 8,
        "name": "AoI vs Density",
        "png": "8_aoi_vs_density.png",
        "pdf": "8_aoi_vs_density.pdf",
        "csv": "aoi_vs_density.csv",
        "type": "plot"
    },
    {
        "id": 9,
        "name": "PDR vs Distance",
        "png": "9_pdr_vs_distance.png",
        "pdf": "9_pdr_vs_distance.pdf",
        "csv": "pdr_vs_distance.csv",
        "type": "plot"
    },
    {
        "id": 10,
        "name": "AoI vs Distance",
        "png": "10_aoi_vs_distance.png",
        "pdf": "10_aoi_vs_distance.pdf",
        "csv": "aoi_vs_distance.csv",
        "type": "plot"
    },
    {
        "id": 11,
        "name": "Hardware Feasibility Table",
        "csv": "11_hardware_feasibility_table.csv",
        "tex": "11_hardware_feasibility_table.tex",
        "type": "table"
    }
]

EXPECTED_BASELINES = [
    "REMO-DQN", "Fixed 10Hz", "ReactDCC", "AdaptDCC", "MoEDQN", "MAPPO",
    "PPO", "SAC", "DDPG", "TD3", "DuelingDQN", "DoubleDQN",
    "VanillaDQN", "QLearning", "SARSA", "ActorCritic", "DecisionTransformer"
]

def run_step(step_name, cmd, cwd=PROJECT_ROOT):
    print(f"\n==================================================")
    print(f"Executing Step: {step_name}")
    print(f"Command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    print(f"Working Dir: {cwd}")
    print(f"==================================================")
    start_t = time.time()
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=isinstance(cmd, str))
    elapsed = time.time() - start_t
    print(f"Exit code: {res.returncode} (Elapsed: {elapsed:.2f}s)")
    if res.stdout:
        print(f"[STDOUT]\n{res.stdout.strip()}")
    if res.stderr:
        print(f"[STDERR]\n{res.stderr.strip()}")
    return {
        "step": step_name,
        "cmd": cmd,
        "returncode": res.returncode,
        "elapsed_sec": elapsed,
        "stdout": res.stdout,
        "stderr": res.stderr
    }

def main():
    results = {
        "pipeline_execution": {},
        "target_specs": [],
        "csv_integrity": [],
        "latex_integrity": [],
        "code_hygiene": {},
        "overall_status": "PENDING"
    }

    # 1. Pipeline Execution Test: prepare_data.py
    res_prep = run_step(
        "Data Preparation (prepare_data.py)",
        [sys.executable, "visualizer/prepare_data.py"]
    )
    results["pipeline_execution"]["prepare_data"] = res_prep

    # 2. Pipeline Execution Test: generate_visualizations.py
    res_gen = run_step(
        "Visualization Generation (generate_visualizations.py)",
        [sys.executable, "visualizer/generate_visualizations.py"]
    )
    results["pipeline_execution"]["generate_visualizations"] = res_gen

    # 3. Code Hygiene: Check for np.random in visualizer/
    res_grep = subprocess.run(
        ["grep", "-rn", "np.random", os.path.join(VIS_DIR, "prepare_data.py"), os.path.join(VIS_DIR, "generate_visualizations.py")],
        capture_output=True, text=True
    )
    results["code_hygiene"]["np_random_matches"] = res_grep.stdout.strip()
    results["code_hygiene"]["clean"] = (res_grep.returncode != 0 and len(res_grep.stdout.strip()) == 0)

    # 4. Measure Artifact Specifications
    print("\n==================================================")
    print("Measuring Artifact Specifications")
    print("==================================================")
    all_targets_valid = True

    for t in EXPECTED_11_TARGETS:
        t_spec = {"id": t["id"], "name": t["name"], "type": t["type"], "checks": {}}
        
        if t["type"] == "plot":
            # PNG Check
            png_path = os.path.join(VIS_DIR, t["png"])
            if os.path.exists(png_path):
                img = Image.open(png_path)
                dpi = img.info.get("dpi", (None, None))
                size_bytes = os.path.getsize(png_path)
                dim = img.size # (width, height)
                t_spec["png"] = {
                    "path": png_path,
                    "exists": True,
                    "size_bytes": size_bytes,
                    "dimensions": f"{dim[0]}x{dim[1]}",
                    "dpi_info": dpi,
                    "dpi_valid": (round(dpi[0]) == 350 and round(dpi[1]) == 350) if dpi[0] is not None else False
                }
                if not (round(dpi[0]) == 350 and round(dpi[1]) == 350):
                    all_targets_valid = False
            else:
                t_spec["png"] = {"path": png_path, "exists": False}
                all_targets_valid = False

            # PDF Check
            pdf_path = os.path.join(VIS_DIR, t["pdf"])
            if os.path.exists(pdf_path):
                size_bytes = os.path.getsize(pdf_path)
                t_spec["pdf"] = {
                    "path": pdf_path,
                    "exists": True,
                    "size_bytes": size_bytes,
                    "valid": size_bytes > 1000
                }
            else:
                t_spec["pdf"] = {"path": pdf_path, "exists": False}
                all_targets_valid = False

        if "tex" in t:
            tex_path = os.path.join(VIS_DIR, t["tex"])
            if os.path.exists(tex_path):
                with open(tex_path, "r", encoding="utf-8") as f:
                    tex_content = f.read()
                has_begin_table = "\\begin{table" in tex_content
                has_end_table = "\\end{table" in tex_content
                has_begin_tabular = "\\begin{tabular}" in tex_content
                has_end_tabular = "\\end{tabular}" in tex_content
                has_caption = "\\caption{" in tex_content
                has_label = "\\label{" in tex_content
                tex_valid = has_begin_table and has_end_table and has_begin_tabular and has_end_tabular
                t_spec["tex"] = {
                    "path": tex_path,
                    "exists": True,
                    "size_bytes": os.path.getsize(tex_path),
                    "valid_structure": tex_valid,
                    "has_caption": has_caption,
                    "has_label": has_label
                }
                if not tex_valid:
                    all_targets_valid = False
            else:
                t_spec["tex"] = {"path": tex_path, "exists": False}
                all_targets_valid = False

        if "csv" in t:
            # Check CSV in data/ and/or visualizer/
            csv_candidates = [
                os.path.join(DATA_DIR, t["csv"]),
                os.path.join(VIS_DIR, t["csv"]),
                os.path.join(VIS_DIR, f"{t['id']}_{t['csv']}" if not t["csv"].startswith(str(t["id"])) else t["csv"])
            ]
            found_csv = None
            for p in csv_candidates:
                if os.path.exists(p):
                    found_csv = p
                    break
            
            if found_csv:
                df = pd.read_csv(found_csv)
                nan_count = int(df.isna().sum().sum())
                t_spec["csv"] = {
                    "path": found_csv,
                    "exists": True,
                    "rows": len(df),
                    "cols": len(df.columns),
                    "columns": list(df.columns),
                    "nan_count": nan_count,
                    "valid": nan_count == 0 and len(df) > 0
                }
                if nan_count > 0 or len(df) == 0:
                    all_targets_valid = False
            else:
                t_spec["csv"] = {"exists": False}
                all_targets_valid = False

        results["target_specs"].append(t_spec)

    # 5. Detailed CSV Integrity Audit across data/
    print("\n==================================================")
    print("Auditing all CSV files in data/")
    print("==================================================")
    for fname in sorted(os.listdir(DATA_DIR)):
        if fname.endswith(".csv"):
            fpath = os.path.join(DATA_DIR, fname)
            try:
                df = pd.read_csv(fpath)
                nan_count = int(df.isna().sum().sum())
                results["csv_integrity"].append({
                    "filename": fname,
                    "rows": len(df),
                    "cols": len(df.columns),
                    "nan_count": nan_count,
                    "status": "PASS" if nan_count == 0 and len(df) > 0 else "FAIL"
                })
            except Exception as e:
                results["csv_integrity"].append({
                    "filename": fname,
                    "error": str(e),
                    "status": "ERROR"
                })

    # 6. Specific 200,000 Step Convergence Validation
    rc_csv = os.path.join(DATA_DIR, "reward_convergence.csv")
    if os.path.exists(rc_csv):
        df_rc = pd.read_csv(rc_csv)
        max_step = df_rc["Global_Step"].max() if "Global_Step" in df_rc.columns else None
        has_200k = (max_step == 200000)
        results["convergence_200k_check"] = {
            "max_step": int(max_step) if max_step is not None else None,
            "episodes": len(df_rc),
            "baselines_count": len([c for c in df_rc.columns if c not in ["Episode", "Global_Step"]]),
            "passed": has_200k and len(df_rc) == 100
        }
    else:
        results["convergence_200k_check"] = {"passed": False, "reason": "reward_convergence.csv missing"}

    # Overall Status Decision
    pipeline_ok = (results["pipeline_execution"]["prepare_data"]["returncode"] == 0 and
                   results["pipeline_execution"]["generate_visualizations"]["returncode"] == 0)
    hygiene_ok = results["code_hygiene"]["clean"]
    conv_ok = results.get("convergence_200k_check", {}).get("passed", False)
    
    if pipeline_ok and all_targets_valid and hygiene_ok and conv_ok:
        results["overall_status"] = "APPROVE"
    else:
        results["overall_status"] = "FAIL"

    # Save summary report
    out_json = os.path.join(PROJECT_ROOT, "etc", "logs", "verification_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n==================================================")
    print(f"OVERALL VERIFICATION STATUS: {results['overall_status']}")
    print(f"Results saved to: {out_json}")
    print(f"==================================================")

if __name__ == "__main__":
    main()
