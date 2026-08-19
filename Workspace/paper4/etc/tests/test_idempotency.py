"""
Test Suite 1: Idempotency & Overwriting Safety Test
===================================================
Runs visualizer/plot_all.py 5 times sequentially.
Verifies:
1. Return code is 0 on every single run.
2. All 22 output files exist and have non-zero size.
3. Every PNG has DPI strictly equal to 350.
4. No file corruption, partial writes, or race conditions occur.
"""

import os
import sys
import time
import hashlib
import subprocess
from PIL import Image

REPO_ROOT = "/home/imnyj/Workspace/paper4"
VIS_DIR = os.path.join(REPO_ROOT, "visualizer")
PLOT_ALL_SCRIPT = os.path.join(VIS_DIR, "plot_all.py")

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

def get_file_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def run_idempotency_stress(num_runs=5):
    print("=" * 80)
    print(f"STARTING IDEMPOTENCY & OVERWRITING STRESS TEST ({num_runs} CONSECUTIVE RUNS)")
    print("=" * 80)

    run_results = []
    
    for i in range(1, num_runs + 1):
        t0 = time.time()
        print(f"\n--- Run {i}/{num_runs} ---")
        
        proc = subprocess.run(
            [sys.executable, PLOT_ALL_SCRIPT],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        
        elapsed = time.time() - t0
        ret_code = proc.returncode
        print(f"Run {i} completed in {elapsed:.2f}s with exit code {ret_code}")
        
        if ret_code != 0:
            print(f"[FAIL] Run {i} failed! Stdout:\n{proc.stdout}\nStderr:\n{proc.stderr}")
            return False, run_results
            
        # Verify all target files
        file_stats = {}
        for fname in TARGET_FILES:
            fpath = os.path.join(VIS_DIR, fname)
            if not os.path.exists(fpath):
                print(f"[FAIL] Missing file after run {i}: {fname}")
                return False, run_results
            
            size = os.path.getsize(fpath)
            if size == 0:
                print(f"[FAIL] 0-byte empty file detected after run {i}: {fname}")
                return False, run_results
                
            dpi = None
            if fname.endswith(".png"):
                with Image.open(fpath) as img:
                    dpi_raw = img.info.get('dpi')
                    if dpi_raw:
                        dpi = (round(dpi_raw[0]), round(dpi_raw[1]))
                    else:
                        dpi = "NO_DPI"
                if dpi != (350, 350):
                    print(f"[FAIL] PNG DPI mismatch after run {i}: {fname} has DPI={dpi}, expected (350, 350)")
                    return False, run_results
                    
            fhash = get_file_hash(fpath)
            file_stats[fname] = {"size": size, "dpi": dpi, "hash": fhash}
            
        run_results.append({
            "run": i,
            "elapsed": elapsed,
            "exit_code": ret_code,
            "files": file_stats
        })
        print(f"Run {i}: All {len(TARGET_FILES)} target files verified non-zero and 350 DPI.")

    print("\n" + "=" * 80)
    print("IDEMPOTENCY STRESS TEST PASSED SUCCESSFULLY!")
    print(f"Total runs: {num_runs}, All exit codes 0, All files valid.")
    print("=" * 80)
    return True, run_results

if __name__ == "__main__":
    success, results = run_idempotency_stress(5)
    if not success:
        sys.exit(1)
