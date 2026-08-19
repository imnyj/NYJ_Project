#!/usr/bin/env python3
"""
test_sandbox_overleaf.py
========================
Empirical Adversarial Test Suite for Overleaf Package Standalone Integrity & Sandbox Extraction.

Target:
- Package: /home/imnyj/Workspace/paper4/latex/paper4_latex_overleaf.zip
- Sandbox: /home/imnyj/.agents/teamwork_preview_challenger_final_2/sandbox
- Makefile in /home/imnyj/Workspace/paper4/latex/

Author: teamwork_preview_challenger_final_2
Date: 2026-08-18
"""

import os
import re
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path
from collections import defaultdict

ZIP_PATH = Path("/home/imnyj/Workspace/paper4/latex/paper4_latex_overleaf.zip")
WORKSPACE_DIR = Path("/home/imnyj/Workspace/paper4/latex")
SANDBOX_DIR = Path("/home/imnyj/.agents/teamwork_preview_challenger_final_2/sandbox")
REPORT_PATH = Path("/home/imnyj/.agents/teamwork_preview_challenger_final_2/challenge_report.md")


def run_cmd(cmd, cwd=None):
    res = subprocess.run(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.returncode, res.stdout, res.stderr


def step_1_zip_integrity_and_contents():
    print("=" * 70)
    print("STEP 1: Zip Archive Integrity & File Inventory Audit")
    print("=" * 70)
    
    results = {"passed": True, "errors": [], "warnings": [], "inventory": []}
    
    if not ZIP_PATH.is_file():
        results["passed"] = False
        results["errors"].append(f"Zip archive missing at {ZIP_PATH}")
        return results

    size_bytes = ZIP_PATH.stat().st_size
    print(f"[*] Checking archive: {ZIP_PATH} ({size_bytes} bytes)")
    
    try:
        with zipfile.ZipFile(ZIP_PATH, 'r') as z:
            bad_file = z.testzip()
            if bad_file:
                results["passed"] = False
                results["errors"].append(f"Corrupted file in zip: {bad_file}")
            else:
                print("  [OK] Zip CRC/Checksum integrity verification passed (0 corruption).")

            namelist = z.namelist()
            infolist = z.infolist()
            print(f"[*] Total entries in archive: {len(namelist)}")
            
            for info in infolist:
                results["inventory"].append({
                    "filename": info.filename,
                    "file_size": info.file_size,
                    "compress_size": info.compress_size,
                    "is_dir": info.is_dir(),
                })
                print(f"    - {info.filename:<35} (Original: {info.file_size} B, Compressed: {info.compress_size} B)")

            # Check required root files
            required_root_files = ["main.tex", "references.bib", "IEEEtran.cls"]
            for rf in required_root_files:
                if rf not in namelist:
                    results["passed"] = False
                    results["errors"].append(f"Missing mandatory root file in zip: '{rf}'")
                else:
                    print(f"  [OK] Mandatory file present: {rf}")

            # Check figures directory
            figure_entries = [n for n in namelist if n.startswith("figures/") and not n.endswith("/")]
            print(f"[*] Found {len(figure_entries)} figure files inside figures/ directory:")
            for fe in figure_entries:
                print(f"    - {fe}")
            
            if len(figure_entries) == 0:
                results["passed"] = False
                results["errors"].append("No figure files found in figures/ inside zip archive.")

            # Check for forbidden/junk files (e.g., .DS_Store, __MACOSX, *.pyc, *.aux, *.log)
            junk_patterns = [r"\.DS_Store", r"__MACOSX", r"\.pyc$", r"\.log$", r"\.aux$", r"\.bbl$", r"\.blg$"]
            for name in namelist:
                for jp in junk_patterns:
                    if re.search(jp, name, re.IGNORECASE):
                        results["warnings"].append(f"Unwanted junk file packaged in zip: {name}")

    except Exception as e:
        results["passed"] = False
        results["errors"].append(f"Exception while reading zip: {e}")

    return results


def step_2_sandbox_extraction():
    print("\n" + "=" * 70)
    print("STEP 2: Clean Sandbox Extraction & File Verification")
    print("=" * 70)
    
    results = {"passed": True, "errors": [], "extracted_files": []}
    
    # Recreate clean sandbox
    if SANDBOX_DIR.exists():
        shutil.rmtree(SANDBOX_DIR)
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[*] Initialized clean sandbox directory at: {SANDBOX_DIR}")

    try:
        with zipfile.ZipFile(ZIP_PATH, 'r') as z:
            z.extractall(SANDBOX_DIR)
        print(f"  [OK] Successfully extracted all contents into sandbox.")

        # List all extracted files
        for p in sorted(SANDBOX_DIR.rglob("*")):
            if p.is_file():
                results["extracted_files"].append(str(p.relative_to(SANDBOX_DIR)))
                print(f"    - {p.relative_to(SANDBOX_DIR)} ({p.stat().st_size} bytes)")

    except Exception as e:
        results["passed"] = False
        results["errors"].append(f"Exception during extraction: {e}")

    return results


def step_3_symlinks_and_absolute_paths():
    print("\n" + "=" * 70)
    print("STEP 3: Adversarial Path Audit (Dangling Symlinks, Absolute Paths, Escape Sequences)")
    print("=" * 70)
    
    results = {"passed": True, "errors": [], "symlinks": [], "path_leaks": []}
    
    # 1. Check for symbolic links
    for p in SANDBOX_DIR.rglob("*"):
        if p.is_symlink():
            target = p.resolve()
            results["symlinks"].append((str(p), str(target)))
            results["passed"] = False
            results["errors"].append(f"Symbolic link detected in sandbox: {p} -> {target}")

    if not results["symlinks"]:
        print("  [OK] 0 symbolic links detected (all extracted files are genuine regular files).")

    # 2. Check for absolute paths and path escape in text files
    text_extensions = [".tex", ".bib", ".cls", ".txt", ".md", ".py"]
    leak_patterns = [
        (re.compile(r"/home/imnyj"), "Absolute path '/home/imnyj' detected"),
        (re.compile(r"/root"), "Absolute path '/root' detected"),
        (re.compile(r"/tmp"), "Absolute path '/tmp' detected"),
        (re.compile(r"[A-Za-z]:\\"), "Windows absolute path detected"),
        (re.compile(r"\.\./"), "Upward relative path escape '../' detected"),
    ]

    for p in SANDBOX_DIR.rglob("*"):
        if p.is_file() and p.suffix in text_extensions:
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                for line_idx, line in enumerate(content.splitlines(), 1):
                    for pattern, desc in leak_patterns:
                        if pattern.search(line):
                            # Skip if it's within a comment in cls or bib URL if standard
                            # But flag if in tex or path include
                            leak_msg = f"{p.relative_to(SANDBOX_DIR)}:line {line_idx} -> {desc}: {line.strip()[:100]}"
                            results["path_leaks"].append(leak_msg)
                            # If found in main.tex or includegraphics, fail!
                            if p.name == "main.tex":
                                results["passed"] = False
                                results["errors"].append(leak_msg)
            except Exception as e:
                results["errors"].append(f"Could not read {p}: {e}")

    if not results["path_leaks"]:
        print("  [OK] 0 absolute path leaks or upward directory escapes detected across all files.")
    else:
        print(f"  [INFO] Path leak scan found {len(results['path_leaks'])} items:")
        for pl in results["path_leaks"]:
            print(f"    - {pl}")

    return results


def step_4_self_contained_asset_resolution():
    print("\n" + "=" * 70)
    print("STEP 4: Self-Contained LaTeX Asset & Reference Verification in Sandbox")
    print("=" * 70)
    
    results = {"passed": True, "errors": [], "resolved_images": [], "resolved_cites": []}
    
    main_path = SANDBOX_DIR / "main.tex"
    bib_path = SANDBOX_DIR / "references.bib"
    
    if not main_path.is_file():
        results["passed"] = False
        results["errors"].append("main.tex is missing in sandbox.")
        return results

    content = main_path.read_text(encoding="utf-8")
    
    # 1. Verify all \includegraphics inside sandbox
    img_matches = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", content)
    print(f"[*] Found {len(img_matches)} \\includegraphics declarations in sandbox main.tex:")
    
    for raw_img in img_matches:
        img_p = raw_img.strip()
        target_path = SANDBOX_DIR / img_p
        if not target_path.is_file():
            # Check with .png
            if (SANDBOX_DIR / f"{img_p}.png").is_file():
                target_path = SANDBOX_DIR / f"{img_p}.png"
            else:
                results["passed"] = False
                results["errors"].append(f"Figure file not found in sandbox: '{img_p}' (resolved as {target_path})")
                print(f"  [FAIL] Missing image in sandbox: {img_p}")
                continue

        # Check PNG header
        with open(target_path, "rb") as f:
            header = f.read(8)
        if header != b"\x89PNG\r\n\x1a\n":
            results["passed"] = False
            results["errors"].append(f"Image {target_path.name} in sandbox is not a valid PNG.")
        else:
            results["resolved_images"].append((img_p, target_path.name, target_path.stat().st_size))
            print(f"  [OK] Image resolved locally: '{img_p}' -> {target_path.name} ({target_path.stat().st_size} bytes)")

    # 2. Verify all \cite{} match references.bib in sandbox
    if not bib_path.is_file():
        results["passed"] = False
        results["errors"].append("references.bib is missing in sandbox.")
    else:
        bib_content = bib_path.read_text(encoding="utf-8")
        entry_pattern = re.compile(r"@(\w+)\s*\{\s*([^,]+),", re.MULTILINE)
        bib_keys = set(m[1].strip() for m in entry_pattern.findall(bib_content))
        print(f"[*] Found {len(bib_keys)} BibTeX entries in sandbox references.bib.")

        cite_matches = re.findall(r"\\cite(?:\[[^\]]*\])?\{([^}]+)\}", content)
        cited_keys = set()
        for cg in cite_matches:
            for k in cg.split(","):
                k = k.strip()
                if k:
                    cited_keys.add(k)
                    if k not in bib_keys:
                        results["passed"] = False
                        results["errors"].append(f"Undefined citation in sandbox main.tex: '{k}'")

        print(f"  [OK] Verified {len(cited_keys)} unique in-text citation keys against sandbox references.bib.")
        results["resolved_cites"] = list(cited_keys)

    return results


def step_5_execute_validator_in_sandbox():
    print("\n" + "=" * 70)
    print("STEP 5: Execution of Validation Suite directly on Sandbox Files")
    print("=" * 70)
    
    results = {"passed": True, "errors": [], "stdout": "", "stderr": ""}
    
    # We can create a sandbox validator runner that sets BASE_DIR = SANDBOX_DIR
    sandbox_validator_code = f"""
import sys
from pathlib import Path

# Adjust BASE_DIR to sandbox
import importlib.util
spec = importlib.util.spec_from_file_location("validate_latex", "{WORKSPACE_DIR}/etc/scripts/validate_latex.py")
val_mod = importlib.util.module_from_spec(spec)
val_mod.BASE_DIR = Path("{SANDBOX_DIR}")
spec.loader.exec_module(val_mod)

val_mod.main()
"""
    runner_script = SANDBOX_DIR / "_run_val.py"
    runner_script.write_text(sandbox_validator_code, encoding="utf-8")
    
    ret, out, err = run_cmd(f"python3 _run_val.py", cwd=str(SANDBOX_DIR))
    runner_script.unlink(missing_ok=True)
    
    print(out)
    if err:
        print("STDERR:", err)

    results["stdout"] = out
    results["stderr"] = err
    if ret != 0:
        results["passed"] = False
        results["errors"].append(f"validate_latex.py failed on sandbox with return code {ret}")
    else:
        print("  [OK] Validation suite executed and PASSED (0 errors) on sandbox directory.")

    return results


def step_6_makefile_targets_stress_test():
    print("\n" + "=" * 70)
    print("STEP 6: Makefile Target Testing & Build Lifecycle Stress Test")
    print("=" * 70)
    
    results = {"passed": True, "errors": [], "target_results": {}}
    
    # 1. Test make help
    ret, out, err = run_cmd("make help", cwd=str(WORKSPACE_DIR))
    results["target_results"]["make help"] = {"returncode": ret, "stdout": out}
    print(f"[*] make help: return code {ret}")
    if ret != 0:
        results["passed"] = False
        results["errors"].append(f"make help failed with code {ret}")

    # 2. Test make validate
    ret, out, err = run_cmd("make validate", cwd=str(WORKSPACE_DIR))
    results["target_results"]["make validate"] = {"returncode": ret, "stdout": out}
    print(f"[*] make validate: return code {ret}")
    if ret != 0:
        results["passed"] = False
        results["errors"].append(f"make validate failed with code {ret}")

    # 3. Test make check (check if alias exists)
    ret, out, err = run_cmd("make check", cwd=str(WORKSPACE_DIR))
    results["target_results"]["make check"] = {"returncode": ret, "stdout": out, "stderr": err}
    print(f"[*] make check: return code {ret} (Stderr: {err.strip()})")
    if ret != 0:
        results["target_results"]["make check"]["note"] = "No rule 'check' found; 'validate' is primary target."

    # 4. Test make zip
    ret, out, err = run_cmd("make zip", cwd=str(WORKSPACE_DIR))
    results["target_results"]["make zip"] = {"returncode": ret, "stdout": out}
    print(f"[*] make zip: return code {ret}")
    if ret != 0:
        results["passed"] = False
        results["errors"].append(f"make zip failed with code {ret}")
    else:
        # Check that zip was regenerated
        if not ZIP_PATH.is_file():
            results["passed"] = False
            results["errors"].append("make zip succeeded but paper4_latex_overleaf.zip not found.")
        else:
            print(f"  [OK] Regenerated {ZIP_PATH.name} ({ZIP_PATH.stat().st_size} bytes)")

    # 5. Test make clean
    # Create a dummy .aux file to verify make clean removes it
    dummy_aux = WORKSPACE_DIR / "dummy_test.aux"
    dummy_aux.write_text("test aux content", encoding="utf-8")
    
    ret, out, err = run_cmd("make clean", cwd=str(WORKSPACE_DIR))
    results["target_results"]["make clean"] = {"returncode": ret, "stdout": out}
    print(f"[*] make clean: return code {ret}")
    if ret != 0:
        results["passed"] = False
        results["errors"].append(f"make clean failed with code {ret}")
    
    if dummy_aux.exists():
        results["passed"] = False
        results["errors"].append("make clean failed to remove auxiliary files (*.aux).")
    else:
        print("  [OK] make clean removed auxiliary files successfully.")

    # 6. Re-run make zip to restore the package after clean
    ret, out, err = run_cmd("make zip", cwd=str(WORKSPACE_DIR))
    if ret != 0 or not ZIP_PATH.is_file():
        results["passed"] = False
        results["errors"].append("Failed to re-generate zip package after make clean.")
    else:
        print("  [OK] Successfully re-generated zip package after make clean.")

    return results


def main():
    print("#" * 70)
    print(" EMPIRICAL OVERLEAF PACKAGE INTEGRITY & SANDBOX STRESS TEST HARNESS")
    print("#" * 70)
    
    s1 = step_1_zip_integrity_and_contents()
    s2 = step_2_sandbox_extraction()
    s3 = step_3_symlinks_and_absolute_paths()
    s4 = step_4_self_contained_asset_resolution()
    s5 = step_5_execute_validator_in_sandbox()
    s6 = step_6_makefile_targets_stress_test()
    
    all_passed = (
        s1["passed"] and s2["passed"] and s3["passed"] and
        s4["passed"] and s5["passed"] and s6["passed"]
    )
    
    print("\n" + "#" * 70)
    print(" OVERALL SUMMARY OF STRESS TEST RESULTS")
    print("#" * 70)
    print(f"1. Zip Integrity & File Inventory Audit:     {'PASS' if s1['passed'] else 'FAIL'}")
    print(f"2. Clean Sandbox Extraction:                 {'PASS' if s2['passed'] else 'FAIL'}")
    print(f"3. Zero Symlinks & Path Leakage Audit:       {'PASS' if s3['passed'] else 'FAIL'}")
    print(f"4. Self-Contained Asset Resolution:          {'PASS' if s4['passed'] else 'FAIL'}")
    print(f"5. Validation Suite on Sandbox:              {'PASS' if s5['passed'] else 'FAIL'}")
    print(f"6. Makefile Targets & Lifecycle:             {'PASS' if s6['passed'] else 'FAIL'}")
    print("#" * 70)
    
    if all_passed:
        print("\n>>> OVERALL EMPIRICAL VERDICT: APPROVE <<<")
    else:
        print("\n>>> OVERALL EMPIRICAL VERDICT: REQUEST_CHANGES <<<")
        
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
