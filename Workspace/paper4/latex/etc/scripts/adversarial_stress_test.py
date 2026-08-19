#!/usr/bin/env python3
"""
adversarial_stress_test.py
===========================
Adversarial Syntax, Cross-Reference, Citation & Math Stress Testing Suite
for IEEE TWC Publication Conversion (main.tex, references.bib, figures/).

Author: teamwork_preview_challenger_final_1
Date: 2026-08-18
"""

import os
import re
import sys
import zipfile
from pathlib import Path
from collections import defaultdict, Counter

BASE_DIR = Path("/home/imnyj/Workspace/paper4/latex")
MAIN_TEX = BASE_DIR / "main.tex"
BIB_FILE = BASE_DIR / "references.bib"
FIG_DIR = BASE_DIR / "figures"
CLS_FILE = BASE_DIR / "IEEEtran.cls"
ZIP_FILE = BASE_DIR / "paper4_latex_overleaf.zip"


def strip_comments(tex_source: str) -> str:
    """Strip LaTeX comments (% ...) while preserving escaped \% and line breaks."""
    lines = []
    for line in tex_source.splitlines():
        m = re.search(r"(?<!\\)(?:\\\\)*%", line)
        lines.append(line[:m.start()] if m else line)
    return "\n".join(lines)


def test_latex_environments_stack(tex_content: str):
    """
    Test balanced LaTeX environments and proper nesting (stack-based LIFO).
    """
    print("\n" + "="*70)
    print("TEST 1: LaTeX Environments Balancing & Stack Nesting (50+ envs)")
    print("="*70)

    clean_content = strip_comments(tex_content)
    token_pattern = re.compile(r"\\(begin|end)\{([a-zA-Z0-9_\*]+)\}")
    
    stack = []
    env_counts = defaultdict(int)
    all_env_names = set()
    errors = []
    
    lines = clean_content.splitlines()
    total_begins = 0
    total_ends = 0

    for line_idx, line in enumerate(lines, 1):
        for match in token_pattern.finditer(line):
            tag_type, env_name = match.groups()
            all_env_names.add(env_name)
            
            if tag_type == "begin":
                total_begins += 1
                env_counts[env_name] += 1
                stack.append((env_name, line_idx, match.start()))
            elif tag_type == "end":
                total_ends += 1
                if not stack:
                    errors.append(f"Line {line_idx}: Unexpected \\end{{{env_name}}} with empty stack.")
                else:
                    top_env, top_line, _ = stack.pop()
                    if top_env != env_name:
                        errors.append(
                            f"Line {line_idx}: Mismatched environment nesting. "
                            f"Expected \\end{{{top_env}}} (opened at line {top_line}), but found \\end{{{env_name}}}."
                        )

    while stack:
        top_env, top_line, _ = stack.pop()
        errors.append(f"Unclosed \\begin{{{top_env}}} opened at line {top_line}.")

    print(f"Total environment openings (\\begin): {total_begins}")
    print(f"Total environment closings (\\end): {total_ends}")
    print(f"Distinct environment types ({len(all_env_names)}):")
    for env, cnt in sorted(env_counts.items(), key=lambda x: -x[1]):
        print(f"  - {env:<15}: {cnt} balanced pair(s)")

    if errors:
        print(f"\n[FAIL] Found {len(errors)} environment nesting/balancing errors:")
        for err in errors:
            print(f"  ERROR: {err}")
    else:
        print(f"\n[PASS] All {total_begins} LaTeX environments ({len(all_env_names)} distinct types) are perfectly balanced and strictly nested.")

    return {
        "passed": len(errors) == 0,
        "total_environments": total_begins,
        "distinct_types": len(all_env_names),
        "env_counts": dict(env_counts),
        "errors": errors,
    }


