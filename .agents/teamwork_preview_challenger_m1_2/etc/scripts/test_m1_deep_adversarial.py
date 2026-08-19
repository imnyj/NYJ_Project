#!/usr/bin/env python3
"""
Deep Adversarial Stress-Testing for Milestone 1 Infrastructure
"""

import os
import sys
import shutil
import zipfile
import subprocess
import hashlib
import re
from pathlib import Path
from PIL import Image

WORKSPACE_DIR = Path("/home/imnyj/Workspace/paper4/latex")
BIB_PATH = WORKSPACE_DIR / "references.bib"
FIG_DIR = WORKSPACE_DIR / "figures"
SANDBOX_DIR = Path("/home/imnyj/.agents/teamwork_preview_challenger_m1_2/etc/temp/adv_sandbox")

def test_zip_with_real_main_tex():
    print("\n--- Testing make zip behavior when main.tex is present ---")
    test_main = WORKSPACE_DIR / "temp_test_main.tex"
    # Note: We must adhere to Rule: review-only, do not modify workspace permanently
    # So we simulate this in sandbox
    if SANDBOX_DIR.exists():
        shutil.rmtree(SANDBOX_DIR)
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    
    # Copy Makefile, IEEEtran.cls, references.bib, figures, etc/scripts to sandbox
    shutil.copy(WORKSPACE_DIR / "Makefile", SANDBOX_DIR / "Makefile")
    shutil.copy(WORKSPACE_DIR / "IEEEtran.cls", SANDBOX_DIR / "IEEEtran.cls")
    shutil.copy(WORKSPACE_DIR / "references.bib", SANDBOX_DIR / "references.bib")
    shutil.copytree(WORKSPACE_DIR / "figures", SANDBOX_DIR / "figures")
    shutil.copytree(WORKSPACE_DIR / "etc", SANDBOX_DIR / "etc")

    # 1. Create main.tex in sandbox
    (SANDBOX_DIR / "main.tex").write_text("\\documentclass{IEEEtran}\n\\begin{document}\nHello World\n\\end{document}\n", encoding="utf-8")
    
    # 2. Run make zip in sandbox
    res = subprocess.run(["make", "zip"], cwd=SANDBOX_DIR, capture_output=True, text=True)
    print(f"Sandbox 'make zip' with main.tex exit code: {res.returncode}")
    print(f"Stdout:\n{res.stdout}")
    
    # 3. Inspect zip contents
    zip_path = SANDBOX_DIR / "paper4_latex_overleaf.zip"
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        print(f"Files in zip with main.tex: {len(names)} items")
        assert "main.tex" in names, "main.tex was not included in zip!"
        assert "IEEEtran.cls" in names, "IEEEtran.cls missing in zip!"
        assert "references.bib" in names, "references.bib missing in zip!"
        assert any(n.startswith("figures/") for n in names), "figures/ missing in zip!"
    print("[PASS] Overleaf zip packaging with main.tex verified successfully.")

def test_references_bib_special_chars_and_fields():
    print("\n--- Testing references.bib Special Characters & Strict BibTeX Formatting ---")
    content = BIB_PATH.read_text(encoding="utf-8")
    entries = [e for e in re.split(r"\n(?=@)", content) if e.strip()]
    
    special_char_warnings = []
    capital_protection_cases = []
    
    for i, entry in enumerate(entries):
        lines = entry.strip().split("\n")
        header = lines[0]
        m = re.match(r"@(\w+)\s*\{\s*([^,]+),", header)
        if not m:
            print(f"Warning: Could not parse header: {header}")
            continue
        entry_type = m.group(1)
        key = m.group(2).strip()
        
        # Check unescaped special chars in title or booktitle or journal
        for line in lines[1:]:
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip().lower()
                v = v.strip()
                
                # Check unescaped &
                if "&" in v and "\\&" not in v:
                    special_char_warnings.append(f"{key}: unescaped '&' in {k}: {v}")
                
                # Check unescaped % (unless comment)
                if "%" in v and "\\%" not in v:
                    special_char_warnings.append(f"{key}: unescaped '%' in {k}: {v}")
                
                # Check unescaped _ in text fields (excluding doi or url)
                if k not in ["doi", "url", "number"] and "_" in v and "\\_" not in v:
                    special_char_warnings.append(f"{key}: unescaped '_' in {k}: {v}")
                
                # Check capitalized acronyms protected by braces in title
                if k == "title":
                    acronyms = re.findall(r"\b[A-Z0-9]{2,}\b", v)
                    for acr in acronyms:
                        if f"{{{acr}}}" in v or v.startswith(f"{{{acr}"):
                            capital_protection_cases.append(f"{key}: protected acronym {{{acr}}}")
                        else:
                            # Check if surrounded by braces or standard word
                            pass

    print(f"Total entries inspected: {len(entries)}")
    print(f"Special character issues found: {len(special_char_warnings)}")
    for w in special_char_warnings:
        print(f"  - {w}")
    print(f"Acronym capital protections found: {len(capital_protection_cases)} instances")

def test_figures_dimensions_and_pil_integrity():
    print("\n--- Testing Figure Dimensions and PIL Rendering Integrity ---")
    fig_files = sorted(list(FIG_DIR.glob("*.png")))
    print(f"Found {len(fig_files)} PNG files in {FIG_DIR}")
    for f in fig_files:
        try:
            with Image.open(f) as img:
                w, h = img.size
                fmt = img.format
                mode = img.mode
                print(f"  [OK] {f.name:30s} : {w}x{h}, format={fmt}, mode={mode}, size={f.stat().st_size} bytes")
                assert w > 100 and h > 100, f"Image {f.name} resolution too small!"
                assert fmt == "PNG", f"Image {f.name} not PNG!"
        except Exception as e:
            print(f"  [FAIL] Could not open image {f.name}: {e}")
            sys.exit(1)

def test_make_check_alias_proposal():
    print("\n--- Testing Makefile Target Coverage ---")
    mf_content = (WORKSPACE_DIR / "Makefile").read_text(encoding="utf-8")
    targets = [line.split(":")[0].strip() for line in mf_content.split("\n") if ":" in line and not line.startswith("#") and not line.startswith("\t")]
    print("Declared Makefile targets:", targets)
    if "check" not in targets:
        print("Finding: 'check' target is missing. Recommended enhancement: add 'check: validate' alias to Makefile.")
    else:
        print("'check' target is present.")

if __name__ == "__main__":
    test_zip_with_real_main_tex()
    test_references_bib_special_chars_and_fields()
    test_figures_dimensions_and_pil_integrity()
    test_make_check_alias_proposal()
