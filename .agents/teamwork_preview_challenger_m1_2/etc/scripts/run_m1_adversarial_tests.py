#!/usr/bin/env python3
"""
Adversarial Verification Suite for Milestone 1:
IEEE TWC LaTeX Conversion - Package Creation & Self-Containment.
"""

import os
import sys
import shutil
import zipfile
import subprocess
import hashlib
import re
from pathlib import Path

WORKSPACE_DIR = Path("/home/imnyj/Workspace/paper4/latex")
SANDBOX_BASE = Path("/home/imnyj/.agents/teamwork_preview_challenger_m1_2/etc/temp")
REPORT_LOG = Path("/home/imnyj/.agents/teamwork_preview_challenger_m1_2/etc/logs/test_execution.log")

EXPECTED_27_KEYS = [
    "Arena2019Overview",
    "Kenney2011DSRC",
    "ETSI_EN_302_637_2",
    "SAE_J2945_1",
    "ETSI_TS_102_687",
    "Zheng2022Age",
    "Liu2024Age",
    "ETSI_TS_103_175",
    "Bansal2013LIMERIC",
    "Ye2019Deep",
    "Hu2021Deep",
    "Wang2023Multi",
    "Mnih2015Human",
    "VanHasselt2016Deep",
    "Wang2016Dueling",
    "Yu2022Surprising",
    "Lowe2017Multi",
    "Rashid2018QMIX",
    "Chen2021Decision",
    "Janner2021Offline",
    "Shazeer2017Outrageously",
    "Xu2025Mixture",
    "Zhang2026Generalizable",
    "Kang2024Task",
    "Du2025Generative",
    "Park2025Ensemble",
    "Bhattacharyya2024Hybrid",
]

EXPECTED_9_BASE_FIGURES = [
    "1_reward_convergence.png",
    "2_ablation_study.png",
    "3_moe_routing.png",
    "4_tsne_clustering.png",
    "5_hardware_feasibility.png",
    "7_cbr_trace.png",
    "8_pdr_vs_density.png",
    "9_aoi_vs_density.png",
    "10_pdr_vs_distance.png",
]

EXPECTED_9_ALIASED_FIGURES = [
    "fig1_reward_convergence.png",
    "fig2_cbr_trace.png",
    "fig3_pdr_vs_density.png",
    "fig4_aoi_vs_density.png",
    "fig5_pdr_vs_distance.png",
    "fig6_hardware_feasibility.png",
    "fig7_ablation_study.png",
    "fig8_moe_routing.png",
    "fig9_tsne_clustering.png",
]

results = []

