#!/usr/bin/env python3
"""
run_adversarial_tests.py
Milestone 1 Adversarial & Stress Testing Suite for teamwork_preview_challenger_m1_2.
"""

import os
import sys
import shutil
import subprocess
import tempfile
import re
from pathlib import Path

# Paths
WORK_DIR = Path("/home/imnyj/.agents/teamwork_preview_challenger_m1_2")
ETC_DIR = WORK_DIR / "etc"
SANDBOX_DIR = ETC_DIR / "sandbox"
LATEX_DIR = Path("/home/imnyj/Workspace/paper4/latex")

TEST_RESULTS = []

def record_result(test_name, passed, details, blast_radius=None):
    TEST_RESULTS.append({
        "name": test_name,
        "passed": passed,
        "details": details,
        "blast_radius": blast_radius
    })
    status_str = "[PASS]" if passed else "[FAIL]"
    print(f"{status_str} {test_name}: {details}")


def test_1_zip_archive_integrity():
    print("\n--- Test 1: Zip Archive Integrity & Self-Containment ---")
    zip_path = LATEX_DIR / "paper4_latex_overleaf.zip"
    if not zip_path.is_file():
        record_result("Zip Archive Existence", False, f"{zip_path} does not exist")
        return

    # Check zip contents
    res = subprocess.run(["unzip", "-l", str(zip_path)], capture_output=True, text=True)
    out = res.stdout

    has_cls = "IEEEtran.cls" in out
    has_bib = "references.bib" in out
    has_fig_dir = "figures/" in out

    record_result("Zip Contains IEEEtran.cls", has_cls, f"IEEEtran.cls present: {has_cls}")
    record_result("Zip Contains references.bib", has_bib, f"references.bib present: {has_bib}")
    record_result("Zip Contains figures/", has_fig_dir, f"figures/ present: {has_fig_dir}")

    # Check for absolute paths inside zip
    lines = out.splitlines()
    abs_paths = [l for l in lines if "/home/" in l or "C:" in l or "\\" in l]
    record_result("No Absolute Paths in Zip", len(abs_paths) == 0, f"Absolute path count: {len(abs_paths)}")


