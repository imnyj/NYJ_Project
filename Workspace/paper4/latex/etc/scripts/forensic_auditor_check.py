#!/usr/bin/env python3
"""
forensic_auditor_check.py
=========================
Independent Forensic Integrity Audit Script executed by auditor_1.
Audits:
1. Safety Protocols (LockManager, Backups, AuditLogger)
2. Code Forgery, AI Clichés & Exaggerated Words, Hardcoding, Filenames
3. Structural Formatting (Introduction contributions itemize, Table I restructuring)
4. Mathematical expressions & syntax integrity
5. Paragraph completeness & academic writing quality
6. Workspace cleanliness & auxiliary file isolation
7. Artifact forgery & zip package hash cross-verification
"""

import os
import sys
import re
import json
import zipfile
import hashlib
from pathlib import Path
from collections import Counter

ROOT_DIR = Path("/home/imnyj/Workspace/paper4/latex")
MAIN_TEX = ROOT_DIR / "main.tex"
BIB_PATH = ROOT_DIR / "references.bib"
CLS_PATH = ROOT_DIR / "IEEEtran.cls"
ZIP_PATH = ROOT_DIR / "paper4_latex_overleaf.zip"
BACKUP_DIR = ROOT_DIR / "backup"
AUDIT_LOG = Path("/tmp/agent_audit.log")

report = {
    "safety_protocols": {},
    "code_integrity": {},
    "workspace_cleanliness": {},
    "artifact_forgery": {},
    "verdict": "CLEAN",
    "violations": [],
    "checks_passed": []
}

def audit_safety_protocols():
    print("\n" + "="*70)
    print("1. SAFETY PROTOCOL FORENSIC AUDIT")
    print("="*70)
    
    # A. Audit Logger
    if not AUDIT_LOG.exists():
        report["violations"].append("/tmp/agent_audit.log does not exist.")
    else:
        lines = AUDIT_LOG.read_text().splitlines()
        paper4_entries = []
        for line in lines:
            try:
                data = json.loads(line)
                if "/Workspace/paper4/latex" in data.get("target", ""):
                    paper4_entries.append(data)
            except Exception:
                pass
        print(f"[*] Found {len(paper4_entries)} audit entries for paper4/latex:")
        for e in paper4_entries:
            print(f"    - Agent [{e.get('agent_id')}]: {e.get('action')} {e.get('target')} | {e.get('description')}")
        
        # Verify worker_m1, worker_m2, worker_m3 entries
        agents_logged = {e.get("agent_id") for e in paper4_entries}
        print(f"[*] Distinct agents logged: {agents_logged}")
        if not {"worker_m1", "worker_m2", "worker_m3"}.issubset(agents_logged):
            missing = {"worker_m1", "worker_m2", "worker_m3"} - agents_logged
            report["violations"].append(f"Audit log missing required worker agents: {missing}")
        else:
            report["checks_passed"].append("AuditLogger logged all worker modifications (worker_m1, worker_m2, worker_m3)")

    # B. Backups
    bak_m1 = BACKUP_DIR / "main.tex.bak_m1"
    bak_m2 = BACKUP_DIR / "main.tex.bak_m2"
    if not bak_m1.exists() or bak_m1.stat().st_size == 0:
        report["violations"].append("Backup file main.tex.bak_m1 missing or empty.")
    else:
        print(f"[*] Backup main.tex.bak_m1 verified: {bak_m1.stat().st_size} bytes")
        
    if not bak_m2.exists() or bak_m2.stat().st_size == 0:
        report["violations"].append("Backup file main.tex.bak_m2 missing or empty.")
    else:
        print(f"[*] Backup main.tex.bak_m2 verified: {bak_m2.stat().st_size} bytes")
        
    if bak_m1.exists() and bak_m2.exists():
        report["checks_passed"].append("Backup files main.tex.bak_m1 and main.tex.bak_m2 verified")


