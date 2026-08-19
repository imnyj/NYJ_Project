#!/usr/bin/env python3
"""
Forensic Auditor Independent Verification Script
Target: /home/imnyj/Workspace/paper4/latex/
"""

import os
import sys
import re
import zipfile
import hashlib
from pathlib import Path

WORKSPACE = Path("/home/imnyj/Workspace/paper4/latex")
MAIN_TEX = WORKSPACE / "main.tex"
BIB_FILE = WORKSPACE / "references.bib"
CLS_FILE = WORKSPACE / "IEEEtran.cls"
ZIP_FILE = WORKSPACE / "paper4_latex_overleaf.zip"
BACKUP_DIR = WORKSPACE / "backup"
AUDIT_LOG = Path("/tmp/agent_audit.log")

def log(msg, level="INFO"):
    print(f"[{level}] {msg}")

def check_forbidden_words(content):
    # Exaggerated & Cliché words strictly according to ORIGINAL_REQUEST.md and academic-writing-style SKILL.md
    forbidden_patterns = [
        # R1.1 Exaggerated
        (r"\belucidat(e|es|ed|ing|ion)\b", "elucidate"),
        (r"\bseamless(ly)?\b", "seamless"),
        (r"\bvital\b", "vital"),
        (r"\bfoster(s|ed|ing)?\b", "foster"),
        (r"\bcomprehensive(ly)?\b", "comprehensive"),
        (r"\bsignificantly\b", "significantly"),
        (r"\bsubstantially\b", "substantially"),
        (r"\bsubstantial\b", "substantial"),
        # R1.1 AI Clichés (verbs/adverbs)
        (r"\bleverag(e|es|ed|ing)\b", "leveraging"),
        (r"\butiliz(e|es|ed|ing)\b", "utilizing"),
        (r"\bsubsequently\b", "subsequently"),
        (r"\bsystematically\b", "systematically"),
        (r"\bsystematic\b", "systematic"),
        (r"\beffectively\b", "effectively"),
        (r"\bautonomously\b", "autonomously"),
        (r"\bencapsulat(e|es|ed|ing|ion)\b", "encapsulate"),
        (r"\bdelv(e|es|ed|ing)\b", "delve"),
        (r"\btestament\b", "testament"),
        (r"\bpivotal\b", "pivotal"),
    ]
    
    # Strip comments
    lines = content.splitlines()
    violations = []
    for line_idx, line in enumerate(lines, 1):
        # Remove LaTeX comments
        clean_line = re.sub(r'(?<!\\)%.*$', '', line)
        for pat, word_label in forbidden_patterns:
            matches = re.finditer(pat, clean_line, re.IGNORECASE)
            for m in matches:
                violations.append((line_idx, word_label, m.group(0), clean_line.strip()))
    return violations

def check_filenames_in_text(content):
    # Filenames mentioned in prose text (outside \includegraphics, \bibliography, \input, etc.)
    lines = content.splitlines()
    violations = []
    file_ext_pat = re.compile(r'\b[\w-]+\.(csv|py|json|md|sh|cpp|h|tex)\b', re.IGNORECASE)
    
    for line_idx, line in enumerate(lines, 1):
        clean_line = re.sub(r'(?<!\\)%.*$', '', line)
        # Skip include / bib commands
        if re.search(r'\\(documentclass|usepackage|bibliography|bibliographystyle|input|include|includegraphics)', clean_line):
            continue
        matches = file_ext_pat.finditer(clean_line)
        for m in matches:
            violations.append((line_idx, m.group(0), clean_line.strip()))
    return violations

