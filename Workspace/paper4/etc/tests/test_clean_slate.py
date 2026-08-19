"""
Test Suite 2: Clean Slate & Isolated Output Directory Test
===========================================================
Tests the visualizer pipeline against an empty output directory
and validates directory auto-creation, path parameterization,
and isolated build capability.
"""

import os
import sys
import shutil
import tempfile
from PIL import Image

REPO_ROOT = "/home/imnyj/Workspace/paper4"
VIS_DIR = os.path.join(REPO_ROOT, "visualizer")
if VIS_DIR not in sys.path:
    sys.path.insert(0, VIS_DIR)

from plot_figures import generate_all_figures
from generate_tables import generate_all_tables
from prepare_data import (
    build_reward_convergence,
    build_ablation_study,
    build_optuna_sensitivity,
    build_tsne_clustering,
    build_moe_routing,
    build_cbr_trace,
    build_pdr_vs_density,
    build_aoi_vs_density,
    build_pdr_vs_distance,
    build_aoi_vs_distance,
    build_hardware_feasibility
)

TARGET_FILES = [
    "1_ablation_study.png", "1_ablation_study.pdf",
    "2_optuna_sensitivity_table.csv", "2_optuna_sensitivity_table.tex",
    "3_reward_convergence.png", "3_reward_convergence.pdf",
    "4_tsne_clustering.png", "4_tsne_clustering.pdf",
    "5_moe_routing.png", "5_moe_routing.pdf",
    "6_cbr_trace.png", "6_cbr_trace.pdf",
    "7_pdr_vs_density.png", "7_pdr_vs_density.pdf",
    "8_aoi_vs_density.png", "8_aoi_vs_density.pdf",
    "9_pdr_vs_distance.png", "9_pdr_vs_distance.pdf",
    "10_aoi_vs_distance.png", "10_aoi_vs_distance.pdf",
    "11_hardware_feasibility_table.csv", "11_hardware_feasibility_table.tex"
]

def run_clean_slate_test():
    print("=" * 80)
    print("STARTING CLEAN SLATE & ISOLATED DIRECTORY STRESS TEST")
    print("=" * 80)
    
    temp_dir = os.path.join(REPO_ROOT, "etc", "temp", "clean_build_test")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    
    print(f"Isolated clean test directory created at: {temp_dir}")
    
    try:
        # 1. Test data generator functions
        print("\n[Sub-test 1/3] Testing data generators...")
        build_reward_convergence()
        build_ablation_study()
        build_optuna_sensitivity()
        build_tsne_clustering()
        build_moe_routing()
        build_cbr_trace()
        build_pdr_vs_density()
        build_aoi_vs_density()
        build_pdr_vs_distance()
        build_aoi_vs_distance()
        build_hardware_feasibility()
        print("[PASS] All 11 data generators executed cleanly.")
        
        # 2. Test figure generation into isolated directory
        print("\n[Sub-test 2/3] Rendering 9 figures into clean isolated directory...")
        generate_all_figures(temp_dir)
        print("[PASS] Figure generation finished.")
        
        # 3. Test table generation into isolated directory
        print("\n[Sub-test 3/3] Generating 2 tables into clean isolated directory...")
        generate_all_tables(temp_dir)
        print("[PASS] Table generation finished.")
        
        # 4. Verify all output files in the isolated directory
        print("\n[Verification] Checking generated files in clean directory...")
        all_passed = True
        for fname in TARGET_FILES:
            fpath = os.path.join(temp_dir, fname)
            if not os.path.exists(fpath):
                print(f"[FAIL] Missing target file in clean directory: {fname}")
                all_passed = False
                continue
            size = os.path.getsize(fpath)
            if size == 0:
                print(f"[FAIL] Empty 0-byte file in clean directory: {fname}")
                all_passed = False
                continue
            if fname.endswith(".png"):
                with Image.open(fpath) as img:
                    dpi_raw = img.info.get('dpi')
                    dpi = (round(dpi_raw[0]), round(dpi_raw[1])) if dpi_raw else None
                    if dpi != (350, 350):
                        print(f"[FAIL] DPI mismatch in clean directory: {fname} (DPI={dpi})")
                        all_passed = False
            print(f"  [OK] {fname:<36} ({size/1024.0:6.1f} KB)")
            
        if all_passed:
            print("\n" + "=" * 80)
            print("CLEAN SLATE & ISOLATED BUILD TEST PASSED SUCCESSFULLY!")
            print("=" * 80)
            return True
        else:
            print("\n[FAIL] Clean slate test failed output verification.")
            return False
            
    finally:
        # Cleanup isolated temp dir
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")

if __name__ == "__main__":
    success = run_clean_slate_test()
    if not success:
        sys.exit(1)