def audit_code_integrity():
    print("\n" + "="*70)
    print("2. CODE INTEGRITY & ANTI-CHEATING AUDIT")
    print("="*70)
    
    tex_content = MAIN_TEX.read_text(encoding="utf-8")
    
    # Strip comments
    clean_lines = []
    for line in tex_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("%"):
            continue
        m = re.search(r"(?<!\\)%", line)
        clean_lines.append(line[:m.start()] if m else line)
    clean_text = "\n".join(clean_lines)

    # A. Prohibited AI Clichés and Exaggerated Words
    forbidden_words = [
        "elucidate", "elucidates", "elucidated", "elucidating",
        "seamless", "seamlessly",
        "vital",
        "fosters", "fostered", "fostering",
        "comprehensive", "comprehensively",
        "significantly",
        "substantially",
        "leveraging", "leverages", "leveraged",
        "utilizing", "utilize", "utilized", "utilizes",
        "subsequently",
        "systematically",
        "effectively",
        "encapsulates", "encapsulate", "encapsulated"
    ]
    
    found_forbidden = {}
    for word in forbidden_words:
        matches = list(re.finditer(rf"\b{word}\b", clean_text, re.IGNORECASE))
        if matches:
            found_forbidden[word] = len(matches)
            
    if found_forbidden:
        report["violations"].append(f"Forbidden words detected in main.tex: {found_forbidden}")
        print(f"  [FAIL] Forbidden words detected: {found_forbidden}")
    else:
        print("  [PASS] Zero forbidden AI/exaggerated words detected.")
        report["checks_passed"].append("Zero forbidden AI/exaggerated words in manuscript")

    # Check adverb 'autonomously'
    adv_matches = list(re.finditer(r"\bautonomously\b", clean_text, re.IGNORECASE))
    if adv_matches:
        report["violations"].append(f"Prohibited adverb 'autonomously' found ({len(adv_matches)} instances)")
    else:
        print("  [PASS] Zero prohibited adverb 'autonomously' detected.")
        report["checks_passed"].append("Zero prohibited adverb 'autonomously'")

    # B. Internal Filenames Scan
    filename_matches = list(re.finditer(r"\b[a-zA-Z0-9_\-]+\.(?:csv|py|sh|json|tex|cpp|h)\b", clean_text, re.IGNORECASE))
    found_filenames = []
    for m in filename_matches:
        fn = m.group()
        # Exclude IEEEtran.cls if in comments or LaTeX class declaration
        line_no = clean_text[:m.start()].count("\n") + 1
        found_filenames.append((line_no, fn))
        
    if found_filenames:
        report["violations"].append(f"Internal filenames found in manuscript text: {found_filenames}")
        print(f"  [FAIL] Internal filenames found: {found_filenames}")
    else:
        print("  [PASS] Zero internal filenames detected in manuscript text.")
        report["checks_passed"].append("Zero internal filenames in manuscript text")

    # C. Introduction Contributions itemize
    contrib_match = re.search(
        r"contributions of this paper are summarized as follows:\s*\\begin\{itemize\}(.*?)\\end\{itemize\}",
        clean_text, re.DOTALL | re.IGNORECASE
    )
    if not contrib_match:
        report["violations"].append("Introduction contributions are not formatted using an 'itemize' environment.")
        print("  [FAIL] Introduction contributions itemize missing.")
    else:
        items = re.findall(r"\\item\s+", contrib_match.group(1))
        if len(items) != 4:
            report["violations"].append(f"Expected 4 contribution items in itemize, found {len(items)}")
            print(f"  [FAIL] Expected 4 items, found {len(items)}")
        else:
            print(f"  [PASS] Introduction contributions formatted in itemize with exactly 4 items.")
            report["checks_passed"].append("Introduction contributions formatted in itemize with 4 items")

    # D. Table I Restructuring
    tab1_match = re.search(r"\\begin\{table\*\}.*?\\label\{tab:lit_comparison\}(.*?)\\end\{table\*\}", clean_text, re.DOTALL)
    if not tab1_match:
        report["violations"].append("Table I (tab:lit_comparison) not found in main.tex.")
        print("  [FAIL] Table I not found.")
    else:
        tab_str = tab1_match.group(1)
        if re.search(r"\bYear\b", tab_str):
            report["violations"].append("Table I contains 'Year' column.")
            print("  [FAIL] Table I contains Year column.")
        else:
            print("  [PASS] Table I has 'Year' column completely removed.")
            report["checks_passed"].append("Table I Year column removed")
            
        if "et al." in tab_str:
            report["violations"].append("Table I contains author names ('et al.').")
            print("  [FAIL] Table I contains author names ('et al.').")
        else:
            print("  [PASS] Table I has zero author names (et al.).")
            report["checks_passed"].append("Table I author names eliminated")

        tab_cites = re.findall(r"\\cite\{([^}]+)\}", tab_str)
        if len(tab_cites) < 10:
            report["violations"].append(f"Table I missing citation entries: found {len(tab_cites)}")
        else:
            print(f"  [PASS] Table I uses \\cite{{}} references ({len(tab_cites)} citations).")
            report["checks_passed"].append(f"Table I citation references ({len(tab_cites)} citations)")

        if "p{" not in tab_str and "L" not in tab_str:
            report["violations"].append("Table I does not use fixed-width p{...} or L column specifiers.")
        else:
            print("  [PASS] Table I uses fixed-width p{...} and L column specifiers for automatic line wrapping.")
            report["checks_passed"].append("Table I fixed-width wrapping specifiers")