def test_2_sandbox_latex_compilation():
    print("\n--- Test 2: Overleaf Mock Compilation in Sandbox ---")
    # Clean and re-extract to sandbox
    if SANDBOX_DIR.exists():
        shutil.rmtree(SANDBOX_DIR)
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

    zip_path = LATEX_DIR / "paper4_latex_overleaf.zip"
    unzip_res = subprocess.run(["unzip", "-q", str(zip_path), "-d", str(SANDBOX_DIR)], capture_output=True, text=True)
    if unzip_res.returncode != 0:
        record_result("Sandbox Unpack", False, f"Failed to unpack: {unzip_res.stderr}")
        return
    record_result("Sandbox Unpack", True, "Successfully unpacked into sandbox")

    # Create dummy main.tex citing all 27 references and including all 9 figures
    # Read bib keys
    bib_content = (SANDBOX_DIR / "references.bib").read_text(encoding="utf-8")
    entry_pattern = re.compile(r"@(\w+)\s*\{\s*([^,]+),", re.MULTILINE)
    bib_keys = [m[1].strip() for m in entry_pattern.findall(bib_content)]

    # Collect figures
    fig_files = sorted([f.name for f in (SANDBOX_DIR / "figures").glob("*.png")])

    dummy_tex = r"""\documentclass[journal]{IEEEtran}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{cite}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{algorithm}
\usepackage{algpseudocode}

\title{Empirical Test of IEEEtran Infrastructure for REMO-DQN}
\author{Test Author}

\begin{document}
\maketitle

\begin{abstract}
This is an adversarial stress-test document to verify IEEEtran compilation, figure inclusion, and BibTeX citation resolution in an isolated sandbox.
\end{abstract}

\section{Introduction}
Testing all citations:
"""
    # Add citations
    for k in bib_keys:
        dummy_tex += f"\\cite{{{k}}} "

    dummy_tex += "\n\n\\section{Figure Inclusion Test}\n"
    for fig in fig_files:
        dummy_tex += f"""\\begin{{figure}}[!t]
\\centering
\\includegraphics[width=0.45\\textwidth]{{figures/{fig}}}
\\caption{{Test Figure {fig}}}
\\label{{fig:{fig.replace('.', '_')}}}
\\end{{figure}}
"""

    dummy_tex += r"""
\bibliographystyle{IEEEtran}
\bibliography{references}

\end{document}
"""

    dummy_tex_path = SANDBOX_DIR / "test_main.tex"
    dummy_tex_path.write_text(dummy_tex, encoding="utf-8")

    # Check if pdflatex is available
    which_pdflatex = subprocess.run(["which", "pdflatex"], capture_output=True, text=True)
    if which_pdflatex.returncode != 0:
        record_result("pdflatex Tool Availability", False, "pdflatex binary not found on system (Overleaf target)")
        return

    # Pass 1: pdflatex
    p1 = subprocess.run(["pdflatex", "-interaction=nonstopmode", "test_main.tex"], cwd=str(SANDBOX_DIR), capture_output=True, text=True)
    record_result("Pass 1: pdflatex Compilation", p1.returncode == 0, f"pdflatex pass 1 exit code {p1.returncode}")

    # Pass 2: bibtex
    b_res = subprocess.run(["bibtex", "test_main"], cwd=str(SANDBOX_DIR), capture_output=True, text=True)
    has_bibtex_errors = "error" in b_res.stdout.lower() or "error" in b_res.stderr.lower()
    record_result("Pass 2: BibTeX Resolution (All 27 references)", b_res.returncode == 0 and not has_bibtex_errors, f"bibtex exit {b_res.returncode}, stdout snippet: {b_res.stdout[:200]}")

    # Pass 3: pdflatex
    p2 = subprocess.run(["pdflatex", "-interaction=nonstopmode", "test_main.tex"], cwd=str(SANDBOX_DIR), capture_output=True, text=True)
    record_result("Pass 3: pdflatex with BibTeX", p2.returncode == 0, f"pdflatex pass 2 exit code {p2.returncode}")

    # Pass 4: pdflatex
    p3 = subprocess.run(["pdflatex", "-interaction=nonstopmode", "test_main.tex"], cwd=str(SANDBOX_DIR), capture_output=True, text=True)
    record_result("Pass 4: Final pdflatex", p3.returncode == 0, f"pdflatex pass 3 exit code {p3.returncode}")

    pdf_out = SANDBOX_DIR / "test_main.pdf"
    record_result("PDF Generation in Isolated Sandbox", pdf_out.is_file() and pdf_out.stat().st_size > 10000, f"Generated PDF size: {pdf_out.stat().st_size if pdf_out.is_file() else 0} bytes")

    # Check for undefined references or citations in log
    log_content = (SANDBOX_DIR / "test_main.log").read_text(encoding="utf-8", errors="ignore")
    undefined_refs = [l for l in log_content.splitlines() if "undefined" in l.lower()]
    record_result("Zero Undefined Citations/Labels in Log", len(undefined_refs) == 0, f"Undefined occurrences: {undefined_refs}")


def test_3_makefile_targets_and_idempotency():
    print("\n--- Test 3: Makefile Targets & Idempotency ---")
    
    # 1. make help
    res_help = subprocess.run(["make", "help"], cwd=str(LATEX_DIR), capture_output=True, text=True)
    record_result("Makefile Target: make help", res_help.returncode == 0, "make help works")

    # 2. make validate
    res_val = subprocess.run(["make", "validate"], cwd=str(LATEX_DIR), capture_output=True, text=True)
    record_result("Makefile Target: make validate", res_val.returncode == 0, "make validate works")

    # 3. make all (default)
    res_all = subprocess.run(["make", "all"], cwd=str(LATEX_DIR), capture_output=True, text=True)
    record_result("Makefile Target: make all", res_all.returncode == 0, "make all works")

    # 4. make zip
    res_zip = subprocess.run(["make", "zip"], cwd=str(LATEX_DIR), capture_output=True, text=True)
    record_result("Makefile Target: make zip", res_zip.returncode == 0, "make zip works")

    # 5. make clean
    res_clean = subprocess.run(["make", "clean"], cwd=str(LATEX_DIR), capture_output=True, text=True)
    record_result("Makefile Target: make clean", res_clean.returncode == 0, "make clean works")

    # Check that clean didn't destroy source files
    cls_exists = (LATEX_DIR / "IEEEtran.cls").is_file()
    bib_exists = (LATEX_DIR / "references.bib").is_file()
    fig_exists = (LATEX_DIR / "figures").is_dir()
    record_result("make clean Preserves Essential Source Files", cls_exists and bib_exists and fig_exists, f"cls: {cls_exists}, bib: {bib_exists}, fig: {fig_exists}")

    # Re-run make zip after clean (idempotency check)
    res_zip2 = subprocess.run(["make", "zip"], cwd=str(LATEX_DIR), capture_output=True, text=True)
    record_result("make zip Idempotency After Clean", res_zip2.returncode == 0, "make zip succeeded after make clean")