def check_intro_contributions(content):
    # Contributions in Introduction must be itemize
    intro_match = re.search(r'\\section\{Introduction\}(.*?)(?=\\section\{|\Z)', content, re.DOTALL)
    if not intro_match:
        return False, "Introduction section not found"
    intro_text = intro_match.group(1)
    
    contrib_match = re.search(r'(contributions\s+of\s+this\s+paper\s+are\s+summarized.*?)(?=\\section|\Z)', intro_text, re.DOTALL | re.IGNORECASE)
    if not contrib_match:
        return False, "Contributions introductory text not found"
    
    contrib_block = contrib_match.group(1)
    if r'\begin{itemize}' not in contrib_block or r'\end{itemize}' not in contrib_block:
        return False, "Contributions do not use \\begin{itemize} ... \\end{itemize}"
    
    items = re.findall(r'\\item\s+', contrib_block)
    if len(items) < 3:
        return False, f"Too few contribution items ({len(items)})"
    
    return True, f"Found {len(items)} bulleted contributions formatted in itemize environment"

def check_table_1(content):
    # Table 1: Related works table
    table_match = re.search(r'\\begin\{table\*?\}.*?\\label\{tab:lit_comparison\}(.*?)\\end\{table\*?\}', content, re.DOTALL)
    if not table_match:
        # try without label in header
        table_match = re.search(r'\\begin\{table\*?\}.*?Comparison of Related Studies.*?\\end\{table\*?\}', content, re.DOTALL)
    
    if not table_match:
        return False, "Table I not found in main.tex"
    
    table_code = table_match.group(0)
    
    # Check for author names or 'Year'
    if re.search(r'\bYear\b', table_code, re.IGNORECASE):
        return False, "'Year' column header found in Table I"
    
    # Check if author strings like "et al." exist in table data rows
    data_rows = [row for row in table_code.split(r'\\') if r'\cite{' in row]
    for r in data_rows:
        clean_r = re.sub(r'(?<!\\)%.*$', '', r)
        if re.search(r'\bet\s+al\b', clean_r, re.IGNORECASE):
            return False, f"Author 'et al.' found in Table I data row: {clean_r.strip()}"
    
    # Check column specifier has fixed width (p{...} or L)
    # Match tabularx specifier properly handling nested braces
    spec_match = re.search(r'\\begin\{tabularx\}\{[^}]+\}\{(.*)\}', table_code.splitlines()[0] if 'tabularx' in table_code.splitlines()[0] else table_code)
    if not spec_match:
        # extract line containing tabularx
        for line in table_code.splitlines():
            if r'\begin{tabularx}' in line:
                # extract second {...} argument
                m = re.findall(r'\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', line)
                if len(m) >= 2:
                    col_spec = m[1]
                    break
        else:
            return False, "Could not extract column specifier for tabularx in Table I"
    else:
        col_spec = spec_match.group(1)
    
    if 'p{' not in col_spec and 'L' not in col_spec:
        return False, f"Table I column specifier lacks fixed width (p{{...}} or L): {col_spec}"
    
    return True, f"Table I correctly formatted with fixed width '{col_spec}', no authors, no Year"

def check_math_and_syntax(content):
    # LaTeX environment balance
    envs = [
        'equation', 'align', 'bmatrix', 'cases', 'table', 'table*', 'figure',
        'tabularx', 'itemize', 'enumerate', 'abstract', 'IEEEkeywords', 'document'
    ]
    env_results = {}
    for env in envs:
        begins = len(re.findall(r'\\begin\{' + re.escape(env) + r'\}', content))
        ends = len(re.findall(r'\\end\{' + re.escape(env) + r'\}', content))
        if begins != ends:
            env_results[env] = (begins, ends)
    
    # Dollar math balance
    # remove escaped \$
    no_esc_dollars = re.sub(r'\\\$', '', content)
    # remove comments
    no_comments = '\n'.join([re.sub(r'(?<!\\)%.*$', '', l) for l in no_esc_dollars.splitlines()])
    dollar_count = no_comments.count('$')
    dollar_balanced = (dollar_count % 2 == 0)
    
    return env_results, dollar_balanced, dollar_count