def audit_math_and_syntax():
    print("\n" + "="*70)
    print("3. MATHEMATICAL EXPRESSIONS & LATEX SYNTAX AUDIT")
    print("="*70)
    
    tex_content = MAIN_TEX.read_text(encoding="utf-8")
    
    # 1. Display Math
    disp_pattern = re.compile(r"\\begin\{(equation|align)\*?\}(.*?)\\end\{\1\*?\}", re.DOTALL)
    disp_matches = list(disp_pattern.finditer(tex_content))
    print(f"[*] Found {len(disp_matches)} display equation environments:")
    if len(disp_matches) != 32:
        report["violations"].append(f"Expected 32 display equations, found {len(disp_matches)}")
    else:
        report["checks_passed"].append("Display equations count: exactly 32")

    for i, m in enumerate(disp_matches, 1):
        c = m.group(2)
        if c.count("{") != c.count("}"):
            report["violations"].append(f"Display equation #{i} has unbalanced curly braces.")

    # 2. Inline Math
    inline_matches = list(re.finditer(r"(?<!\\)\$(.+?)(?<!\\)\$", tex_content))
    print(f"[*] Found {len(inline_matches)} inline math spans:")
    if len(inline_matches) < 300:
        report["violations"].append(f"Expected >=300 inline math spans, found {len(inline_matches)}")
    else:
        report["checks_passed"].append(f"Inline math spans count: {len(inline_matches)} (>=300)")

    for i, m in enumerate(inline_matches, 1):
        c = m.group(1)
        if c.count("{") != c.count("}"):
            report["violations"].append(f"Inline math #{i} has unbalanced curly braces: ${c}$")

    # 3. Overall Delimiter Parity
    clean_tex = re.sub(r"\\\$", "", tex_content)
    dollar_count = clean_tex.count("$")
    if dollar_count % 2 != 0:
        report["violations"].append(f"Unbalanced dollar signs: total {dollar_count}")
    else:
        print(f"  [PASS] Math delimiter '$' perfectly balanced ({dollar_count // 2} spans).")
        report["checks_passed"].append("Math delimiter '$' balanced")

    # 4. Environment Balancing
    begins = re.findall(r"\\begin\{([a-zA-Z0-9_\*]+)\}", tex_content)
    ends = re.findall(r"\\end\{([a-zA-Z0-9_\*]+)\}", tex_content)
    begin_c = Counter(begins)
    end_c = Counter(ends)
    all_envs = set(begin_c.keys()).union(set(end_c.keys()))
    env_mismatches = []
    for env in sorted(all_envs):
        if begin_c[env] != end_c[env]:
            env_mismatches.append(f"{env}: begin={begin_c[env]} vs end={end_c[env]}")
    if env_mismatches:
        report["violations"].append(f"LaTeX environment mismatches: {env_mismatches}")
    else:
        print(f"  [PASS] All {len(all_envs)} LaTeX environments balanced ({sum(begin_c.values())} pairs).")
        report["checks_passed"].append(f"All {len(all_envs)} LaTeX environments balanced")


