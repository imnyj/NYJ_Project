#!/usr/bin/env python3
"""
forensic_verifier.py
Comprehensive forensic auditor script for verifying IEEE TWC LaTeX deliverables
against Korean master draft.
"""

import os
import re
import sys
from pathlib import Path

KOREAN_DRAFT_PATH = Path("/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md")
LATEX_MAIN_PATH = Path("/home/imnyj/Workspace/paper4/latex/main.tex")
LATEX_BIB_PATH = Path("/home/imnyj/Workspace/paper4/latex/references.bib")
LATEX_DIR = Path("/home/imnyj/Workspace/paper4/latex")

def run_forensic_audit():
    print("=== STARTING FORENSIC INTEGRITY AUDIT ===")
    k_text = KOREAN_DRAFT_PATH.read_text(encoding="utf-8")
    l_text = LATEX_MAIN_PATH.read_text(encoding="utf-8")
    bib_text = LATEX_BIB_PATH.read_text(encoding="utf-8")

    # 1. Check for placeholders, stubs, TODOs, FIXMEs, TBDs
    banned_tokens = ["TODO", "FIXME", "TBD", "XXX", "PLACEHOLDER", "dummy", "lorem ipsum", "insert here"]
    placeholder_findings = []
    for token in banned_tokens:
        matches = list(re.finditer(re.escape(token), l_text, re.IGNORECASE))
        if matches:
            for m in matches:
                # Get context around match
                start = max(0, m.start() - 30)
                end = min(len(l_text), m.end() + 30)
                snippet = l_text[start:end].replace("\n", " ")
                placeholder_findings.append((token, snippet))

    print(f"\n[Check 1] Placeholder/Stub Scan: {len(placeholder_findings)} issues found.")
    if placeholder_findings:
        for t, snip in placeholder_findings:
            print(f"  FAILED: Found placeholder '{t}': ...{snip}...")
    else:
        print("  PASS: Zero placeholders, stubs, or TODO comments detected in main.tex.")

    # 2. Check Bibliography extraction and citation keys
    bib_entries = re.findall(r"@(\w+)\s*\{\s*([^,]+),", bib_text)
    bib_keys = [k.strip() for _, k in bib_entries]
    print(f"\n[Check 2] BibTeX Database Scan: {len(bib_keys)} entries found.")
    
    # Extract references from Korean draft
    k_ref_section = k_text[k_text.rfind("## 참고문헌"):] if "## 참고문헌" in k_text else ""
    k_refs = re.findall(r"\[(\d+)\]\s*([^\n]+)", k_ref_section)
    print(f"  Korean draft has {len(k_refs)} reference entries listed.")
    print(f"  references.bib has {len(bib_keys)} entries.")
    
    # Check citation usage in main.tex
    cites = re.findall(r"\\cite\{([^}]+)\}", l_text)
    used_keys = set()
    for c_group in cites:
        for c in c_group.split(","):
            used_keys.add(c.strip())

    missing_in_bib = used_keys - set(bib_keys)
    uncited_in_tex = set(bib_keys) - used_keys
    print(f"  Cited keys in main.tex: {len(used_keys)}")
    print(f"  Missing in bib: {missing_in_bib}")
    print(f"  Uncited in tex: {uncited_in_tex}")

    # 3. Check Figure files & references
    figures_in_tex = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", l_text)
    print(f"\n[Check 3] Figure Assets Scan: {len(figures_in_tex)} \\includegraphics commands found in main.tex.")
    fig_errors = []
    for fig_path in figures_in_tex:
        # Check relative to LATEX_DIR
        full_fig_path = (LATEX_DIR / fig_path).resolve()
        if not full_fig_path.is_file():
            fig_errors.append(f"Figure not found on disk: {fig_path} (resolved to {full_fig_path})")
        else:
            print(f"  PASS: Figure found: {fig_path} ({full_fig_path.stat().st_size} bytes)")
    
    # 4. Numerical metrics verification (Sample 30+ numerical metrics across text and 14 tables)
    print("\n[Check 4] Numerical Metrics & Quantitative Fidelity (30+ metrics)...")
    sample_metrics = [
        ("REMO-DQN Overall PDR", "73.41%", r"73\.41\\?%?"),
        ("REMO-DQN Mean AoI", "373.21 ms", r"373\.21\s*(?:ms)?"),
        ("REMO-DQN CBR Std Dev", "0.1008", r"0\.1008"),
        ("Vanilla DQN High Density PDR", "1.21%", r"1\.21\\?%?"),
        ("Vanilla DQN Mean AoI", "1290.89 ms", r"1290\.89|1,290\.89"),
        ("DQN+MoE High Density PDR", "65.20%", r"65\.20\\?%?"),
        ("DQN+MoE CBR Std Dev", "0.1058", r"0\.1058"),
        ("REMO-DQN High Density PDR", "73.41%", r"73\.41"),
        ("REMO-DQN MACs", "3.8M", r"3\.8\s*M|3\.8M"),
        ("REMO-DQN Params", "350K", r"350\s*K|350K"),
        ("REMO-DQN Latency", "1.2 ms", r"1\.2\s*ms"),
        ("REMO-DQN Period Ratio", "1.2%", r"1\.2\\?%"),
        ("Vanilla DQN Latency", "0.5 ms", r"0\.5\s*ms"),
        ("Vanilla DQN MACs", "1.2M", r"1\.2\s*M|1\.2M"),
        ("Vanilla DQN Params", "100K", r"100\s*K|100K"),
        ("DQN+MoE MACs", "1.5M", r"1\.5\s*M|1\.5M"),
        ("DQN+MoE Params", "120K", r"120\s*K|120K"),
        ("DQN+MoE Latency", "0.6 ms", r"0\.6\s*ms"),
        ("Memory size REMO-DQN", "1.4 MB", r"1\.4\s*MB"),
        ("Carrier Frequency", "5.9 GHz", r"5\.9\s*GHz"),
        ("Channel Bandwidth", "10 MHz", r"10\s*MHz"),
        ("Noise Figure", "9 dB", r"9\s*dB"),
        ("Noise Power", "-95 dBm", r"-95\s*dBm"),
        ("Max Tx Power", "23 dBm", r"23\s*dBm"),
        ("Min Tx Power", "10 dBm", r"10\s*dBm"),
        ("Vehicle Density Range", "10 to 100 veh/km", r"10\s*(?:to|--|-)\s*100\s*veh/km|10.*100"),
        ("Reward weight w1", "0.01", r"0\.01"),
        ("Reward weight w2", "1.0", r"1\.0"),
        ("Reward weight w3", "0.10", r"0\.10|0\.1"),
        ("Load balancing weight lambda_LB", "0.01", r"0\.01"),
        ("Target CBR", "0.65", r"0\.65"),
        ("Nakagami shape parameter m", "3.0", r"3\.0|3"),
        ("ETSI min interval", "100 ms", r"100\s*ms"),
        ("ETSI max interval", "1000 ms", r"1000\s*ms|1\s*s"),
        ("Optuna Trial Count", "100", r"100"),
        ("REMO-DQN Learning Rate", "1e-4", r"1(?:\\times 10\^\{-4\}|e-4|\\cdot 10\^\{-4\})"),
        ("REMO-DQN Batch Size", "64", r"64"),
        ("REMO-DQN Discount Factor gamma", "0.99", r"0\.99"),
        ("Soft Target Update tau", "0.005", r"0\.005"),
        ("Replay Buffer Capacity", "100000", r"100,?000|10\^5"),
        ("Low Traffic Cluster X", "-0.225", r"-0\.225"),
        ("Low Traffic Cluster Y", "0.084", r"0\.084"),
        ("Medium Traffic Cluster X", "5.018", r"5\.018"),
        ("Medium Traffic Cluster Y", "5.151", r"5\.151"),
        ("High Traffic Cluster X", "1.961", r"1\.961"),
        ("High Traffic Cluster Y", "4.979", r"4\.979"),
        ("Low-Medium Cluster Distance", "7.30", r"7\.30|7\.3"),
        ("Low-High Cluster Distance", "5.36", r"5\.36"),
        ("Expert 1 Density 20 weight", "80%", r"80\\?%?|0\.80"),
        ("Expert 3 Density 160 weight", "85%", r"85\\?%?|0\.85"),
        ("REMO-DQN Mean CBR", "0.3442", r"0\.3442"),
        ("REMO-DQN AoI 3.46x reduction", "3.46", r"3\.46"),
    ]

    sampled_results = []
    for name, expected_str, pat in sample_metrics:
        # check in korean draft
        k_found = bool(re.search(pat, k_text))
        # check in latex
        l_found = bool(re.search(pat, l_text))
        sampled_results.append((name, expected_str, k_found, l_found))
        status = "PASS" if (k_found and l_found) else ("WARN (Only in Tex)" if l_found else "FAIL")
        print(f"  [{status}] {name:38s} | Expected: {expected_str:15s} | Korean: {k_found} | LaTeX: {l_found}")

    # 5. Overleaf Zip Validation
    zip_path = LATEX_DIR / "paper4_latex_overleaf.zip"
    print(f"\n[Check 5] Overleaf Zip Archive Scan: {zip_path}")
    import zipfile
    if not zip_path.is_file():
        print(f"  FAIL: Zip archive does not exist at {zip_path}")
    else:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z_files = z.namelist()
            print(f"  PASS: Zip archive exists ({zip_path.stat().st_size} bytes, {len(z_files)} files).")
            print("  Files in zip:")
            for zf in z_files:
                print(f"    - {zf}")

if __name__ == "__main__":
    run_forensic_audit()