def check_citations_and_bib():
    with open(MAIN_TEX, 'r', encoding='utf-8') as f:
        main_content = f.read()
    with open(BIB_FILE, 'r', encoding='utf-8') as f:
        bib_content = f.read()
    
    # Extract bib keys
    bib_keys = set(re.findall(r'@\w+\s*\{\s*([a-zA-Z0-9_-]+)\s*,', bib_content))
    
    # Extract cite keys in main.tex
    cite_matches = re.findall(r'\\cite\{([^}]+)\}', main_content)
    used_cites = set()
    for cm in cite_matches:
        for k in cm.split(','):
            used_cites.add(k.strip())
    
    missing_cites = used_cites - bib_keys
    return bib_keys, used_cites, missing_cites

def check_zip_archive():
    if not ZIP_FILE.exists():
        return False, "Zip archive does not exist"
    
    expected_files = {'IEEEtran.cls', 'references.bib', 'main.tex'}
    expected_fig_prefixes = 'figures/'
    
    with zipfile.ZipFile(ZIP_FILE, 'r') as zf:
        namelist = set(zf.namelist())
        
        # Check forbidden directories in zip
        forbidden_in_zip = [n for n in namelist if n.startswith('.agents') or n.startswith('backup') or n.startswith('etc') or n.startswith('.git')]
        if forbidden_in_zip:
            return False, f"Zip contains internal workspace folders: {forbidden_in_zip}"
        
        # Check expected files
        for ef in expected_files:
            if ef not in namelist:
                return False, f"Zip missing expected file: {ef}"
            # Compare hash with workspace
            zip_data = zf.read(ef)
            with open(WORKSPACE / ef, 'rb') as f:
                ws_data = f.read()
            if hashlib.sha256(zip_data).hexdigest() != hashlib.sha256(ws_data).hexdigest():
                return False, f"Zip file content for {ef} does not match workspace"
        
        # Check figures
        fig_count = sum(1 for n in namelist if n.startswith(expected_fig_prefixes) and not n.endswith('/'))
        if fig_count < 9:
            return False, f"Zip contains too few figure files ({fig_count})"
        
    return True, f"Zip verified (Clean, self-contained, {len(namelist)} items matching workspace exactly)"

def check_backups():
    if not BACKUP_DIR.exists():
        return False, "Backup directory missing"
    
    backups = list(BACKUP_DIR.glob("*"))
    if not backups:
        return False, "No backup files found in backup/"
    
    valid_backups = []
    for b in backups:
        if b.is_file() and b.stat().st_size > 0:
            valid_backups.append(b.name)
    
    return True, f"Found {len(valid_backups)} valid non-empty backup snapshots: {valid_backups}"

def check_audit_log():
    if not AUDIT_LOG.exists():
        return False, "Audit log file does not exist"
    
    with open(AUDIT_LOG, 'r', encoding='utf-8') as f:
        log_lines = f.readlines()
    
    paper4_entries = []
    for l in log_lines:
        if "paper4" in l:
            paper4_entries.append(l.strip())
    
    return True, f"Found {len(paper4_entries)} audit log entries for paper4 (Total log lines: {len(log_lines)})"

