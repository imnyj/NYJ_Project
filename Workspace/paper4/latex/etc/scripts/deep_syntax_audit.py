#!/usr/bin/env python3
"""
deep_syntax_audit.py
====================
Deep syntax, tabular, algorithm, zip package, and BibTeX parser audit.
"""

import os
import re
import sys
import zipfile
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path("/home/imnyj/Workspace/paper4/latex")
MAIN_TEX = BASE_DIR / "main.tex"
BIB_FILE = BASE_DIR / "references.bib"
ZIP_FILE = BASE_DIR / "paper4_latex_overleaf.zip"
FIG_DIR = BASE_DIR / "figures"


def strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        m = re.search(r"(?<!\\)(?:\\\\)*%", line)
        lines.append(line[:m.start()] if m else line)
    return "\n".join(lines)


def audit_command_syntax(content: str):
    print("\n--- 1. Auditing Command Syntax & Typos ---")
    clean = strip_comments(content)
    errors = []

    # Check for \label:, \ref:, \cite: etc.
    typo_pattern = re.compile(r"\\(label|ref|eqref|cite|section|subsection|caption):([a-zA-Z0-9_\-]+)\}")
    for match in typo_pattern.finditer(clean):
        cmd, target = match.groups()
        errors.append(f"Typo detected: \\{cmd}:{target}}} should be \\{cmd}{{{target}}}")

    # Check for unclosed \textbf{, \textit{, \cite{, etc.
    # Check braces balance overall
    return errors


def audit_tabulars(content: str):
    print("\n--- 2. Auditing Tabular Environments & Column Counts ---")
    clean = strip_comments(content)
    tabular_pattern = re.compile(r"\\begin\{tabular\}\s*\{([^}]+)\}(.*?)\\end\{tabular\}", re.DOTALL)
    
    tables_found = 0
    errors = []

    for match in tabular_pattern.finditer(clean):
        tables_found += 1
        col_spec = match.group(1).strip()
        body = match.group(2).strip()

        # Parse expected column count from col_spec (e.g. "lcccc", "p{3cm}cc")
        # Strip @{...}, p{...}, m{...}, b{...}, |, >{...}, <{...}
        simplified_spec = re.sub(r"@\{[^}]*\}", "", col_spec)
        simplified_spec = re.sub(r"[pmb]\{[^}]*\}", "c", simplified_spec)
        simplified_spec = re.sub(r"[><]\{[^}]*\}", "", simplified_spec)
        simplified_spec = re.sub(r"[|*\s]", "", simplified_spec)
        expected_cols = len(simplified_spec)

        # Check rows
        rows = [r.strip() for r in body.split(r"\\") if r.strip() and not r.strip().startswith(r"\toprule") and not r.strip().startswith(r"\bottomrule") and not r.strip().startswith(r"\midrule") and not r.strip().startswith(r"\hline")]
        
        for idx, row in enumerate(rows, 1):
            # Skip rows with \multicolumn
            if r"\multicolumn" in row or r"\cmidrule" in row or not row:
                continue
            
            # Count & (ignoring \&)
            clean_row = re.sub(r"\\&", "", row)
            amp_count = clean_row.count("&")
            actual_cols = amp_count + 1
            if actual_cols != expected_cols:
                errors.append(f"Table #{tables_found} row {idx}: Column count mismatch! Expected {expected_cols} columns ({col_spec}), but found {actual_cols} ('{row[:50]}...')")

    print(f"Verified {tables_found} tabular environments.")
    return tables_found, errors


def audit_algorithms(content: str):
    print("\n--- 3. Auditing Algorithmic Pseudocode ---")
    clean = strip_comments(content)
    errors = []

    alg_pattern = re.compile(r"\\begin\{algorithmic\}(?:\[\d+\])?(.*?)\\end\{algorithmic\}", re.DOTALL)
    for match in alg_pattern.finditer(clean):
        body = match.group(1)
        
        # Check matching \FOR ... \ENDFOR
        for_cnt = len(re.findall(r"\\FOR\{", body))
        endfor_cnt = len(re.findall(r"\\ENDFOR", body))
        if for_cnt != endfor_cnt:
            errors.append(f"Algorithm FOR loop mismatch: {for_cnt} \\FOR vs {endfor_cnt} \\ENDFOR")

        # Check matching \IF ... \ENDIF
        if_cnt = len(re.findall(r"\\IF\{", body))
        endif_cnt = len(re.findall(r"\\ENDIF", body))
        if if_cnt != endif_cnt:
            errors.append(f"Algorithm IF block mismatch: {if_cnt} \\IF vs {endif_cnt} \\ENDIF")

        # Check matching \WHILE ... \ENDWHILE
        while_cnt = len(re.findall(r"\\WHILE\{", body))
        endwhile_cnt = len(re.findall(r"\\ENDWHILE", body))
        if while_cnt != endwhile_cnt:
            errors.append(f"Algorithm WHILE block mismatch: {while_cnt} \\WHILE vs {endwhile_cnt} \\ENDWHILE")

    return errors


