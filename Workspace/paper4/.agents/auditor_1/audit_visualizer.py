import os
import sys
import json
from PIL import Image
import pandas as pd

VIS_DIR = "/home/imnyj/Workspace/paper4/visualizer"

target_artifacts = [
    ("1_ablation_study.png", "1_ablation_study.pdf"),
    ("2_optuna_sensitivity_table.csv", "2_optuna_sensitivity_table.tex"),
    ("3_reward_convergence.png", "3_reward_convergence.pdf"),
    ("4_tsne_clustering.png", "4_tsne_clustering.pdf"),
    ("5_moe_routing.png", "5_moe_routing.pdf"),
    ("6_cbr_trace.png", "6_cbr_trace.pdf"),
    ("7_pdr_vs_density.png", "7_pdr_vs_density.pdf"),
    ("8_aoi_vs_density.png", "8_aoi_vs_density.pdf"),
    ("9_pdr_vs_distance.png", "9_pdr_vs_distance.pdf"),
    ("10_aoi_vs_distance.png", "10_aoi_vs_distance.pdf"),
    ("11_hardware_feasibility_table.csv", "11_hardware_feasibility_table.tex"),
]

results = {}
all_passed = True

for item in target_artifacts:
    f1, f2 = item
    p1 = os.path.join(VIS_DIR, f1)
    p2 = os.path.join(VIS_DIR, f2)
    
    info1 = {"exists": os.path.exists(p1), "size": os.path.getsize(p1) if os.path.exists(p1) else 0}
    info2 = {"exists": os.path.exists(p2), "size": os.path.getsize(p2) if os.path.exists(p2) else 0}
    
    if f1.endswith('.png') and info1["exists"]:
        try:
            with Image.open(p1) as img:
                info1["dimensions"] = list(img.size)
                info1["dpi"] = img.info.get("dpi", "Unknown")
        except Exception as e:
            info1["error"] = str(e)
            all_passed = False
            
    if f1.endswith('.csv') and info1["exists"]:
        try:
            df = pd.read_csv(p1)
            info1["rows"] = len(df)
            info1["cols"] = len(df.columns)
        except Exception as e:
            info1["error"] = str(e)
            all_passed = False
            
    results[f"{f1} + {f2}"] = {"primary": info1, "secondary": info2}
    print(f"[{'PASS' if info1['exists'] and info2['exists'] else 'FAIL'}] {f1} ({info1['size']} B) & {f2} ({info2['size']} B)")

print(f"\nAll 11 target output pairs present: {all_passed}")

with open("/home/imnyj/Workspace/paper4/.agents/auditor_1/visualizer_audit.json", "w") as f:
    json.dump(results, f, indent=2)