def log(msg):
    print(msg)
    with open(REPORT_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def record_test(name, passed, details):
    results.append({"name": name, "passed": passed, "details": details})
    status = "PASS" if passed else "FAIL"
    log(f"[{status}] {name}")
    if not passed or details:
        log(f"       Details: {details}")

def run_cmd(cmd, cwd=WORKSPACE_DIR):
    res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return res

def test_1_makefile_targets():
    log("\n=== TEST 1: Makefile Targets Execution ===")
    
    # 1.1 make help
    r = run_cmd("make help")
    record_test("Makefile: 'make help'", r.returncode == 0 and "make validate" in r.stdout, f"exit={r.returncode}, out={r.stdout.strip()}")

    # 1.2 make validate / make all
    r = run_cmd("make validate")
    record_test("Makefile: 'make validate'", r.returncode == 0 and "ALL INTEGRITY & VALIDATION CHECKS PASSED" in r.stdout, f"exit={r.returncode}")

    r = run_cmd("make all")
    record_test("Makefile: 'make all'", r.returncode == 0 and "ALL INTEGRITY & VALIDATION CHECKS PASSED" in r.stdout, f"exit={r.returncode}")

    # 1.3 make check (testing if target exists)
    r = run_cmd("make check")
    record_test("Makefile: 'make check' target existence", r.returncode == 0, f"exit={r.returncode}, err={r.stderr.strip()}")

    # 1.4 make compile (graceful failure when pdflatex not found)
    r = run_cmd("make compile")
    pdflatex_msg_found = "pdflatex not found in local environment" in r.stdout or "pdflatex not found in local environment" in r.stderr
    record_test("Makefile: 'make compile' graceful fallback", r.returncode != 0 and pdflatex_msg_found, f"exit={r.returncode}, out={r.stdout.strip()} {r.stderr.strip()}")

    # 1.5 make zip
    r = run_cmd("make zip")
    zip_created = (WORKSPACE_DIR / "paper4_latex_overleaf.zip").is_file()
    record_test("Makefile: 'make zip' creation", r.returncode == 0 and zip_created, f"exit={r.returncode}, zip_exists={zip_created}")

    # 1.6 make clean
    r = run_cmd("make clean")
    zip_removed = not (WORKSPACE_DIR / "paper4_latex_overleaf.zip").is_file()
    record_test("Makefile: 'make clean' cleans zip and aux", r.returncode == 0 and zip_removed, f"exit={r.returncode}, zip_removed={zip_removed}")

    # 1.7 Idempotency test
    r1 = run_cmd("make zip && make zip")
    r2 = run_cmd("make clean && make clean")
    record_test("Makefile: Target idempotency", r1.returncode == 0 and r2.returncode == 0, f"r1={r1.returncode}, r2={r2.returncode}")

def test_2_zip_package_and_self_containment():
    log("\n=== TEST 2: Overleaf Zip Packaging & Sandbox Self-Containment ===")
    # Re-generate zip
    run_cmd("make zip")
    zip_path = WORKSPACE_DIR / "paper4_latex_overleaf.zip"
    if not zip_path.is_file():
        record_test("Zip package existence", False, "paper4_latex_overleaf.zip not found")
        return

    # Check zip integrity with unzip -t
    r_test = run_cmd(f"unzip -t {zip_path}")
    record_test("Zip archive structural integrity (unzip -t)", r_test.returncode == 0, r_test.stdout.strip().split("\n")[-1])

    # Unpack into temporary sandbox
    sandbox_dir = SANDBOX_BASE / "sandbox_unpacked"
    if sandbox_dir.exists():
        shutil.rmtree(sandbox_dir)
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(sandbox_dir)
        zip_namelist = zf.namelist()

    log(f"  Extracted {len(zip_namelist)} items from zip:")
    for item in sorted(zip_namelist):
        log(f"    - {item}")

    # Verify no path traversal (../) or absolute paths (/foo)
    suspicious_paths = [name for name in zip_namelist if name.startswith("/") or ".." in name]
    record_test("Zip safety: No absolute paths or directory traversal", len(suspicious_paths) == 0, f"suspicious: {suspicious_paths}")

    # Verify no unwanted files (e.g. etc/, .pytest_cache, .git, etc.)
    unwanted = [name for name in zip_namelist if any(x in name for x in ["etc/", ".pytest_cache", ".git", ".DS_Store", "__pycache__"])]
    record_test("Zip cleanliness: No development artifacts (etc/, caches)", len(unwanted) == 0, f"unwanted: {unwanted}")

    # Check IEEEtran.cls
    sandbox_cls = sandbox_dir / "IEEEtran.cls"
    cls_valid = False
    if sandbox_cls.is_file():
        src_hash = hashlib.sha256((WORKSPACE_DIR / "IEEEtran.cls").read_bytes()).hexdigest()
        sand_hash = hashlib.sha256(sandbox_cls.read_bytes()).hexdigest()
        cls_valid = (src_hash == sand_hash) and sandbox_cls.stat().st_size > 200000
    record_test("Self-containment: IEEEtran.cls present and byte-identical", cls_valid, f"size={sandbox_cls.stat().st_size if sandbox_cls.is_file() else 'N/A'}")

    # Check references.bib
    sandbox_bib = sandbox_dir / "references.bib"
    bib_valid = False
    if sandbox_bib.is_file():
        src_bib_hash = hashlib.sha256((WORKSPACE_DIR / "references.bib").read_bytes()).hexdigest()
        sand_bib_hash = hashlib.sha256(sandbox_bib.read_bytes()).hexdigest()
        bib_valid = (src_bib_hash == sand_bib_hash)
    record_test("Self-containment: references.bib present and byte-identical", bib_valid, f"size={sandbox_bib.stat().st_size if sandbox_bib.is_file() else 'N/A'}")

    # Check figures/ directory in sandbox
    sandbox_fig_dir = sandbox_dir / "figures"
    fig_count = 0
    all_figs_valid = True
    fig_details = []
    PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
    if sandbox_fig_dir.is_dir():
        for fname in EXPECTED_9_BASE_FIGURES + EXPECTED_9_ALIASED_FIGURES:
            fpath = sandbox_fig_dir / fname
            if not fpath.is_file():
                all_figs_valid = False
                fig_details.append(f"Missing {fname}")
            else:
                with open(fpath, "rb") as f:
                    hdr = f.read(8)
                    if hdr != PNG_MAGIC:
                        all_figs_valid = False
                        fig_details.append(f"Invalid PNG magic in {fname}")
                fig_count += 1
    else:
        all_figs_valid = False
        fig_details.append("figures directory missing in sandbox")

    record_test("Self-containment: figures/ has all 18 valid PNG figures", all_figs_valid and fig_count == 18, f"found {fig_count}/18 figures, issues={fig_details}")

def test_3_sandbox_dummy_compilation_and_resolution():
    log("\n=== TEST 3: Sandbox Simulation with Synthetic main.tex ===")
    sandbox_dir = SANDBOX_BASE / "sandbox_unpacked"
    if not sandbox_dir.exists():
        record_test("Sandbox simulation setup", False, "Sandbox unpacked dir missing")
        return

    # Create synthetic main.tex in sandbox
    cites_str = ", ".join([f"\\cite{{{k}}}" for k in EXPECTED_27_KEYS])
    figures_str = "\n".join([
        f"\\begin{{figure}}[htbp]\n\\centering\n\\includegraphics[width=\\columnwidth]{{figures/{f}}}\n\\caption{{Caption for {f}}}\n\\label{{fig:{f.split('.')[0]}}}\n\\end{{figure}}"
        for f in EXPECTED_9_ALIASED_FIGURES
    ])

    dummy_tex = f"""\\documentclass[journal]{{IEEEtran}}
\\usepackage{{amsmath}}
\\usepackage{{graphicx}}
\\usepackage{{cite}}

\\title{{Test Autonomous V2X Communications}}
\\author{{Author One}}

\\begin{{document}}
\\maketitle

\\begin{{abstract}}
This is a self-containment test for IEEEtran LaTeX package.
\\end{{abstract}}

\\section{{Introduction}}
\\label{{sec:intro}}
Testing citation of all 27 references: {cites_str}.

\\section{{Figures}}
\\label{{sec:figures}}
{figures_str}

\\bibliographystyle{{IEEEtran}}
\\bibliography{{references}}

\\end{{document}}
"""
    dummy_path = sandbox_dir / "main.tex"
    dummy_path.write_text(dummy_tex, encoding="utf-8")

    # Run validation on the sandbox dummy document
    validator_path = WORKSPACE_DIR / "etc" / "scripts" / "validate_latex.py"
    res = subprocess.run([sys.executable, str(validator_path)], cwd=sandbox_dir, capture_output=True, text=True)
    record_test("Sandbox synthetic main.tex validation via validate_latex.py", res.returncode == 0, f"exit={res.returncode}")

def test_4_references_bib_deep_inspection():
    log("\n=== TEST 4: Deep Inspection of references.bib ===")
    bib_path = WORKSPACE_DIR / "references.bib"
    content = bib_path.read_text(encoding="utf-8")

    entry_pattern = re.compile(r"@(\w+)\s*\{\s*([^,]+),([^@]*)(?=(?:@|\Z))", re.DOTALL)
    matches = entry_pattern.findall(content)
    
    record_test("BibTeX entry count == 27", len(matches) == 27, f"found {len(matches)}")

    keys_found = [m[1].strip() for m in matches]
    duplicates = [k for k in keys_found if keys_found.count(k) > 1]
    record_test("BibTeX no duplicate keys", len(duplicates) == 0, f"duplicates={set(duplicates)}")

    missing_keys = [k for k in EXPECTED_27_KEYS if k not in keys_found]
    record_test("BibTeX all 27 required keys present", len(missing_keys) == 0, f"missing={missing_keys}")

    # Check required fields and balanced braces
    field_issues = []
    entries_split = [e for e in re.split(r"\n(?=@)", content) if e.strip()]
    for entry_text in entries_split:
        # Extract key
        m = re.match(r"@\w+\s*\{\s*([^,]+),", entry_text)
        key = m.group(1).strip() if m else "UNKNOWN"
        open_b = entry_text.count("{")
        close_b = entry_text.count("}")
        if open_b != close_b:
            field_issues.append(f"{key}: unbalanced braces ({{={open_b}, }}={close_b})")
        
        # Check essential fields (author, title, year)
        body_lower = entry_text.lower()
        if "author" not in body_lower:
            field_issues.append(f"{key}: missing 'author' field")
        if "title" not in body_lower:
            field_issues.append(f"{key}: missing 'title' field")
        if "year" not in body_lower:
            field_issues.append(f"{key}: missing 'year' field")

    record_test("BibTeX entries field completeness and balanced braces", len(field_issues) == 0, f"issues={field_issues}")

def test_5_figures_alias_consistency():
    log("\n=== TEST 5: Figure Aliasing Consistency Check ===")
    fig_dir = WORKSPACE_DIR / "figures"
    alias_mapping = {
        "fig1_reward_convergence.png": "1_reward_convergence.png",
        "fig2_cbr_trace.png": "7_cbr_trace.png",
        "fig3_pdr_vs_density.png": "8_pdr_vs_density.png",
        "fig4_aoi_vs_density.png": "9_aoi_vs_density.png",
        "fig5_pdr_vs_distance.png": "10_pdr_vs_distance.png",
        "fig6_hardware_feasibility.png": "5_hardware_feasibility.png",
        "fig7_ablation_study.png": "2_ablation_study.png",
        "fig8_moe_routing.png": "3_moe_routing.png",
        "fig9_tsne_clustering.png": "4_tsne_clustering.png",
    }
    
    mismatches = []
    for alias, base in alias_mapping.items():
        alias_p = fig_dir / alias
        base_p = fig_dir / base
        if not alias_p.is_file() or not base_p.is_file():
            mismatches.append(f"Missing file for pair {alias} <-> {base}")
            continue
        h_alias = hashlib.sha256(alias_p.read_bytes()).hexdigest()
        h_base = hashlib.sha256(base_p.read_bytes()).hexdigest()
        if h_alias != h_base:
            mismatches.append(f"Hash mismatch: {alias} != {base}")

    record_test("Figure alias hash consistency (9 pairs)", len(mismatches) == 0, f"mismatches={mismatches}")

def main():
    if REPORT_LOG.exists():
        REPORT_LOG.unlink()
    log("==================================================================")
    log(" teamwork_preview_challenger_m1_2: Adversarial Empirical Suite")
    log("==================================================================")

    test_1_makefile_targets()
    test_2_zip_package_and_self_containment()
    test_3_sandbox_dummy_compilation_and_resolution()
    test_4_references_bib_deep_inspection()
    test_5_figures_alias_consistency()

    log("\n==================================================================")
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = total - passed_count
    log(f"SUMMARY: Total Tests: {total} | PASSED: {passed_count} | FAILED: {failed_count}")
    log("==================================================================")
    
    return failed_count

if __name__ == "__main__":
    sys.exit(main())