def test_math_delimiters(tex_content: str):
    """
    Test balanced math delimiters: inline $, $$, \[ \], \( \), and math environments.
    """
    print("\n" + "="*70)
    print("TEST 2: Math Delimiters Balancing ($ , $$ , \\[ \\] , math environments)")
    print("="*70)

    clean_content = strip_comments(tex_content)
    errors = []

    # 1. Inline $ count (ignoring escaped \$)
    no_escaped_dollar = re.sub(r"\\\$", "", clean_content)
    
    # Check display $$
    double_dollars = re.findall(r"\$\$", no_escaped_dollar)
    no_double_dollar = re.sub(r"\$\$", "", no_escaped_dollar)
    
    single_dollars = no_double_dollar.count("$")
    if single_dollars % 2 != 0:
        errors.append(f"Odd number of single '$' delimiters: {single_dollars} occurrences.")
    else:
        print(f"[OK] Single '$' inline math delimiters balanced: {single_dollars} occurrences ({single_dollars // 2} spans).")

    if len(double_dollars) % 2 != 0:
        errors.append(f"Odd number of '$$' display math delimiters: {len(double_dollars)} occurrences.")
    else:
        print(f"[OK] Double '$$' display math delimiters balanced: {len(double_dollars)} occurrences.")

    # 2. Check \[ and \]
    open_sq_math = len(re.findall(r"\\\[", clean_content))
    close_sq_math = len(re.findall(r"\\\]", clean_content))
    if open_sq_math != close_sq_math:
        errors.append(f"Mismatched \\[ and \\]: {open_sq_math} \\[ vs {close_sq_math} \\].")
    else:
        print(f"[OK] \\[ and \\] display math delimiters balanced: {open_sq_math} pairs.")

    # 3. Check math equation environments specifically
    math_envs = [
        "equation", "equation*", "align", "align*", "gather", "gather*",
        "multline", "multline*", "split", "cases", "bmatrix", "pmatrix"
    ]
    math_env_stats = {}
    for menv in math_envs:
        b_cnt = len(re.findall(rf"\\begin\{{{re.escape(menv)}\}}", clean_content))
        e_cnt = len(re.findall(rf"\\end\{{{re.escape(menv)}\}}", clean_content))
        if b_cnt != e_cnt:
            errors.append(f"Math environment mismatch for '{menv}': \\begin={b_cnt}, \\end={e_cnt}")
        if b_cnt > 0:
            math_env_stats[menv] = b_cnt
            print(f"[OK] Math environment '{menv}': {b_cnt} balanced pairs.")

    if errors:
        print(f"\n[FAIL] Found {len(errors)} math delimiter errors:")
        for err in errors:
            print(f"  ERROR: {err}")
    else:
        print(f"\n[PASS] All math delimiters are strictly balanced.")

    return {
        "passed": len(errors) == 0,
        "single_dollars": single_dollars,
        "math_env_stats": math_env_stats,
        "errors": errors,
    }


def test_bibtex_citations(tex_content: str, bib_content: str):
    """
    Test BibTeX citation resolution and 100% coverage of all 27 references.
    """
    print("\n" + "="*70)
    print("TEST 3: BibTeX Citations Resolution & Coverage (27 references)")
    print("="*70)

    clean_content = strip_comments(tex_content)
    errors = []

    # 1. Parse references.bib
    entry_pattern = re.compile(r"@(\w+)\s*\{\s*([^,]+),", re.MULTILINE)
    bib_entries = entry_pattern.findall(bib_content)
    bib_keys = [k.strip() for _, k in bib_entries]
    bib_key_set = set(bib_keys)

    print(f"Found {len(bib_keys)} entries in references.bib (Unique: {len(bib_key_set)}).")

    if len(bib_keys) != 27:
        errors.append(f"Expected exactly 27 BibTeX entries in references.bib, but found {len(bib_keys)}.")
    if len(bib_keys) != len(bib_key_set):
        duplicates = [k for k in bib_keys if bib_keys.count(k) > 1]
        errors.append(f"Duplicate BibTeX citation keys in references.bib: {set(duplicates)}")

    # 2. Extract citations in main.tex
    cite_patterns = [
        re.compile(r"\\cite(?:\[[^\]]*\])?\{([^}]+)\}"),
        re.compile(r"\\citep(?:\[[^\]]*\])?\{([^}]+)\}"),
        re.compile(r"\\citet(?:\[[^\]]*\])?\{([^}]+)\}"),
    ]
    
    cited_keys_freq = defaultdict(int)
    citation_occurrences = []

    for pattern in cite_patterns:
        for match in pattern.finditer(clean_content):
            c_group = match.group(1)
            for raw_k in c_group.split(","):
                k = raw_k.strip()
                if k:
                    cited_keys_freq[k] += 1
                    citation_occurrences.append(k)

    cited_key_set = set(cited_keys_freq.keys())
    print(f"Total \\cite instances in main.tex: {len(citation_occurrences)}")
    print(f"Unique citation keys cited in main.tex: {len(cited_key_set)}")

    # 3. Check for undefined citations (cited in tex, missing in bib)
    undefined_citations = cited_key_set - bib_key_set
    if undefined_citations:
        errors.append(f"Undefined citation keys cited in main.tex: {sorted(undefined_citations)}")
        for uc in undefined_citations:
            print(f"  [ERROR] Undefined citation: {uc}")
    else:
        print("  [OK] Zero undefined citations (0 broken \\cite links).")

    # 4. Check for orphan references (in bib, not cited in tex)
    uncited_bib_keys = bib_key_set - cited_key_set
    if uncited_bib_keys:
        errors.append(f"BibTeX references not cited in main.tex ({len(uncited_bib_keys)}): {sorted(uncited_bib_keys)}")
        for ub in uncited_bib_keys:
            print(f"  [ERROR] Uncited BibTeX reference: {ub}")
    else:
        print(f"  [OK] 100% citation coverage: all {len(bib_key_set)} BibTeX references are cited in main.tex.")

    # Print breakdown of citation frequency
    print("\nCitation Frequency Breakdown:")
    for k in sorted(bib_key_set):
        count = cited_keys_freq.get(k, 0)
        print(f"  - {k:<25}: {count} citation(s)")

    if errors:
        print(f"\n[FAIL] Found {len(errors)} citation errors:")
        for err in errors:
            print(f"  ERROR: {err}")
    else:
        print(f"\n[PASS] Citation resolution is 100% valid with zero undefined citations and complete coverage.")

    return {
        "passed": len(errors) == 0,
        "total_bib_entries": len(bib_keys),
        "unique_bib_entries": len(bib_key_set),
        "total_citations_in_tex": len(citation_occurrences),
        "unique_citations_in_tex": len(cited_key_set),
        "citation_frequency": dict(cited_keys_freq),
        "undefined_citations": list(undefined_citations),
        "uncited_bib_keys": list(uncited_bib_keys),
        "errors": errors,
    }


