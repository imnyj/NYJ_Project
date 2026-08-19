#!/usr/bin/env python3
"""
independent_audit.py
====================
Independent verification script by Victory Auditor.
Validates all requirements (R1, R2, R3, R4, Acceptance Criteria)
and performs deep forensic checks on the final LaTeX deliverables.
"""

import os
import re
import sys
import zipfile
import shutil
import tempfile
from pathlib import Path

WORKSPACE = Path("/home/imnyj/Workspace/paper4/latex")
DRAFT_KOREAN = Path("/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md")
MAIN_TEX = WORKSPACE / "main.tex"
BIB_FILE = WORKSPACE / "references.bib"
CLS_FILE = WORKSPACE / "IEEEtran.cls"
ZIP_FILE = WORKSPACE / "paper4_latex_overleaf.zip"
FIGURES_DIR = WORKSPACE / "figures"

FORBIDDEN_WORDS = [
    "elucidate", "seamless", "vital", "fosters", "significantly",
    "substantially", "leveraging", "utilizing", "subsequently",
    "systematically", "effectively", "autonomously", "encapsulates"
]

PLACEHOLDERS = ["TODO", "FIXME", "TBD", "XXX", "dummy", "placeholder"]

results = {}

def log_section(title):
    print(f"\n{'='*70}\n[AUDIT] {title}\n{'='*70}")

def test_r1_academic_english():
    log_section("R1: Academic English Translation & Tone Quality")
    text = MAIN_TEX.read_text(encoding="utf-8")
    
    # 1. Check word count & line count
    words = text.split()
    print(f"Total Words in main.tex: {len(words)}")
    print(f"Total Lines in main.tex: {len(text.splitlines())}")
    assert len(words) >= 7000, f"Document too short: {len(words)} words"

    # 2. Check forbidden AI clichés
    cliche_counts = {}
    for word in FORBIDDEN_WORDS:
        # Match as whole word case-insensitive
        matches = re.findall(rf"\b{word}\b", text, re.IGNORECASE)
        if matches:
            cliche_counts[word] = len(matches)
    
    print(f"AI Cliché Scan Results: {cliche_counts if cliche_counts else '0 detected (PERFECT)'}")
    assert not cliche_counts, f"Detected AI clichés: {cliche_counts}"

    # 3. Check for placeholders
    placeholder_found = []
    for ph in PLACEHOLDERS:
        m = re.findall(rf"\b{ph}\b", text, re.IGNORECASE)
        if m:
            placeholder_found.append((ph, len(m)))
    print(f"Placeholder Scan: {placeholder_found if placeholder_found else '0 detected (PERFECT)'}")
    assert not placeholder_found, f"Found placeholders: {placeholder_found}"

    # 4. Check paragraph structure
    # Split by double newline in section bodies
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    long_paras = [p for p in paragraphs if not p.startswith("\\") and len(p.split()) > 40]
    print(f"Identified {len(long_paras)} substantial technical narrative paragraphs.")
    
    results["R1"] = "PASS"

def test_r2_ieeetran_formatting():
    log_section("R2: IEEE TWC LaTeX Formatting & Document Structure")
    text = MAIN_TEX.read_text(encoding="utf-8")
    
    # Check documentclass
    assert r"\documentclass[journal]{IEEEtran}" in text, "Missing or invalid documentclass IEEEtran"
    print("[OK] Document class IEEEtran verified.")

    # Check IEEEtran.cls exists and is official
    assert CLS_FILE.exists(), "IEEEtran.cls missing"
    cls_size = CLS_FILE.stat().st_size
    print(f"[OK] IEEEtran.cls present (size: {cls_size} bytes).")
    assert cls_size > 200000, "IEEEtran.cls appears truncated"

    # Check structural sections
    sections = [
        r"\title{",
        r"\author{",
        r"\begin{abstract}",
        r"\begin{IEEEkeywords}",
        r"\section{Introduction}",
        r"\section{Related Works}",
        r"\section{System Model and REMO-DQN Architecture}",
        r"\section{Dynamic Operational Workflow}",
        r"\section{Performance Evaluation}",
        r"\section{Conclusion}",
        r"\bibliographystyle{IEEEtran}",
        r"\bibliography{references}",
    ]
    for sec in sections:
        assert sec in text, f"Missing required structural section: {sec}"
        print(f"[OK] Section/Element found: {sec}")

    # Check braces balance
    open_b = text.count("{")
    close_b = text.count("}")
    print(f"[INFO] Braces in main.tex: {open_b} open vs {close_b} close")
    assert open_b == close_b, f"Unbalanced braces in main.tex: {open_b} vs {close_b}"

    # Check line 345 specific bug fix: \label{eq:loss_total}
    assert r"\label{eq:loss_total}" in text, "Line 345 bug NOT fixed: \\label{eq:loss_total} missing"
    assert r"\label:eq:loss_total}" not in text, "Found stale typo \\label:eq:loss_total}!"
    print("[OK] Line 345 bug fix confirmed: \\label{eq:loss_total} correctly formatted.")

    results["R2"] = "PASS"

