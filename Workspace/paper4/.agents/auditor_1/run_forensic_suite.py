import subprocess
import sys
import os
import time

PROJECT_ROOT = "/home/imnyj/Workspace/paper4"
CODE_DIR = os.path.join(PROJECT_ROOT, "code")

test_files = [
    "test_c3_reward.py",
    "test_h4_grid.py",
    "test_h5_ablation.py",
    "test_h6_tabular.py",
    "test_m7_nest.py",
    "test_m8_local_cbr.py",
    "test_m9_paths.py",
    "test_m10_training_params.py",
    "test_m11_benchmark_models.py",
    "test_m12_terminal_transitions.py",
    "test_comm_module.py",
    "test_sac_hook.py"
]

results = {}

print("=== RUNNING FAST INDEPENDENT REGRESSION TESTS ===")
for tf in test_files:
    path = os.path.join(CODE_DIR, tf)
    if not os.path.exists(path):
        results[tf] = {"status": "MISSING", "time": 0.0, "output": "File not found"}
        continue
    
    t0 = time.time()
    p = subprocess.run(
        [sys.executable, path],
        cwd=CODE_DIR,
        capture_output=True,
        text=True
    )
    elapsed = time.time() - t0
    status = "PASS" if p.returncode == 0 else "FAIL"
    results[tf] = {
        "status": status,
        "time": round(elapsed, 3),
        "returncode": p.returncode,
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip()
    }
    print(f"[{status}] {tf:35s} in {elapsed:6.3f}s (rc={p.returncode})")

passed = sum(1 for r in results.values() if r["status"] == "PASS")
total = len(results)
print(f"\nSummary: {passed}/{total} tests passed.")