def test_cross_references(tex_content: str):
    """
    Test cross-references (\\label vs \\ref, \\eqref, \\autoref, \\cref).
    """
    print("\n" + "="*70)
    print("TEST 4: Cross-Reference Integrity (\\label vs \\ref / \\eqref)")
    print("="*70)

    clean_content = strip_comments(tex_content)
    errors = []

    # 1. Extract all \label{...}
    label_pattern = re.compile(r"\\label\{([^}]+)\}")
    labels = label_pattern.findall(clean_content)
    label_set = set(labels)
    
    print(f"Total \\label declarations in main.tex: {len(labels)} (Unique: {len(label_set)})")

    # Check for duplicate labels
    if len(labels) != len(label_set):
        dups = [l for l in labels if labels.count(l) > 1]
        errors.append(f"Duplicate \\label declarations detected: {set(dups)}")

    # Categorize labels
    label_categories = defaultdict(list)
    for l in sorted(label_set):
        prefix = l.split(":")[0] if ":" in l else "other"
        label_categories[prefix].append(l)

    print("Declared Label Categories:")
    for prefix, items in sorted(label_categories.items()):
        print(f"  - {prefix:<10} ({len(items)} labels): {', '.join(items[:5])}{' ...' if len(items) > 5 else ''}")

    # 2. Extract all reference targets
    ref_pattern = re.compile(r"\\ref\{([^}]+)\}")
    eqref_pattern = re.compile(r"\\eqref\{([^}]+)\}")
    autoref_pattern = re.compile(r"\\autoref\{([^}]+)\}")
    cref_pattern = re.compile(r"\\(?:c|C)ref\{([^}]+)\}")

    refs = []
    for m in ref_pattern.finditer(clean_content):
        for r in m.group(1).split(","):
            refs.append(("ref", r.strip()))

    for m in eqref_pattern.finditer(clean_content):
        for r in m.group(1).split(","):
            refs.append(("eqref", r.strip()))

    for m in autoref_pattern.finditer(clean_content):
        for r in m.group(1).split(","):
            refs.append(("autoref", r.strip()))

    for m in cref_pattern.finditer(clean_content):
        for r in m.group(1).split(","):
            refs.append(("cref", r.strip()))

    print(f"Total cross-reference calls: {len(refs)}")
    ref_targets = set(r for _, r in refs)
    print(f"Unique cross-reference targets: {len(ref_targets)}")

    # 3. Check for dangling references
    dangling_refs = ref_targets - label_set
    if dangling_refs:
        errors.append(f"Dangling cross-references (no matching \\label): {sorted(dangling_refs)}")
        for dr in sorted(dangling_refs):
            print(f"  [ERROR] Dangling reference: {dr}")
    else:
        print(f"  [OK] 0 dangling references: all {len(ref_targets)} reference targets match declared labels.")

    # 4. Check for orphan labels
    orphan_labels = label_set - ref_targets
    print(f"\nDiagnostic: {len(orphan_labels)} labels declared but not directly referenced:")
    for ol in sorted(orphan_labels):
        print(f"  - (Diagnostic) Orphan label: {ol}")

    if errors:
        print(f"\n[FAIL] Found {len(errors)} cross-referencing errors:")
        for err in errors:
            print(f"  ERROR: {err}")
    else:
        print(f"\n[PASS] All cross-references (\\ref, \\eqref) are 100% resolved.")

    return {
        "passed": len(errors) == 0,
        "total_labels": len(labels),
        "unique_labels": len(label_set),
        "total_references": len(refs),
        "unique_ref_targets": len(ref_targets),
        "label_categories": {k: len(v) for k, v in label_categories.items()},
        "dangling_references": list(dangling_refs),
        "orphan_labels": list(orphan_labels),
        "errors": errors,
    }