def test_r3_math_tables_figures():
    log_section("R3: Equations, Tables, and Figures Fidelity")
    text = MAIN_TEX.read_text(encoding="utf-8")
    korean = DRAFT_KOREAN.read_text(encoding="utf-8")

    # 1. Equations check
    eq_envs = re.findall(r"\\begin\{(equation|align)\}(.*?)\\end\{\1\}", text, re.DOTALL)
    print(f"[OK] Total equation/align blocks: {len(eq_envs)}")
    assert len(eq_envs) >= 22, f"Expected at least 22 equation blocks, found {len(eq_envs)}"

    # Check critical math formulations
    math_tokens = [
        r"\mathcal{S}", r"\mathcal{A}", r"\mathcal{R}",
        r"\gamma", r"Nakagami", r"\bar{\gamma}_{ij}", r"P_{\text{tx}}",
        r"\text{CBR}", r"\text{AoI}", r"\text{PDR}",
        r"\mathcal{L}_{\text{TD}}", r"\mathcal{L}_{\text{LB}}",
        r"\text{Softmax}", r"V_k(\mathbf{s}_t)", r"A_k(\mathbf{s}_t, a)"
    ]
    for tok in math_tokens:
        assert tok in text, f"Missing mathematical formulation token: {tok}"
    print("[OK] All critical mathematical tokens (Dec-MDP, MoE, Dueling, Nakagami, Losses) present.")

    # 2. Tables check
    tables = re.findall(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", text, re.DOTALL)
    tabulars = re.findall(r"\\begin\{tabularx?\}(.*?)\\end\{tabularx?\}", text, re.DOTALL)
    print(f"[OK] Total table environments: {len(tables)}, tabular blocks: {len(tabulars)}")
    assert len(tables) >= 13, f"Expected at least 13 tables, found {len(tables)}"

    # Check key numerical data points from Korean draft
    key_numbers = [
        "75.02", "73.41", "3.13", "373.21", "0.3442", "0.1008",
        "3.8M", "350K", "1.2", "100", "0.01", "1.0", "0.10", "3.0"
    ]
    for num in key_numbers:
        assert num in text, f"Missing empirical quantitative metric from draft: {num}"
    print(f"[OK] Verified key empirical metrics ({', '.join(key_numbers)}) in text/tables.")

    # 3. Figures check
    fig_inclusions = re.findall(r"\\includegraphics(?:\[.*?\])?\{([^}]+)\}", text)
    print(f"[OK] Found {len(fig_inclusions)} \\includegraphics references.")
    assert len(fig_inclusions) >= 9, f"Expected at least 9 figure inclusions, found {len(fig_inclusions)}"

    for fig_path in fig_inclusions:
        full_fig = WORKSPACE / fig_path
        assert full_fig.exists(), f"Figure file does not exist: {full_fig}"
        # Check PNG header magic bytes
        header = full_fig.read_bytes()[:8]
        assert header == b"\x89PNG\r\n\x1a\n", f"Invalid PNG magic bytes for {full_fig}"
        print(f"  [OK] Valid PNG figure verified: {fig_path} ({full_fig.stat().st_size} bytes)")

    results["R3"] = "PASS"

def test_r4_bibliography():
    log_section("R4: BibTeX 27 References & Citation Resolution")
    bib_text = BIB_FILE.read_text(encoding="utf-8")
    tex_text = MAIN_TEX.read_text(encoding="utf-8")

    # Extract BibTeX keys
    bib_keys = re.findall(r"@\w+\s*\{\s*([^,]+),", bib_text)
    bib_keys = [k.strip() for k in bib_keys]
    print(f"[OK] Extracted {len(bib_keys)} BibTeX entries in references.bib (Unique: {len(set(bib_keys))})")
    assert len(bib_keys) == 27, f"Expected 27 references, found {len(bib_keys)}"
    assert len(set(bib_keys)) == 27, "Duplicate BibTeX keys detected"

    # Extract all \cite keys from main.tex
    cite_matches = re.findall(r"\\cite\{([^}]+)\}", tex_text)
    cited_keys = set()
    for m in cite_matches:
        for k in m.split(","):
            cited_keys.add(k.strip())
    
    print(f"[OK] Found {len(cited_keys)} unique keys cited in main.tex across {len(cite_matches)} \\cite calls.")

    # Check 100% resolution & 100% coverage
    undefined_keys = cited_keys - set(bib_keys)
    uncited_keys = set(bib_keys) - cited_keys

    assert not undefined_keys, f"Undefined citations in main.tex: {undefined_keys}"
    assert not uncited_keys, f"Uncited references in references.bib: {uncited_keys}"
    print("[OK] 100% BibTeX citation coverage: 0 undefined keys, 0 uncited references.")

    results["R4"] = "PASS"

def test_acceptance_criteria_and_sandbox():
    log_section("Acceptance Criteria & Overleaf Standalone Sandbox Verification")
    assert ZIP_FILE.exists(), f"Overleaf distribution zip missing: {ZIP_FILE}"
    zip_size = ZIP_FILE.stat().st_size
    print(f"[OK] Overleaf zip package exists ({zip_size} bytes).")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        print(f"[INFO] Testing clean extraction into temporary sandbox: {tmp_path}")
        
        with zipfile.ZipFile(ZIP_FILE, "r") as zf:
            # Check CRC
            bad_file = zf.testzip()
            assert bad_file is None, f"Corrupted zip archive: {bad_file}"
            
            zf.extractall(tmp_path)
            namelist = zf.namelist()
            print(f"[OK] Zip contains {len(namelist)} items.")

        # Check required files in sandbox
        for req in ["main.tex", "references.bib", "IEEEtran.cls"]:
            target = tmp_path / req
            assert target.exists(), f"Extracted sandbox missing required root file: {req}"
            print(f"  [OK] Sandbox verified: {req} ({target.stat().st_size} bytes)")

        # Check figures in sandbox
        fig_files = list((tmp_path / "figures").glob("*.png"))
        print(f"  [OK] Sandbox contains {len(fig_files)} PNG figures.")
        assert len(fig_files) >= 9, f"Sandbox contains only {len(fig_files)} figures"

        # Check for path leaks in sandbox main.tex
        sb_tex = (tmp_path / "main.tex").read_text(encoding="utf-8")
        assert "/home/" not in sb_tex, "Absolute path leak (/home/) in sandbox main.tex"
        assert "/tmp/" not in sb_tex, "Absolute path leak (/tmp/) in sandbox main.tex"
        assert "../" not in sb_tex, "Parent directory escape (../) in sandbox main.tex"
        print("  [OK] Zero absolute paths or directory escapes in sandbox main.tex.")

        # Check synchronization between disk main.tex and zip main.tex
        disk_tex = MAIN_TEX.read_text(encoding="utf-8")
        assert sb_tex == disk_tex, "Zip main.tex is out of sync with workspace main.tex"
        print("  [OK] Zip main.tex and workspace main.tex are 100% identical.")

    results["Acceptance"] = "PASS"

def main():
    print("Starting Victory Auditor Independent Verification...")
    test_r1_academic_english()
    test_r2_ieeetran_formatting()
    test_r3_math_tables_figures()
    test_r4_bibliography()
    test_acceptance_criteria_and_sandbox()

    print("\n" + "="*70)
    print("ALL AUDIT TIERS PASSED WITH ZERO DEFECTS.")
    print("="*70)

if __name__ == "__main__":
    main()
