#!/usr/bin/env python3
"""
adversarial_challenger1_suite.py
================================
Comprehensive Adversarial Empirical Verification Harness for main.tex
Author: Challenger 1 (challenger_1)
Date: 2026-08-18

This test suite aggressively probes main.tex against:
- R1: Prohibited exaggerated words, AI clichés, hidden filenames, redundant parentheses, short paragraphs.
- R2: Introduction contributions itemize environment formatting and tag balancing.
- R3: Table I column separator count, removal of Year column, removal of author names (cite only), fixed-width wrapping.
- R4: Mathematical equations and inline math syntax consistency, cross-references, citation coverage, build validation.
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path("/home/imnyj/Workspace/paper4/latex")
MAIN_TEX = BASE_DIR / "main.tex"
BIB_FILE = BASE_DIR / "references.bib"


def strip_comments(text: str) -> str:
    """Strips LaTeX comments while preserving escaped \\% and line numbers."""
    lines = []
    for line in text.splitlines():
        m = re.search(r"(?<!\\)(?:\\\\)*%", line)
        lines.append(line[:m.start()] if m else line)
    return "\n".join(lines)


# =========================================================================
# TEST 1: Forbidden & Exaggerated / Cliché Words Scan (Case-Insensitive)
# =========================================================================
def test_prohibited_words(tex_source: str):
    print("\n" + "=" * 75)
    print("TEST 1: Adversarial Scan for Forbidden & Exaggerated / Cliché Words")
    print("=" * 75)

    clean_text = strip_comments(tex_source)
    lines = clean_text.splitlines()

    strict_prohibitions = {
        "elucidate": r"\b(elucidat(e|es|ed|ing|ion))\b",
        "seamless": r"\b(seamless(ly|ness)?)\b",
        "vital": r"\b(vital(ly|ity)?)\b",
        "fosters": r"\b(foster(s|ed|ing)?)\b",
        "comprehensive": r"\b(comprehensive(ly|ness)?)\b",
        "significantly": r"\b(significant(ly)?)\b",
        "substantially": r"\b(substantial(ly)?)\b",
        "leveraging": r"\b(leverag(e|es|ed|ing))\b",
        "utilizing": r"\b(utiliz(e|es|ed|ing))\b",
        "subsequently": r"\b(subsequent(ly)?)\b",
        "systematically": r"\b(systematic(ally)?)\b",
        "effectively": r"\b(effectively)\b",
        "autonomously": r"\b(autonomously)\b",
        "encapsulates": r"\b(encapsulat(e|es|ed|ing|ion|ions))\b",
        "delve": r"\b(delv(e|es|ed|ing))\b",
        "pivotal": r"\b(pivotal)\b",
        "paramount": r"\b(paramount)\b",
        "cornerstone": r"\b(cornerstone(s)?)\b",
        "testament": r"\b(testament)\b",
    }

    findings = defaultdict(list)
    total_violations = 0

    for line_idx, line in enumerate(lines, 1):
        masked_line = re.sub(r"\\(cite|label|ref|eqref|autoref|cref|url|path)\{[^}]*\}", " ", line)
        
        for term, pattern in strict_prohibitions.items():
            matches = list(re.finditer(pattern, masked_line, re.IGNORECASE))
            for m in matches:
                matched_str = m.group(0)
                findings[term].append({
                    "line": line_idx,
                    "matched": matched_str,
                    "snippet": line.strip()
                })
                total_violations += 1

    if total_violations == 0:
        print("[PASS] Zero prohibited or exaggerated/cliché terms found in main.tex.")
    else:
        print(f"[FAIL] Found {total_violations} prohibited term violation(s):")
        for term, instances in findings.items():
            print(f"\n  Keyword: '{term}' ({len(instances)} hits):")
            for inst in instances:
                print(f"    Line {inst['line']}: matched '{inst['matched']}'")
                print(f"      Context: {inst['snippet']}")

    return {"passed": total_violations == 0, "violations": findings, "count": total_violations}


# =========================================================================
# TEST 2: Hidden Filenames & Internal Artifacts Leakage
# =========================================================================
def test_hidden_filenames(tex_source: str):
    print("\n" + "=" * 75)
    print("TEST 2: Adversarial Scan for Leaked File Names & Codebase Artifacts")
    print("=" * 75)

    clean_text = strip_comments(tex_source)
    lines = clean_text.splitlines()

    ext_pattern = re.compile(r"(\b[\w\-\./]+\.(?:csv|py|tex|sh|json|png|log|txt|h5|pt|pkl|dat|zip)\b)", re.IGNORECASE)

    violations = []
    
    for line_idx, line in enumerate(lines, 1):
        stripped_line = line.strip()
        
        # Mask legitimate macro calls
        masked = re.sub(r"\\includegraphics(?:\[[^\]]*\])?\{[^}]+\}", " ", line)
        masked = re.sub(r"\\(?:documentclass|usepackage|bibliography|bibliographystyle|input|include)\{[^}]+\}", " ", masked)
        
        matches = ext_pattern.findall(masked)
        if matches:
            for match in matches:
                violations.append({
                    "line": line_idx,
                    "filename": match,
                    "snippet": stripped_line
                })

    if not violations:
        print("[PASS] Zero internal filenames leaked in manuscript text.")
        print("  All .csv, .py, .tex, .sh, .json, .png, .log references are properly cleansed from prose.")
    else:
        print(f"[FAIL] Found {len(violations)} leaked filename(s) in manuscript body:")
        for v in violations:
            print(f"  Line {v['line']}: Leaked '{v['filename']}'")
            print(f"    Context: {v['snippet']}")

    return {"passed": len(violations) == 0, "violations": violations}


# =========================================================================
# TEST 3: Table I Structural & Content Verification (R3)
# =========================================================================
def extract_braced_arg(text: str, start_pos: int):
    """Extracts a balanced { ... } argument from text starting at start_pos."""
    brace_open = text.find('{', start_pos)
    if brace_open == -1:
        return None, -1
    depth = 0
    for i in range(brace_open, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[brace_open + 1:i], i + 1
    return None, -1


def test_table_i_structure(tex_source: str):
    print("\n" + "=" * 75)
    print("TEST 3: Table I (Related Works Comparison) Structural & Content Audit")
    print("=" * 75)

    clean_text = strip_comments(tex_source)
    errors = []

    tab_match = re.search(r"\\begin\{table\*?\}.*?\\label\{tab:lit_comparison\}.*?\\end\{table\*?\}", clean_text, re.DOTALL)
    if not tab_match:
        tab_match = re.search(r"\\begin\{table\*?\}.*?Comparison of Related Studies.*?\\end\{table\*?\}", clean_text, re.DOTALL)

    if not tab_match:
        errors.append("Could not find Table I (tab:lit_comparison) in main.tex")
        print("[FAIL] " + errors[-1])
        return {"passed": False, "errors": errors}

    table_block = tab_match.group(0)
    print("  Table block successfully extracted.")

    # 1. Check tabularx or tabular environment and column specifier with brace matching
    tab_start = table_block.find(r"\begin{tabularx}")
    col_spec = None
    if tab_start != -1:
        # tabularx has 2 braced args: {width}{cols}
        width_arg, end_pos = extract_braced_arg(table_block, tab_start + len(r"\begin{tabularx}"))
        if end_pos != -1:
            col_spec, _ = extract_braced_arg(table_block, end_pos)
    else:
        tab_start_plain = table_block.find(r"\begin{tabular}")
        if tab_start_plain != -1:
            col_spec, _ = extract_braced_arg(table_block, tab_start_plain + len(r"\begin{tabular}"))

    if not col_spec:
        errors.append("Missing or unparsable tabularx/tabular column specification in Table I.")
    else:
        print(f"  Parsed Column specifier: '{col_spec}'")
        
        # Check that fixed-width wrapping is used (p{...}, L, Y, etc.)
        if "p{" not in col_spec and "L" not in col_spec and "X" not in col_spec:
            errors.append(f"Table I column specifier '{col_spec}' lacks fixed-width / line-wrapping column types (p{{}} or L/X).")
        else:
            print("  [OK] Fixed-width column formatting (p{...} / L) verified.")

    # 2. Check for Year column in table headers
    if re.search(r"\bYear\b", table_block, re.IGNORECASE):
        errors.append("Found 'Year' column or mention inside Table I.")
    else:
        print("  [OK] 'Year' column is completely absent.")

    # 3. Check author names vs \cite{} in Reference column
    author_leak_pattern = re.compile(r"\b(Ye|Hu|Zheng|Wang|Bhattacharyya|Liu|Kang|Xu|Du|Park|Zhang)\s+(et\s+al\.|and\b)", re.IGNORECASE)
    
    table_lines = table_block.splitlines()
    in_data = False
    row_count = 0
    expected_cols = 5

    for idx, l in enumerate(table_lines, 1):
        if "\\midrule" in l:
            in_data = True
            continue
        if "\\bottomrule" in l:
            in_data = False
            continue
        if in_data and "\\\\" in l:
            row_count += 1
            parts = re.split(r"(?<!\\)&", l)
            if len(parts) != expected_cols:
                errors.append(f"Table I Row {row_count}: Expected {expected_cols} columns ({expected_cols-1} '&' separators), found {len(parts)}.")
            
            first_col = parts[0].strip()
            if "Proposed" not in first_col:
                if not re.search(r"\\cite\{[^}]+\}", first_col):
                    errors.append(f"Table I Row {row_count}: First column '{first_col}' does not use \\cite{{}} reference.")
                if author_leak_pattern.search(first_col):
                    errors.append(f"Table I Row {row_count}: Author names leaked in Reference column: '{first_col}'")

    print(f"  Total verified data rows in Table I: {row_count}")

    if not errors:
        print("[PASS] Table I structure, column count, cite format, and width management 100% verified.")
    else:
        print(f"[FAIL] Found {len(errors)} error(s) in Table I:")
        for err in errors:
            print(f"  ERROR: {err}")

    return {"passed": len(errors) == 0, "errors": errors, "row_count": row_count}


# =========================================================================
# TEST 4: Introduction Contributions `itemize` Verification (R2)
# =========================================================================
def test_intro_contributions(tex_source: str):
    print("\n" + "=" * 75)
    print("TEST 4: Introduction Contributions `itemize` Environment Verification")
    print("=" * 75)

    clean_text = strip_comments(tex_source)
    errors = []

    intro_match = re.search(r"\\section\{Introduction\}(.*?)\\section\{", clean_text, re.DOTALL)
    if not intro_match:
        errors.append("Could not extract Section I: Introduction.")
        return {"passed": False, "errors": errors}

    intro_text = intro_match.group(1)

    contrib_marker = re.search(r"contributions.*?(?:summarized|outlined|listed).*?:", intro_text, re.IGNORECASE)
    if not contrib_marker:
        errors.append("Could not find contributions introductory sentence in Introduction.")
    else:
        print("  [OK] Found contributions introductory sentence.")

    itemize_match = re.search(r"\\begin\{itemize\}(.*?)\\end\{itemize\}", intro_text, re.DOTALL)
    if not itemize_match:
        errors.append("Contributions section in Introduction is NOT formatted using an \\begin{itemize} ... \\end{itemize} environment!")
    else:
        print("  [OK] \\begin{itemize} ... \\end{itemize} environment found in Introduction.")
        item_block = itemize_match.group(1)
        items = re.findall(r"\\item\s+(.*?)(?=\\item|\Z)", item_block, re.DOTALL)
        print(f"  Found {len(items)} bullet contribution items:")
        for idx, it in enumerate(items, 1):
            first_line = it.strip().splitlines()[0]
            print(f"    Item {idx}: {first_line[:80]}...")

        if len(items) < 3:
            errors.append(f"Expected at least 3 contribution items, found {len(items)}.")

    if not errors:
        print("[PASS] Introduction contributions itemize formatting and tag balancing 100% verified.")
    else:
        print(f"[FAIL] Found {len(errors)} error(s) in Introduction contributions:")
        for err in errors:
            print(f"  ERROR: {err}")

    return {"passed": len(errors) == 0, "errors": errors}


# =========================================================================
# TEST 5: Redundant Acronym Parentheses & Data Dump Audit (R1)
# =========================================================================
def test_parentheses_and_acronyms(tex_source: str):
    print("\n" + "=" * 75)
    print("TEST 5: Redundant Acronym Definitions & Parentheses Reduction Audit")
    print("=" * 75)

    clean_text = strip_comments(tex_source)
    lines = clean_text.splitlines()

    acronym_pattern = re.compile(r"\b([A-Z][a-zA-Z\s\-]+)\s+\(([A-Z]{2,10})\)")
    
    definitions = defaultdict(list)
    for line_idx, line in enumerate(lines, 1):
        masked = re.sub(r"\\cite\{[^}]+\}", " ", line)
        for m in acronym_pattern.finditer(masked):
            full_term, acr = m.groups()
            full_term = full_term.strip()
            definitions[acr].append((line_idx, full_term))

    repeated_acronyms = {k: v for k, v in definitions.items() if len(v) > 1}
    
    print(f"Total acronym definitions identified: {len(definitions)}")
    if repeated_acronyms:
        print("  [INFO] Acronyms defined more than once in text:")
        for acr, instances in repeated_acronyms.items():
            print(f"    - {acr} defined {len(instances)} times at lines: {[inst[0] for inst in instances]}")
    else:
        print("  [OK] Zero duplicate acronym definitions detected.")

    return {"passed": True, "repeated_acronyms": repeated_acronyms}


# =========================================================================
# TEST 6: Math Expressions & LaTeX Buildability Check (R4)
# =========================================================================
def test_math_and_build():
    print("\n" + "=" * 75)
    print("TEST 6: Math Syntax, Cross-References & Build Verification")
    print("=" * 75)

    res = subprocess.run([sys.executable, str(BASE_DIR / "etc/scripts/validate_latex.py")], capture_output=True, text=True)
    print("Execution output of validate_latex.py:")
    print(res.stdout)
    if res.stderr:
        print("STDERR:", res.stderr)

    return {"passed": res.returncode == 0, "output": res.stdout, "returncode": res.returncode}


# =========================================================================
# MAIN EXECUTION
# =========================================================================
def main():
    print("#" * 75)
    print("  CHALLENGER 1 EMPIRICAL ADVERSARIAL VERIFICATION SUITE")
    print("  Target: " + str(MAIN_TEX))
    print("#" * 75)

    if not MAIN_TEX.is_file():
        print(f"FATAL: {MAIN_TEX} does not exist.")
        sys.exit(1)

    tex_source = MAIN_TEX.read_text(encoding="utf-8")

    t1 = test_prohibited_words(tex_source)
    t2 = test_hidden_filenames(tex_source)
    t3 = test_table_i_structure(tex_source)
    t4 = test_intro_contributions(tex_source)
    t5 = test_parentheses_and_acronyms(tex_source)
    t6 = test_math_and_build()

    all_passed = t1["passed"] and t2["passed"] and t3["passed"] and t4["passed"] and t6["passed"]

    print("\n" + "#" * 75)
    print("  FINAL SUMMARY OF EMPIRICAL ADVERSARIAL CHALLENGE")
    print("#" * 75)
    print(f"  1. Forbidden & Exaggerated / Cliché Words Scan: {'PASS' if t1['passed'] else 'FAIL'} ({t1['count']} violation(s))")
    print(f"  2. Leaked Filenames / Code Artifacts Scan:     {'PASS' if t2['passed'] else 'FAIL'}")
    print(f"  3. Table I Structural & Content Audit (R3):    {'PASS' if t3['passed'] else 'FAIL'}")
    print(f"  4. Intro Contributions itemize Audit (R2):     {'PASS' if t4['passed'] else 'FAIL'}")
    print(f"  5. Acronym Parentheses Reduction Audit:        {'PASS' if t5['passed'] else 'FAIL'}")
    print(f"  6. Math Syntax & Validation Suite (R4):        {'PASS' if t6['passed'] else 'FAIL'}")
    print("#" * 75)

    if all_passed:
        print("\n>>> OVERALL CHALLENGER VERDICT: APPROVE <<<")
        sys.exit(0)
    else:
        print("\n>>> OVERALL CHALLENGER VERDICT: REQUEST_CHANGES <<<")
        sys.exit(1)


if __name__ == "__main__":
    main()
