"""
Empirical Harness 1: Falsify run_e2e_tests.py
Tests whether run_e2e_tests.py correctly returns exit code 1 on test assertion failure and on pytest collection error.
"""

import os
import sys
import subprocess
import shutil
import tempfile

PROJECT_ROOT = "/home/imnyj/Workspace/House"

def test_assertion_failure_exit_code():
    """Verify exit code when a test assertion fails."""
    # Create a temporary directory copying etc/tests layout
    with tempfile.TemporaryDirectory() as tmpdir:
        tests_dir = os.path.join(tmpdir, "etc/tests")
        logs_dir = os.path.join(tmpdir, "etc/logs")
        os.makedirs(tests_dir)
        os.makedirs(logs_dir)

        # Copy helpers
        shutil.copytree(os.path.join(PROJECT_ROOT, "etc/tests/helpers"), os.path.join(tests_dir, "helpers"))

        # Create dummy passing test_tier1.py, test_tier2.py, test_tier3.py
        for tier in ["test_tier1.py", "test_tier2.py", "test_tier3.py"]:
            with open(os.path.join(tests_dir, tier), "w") as f:
                f.write("def test_pass(): assert True\n")

        # Create failing test_tier4.py
        with open(os.path.join(tests_dir, "test_tier4.py"), "w") as f:
            f.write("def test_fail(): assert 1 == 2, 'Falsification failure'\n")

        # Copy run_e2e_tests.py but update project_root path to tmpdir
        runner_code = open(os.path.join(PROJECT_ROOT, "etc/tests/run_e2e_tests.py"), "r").read()
        runner_code = runner_code.replace('project_root = "/home/imnyj/Workspace/House"', f'project_root = "{tmpdir}"')
        
        runner_path = os.path.join(tests_dir, "run_e2e_tests.py")
        with open(runner_path, "w") as f:
            f.write(runner_code)

        # Execute modified runner script
        res = subprocess.run([sys.executable, runner_path], capture_output=True, text=True)
        print("=== Test 1A: Assertion Failure Exit Code ===")
        print(f"Exit Code: {res.returncode}")
        print(f"Stdout:\n{res.stdout}")
        print(f"Stderr:\n{res.stderr}")
        return res.returncode


def test_collection_error_exit_code():
    """Verify exit code when pytest encounters a SyntaxError or ImportError during collection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tests_dir = os.path.join(tmpdir, "etc/tests")
        logs_dir = os.path.join(tmpdir, "etc/logs")
        os.makedirs(tests_dir)
        os.makedirs(logs_dir)

        shutil.copytree(os.path.join(PROJECT_ROOT, "etc/tests/helpers"), os.path.join(tests_dir, "helpers"))

        for tier in ["test_tier1.py", "test_tier2.py", "test_tier3.py"]:
            with open(os.path.join(tests_dir, tier), "w") as f:
                f.write("def test_pass(): assert True\n")

        # Create syntax error in test_tier4.py
        with open(os.path.join(tests_dir, "test_tier4.py"), "w") as f:
            f.write("def test_syntax_error(: def invalid_syntax\n")

        runner_code = open(os.path.join(PROJECT_ROOT, "etc/tests/run_e2e_tests.py"), "r").read()
        runner_code = runner_code.replace('project_root = "/home/imnyj/Workspace/House"', f'project_root = "{tmpdir}"')
        
        runner_path = os.path.join(tests_dir, "run_e2e_tests.py")
        with open(runner_path, "w") as f:
            f.write(runner_code)

        res = subprocess.run([sys.executable, runner_path], capture_output=True, text=True)
        print("=== Test 1B: Collection Error / Syntax Error Exit Code ===")
        print(f"Exit Code: {res.returncode}")
        print(f"Stdout:\n{res.stdout}")
        print(f"Stderr:\n{res.stderr}")
        return res.returncode

if __name__ == "__main__":
    code1 = test_assertion_failure_exit_code()
    code2 = test_collection_error_exit_code()
    print(f"\nSummary: Assertion Failure Exit Code={code1}, Collection Error Exit Code={code2}")
