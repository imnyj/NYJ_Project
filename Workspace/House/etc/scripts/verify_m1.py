"""
verify_m1.py - Milestone 1 Automated Verification Runner Script
Location: /home/imnyj/Workspace/House/etc/scripts/verify_m1.py

Runs pytest on etc/tests/test_calc_engine.py and displays full verification report.
"""

import sys
import subprocess
from pathlib import Path


def run_verification():
    print("=====================================================================")
    print("      MILESTONE 1 AUTOMATED FINANCIAL DATA ENGINE VERIFICATION      ")
    print("=====================================================================")

    project_root = Path(__file__).resolve().parent.parent.parent
    test_file = project_root / "etc" / "tests" / "test_calc_engine.py"

    if not test_file.exists():
        print(f"Error: Test file not found at {test_file}")
        sys.exit(1)

    cmd = [sys.executable, "-m", "pytest", str(test_file), "-v", "-s"]
    print("Running command:", " ".join(cmd))
    print()

    res = subprocess.run(cmd, cwd=str(project_root))
    if res.returncode == 0:
        print()
        print("=====================================================================")
        print("      SUCCESS: ALL MILESTONE 1 VERIFICATION TESTS PASSED (100%)     ")
        print("=====================================================================")
        sys.exit(0)
    else:
        print()
        print("=====================================================================")
        print("      FAILURE: MILESTONE 1 VERIFICATION TESTS FAILED                 ")
        print("=====================================================================")
        sys.exit(1)


if __name__ == "__main__":
    run_verification()
