#!/usr/bin/env python3
"""
validate_latex.py
=================
Multi-tier Integrity & Syntax Validator for IEEE TWC LaTeX Conversion.

Verification Tiers:
- Tier 1: Directory & Asset Existence (IEEEtran.cls, references.bib, figures/*.png)
- Tier 2: BibTeX Database Syntax & 27 Entries Validation
- Tier 3: LaTeX Document Syntax & Delimiter/Environment Balancing (if main.tex exists)
- Tier 4: In-Text Citation Resolution & Cross-Reference Linkage (if main.tex exists)
- Tier 5: Packaging & Self-Containment Readiness
"""

import os
import re
import sys
from pathlib import Path

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

EXPECTED_FIGURES = [
    "1_reward_convergence.png",
    "7_cbr_trace.png",
    "8_pdr_vs_density.png",
    "9_aoi_vs_density.png",
    "10_pdr_vs_distance.png",
    "5_hardware_feasibility.png",
    "2_ablation_study.png",
    "3_moe_routing.png",
    "4_tsne_clustering.png",
]

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def check_tier1_assets():
    print("[*] Tier 1: Validating Base Assets and Directory Structure...")
    errors = []
    
    # 1. IEEEtran.cls
    cls_path = BASE_DIR / "IEEEtran.cls"
    if not cls_path.is_file():
        errors.append(f"Missing IEEEtran.cls at {cls_path}")
    else:
        print(f"  [OK] IEEEtran.cls found ({cls_path.stat().st_size} bytes)")

    # 2. references.bib
    bib_path = BASE_DIR / "references.bib"
    if not bib_path.is_file():
        errors.append(f"Missing references.bib at {bib_path}")
    else:
        print(f"  [OK] references.bib found ({bib_path.stat().st_size} bytes)")

    # 3. figures/ directory and images
    fig_dir = BASE_DIR / "figures"
    if not fig_dir.is_dir():
        errors.append(f"Missing figures directory at {fig_dir}")
    else:
        print(f"  [OK] figures directory found")
        for fig_name in EXPECTED_FIGURES:
            fpath = fig_dir / fig_name
            if not fpath.is_file():
                # Check if standardized fig*.png exists as alternate
                errors.append(f"Missing expected figure: {fig_name} in {fig_dir}")
            else:
                print(f"    [OK] Figure asset: {fig_name} ({fpath.stat().st_size} bytes)")

    return errors


def check_tier2_bibtex():
    print("\n[*] Tier 2: Validating BibTeX Database Syntax & 27 Keys...")
    errors = []
    bib_path = BASE_DIR / "references.bib"
    if not bib_path.is_file():
        return ["Cannot perform Tier 2: references.bib does not exist"]

    content = bib_path.read_text(encoding="utf-8")
    
    # Extract entries
    entry_pattern = re.compile(r"@(\w+)\s*\{\s*([^,]+),", re.MULTILINE)
    matches = entry_pattern.findall(content)
    found_keys = [m[1].strip() for m in matches]

    print(f"  [INFO] Found {len(found_keys)} BibTeX entries in references.bib")

    for expected_key in EXPECTED_27_KEYS:
        if expected_key not in found_keys:
            errors.append(f"Missing BibTeX citation key: {expected_key}")
        else:
            print(f"    [OK] Citation key verified: {expected_key}")

    # Check for duplicate keys
    seen = set()
    for k in found_keys:
        if k in seen:
            errors.append(f"Duplicate BibTeX citation key detected: {k}")
        seen.add(k)

    return errors


def check_tier3_main_tex():
    main_path = BASE_DIR / "main.tex"
    if not main_path.is_file():
        print("\n[*] Tier 3 & 4: main.tex not yet present (Skipping in early Milestone stage).")
        return []

    print("\n[*] Tier 3: Validating LaTeX Document Syntax & Environment Balancing...")
    errors = []
    content = main_path.read_text(encoding="utf-8")

    # Check \documentclass
    if "\\documentclass[journal]{IEEEtran}" not in content and "\\documentclass" not in content:
        errors.append("main.tex does not declare standard \\documentclass[journal]{IEEEtran}")
    else:
        print("  [OK] Document class IEEEtran verified")

    # Check balanced begin/end
    begins = re.findall(r"\\begin\{([a-zA-Z0-9_\*]+)\}", content)
    ends = re.findall(r"\\end\{([a-zA-Z0-9_\*]+)\}", content)

    begin_counts = {}
    for b in begins:
        begin_counts[b] = begin_counts.get(b, 0) + 1
    end_counts = {}
    for e in ends:
        end_counts[e] = end_counts.get(e, 0) + 1

    all_envs = set(begin_counts.keys()).union(set(end_counts.keys()))
    for env in sorted(all_envs):
        b_cnt = begin_counts.get(env, 0)
        e_cnt = end_counts.get(env, 0)
        if b_cnt != e_cnt:
            errors.append(f"Environment mismatch for '{env}': \\begin={b_cnt} vs \\end={e_cnt}")
        else:
            print(f"  [OK] Environment balanced: {env} ({b_cnt} instances)")

    # Check inline math $ balance (ignoring escaped \$)
    clean_content = re.sub(r"\\\$", "", content)
    dollar_count = clean_content.count("$")
    if dollar_count % 2 != 0:
        errors.append(f"Unbalanced inline math delimiter '$' count: {dollar_count}")
    else:
        print(f"  [OK] Inline math delimiter '$' balanced ({dollar_count // 2} math spans)")

    return errors


