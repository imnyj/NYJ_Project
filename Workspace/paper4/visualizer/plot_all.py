"""
Master Visualization Pipeline for Paper4 (REMO-DQN)
===================================================
Orchestrates data verification, figure plotting, and table generation
for all 11 target outputs specified in evaluation_plan.md and ORIGINAL_REQUEST.md.

Targets:
1.  ablation_study.png / ablation_study.pdf               (Ablation curves)
2.  optuna_sensitivity_table.csv / optuna_sensitivity_table.tex (Optuna table)
3.  reward_convergence.png / reward_convergence.pdf       (17 Baselines convergence)
4.  tsne_clustering.png / tsne_clustering.pdf             (t-SNE latent clustering)
5.  moe_routing.png / moe_routing.pdf                     (MoE dynamic routing)
6.  cbr_trace.png / cbr_trace.pdf                         (CBR trace + 0.60 target)
7.  pdr_vs_density.png / pdr_vs_density.pdf               (PDR vs density)
8.  aoi_vs_density.png / aoi_vs_density.pdf               (AoI vs density)
9.  pdr_vs_distance.png / pdr_vs_distance.pdf             (PDR vs distance)
10. aoi_vs_distance.png / aoi_vs_distance.pdf             (AoI vs distance)
11. hardware_feasibility_table.csv / hardware_feasibility_table.tex (Hardware feasibility table)
"""

import os
import sys
import time

# Add current directory to path
VIS_DIR = os.path.dirname(os.path.abspath(__file__))
if VIS_DIR not in sys.path:
    sys.path.insert(0, VIS_DIR)

from PIL import Image
from prepare_data import main as prepare_all_data
from plot_figures import generate_all_figures
from generate_tables import generate_all_tables

TARGET_OUTPUTS = [
    ("1_ablation_study.png", "PNG", "Target 1: Ablation Study Curves (PNG 350 DPI)"),
    ("1_ablation_study.pdf", "PDF", "Target 1: Ablation Study Curves (Vector PDF)"),
    ("2_optuna_sensitivity_table.csv", "CSV", "Target 2: Optuna Sensitivity Table (CSV)"),
    ("2_optuna_sensitivity_table.tex", "TeX", "Target 2: Optuna Sensitivity Table (LaTeX)"),
    ("3_reward_convergence.png", "PNG", "Target 3: Reward Convergence Curves (PNG 350 DPI)"),
    ("3_reward_convergence.pdf", "PDF", "Target 3: Reward Convergence Curves (Vector PDF)"),
    ("4_tsne_clustering.png", "PNG", "Target 4: t-SNE Latent Clustering (PNG 350 DPI)"),
    ("4_tsne_clustering.pdf", "PDF", "Target 4: t-SNE Latent Clustering (Vector PDF)"),
    ("5_moe_routing.png", "PNG", "Target 5: MoE Dynamic Routing Distribution (PNG 350 DPI)"),
    ("5_moe_routing.pdf", "PDF", "Target 5: MoE Dynamic Routing Distribution (Vector PDF)"),
    ("6_cbr_trace.png", "PNG", "Target 6: Time-Series CBR Trace & Stability (PNG 350 DPI)"),
    ("6_cbr_trace.pdf", "PDF", "Target 6: Time-Series CBR Trace & Stability (Vector PDF)"),
    ("7_pdr_vs_density.png", "PNG", "Target 7: PDR vs. Vehicle Density (PNG 350 DPI)"),
    ("7_pdr_vs_density.pdf", "PDF", "Target 7: PDR vs. Vehicle Density (Vector PDF)"),
    ("8_aoi_vs_density.png", "PNG", "Target 8: AoI vs. Vehicle Density (PNG 350 DPI)"),
    ("8_aoi_vs_density.pdf", "PDF", "Target 8: AoI vs. Vehicle Density (Vector PDF)"),
    ("9_pdr_vs_distance.png", "PNG", "Target 9: PDR vs. Communication Distance (PNG 350 DPI)"),
    ("9_pdr_vs_distance.pdf", "PDF", "Target 9: PDR vs. Communication Distance (Vector PDF)"),
    ("10_aoi_vs_distance.png", "PNG", "Target 10: AoI vs. Communication Distance (PNG 350 DPI)"),
    ("10_aoi_vs_distance.pdf", "PDF", "Target 10: AoI vs. Communication Distance (Vector PDF)"),
    ("11_hardware_feasibility_table.csv", "CSV", "Target 11: Hardware Feasibility Table (CSV)"),
    ("11_hardware_feasibility_table.tex", "TeX", "Target 11: Hardware Feasibility Table (LaTeX)"),
]

def verify_outputs():
    print("\n" + "="*80)
    print("      PAPER4 VISUALIZATION OUTPUT VERIFICATION REPORT (350 DPI & TARGETS 1-11)")
    print("="*80)
    
    all_passed = True
    for filename, fmt, desc in TARGET_OUTPUTS:
        filepath = os.path.join(VIS_DIR, filename)
        if os.path.exists(filepath):
            size_bytes = os.path.getsize(filepath)
            size_kb = size_bytes / 1024.0
            if size_bytes > 0:
                dpi_info = ""
                if fmt == "PNG":
                    try:
                        img = Image.open(filepath)
                        dpi_val = img.info.get('dpi')
                        if dpi_val and round(dpi_val[0]) == 350 and round(dpi_val[1]) == 350:
                            dpi_info = f" [DPI: {round(dpi_val[0])}]"
                        else:
                            dpi_info = f" [DPI WARN: {dpi_val}]"
                            all_passed = False
                    except Exception as e:
                        dpi_info = f" [DPI ERR: {e}]"
                status = f"[PASS] ({size_kb:6.1f} KB){dpi_info}"
            else:
                status = "[FAIL] (0 bytes empty file)"
                all_passed = False
        else:
            status = "[MISSING]"
            all_passed = False
            
        print(f"{status:<28} | {filename:<36} | {desc}")
        
    print("="*80)
    if all_passed:
        print("[SUCCESS] All 11 target visualization outputs (22 files: 350 DPI PNG, PDF, CSV, TeX) verified successfully!")
    else:
        print("[ERROR] Some target outputs failed or are missing.")
    print("="*80 + "\n")
    return all_passed

def main():
    t0 = time.time()
    print("======================================================================")
    print("  Starting Paper4 Full Visualization Pipeline Execution (350 DPI)")
    print("======================================================================")
    
    # 1. Prepare & Synchronize Datasets
    print("\n[Step 1/3] Synchronizing datasets across data/ and coder/data/...")
    prepare_all_data()
    
    # 2. Generate Figures (PDFs + 350 DPI PNG)
    print("\n[Step 2/3] Rendering 9 publication figures (Vector PDF & 350 DPI PNG)...")
    generate_all_figures(VIS_DIR)
    
    # 3. Generate Tables (CSV + LaTeX)
    print("\n[Step 3/3] Generating 2 evaluation tables in CSV and LaTeX...")
    generate_all_tables(VIS_DIR)
    
    # 4. Final Output Verification
    success = verify_outputs()
    elapsed = time.time() - t0
    print(f"Pipeline executed in {elapsed:.2f} seconds.")
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
