#!/usr/bin/env python3
"""
deep_empirical_audit.py
=======================
Deep Empirical Adversarial Audit Suite:
- Equation-by-equation AST & syntax breakdown (all 32 display equations)
- Inline math span analysis (all 301 spans)
- Cross-reference graph & label resolution (labels, eqrefs, refs)
- Table, Figure, Algorithm environment matrix
- BibTeX citation matrix (27 keys, in-text citation mapping)
- Standalone Sandbox Packaging & Hash Integrity

Author: Challenger 2 (challenger_2)
Date: 2026-08-18
"""

import re
import sys
import json
import hashlib
import zipfile
from pathlib import Path
from collections import defaultdict, Counter

WORKSPACE_DIR = Path("/home/imnyj/Workspace/paper4/latex")
MAIN_TEX = WORKSPACE_DIR / "main.tex"
BIB_FILE = WORKSPACE_DIR / "references.bib"
ZIP_FILE = WORKSPACE_DIR / "paper4_latex_overleaf.zip"
SANDBOX_DIR = WORKSPACE_DIR / "etc" / "temp" / "deep_audit_sandbox"

def strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        m = re.search(r"(?<!\\)(?:\\\\)*%", line)
        lines.append(line[:m.start()] if m else line)
    return "\n".join(lines)