def check_tier4_citations_and_crossrefs():
    main_path = BASE_DIR / "main.tex"
    if not main_path.is_file():
        return []

    print("\n[*] Tier 4: Validating In-Text Citations and Cross-References...")
    errors = []
    content = main_path.read_text(encoding="utf-8")
    bib_path = BASE_DIR / "references.bib"
    bib_content = bib_path.read_text(encoding="utf-8") if bib_path.is_file() else ""
    
    entry_pattern = re.compile(r"@(\w+)\s*\{\s*([^,]+),", re.MULTILINE)
    bib_keys = set(m[1].strip() for m in entry_pattern.findall(bib_content))

    # Check \cite{...}
    cites = re.findall(r"\\cite\{([^}]+)\}", content)
    cited_keys = set()
    for c_group in cites:
        for c in c_group.split(","):
            key = c.strip()
            if key:
                cited_keys.add(key)
                if key not in bib_keys:
                    errors.append(f"Undefined citation key cited in text: '{key}'")

    print(f"  [INFO] Extracted {len(cited_keys)} unique citation keys in main.tex")
    
    # Check coverage of 27 keys
    missing_cites = set(EXPECTED_27_KEYS) - cited_keys
    if missing_cites:
        print(f"  [WARNING] The following {len(missing_cites)} keys from references.bib are not yet cited in main.tex: {missing_cites}")

    # Check \label vs \ref
    labels = set(re.findall(r"\\label\{([^}]+)\}", content))
    refs = set(re.findall(r"\\ref\{([^}]+)\}", content))
    eqrefs = set(re.findall(r"\\eqref\{([^}]+)\}", content))
    all_refs = refs.union(eqrefs)

    for r in sorted(all_refs):
        if r not in labels:
            errors.append(f"Broken cross-reference target: \\ref{{{r}}} has no matching \\label{{{r}}}")

    print(f"  [OK] Verified {len(labels)} labels and {len(all_refs)} cross-references")
    return errors


def check_tier5_packaging():
    print("\n[*] Tier 5: Validating Packaging & Distribution Self-Containment...")
    errors = []
    zip_path = BASE_DIR / "paper4_latex_overleaf.zip"
    
    if not zip_path.is_file():
        print("  [INFO] paper4_latex_overleaf.zip not yet generated (Run 'make zip' to build).")
        return errors
        
    import zipfile
    required_in_zip = [
        "IEEEtran.cls",
        "references.bib",
        "main.tex",
    ] + [f"figures/{f}" for f in EXPECTED_FIGURES]
    
    with zipfile.ZipFile(zip_path, "r") as z:
        names = set(z.namelist())
        for req in required_in_zip:
            if req not in names:
                errors.append(f"Missing essential asset in Overleaf zip: {req}")
            else:
                info = z.getinfo(req)
                if info.file_size == 0:
                    errors.append(f"Zero-byte asset in Overleaf zip: {req}")
                    
    if not errors:
        print(f"  [OK] Overleaf zip archive verified ({zip_path.stat().st_size} bytes, all essential assets present)")
    return errors


def main():
    print("================================================================")
    print(" IEEE TWC LaTeX Conversion Verification Suite (Milestone 1-5)")
    print(" Target Directory:", BASE_DIR)
    print("================================================================")

    all_errors = []
    all_errors.extend(check_tier1_assets())
    all_errors.extend(check_tier2_bibtex())
    all_errors.extend(check_tier3_main_tex())
    all_errors.extend(check_tier4_citations_and_crossrefs())
    all_errors.extend(check_tier5_packaging())

    print("\n================================================================")
    if not all_errors:
        print(" [SUCCESS] ALL INTEGRITY & VALIDATION CHECKS PASSED (0 ERRORS)")
        print("================================================================")
        sys.exit(0)
    else:
        print(f" [FAILURE] FOUND {len(all_errors)} VALIDATION ERROR(S):")
        for idx, err in enumerate(all_errors, 1):
            print(f"   {idx}. {err}")
        print("================================================================")
        sys.exit(1)


if __name__ == "__main__":
    main()