def test_4_figure_assets_deep_inspection():
    print("\n--- Test 4: Figure Assets Deep Inspection ---")
    fig_dir = LATEX_DIR / "figures"
    fig_files = list(fig_dir.glob("*.png"))
    record_result("Figure Files Count", len(fig_files) == 18, f"Found {len(fig_files)} PNG files (9 original + 9 aliases)")

    PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
    corrupt_count = 0
    small_count = 0

    for f in fig_files:
        with open(f, "rb") as fp:
            header = fp.read(8)
            if header != PNG_MAGIC:
                corrupt_count += 1
        if f.stat().st_size < 5000:
            small_count += 1

    record_result("PNG Header Magic Number Verification", corrupt_count == 0, f"Corrupted files: {corrupt_count}")
    record_result("PNG File Size Sanity Check (>5KB)", small_count == 0, f"Suspiciously small files: {small_count}")


def test_5_validator_fault_injection():
    print("\n--- Test 5: Fault Injection & Validator Robustness ---")
    # We test in a temporary cloned environment
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Copy latex dir
        shutil.copytree(LATEX_DIR, tmp_path / "latex")
        t_latex = tmp_path / "latex"
        val_script = t_latex / "etc" / "scripts" / "validate_latex.py"

        # Baseline check
        r_base = subprocess.run([sys.executable, str(val_script)], cwd=str(t_latex), capture_output=True, text=True)
        record_result("Fault Injection Baseline", r_base.returncode == 0, "Baseline validator passes")

        # Fault 1: Delete references.bib
        (t_latex / "references.bib").unlink()
        r_f1 = subprocess.run([sys.executable, str(val_script)], cwd=str(t_latex), capture_output=True, text=True)
        record_result("Validator Catches Missing references.bib", r_f1.returncode != 0, f"Return code: {r_f1.returncode}")

        # Restore
        shutil.copyfile(LATEX_DIR / "references.bib", t_latex / "references.bib")

        # Fault 2: Delete a required figure
        (t_latex / "figures" / "1_reward_convergence.png").unlink()
        r_f2 = subprocess.run([sys.executable, str(val_script)], cwd=str(t_latex), capture_output=True, text=True)
        record_result("Validator Catches Missing Figure", r_f2.returncode != 0, f"Return code: {r_f2.returncode}")

        # Restore
        shutil.copyfile(LATEX_DIR / "figures" / "1_reward_convergence.png", t_latex / "figures" / "1_reward_convergence.png")

        # Fault 3: Inject duplicate citation key in bib
        bib_txt = (t_latex / "references.bib").read_text(encoding="utf-8")
        (t_latex / "references.bib").write_text(bib_txt + "\n@article{Arena2019Overview, title={Duplicate}}\n", encoding="utf-8")
        r_f3 = subprocess.run([sys.executable, str(val_script)], cwd=str(t_latex), capture_output=True, text=True)
        record_result("Validator Catches Duplicate Citation Key", r_f3.returncode != 0, f"Return code: {r_f3.returncode}")


def main():
    test_1_zip_archive_integrity()
    test_2_sandbox_latex_compilation()
    test_3_makefile_targets_and_idempotency()
    test_4_figure_assets_deep_inspection()
    test_5_validator_fault_injection()

    print("\n==================================================")
    total = len(TEST_RESULTS)
    passed = sum(1 for t in TEST_RESULTS if t["passed"])
    failed = total - passed
    print(f"SUMMARY: {passed}/{total} PASSED, {failed} FAILED")
    print("==================================================")


if __name__ == "__main__":
    main()