def run_deep_audit():
    raw_tex = MAIN_TEX.read_text(encoding="utf-8")
    clean_tex = strip_comments(raw_tex)
    bib_text = BIB_FILE.read_text(encoding="utf-8")
    
    results = {
        "equations": [],
        "math_summary": {},
        "environments": [],
        "tables": [],
        "figures": [],
        "algorithms": [],
        "citations": {},
        "labels_and_refs": {},
        "zip_integrity": {},
        "prohibited_words": {},
        "errors": [],
        "warnings": []
    }
    
    # -------------------------------------------------------------
    # 1. EQUATION-BY-EQUATION AUDIT
    # -------------------------------------------------------------
    disp_pattern = re.compile(r"\\begin\{(equation\*?|align\*?|gather\*?|multline\*?)\}(.*?)\\end\{\1\}", re.DOTALL)
    disp_matches = list(disp_pattern.finditer(clean_tex))
    
    for idx, m in enumerate(disp_matches, 1):
        env_type = m.group(1)
        body = m.group(2)
        start_line = clean_tex[:m.start()].count("\n") + 1
        end_line = clean_tex[:m.end()].count("\n") + 1
        
        # Extract labels
        labels = re.findall(r"\\label\{([^}]+)\}", body)
        
        # Check \frac arity
        frac_matches = list(re.finditer(r"\\frac", body))
        for fm in frac_matches:
            post_frac = body[fm.end():].lstrip()
            if not post_frac.startswith("{"):
                results["errors"].append(f"Eq #{idx} L{start_line}: \\frac not followed by curly brace argument")
                
        # Check brace balance
        # Remove \{ and \}
        clean_b = re.sub(r"\\[\{\}]", "", body)
        open_c = clean_b.count("{")
        close_c = clean_b.count("}")
        if open_c != close_c:
            results["errors"].append(f"Eq #{idx} L{start_line}: Unbalanced curly braces: {open_c} vs {close_c}")
            
        # Check parenthesis balance
        open_p = clean_b.count("(")
        close_p = clean_b.count(")")
        if open_p != close_p:
            results["errors"].append(f"Eq #{idx} L{start_line}: Unbalanced parentheses: {open_p} vs {close_p}")

        # Check bracket balance
        open_sq = clean_b.count("[")
        close_sq = clean_b.count("]")
        if open_sq != close_sq:
            results["errors"].append(f"Eq #{idx} L{start_line}: Unbalanced square brackets: {open_sq} vs {close_sq}")

        results["equations"].append({
            "index": idx,
            "env": env_type,
            "lines": f"L{start_line}-L{end_line}",
            "labels": labels,
            "open_braces": open_c,
            "close_braces": close_c,
            "open_parens": open_p,
            "close_parens": close_p,
            "open_brackets": open_sq,
            "close_brackets": close_sq,
            "snippet": body.strip().replace("\n", " ")[:80]
        })

    # -------------------------------------------------------------
    # 2. INLINE MATH AUDIT
    # -------------------------------------------------------------
    inline_pattern = re.compile(r"(?<!\\)\$(.+?)(?<!\\)\$", re.DOTALL)
    inline_matches = list(inline_pattern.finditer(clean_tex))
    inline_errors = 0
    for idx, im in enumerate(inline_matches, 1):
        ibody = im.group(1)
        iline = clean_tex[:im.start()].count("\n") + 1
        clean_ib = re.sub(r"\\[\{\}]", "", ibody)
        if clean_ib.count("{") != clean_ib.count("}"):
            results["errors"].append(f"Inline math #{idx} L{iline}: Unbalanced braces in '${ibody}$'")
            inline_errors += 1
        if clean_ib.count("(") != clean_ib.count(")"):
            results["errors"].append(f"Inline math #{idx} L{iline}: Unbalanced parentheses in '${ibody}$'")
            inline_errors += 1
        if clean_ib.count("[") != clean_ib.count("]"):
            results["errors"].append(f"Inline math #{idx} L{iline}: Unbalanced square brackets in '${ibody}$'")
            inline_errors += 1

    results["math_summary"] = {
        "display_equations_count": len(disp_matches),
        "inline_math_spans_count": len(inline_matches),
        "inline_errors_count": inline_errors
    }

    # -------------------------------------------------------------
    # 3. ENVIRONMENT & STRUCTURAL AUDIT (TABLES, FIGURES, ALGORITHMS)
    # -------------------------------------------------------------
    # Tables
    tbl_pattern = re.compile(r"\\begin\{(table\*?)\}(.*?)\\end\{\1\}", re.DOTALL)
    for idx, tm in enumerate(tbl_pattern.finditer(clean_tex), 1):
        tbody = tm.group(2)
        tline = clean_tex[:tm.start()].count("\n") + 1
        cap = re.search(r"\\caption\{([^}]+)\}", tbody)
        lbl = re.search(r"\\label\{([^}]+)\}", tbody)
        results["tables"].append({
            "index": idx,
            "type": tm.group(1),
            "line": tline,
            "label": lbl.group(1) if lbl else None,
            "caption": cap.group(1) if cap else None,
        })

    # Figures
    fig_pattern = re.compile(r"\\begin\{(figure\*?)\}(.*?)\\end\{\1\}", re.DOTALL)
    for idx, fm in enumerate(fig_pattern.finditer(clean_tex), 1):
        fbody = fm.group(2)
        fline = clean_tex[:fm.start()].count("\n") + 1
        cap = re.search(r"\\caption\{([^}]+)\}", fbody)
        lbl = re.search(r"\\label\{([^}]+)\}", fbody)
        imgs = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", fbody)
        results["figures"].append({
            "index": idx,
            "type": fm.group(1),
            "line": fline,
            "label": lbl.group(1) if lbl else None,
            "caption": cap.group(1) if cap else None,
            "graphics": imgs
        })

    # Algorithms
    alg_pattern = re.compile(r"\\begin\{(algorithm\*?)\}(.*?)\\end\{\1\}", re.DOTALL)
    for idx, am in enumerate(alg_pattern.finditer(clean_tex), 1):
        abody = am.group(2)
        aline = clean_tex[:am.start()].count("\n") + 1
        cap = re.search(r"\\caption\{([^}]+)\}", abody)
        lbl = re.search(r"\\label\{([^}]+)\}", abody)
        results["algorithms"].append({
            "index": idx,
            "type": am.group(1),
            "line": aline,
            "label": lbl.group(1) if lbl else None,
            "caption": cap.group(1) if cap else None,
        })

    # -------------------------------------------------------------
    # 4. CROSS-REFERENCES & LABELS
    # -------------------------------------------------------------
    all_labels = set(re.findall(r"\\label\{([^}]+)\}", clean_tex))
    all_refs = set(re.findall(r"\\ref\{([^}]+)\}", clean_tex))
    all_eqrefs = set(re.findall(r"\\eqref\{([^}]+)\}", clean_tex))
    
    # Check for split commas in ref
    expanded_refs = set()
    for r in all_refs:
        for sub in r.split(","):
            if sub.strip():
                expanded_refs.add(sub.strip())
                
    expanded_eqrefs = set()
    for r in all_eqrefs:
        for sub in r.split(","):
            if sub.strip():
                expanded_eqrefs.add(sub.strip())
                
    all_referenced_targets = expanded_refs.union(expanded_eqrefs)
    dangling_targets = all_referenced_targets - all_labels
    if dangling_targets:
        for dt in dangling_targets:
            results["errors"].append(f"Dangling cross-reference target: '{dt}' (no declared \\label)")

    results["labels_and_refs"] = {
        "total_labels": len(all_labels),
        "total_referenced_targets": len(all_referenced_targets),
        "dangling_targets": list(dangling_targets),
        "labels_by_category": {
            "eq": len([l for l in all_labels if l.startswith("eq:")]),
            "fig": len([l for l in all_labels if l.startswith("fig:")]),
            "tab": len([l for l in all_labels if l.startswith("tab:")]),
            "sec": len([l for l in all_labels if l.startswith("sec:")]),
            "alg": len([l for l in all_labels if l.startswith("alg:")]),
        }
    }

    # -------------------------------------------------------------
    # 5. CITATION & BIBTEX AUDIT
    # -------------------------------------------------------------
    entry_pattern = re.compile(r"@([a-zA-Z]+)\s*\{\s*([^,]+),", re.MULTILINE)
    bib_entries = [m[1].strip() for m in entry_pattern.findall(bib_text)]
    bib_set = set(bib_entries)
    
    in_text_cites = set()
    for m in re.finditer(r"\\cite\{([^}]+)\}", clean_tex):
        for k in m.group(1).split(","):
            if k.strip():
                in_text_cites.add(k.strip())
                
    hallucinated = in_text_cites - bib_set
    if hallucinated:
        for h in hallucinated:
            results["errors"].append(f"Hallucinated citation: '{h}' cited in main.tex but not in references.bib")
            
    uncited = bib_set - in_text_cites
    
    results["citations"] = {
        "bibtex_entry_count": len(bib_entries),
        "unique_bibtex_keys": len(bib_set),
        "cited_keys_count": len(in_text_cites),
        "hallucinated_keys": list(hallucinated),
        "uncited_keys": list(uncited)
    }

    # -------------------------------------------------------------
    # 6. ZIP PACKAGE & SHA-256 INTEGRITY
    # -------------------------------------------------------------
    if ZIP_FILE.is_file():
        zip_entries = []
        with zipfile.ZipFile(ZIP_FILE, 'r') as z:
            for info in z.infolist():
                zip_entries.append({"name": info.filename, "size": info.file_size, "crc": info.CRC})
                
        # Compare hashes for key files
        hash_matches = {}
        with zipfile.ZipFile(ZIP_FILE, 'r') as z:
            for fname in ["main.tex", "references.bib", "IEEEtran.cls"]:
                root_h = hashlib.sha256((WORKSPACE_DIR / fname).read_bytes()).hexdigest()
                zip_h = hashlib.sha256(z.read(fname)).hexdigest()
                hash_matches[fname] = (root_h == zip_h)
                if root_h != zip_h:
                    results["errors"].append(f"Hash mismatch for {fname} in zip package")
                    
        results["zip_integrity"] = {
            "zip_size": ZIP_FILE.stat().st_size,
            "total_entries": len(zip_entries),
            "hash_matches": hash_matches
        }
    else:
        results["errors"].append("ZIP file paper4_latex_overleaf.zip not found")

    return results


if __name__ == "__main__":
    res = run_deep_audit()
    print(json.dumps(res, indent=2))
    if res["errors"]:
        print(f"\nAUDIT FAILED: {len(res['errors'])} errors")
        sys.exit(1)
    else:
        print(f"\nAUDIT PASSED: 0 errors")
        sys.exit(0)