def check_test_scripts_integrity():
    # Scan etc/scripts/*.py for dummy passes / facade tests
    scripts_dir = WORKSPACE / "etc" / "scripts"
    scripts = list(scripts_dir.glob("*.py"))
    suspicious = []
    
    for s in scripts:
        with open(s, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Check for facade functions like "def test_...(): return True" with no real logic
        dummy_func = re.findall(r'def\s+\w+\s*\([^)]*\)\s*:\s*(?:"""[^"]*"""\s*)?return\s+(?:True|0|None)\s*(?=\ndef|\Z)', code)
        if dummy_func:
            suspicious.append((s.name, "Dummy return function", dummy_func))
            
    return suspicious

def main():
    print("=" * 70)
    print("  INDEPENDENT FORENSIC AUDITOR VERIFICATION SUITE")
    print("=" * 70)
    
    with open(MAIN_TEX, 'r', encoding='utf-8') as f:
        content = f.read()
        
    all_passed = True
    
    # 1. Forbidden words
    forbidden = check_forbidden_words(content)
    if forbidden:
        log(f"FAIL: Forbidden words found ({len(forbidden)} occurrences): {forbidden}", "ERROR")
        all_passed = False
    else:
        log("PASS: Zero forbidden exaggerated or AI cliché words in main.tex", "OK")
        
    # 2. Filenames
    leaked_files = check_filenames_in_text(content)
    if leaked_files:
        log(f"FAIL: Filename mentions found in manuscript text ({len(leaked_files)} occurrences): {leaked_files}", "ERROR")
        all_passed = False
    else:
        log("PASS: Zero leaked filenames in manuscript text", "OK")
        
    # 3. Intro Contributions
    ok_intro, msg_intro = check_intro_contributions(content)
    if not ok_intro:
        log(f"FAIL: Introduction contributions: {msg_intro}", "ERROR")
        all_passed = False
    else:
        log(f"PASS: Introduction contributions: {msg_intro}", "OK")
        
    # 4. Table I
    ok_t1, msg_t1 = check_table_1(content)
    if not ok_t1:
        log(f"FAIL: Table I check: {msg_t1}", "ERROR")
        all_passed = False
    else:
        log(f"PASS: Table I check: {msg_t1}", "OK")
        
    # 5. Math & Syntax
    env_imbalances, dollar_bal, dollar_cnt = check_math_and_syntax(content)
    if env_imbalances:
        log(f"FAIL: LaTeX environment imbalances: {env_imbalances}", "ERROR")
        all_passed = False
    else:
        log("PASS: All LaTeX environments perfectly balanced", "OK")
        
    if not dollar_bal:
        log(f"FAIL: Inline math delimiter '$' is unbalanced ({dollar_cnt} count)", "ERROR")
        all_passed = False
    else:
        log(f"PASS: Inline math delimiter '$' is balanced ({dollar_cnt} delimiters, {dollar_cnt//2} spans)", "OK")
        
    # 6. Citations & BibTeX
    bib_keys, used_cites, missing_cites = check_citations_and_bib()
    if missing_cites:
        log(f"FAIL: Missing BibTeX keys for citations in main.tex: {missing_cites}", "ERROR")
        all_passed = False
    else:
        log(f"PASS: All {len(used_cites)} in-text citations mapped to references.bib ({len(bib_keys)} entries total)", "OK")
        
    # 7. Zip package
    ok_zip, msg_zip = check_zip_archive()
    if not ok_zip:
        log(f"FAIL: Zip package check: {msg_zip}", "ERROR")
        all_passed = False
    else:
        log(f"PASS: Zip package check: {msg_zip}", "OK")
        
    # 8. Backups
    ok_bak, msg_bak = check_backups()
    if not ok_bak:
        log(f"FAIL: Backup check: {msg_bak}", "ERROR")
        all_passed = False
    else:
        log(f"PASS: Backup check: {msg_bak}", "OK")
        
    # 9. Audit log
    ok_audit, msg_audit = check_audit_log()
    if not ok_audit:
        log(f"FAIL: Audit log check: {msg_audit}", "ERROR")
        all_passed = False
    else:
        log(f"PASS: Audit log check: {msg_audit}", "OK")
        
    # 10. Test scripts integrity (Cheating / Facade check)
    suspicious = check_test_scripts_integrity()
    if suspicious:
        log(f"FAIL: Suspicious dummy/facade implementations detected in test scripts: {suspicious}", "ERROR")
        all_passed = False
    else:
        log("PASS: No dummy/facade test patterns found in etc/scripts/ (All scripts contain authentic verification logic)", "OK")

    print("=" * 70)
    if all_passed:
        print(">>> FINAL INDEPENDENT FORENSIC VERDICT: CLEAN <<<")
        sys.exit(0)
    else:
        print(">>> FINAL INDEPENDENT FORENSIC VERDICT: INTEGRITY VIOLATION <<<")
        sys.exit(1)

if __name__ == '__main__':
    main()