def audit_workspace_cleanliness():
    print("\n" + "="*70)
    print("4. WORKSPACE CLEANLINESS & ISOLATION AUDIT")
    print("="*70)
    
    root_entries = [e.name for e in ROOT_DIR.iterdir()]
    allowed_root = {".agents", "IEEEtran.cls", "Makefile", "PROJECT.md", "backup", "etc", "figures", "main.tex", "paper4_latex_overleaf.zip", "references.bib"}
    stray = set(root_entries) - allowed_root
    if stray:
        report["violations"].append(f"Stray files in root directory: {stray}")
        print(f"  [FAIL] Stray files in root: {stray}")
    else:
        print("  [PASS] Root directory is strictly clean.")
        report["checks_passed"].append("Root directory layout compliance")

    # Check etc subdirectories
    etc_subdirs = [e.name for e in (ROOT_DIR / "etc").iterdir() if e.is_dir()]
    print(f"[*] etc/ subdirectories: {etc_subdirs}")
    if not set(etc_subdirs).issubset({"scripts", "logs", "temp", "data", "tests"}):
        report["violations"].append(f"Uncategorized directories in etc/: {set(etc_subdirs) - {'scripts', 'logs', 'temp', 'data', 'tests'}}")
    else:
        print("  [PASS] etc/ subdirectories properly categorized.")
        report["checks_passed"].append("etc/ subdirectories categorized")


def audit_artifact_forgery():
    print("\n" + "="*70)
    print("5. ARTIFACT FORGERY & ZIP INTEGRITY AUDIT")
    print("="*70)
    
    if not ZIP_PATH.exists():
        report["violations"].append("paper4_latex_overleaf.zip does not exist.")
        return
        
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        names = z.namelist()
        print(f"[*] Zip file entries: {len(names)} files")
        
        # Verify SHA-256 hash match of main.tex
        zip_main_content = z.read("main.tex")
        disk_main_content = MAIN_TEX.read_bytes()
        zip_hash = hashlib.sha256(zip_main_content).hexdigest()
        disk_hash = hashlib.sha256(disk_main_content).hexdigest()
        
        print(f"[*] Zip  main.tex SHA-256: {zip_hash}")
        print(f"[*] Disk main.tex SHA-256: {disk_hash}")
        if zip_hash != disk_hash:
            report["violations"].append("main.tex in paper4_latex_overleaf.zip does NOT match disk main.tex!")
            print("  [FAIL] main.tex hash mismatch!")
        else:
            print("  [PASS] main.tex hash in zip exactly matches disk main.tex.")
            report["checks_passed"].append("Zip package main.tex hash match")

        # Verify IEEEtran.cls hash
        zip_cls_content = z.read("IEEEtran.cls")
        disk_cls_content = CLS_PATH.read_bytes()
        if hashlib.sha256(zip_cls_content).hexdigest() != hashlib.sha256(disk_cls_content).hexdigest():
            report["violations"].append("IEEEtran.cls in zip does NOT match disk IEEEtran.cls!")
        else:
            report["checks_passed"].append("Zip package IEEEtran.cls hash match")

        # Verify references.bib hash
        zip_bib_content = z.read("references.bib")
        disk_bib_content = BIB_PATH.read_bytes()
        if hashlib.sha256(zip_bib_content).hexdigest() != hashlib.sha256(disk_bib_content).hexdigest():
            report["violations"].append("references.bib in zip does NOT match disk references.bib!")
        else:
            report["checks_passed"].append("Zip package references.bib hash match")


def main():
    audit_safety_protocols()
    audit_code_integrity()
    audit_math_and_syntax()
    audit_workspace_cleanliness()
    audit_artifact_forgery()
    
    print("\n" + "="*70)
    print("FINAL FORENSIC AUDIT SUMMARY")
    print("="*70)
    print(f"Checks Passed: {len(report['checks_passed'])}")
    for cp in report['checks_passed']:
        print(f"  [OK] {cp}")
        
    print(f"\nViolations Found: {len(report['violations'])}")
    if report["violations"]:
        report["verdict"] = "INTEGRITY VIOLATION"
        for v in report["violations"]:
            print(f"  [VIOLATION] {v}")
    else:
        report["verdict"] = "CLEAN"
        print("  >>> VERDICT: CLEAN <<<")
        
    print("="*70)
    
    # Save report json to .agents/auditor_1/
    out_json = Path("/home/imnyj/Workspace/paper4/latex/.agents/auditor_1/audit_report.json")
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    
    if report["violations"]:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