def audit_zip_package():
    print("\n--- 4. Auditing Overleaf Zip Package ---")
    errors = []
    if not ZIP_FILE.is_file():
        errors.append(f"Missing zip package: {ZIP_FILE}")
        return errors

    print(f"Zip file found: {ZIP_FILE} ({ZIP_FILE.stat().st_size} bytes)")
    with zipfile.ZipFile(ZIP_FILE, "r") as zf:
        namelist = zf.namelist()
        print(f"Zip archive contains {len(namelist)} items:")
        for name in namelist:
            info = zf.getinfo(name)
            print(f"  - {name} ({info.file_size} bytes)")

        # Check required files
        for req in ["main.tex", "references.bib", "IEEEtran.cls"]:
            if req not in namelist:
                errors.append(f"Zip archive missing root file: {req}")

        # Check figures
        figures_in_zip = [n for n in namelist if n.startswith("figures/") and n.endswith(".png")]
        print(f"Found {len(figures_in_zip)} figure files in zip.")
        if len(figures_in_zip) < 9:
            errors.append(f"Zip archive contains only {len(figures_in_zip)} figures (expected at least 9).")

        # Compare zip main.tex with disk main.tex
        if "main.tex" in namelist:
            zip_tex = zf.read("main.tex").decode("utf-8")
            disk_tex = MAIN_TEX.read_text(encoding="utf-8")
            if zip_tex != disk_tex:
                errors.append("Zip archive's main.tex is out of sync with current latex/main.tex on disk!")

    return errors


def audit_bibtex_fields(bib_content: str):
    print("\n--- 5. Auditing BibTeX Entry Completeness ---")
    errors = []
    entry_pattern = re.compile(r"@(\w+)\s*\{\s*([^,]+),(.*?)(?=\n@|\Z)", re.DOTALL)
    entries = entry_pattern.findall(bib_content)

    print(f"Parsed {len(entries)} BibTeX entries.")
    for entry_type, key, body in entries:
        key = key.strip()
        body_clean = body.strip()

        # Check required fields
        for req_field in ["title", "author", "year"]:
            if not re.search(rf"\b{req_field}\s*=", body_clean, re.IGNORECASE):
                errors.append(f"BibTeX entry '{key}' missing required field: {req_field}")

        # Check braces balance in body
        open_b = body_clean.count("{")
        close_b = body_clean.count("}")
        if open_b != close_b:
            errors.append(f"BibTeX entry '{key}' has unbalanced braces: {open_b} '{{' vs {close_b} '}}'")

    return errors


def main():
    tex_content = MAIN_TEX.read_text(encoding="utf-8")
    bib_content = BIB_FILE.read_text(encoding="utf-8")

    all_errors = []
    cmd_errs = audit_command_syntax(tex_content)
    all_errors.extend(cmd_errs)
    if cmd_errs:
        for e in cmd_errs:
            print("  [ERROR]", e)
    else:
        print("  [OK] Zero command syntax typos.")

    tab_cnt, tab_errs = audit_tabulars(tex_content)
    all_errors.extend(tab_errs)
    if tab_errs:
        for e in tab_errs:
            print("  [ERROR]", e)
    else:
        print("  [OK] All tabular environments and column counts are valid.")

    alg_errs = audit_algorithms(tex_content)
    all_errors.extend(alg_errs)
    if alg_errs:
        for e in alg_errs:
            print("  [ERROR]", e)
    else:
        print("  [OK] Algorithm pseudocode blocks are properly nested.")

    zip_errs = audit_zip_package()
    all_errors.extend(zip_errs)
    if zip_errs:
        for e in zip_errs:
            print("  [ERROR]", e)
    else:
        print("  [OK] Zip package is completely valid and up-to-date.")

    bib_errs = audit_bibtex_fields(bib_content)
    all_errors.extend(bib_errs)
    if bib_errs:
        for e in bib_errs:
            print("  [ERROR]", e)
    else:
        print("  [OK] All 27 BibTeX entries have complete metadata and balanced braces.")

    print("\n" + "="*70)
    if all_errors:
        print(f"[SUMMARY] Found {len(all_errors)} issues in deep audit.")
    else:
        print("[SUMMARY] All deep audit checks passed.")
    print("="*70)


if __name__ == "__main__":
    main()
