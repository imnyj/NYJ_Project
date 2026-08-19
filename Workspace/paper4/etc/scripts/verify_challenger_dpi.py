#!/usr/bin/env python3
"""
Empirical Challenger Script 1: DPI & Image Integrity Verification
Checks all 9 PNG files in visualizer/ using PIL.
"""

import os
import sys
from PIL import Image

VIS_DIR = "/home/imnyj/Workspace/paper4/visualizer"

PNG_TARGETS = [
    "1_ablation_study.png",
    "3_reward_convergence.png",
    "4_tsne_clustering.png",
    "5_moe_routing.png",
    "6_cbr_trace.png",
    "7_pdr_vs_density.png",
    "8_aoi_vs_density.png",
    "9_pdr_vs_distance.png",
    "10_aoi_vs_distance.png"
]

def main():
    print("=" * 80)
    print("CHALLENGER 1: PIL-based 350 DPI & Image Resolution Empirical Verification")
    print("=" * 80)
    
    all_passed = True
    results = []
    
    for filename in PNG_TARGETS:
        filepath = os.path.join(VIS_DIR, filename)
        if not os.path.exists(filepath):
            print(f"[FAIL - MISSING] {filename} does not exist!")
            all_passed = False
            results.append((filename, "MISSING", 0, 0, (0, 0), "N/A", False))
            continue
            
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            print(f"[FAIL - EMPTY] {filename} is 0 bytes!")
            all_passed = False
            results.append((filename, "EMPTY", 0, 0, (0, 0), "N/A", False))
            continue
            
        try:
            with Image.open(filepath) as img:
                img.verify() # Verify image integrity
            
            # Reopen to read metadata (verify closes the image)
            with Image.open(filepath) as img:
                width, height = img.size
                dpi = img.info.get("dpi", None)
                mode = img.mode
                format_type = img.format
                
                dpi_valid = False
                if dpi is not None:
                    xdpi, ydpi = dpi
                    if round(xdpi) == 350 and round(ydpi) == 350:
                        dpi_valid = True
                
                status = "[PASS]" if dpi_valid else "[FAIL - DPI MISMATCH]"
                if not dpi_valid:
                    all_passed = False
                    
                print(f"{status:<22} | {filename:<26} | Size: {file_size/1024:6.1f} KB | "
                      f"Res: {width}x{height} | DPI: {dpi} | Mode: {mode} | Format: {format_type}")
                results.append((filename, "OK" if dpi_valid else "DPI_MISMATCH", file_size, (width, height), dpi, mode, dpi_valid))
        except Exception as e:
            print(f"[FAIL - CORRUPTED] {filename}: {e}")
            all_passed = False
            results.append((filename, f"ERROR: {e}", file_size, (0, 0), None, "ERR", False))
            
    print("=" * 80)
    print(f"SUMMARY: {sum(1 for r in results if r[6])}/{len(PNG_TARGETS)} PNG files passed 350 DPI verification.")
    if all_passed:
        print(">> VERDICT: ALL 9 PNG FILES STRICTLY SATISFY 350 DPI RESOLUTION REQUIREMENT.")
    else:
        print(">> VERDICT: DPI VERIFICATION FAILED FOR SOME FILES.")
    print("=" * 80)
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
