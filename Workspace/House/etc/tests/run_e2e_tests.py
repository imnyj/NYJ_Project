#!/usr/bin/env python3
"""
Master E2E Test Runner for House Financial Simulation Project.
Executes all test tiers (Tier 1-4), records execution statistics in etc/logs/e2e_results.json,
and returns exit code 0 on complete pass.
"""

import os
import sys
import json
import time
import subprocess


def run_e2e_tests():
    project_root = "/home/imnyj/Workspace/House"
    tests_dir = os.path.join(project_root, "etc/tests")
    logs_dir = os.path.join(project_root, "etc/logs")
    log_file = os.path.join(logs_dir, "e2e_results.json")

    os.makedirs(logs_dir, exist_ok=True)

    tier_files = [
        "test_tier1.py",
        "test_tier2.py",
        "test_tier3.py",
        "test_tier4.py"
    ]

    print("=" * 70)
    print("      Cheongju House Financial Simulation — E2E Test Runner      ")
    print("=" * 70)

    start_time = time.time()
    all_tier_results = {}
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_tests_count = 0
    failures_detail = []

    pytest_binary = "/home/imnyj/venv/bin/pytest"
    if not os.path.exists(pytest_binary):
        pytest_binary = sys.executable

    for tier_file in tier_files:
        tier_path = os.path.join(tests_dir, tier_file)
        print(f"\n[RUNNING] {tier_file} ...")
        
        # Execute pytest on individual tier file with json/short reporting
        cmd = [
            pytest_binary,
            tier_path,
            "-v",
            "--tb=short"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        stdout = result.stdout
        stderr = result.stderr

        # Parse passed / failed numbers from stdout output lines
        passed = 0
        failed = 0
        skipped = 0

        for line in stdout.splitlines():
            if " passed" in line or " failed" in line:
                # e.g., "=== 26 passed in 0.15s ==="
                parts = line.strip(" =").split(",")
                for part in parts:
                    subparts = part.strip().split()
                    if len(subparts) >= 2:
                        val = subparts[0]
                        label = subparts[1]
                        if val.isdigit():
                            if "passed" in label:
                                passed = int(val)
                            elif "failed" in label:
                                failed = int(val)
                            elif "skipped" in label:
                                skipped = int(val)

        tier_total = passed + failed + skipped
        total_passed += passed
        total_failed += failed
        total_skipped += skipped
        total_tests_count += tier_total

        status = "PASSED" if (result.returncode == 0 and failed == 0) else "FAILED"
        print(f"[{status}] {tier_file}: {passed} passed, {failed} failed, {skipped} skipped (Total: {tier_total})")

        if status == "FAILED":
            failures_detail.append({
                "file": tier_file,
                "stdout": stdout[-1000:],
                "stderr": stderr[-1000:]
            })

        all_tier_results[tier_file] = {
            "status": status,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total": tier_total,
            "exit_code": result.returncode
        }

    duration = round(time.time() - start_time, 3)
    overall_status = "SUCCESS" if total_failed == 0 else "FAILURE"

    report_payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": overall_status,
        "summary": {
            "total_tests": total_tests_count,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
            "duration_seconds": duration
        },
        "tier_results": all_tier_results,
        "failures_detail": failures_detail
    }

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"OVERALL RESULT: {overall_status}")
    print(f"Total: {total_tests_count} | Passed: {total_passed} | Failed: {total_failed} | Skipped: {total_skipped}")
    print(f"Duration: {duration}s")
    print(f"Log written to: {log_file}")
    print("=" * 70)

    if total_failed > 0 or overall_status != "SUCCESS":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    run_e2e_tests()