def test_figure_assets(tex_content: str):
    """
    Test all \\includegraphics paths in main.tex and verify physical file existence in figures/.
    """
    print("\n" + "="*70)
    print("TEST 5: Figure Assets Resolution (\\includegraphics vs figures/)")
    print("="*70)

    clean_content = strip_comments(tex_content)
    errors = []

    img_pattern = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
    img_matches = img_pattern.findall(clean_content)

    print(f"Total \\includegraphics declarations in main.tex: {len(img_matches)}")

    verified_images = []
    for raw_path in img_matches:
        raw_path = raw_path.strip()
        p = Path(raw_path)
        
        candidates = [
            BASE_DIR / raw_path,
            FIG_DIR / p.name,
            BASE_DIR / (raw_path + ".png"),
            FIG_DIR / (p.name + ".png"),
        ]
        
        found = False
        resolved_path = None
        for cand in candidates:
            if cand.is_file():
                found = True
                resolved_path = cand
                break

        if not found:
            errors.append(f"Figure file not found on disk: '{raw_path}'")
            print(f"  [ERROR] Missing figure file: {raw_path}")
        else:
            file_size = resolved_path.stat().st_size
            with open(resolved_path, "rb") as f:
                header = f.read(8)
            is_valid_png = (header == b"\x89PNG\r\n\x1a\n")
            
            if not is_valid_png:
                errors.append(f"Figure file '{resolved_path}' is not a valid PNG image.")
                print(f"  [ERROR] Invalid PNG format: {resolved_path.name}")
            else:
                verified_images.append((raw_path, resolved_path.name, file_size))
                print(f"  [OK] Verified figure: '{raw_path}' -> {resolved_path.name} ({file_size} bytes)")

    if errors:
        print(f"\n[FAIL] Found {len(errors)} figure asset errors:")
        for err in errors:
            print(f"  ERROR: {err}")
    else:
        print(f"\n[PASS] All {len(img_matches)} figure inclusions point to valid, existing PNG files.")

    return {
        "passed": len(errors) == 0,
        "total_figures_in_tex": len(img_matches),
        "verified_images": verified_images,
        "errors": errors,
    }


def test_syntax_defects_and_braces(tex_content: str):
    """
    Test for syntax defects, typos in commands, unbalanced curly braces, and placeholders.
    """
    print("\n" + "="*70)
    print("TEST 6: Adversarial Command Syntax, Braces & Placeholder Audit")
    print("="*70)

    clean_content = strip_comments(tex_content)
    errors = []

    # 1. Search for command typos (e.g. \label:..., \ref:..., \cite:...)
    typo_pattern = re.compile(r"\\(label|ref|eqref|cite|section|subsection|caption):([a-zA-Z0-9_\-:]+)\}")
    for match in typo_pattern.finditer(clean_content):
        cmd, target = match.groups()
        # Find line number
        lno = clean_content[:match.start()].count("\n") + 1
        errors.append(f"Line {lno}: Typo syntax detected: '\\{cmd}:{target}}}' should be '\\{cmd}{{{target}}}'")

    # 2. Check balanced curly braces { } (ignoring escaped \{ and \})
    no_escaped_braces = re.sub(r"\\[\{\}]", "", clean_content)
    open_curly = no_escaped_braces.count("{")
    close_curly = no_escaped_braces.count("}")
    if open_curly != close_curly:
        errors.append(f"Unbalanced curly braces: {open_curly} '{{' vs {close_curly} '}}' (Delta: {abs(open_curly - close_curly)})")
    else:
        print(f"[OK] Curly braces balanced: {open_curly} pairs.")

    # 3. Check for placeholder markers
    placeholders = ["TODO", "FIXME", "TBD", "XXX", "\\cite{?}", "\\ref{?}", "[?]"]
    for ph in placeholders:
        matches = re.findall(rf"\b{re.escape(ph)}\b", clean_content)
        if matches:
            errors.append(f"Unresolved placeholder detected: '{ph}' ({len(matches)} occurrence(s))")

    # 4. Check document structure
    if "\\documentclass[journal]{IEEEtran}" not in clean_content:
        errors.append("Missing exact \\documentclass[journal]{IEEEtran}")
    else:
        print("[OK] Exact IEEEtran documentclass declaration present.")

    required_sections = [
        "\\title{", "\\author{", "\\maketitle", "\\begin{abstract}", "\\begin{IEEEkeywords}",
        "\\section{Introduction}", "\\section{Related Works}", "\\section{System Model and REMO-DQN Architecture}",
        "\\section{Dynamic Operational Workflow}", "\\section{Performance Evaluation}", "\\section{Conclusion}",
        "\\bibliographystyle{IEEEtran}", "\\bibliography{references}"
    ]

    for req in required_sections:
        if req not in clean_content:
            errors.append(f"Missing required section / structural marker: '{req}'")
        else:
            print(f"[OK] Structural marker present: '{req}'")

    if errors:
        print(f"\n[FAIL] Found {len(errors)} syntax / brace / structure error(s):")
        for err in errors:
            print(f"  ERROR: {err}")
    else:
        print(f"\n[PASS] Document syntax, braces, and structure are 100% verified.")

    return {
        "passed": len(errors) == 0,
        "open_curly": open_curly,
        "close_curly": close_curly,
        "errors": errors,
    }


def main():
    print("#"*70)
    print(" EMPIRICAL ADVERSARIAL STRESS TEST SUITE")
    print(" Target: " + str(BASE_DIR))
    print("#"*70)

    if not MAIN_TEX.is_file():
        print(f"FATAL: {MAIN_TEX} does not exist.")
        sys.exit(1)
    if not BIB_FILE.is_file():
        print(f"FATAL: {BIB_FILE} does not exist.")
        sys.exit(1)

    tex_content = MAIN_TEX.read_text(encoding="utf-8")
    bib_content = BIB_FILE.read_text(encoding="utf-8")

    r1 = test_latex_environments_stack(tex_content)
    r2 = test_math_delimiters(tex_content)
    r3 = test_bibtex_citations(tex_content, bib_content)
    r4 = test_cross_references(tex_content)
    r5 = test_figure_assets(tex_content)
    r6 = test_syntax_defects_and_braces(tex_content)

    all_passed = (
        r1["passed"] and r2["passed"] and r3["passed"] and
        r4["passed"] and r5["passed"] and r6["passed"]
    )

    print("\n" + "#"*70)
    print(" SUMMARY OF EMPIRICAL ADVERSARIAL STRESS TEST RESULTS")
    print("#"*70)
    print(f"1. LaTeX Environments Balancing & Stack Nesting: {'PASS' if r1['passed'] else 'FAIL'}")
    print(f"2. Math Delimiters & Environments:             {'PASS' if r2['passed'] else 'FAIL'}")
    print(f"3. BibTeX Citation Resolution & Coverage:       {'PASS' if r3['passed'] else 'FAIL'}")
    print(f"4. Cross-Reference Integrity (\\label/\\ref):     {'PASS' if r4['passed'] else 'FAIL'}")
    print(f"5. Figure Asset Resolution (\\includegraphics):   {'PASS' if r5['passed'] else 'FAIL'}")
    print(f"6. Adversarial Syntax & Structure Audit:        {'PASS' if r6['passed'] else 'FAIL'}")
    print("#"*70)

    if all_passed:
        print("\n>>> OVERALL VERDICT: APPROVE (0 ERRORS DETECTED) <<<")
        sys.exit(0)
    else:
        print("\n>>> OVERALL VERDICT: REQUEST_CHANGES <<<")
        sys.exit(1)


if __name__ == "__main__":
    main()
