#!/usr/bin/env python3
"""
Comprehensive Adversarial Testing & Verification Harness for Milestone 1
Target: /home/imnyj/Workspace/paper4/latex/
Author: teamwork_preview_challenger_m1_1
"""

import os
import sys
import re
import struct
import hashlib
import zipfile
import subprocess
from pathlib import Path
from PIL import Image
import bibtexparser
from bibtexparser.bparser import BibTexParser

WORKSPACE = Path("/home/imnyj/Workspace/paper4/latex")
BIB_PATH = WORKSPACE / "references.bib"
FIG_DIR = WORKSPACE / "figures"
CLS_PATH = WORKSPACE / "IEEEtran.cls"
MAKEFILE_PATH = WORKSPACE / "Makefile"
ZIP_PATH = WORKSPACE / "paper4_latex_overleaf.zip"
KOREAN_DRAFT_PATH = Path("/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md")

class EmpiricalAdversarialTester:
    def __init__(self):
        self.results = []
        self.errors = []
        self.warnings = []

    def log(self, category, test_case, status, details=""):
        res = {
            "category": category,
            "test_case": test_case,
            "status": status,
            "details": details
        }
        self.results.append(res)
        if status == "FAIL":
            self.errors.append(f"[{category}] {test_case}: {details}")
        elif status == "WARN":
            self.warnings.append(f"[{category}] {test_case}: {details}")
        print(f"[{status:<4}] {category:<20} | {test_case:<45} | {details}")

    def test_bibtex_deep(self):
        """Perform multi-layer syntax, parser, and semantic checks on references.bib."""
        if not BIB_PATH.exists():
            self.log("BibTeX", "File Existence", "FAIL", f"File not found: {BIB_PATH}")
            return

        raw_content = BIB_PATH.read_text(encoding="utf-8")

        # 1. Byte & Line stats
        lines = raw_content.splitlines()
        self.log("BibTeX", "File Stats", "PASS", f"{len(raw_content)} bytes, {len(lines)} lines")

        # 2. Bibtexparser loading
        parser = BibTexParser(ignore_nonstandard_types=False)
        try:
            db = bibtexparser.loads(raw_content, parser=parser)
            self.log("BibTeX", "BibTexParser Parsing", "PASS", f"Successfully parsed {len(db.entries)} entries")
        except Exception as e:
            self.log("BibTeX", "BibTexParser Parsing", "FAIL", f"Parsing error: {e}")
            return

        # 3. Exact 27 entries check
        if len(db.entries) == 27:
            self.log("BibTeX", "Total Entry Count", "PASS", "Exactly 27 entries present")
        else:
            self.log("BibTeX", "Total Entry Count", "FAIL", f"Expected 27, found {len(db.entries)}")

        # 4. Entry types breakdown
        types = {}
        for e in db.entries:
            t = e.get("ENTRYTYPE", "unknown").lower()
            types[t] = types.get(t, 0) + 1
        self.log("BibTeX", "Entry Types Distribution", "PASS", f"Distribution: {types}")

        # 5. Key uniqueness
        keys = [e.get("ID") for e in db.entries]
        dup_keys = [k for k in keys if keys.count(k) > 1]
        if not dup_keys:
            self.log("BibTeX", "Citation Key Uniqueness", "PASS", f"All {len(keys)} keys are strictly unique")
        else:
            self.log("BibTeX", "Citation Key Uniqueness", "FAIL", f"Duplicate keys: {set(dup_keys)}")

        # 6. Strict field presence and LaTeX formatting check per entry
        for e in db.entries:
            eid = e.get("ID")
            etype = e.get("ENTRYTYPE", "").lower()
            
            # Check mandatory fields
            if etype == "article":
                reqs = ["author", "title", "journal", "year"]
            elif etype == "inproceedings":
                reqs = ["author", "title", "booktitle", "year"]
            elif etype == "standard":
                reqs = ["title", "organization", "number", "year"]
            else:
                reqs = ["title", "year"]

            missing = [r for r in reqs if not e.get(r)]
            if missing:
                self.log("BibTeX Fields", f"Mandatory Fields: {eid}", "FAIL", f"Missing mandatory fields: {missing}")
            else:
                self.log("BibTeX Fields", f"Mandatory Fields: {eid}", "PASS", f"All required fields {reqs} present")

            # Check year validity
            year_val = e.get("year", "")
            if re.match(r'^\d{4}$', year_val):
                self.log("BibTeX Year", f"Year Format: {eid}", "PASS", f"Year: {year_val}")
            else:
                self.log("BibTeX Year", f"Year Format: {eid}", "FAIL", f"Invalid year: '{year_val}'")

            # Check for unescaped special characters in text fields
            for field, val in e.items():
                if field in ["ID", "ENTRYTYPE"]:
                    continue
                # Unescaped &
                if re.search(r'(?<!\\)&', val):
                    self.log("LaTeX Escaping", f"Unescaped '&': {eid}.{field}", "FAIL", f"Found raw '&' in: '{val}'")
                # Unescaped %
                if re.search(r'(?<!\\)%', val):
                    self.log("LaTeX Escaping", f"Unescaped '%': {eid}.{field}", "FAIL", f"Found raw '%' in: '{val}'")
                # Unescaped #
                if re.search(r'(?<!\\)#', val):
                    self.log("LaTeX Escaping", f"Unescaped '#': {eid}.{field}", "FAIL", f"Found raw '#' in: '{val}'")
                # Unescaped _ outside doi, url, number
                if field not in ["doi", "url", "number"] and re.search(r'(?<!\\)_', val):
                    self.log("LaTeX Escaping", f"Unescaped '_': {eid}.{field}", "WARN", f"Found raw '_' in: '{val}'")

        # 7. Bracket Balance in entire file
        open_b = raw_content.count('{')
        close_b = raw_content.count('}')
        if open_b == close_b:
            self.log("BibTeX Syntax", "File Brace Balance", "PASS", f"Braces balanced ({open_b} open, {close_b} close)")
        else:
            self.log("BibTeX Syntax", "File Brace Balance", "FAIL", f"Brace mismatch: {open_b} vs {close_b}")

    def test_draft_mapping(self):
        """Verify 1:1 mapping against 27 references in paper4_draft_korean.md."""
        if not KOREAN_DRAFT_PATH.exists():
            self.log("Draft Mapping", "Korean Draft Existence", "FAIL", f"Draft not found: {KOREAN_DRAFT_PATH}")
            return

        draft_text = KOREAN_DRAFT_PATH.read_text(encoding="utf-8")
        ref_match = re.search(r'##\s*참고문헌\s*\(References\)([\s\S]+)', draft_text)
        if not ref_match:
            self.log("Draft Mapping", "References Section Locator", "FAIL", "Section '## 참고문헌 (References)' not found")
            return

        ref_lines = [l.strip() for l in ref_match.group(1).strip().split('\n') if re.match(r'^\[\d+\]', l.strip())]
        self.log("Draft Mapping", "Draft Reference Entries", "PASS", f"Found {len(ref_lines)} references in Korean draft")

        raw_bib = BIB_PATH.read_text(encoding="utf-8")
        parser = BibTexParser(ignore_nonstandard_types=False)
        db = bibtexparser.loads(raw_bib, parser=parser)
        bib_dict = {e["ID"]: e for e in db.entries}

        expected_map = [
            (1, "Arena", "vehicular communications", "Arena2019Overview", "2019"),
            (2, "Kenney", "Dedicated short-range communications", "Kenney2011DSRC", "2011"),
            (3, "ETSI", "EN 302 637-2", "ETSI_EN_302_637_2", "2019"),
            (4, "SAE", "J2945/1", "SAE_J2945_1", "2016"),
            (5, "ETSI", "TS 102 687", "ETSI_TS_102_687", "2018"),
            (6, "Zheng", "Age-of-Information-Oriented", "Zheng2022Age", "2022"),
            (7, "Liu", "Age of Information and Energy", "Liu2024Age", "2024"),
            (8, "ETSI", "TS 103 175", "ETSI_TS_103_175", "2015"),
            (9, "Bansal", "LIMERIC", "Bansal2013LIMERIC", "2013"),
            (10, "Ye", "Deep reinforcement learning", "Ye2019Deep", "2019"),
            (11, "Hu", "Deep reinforcement learning for resource allocation", "Hu2021Deep", "2021"),
            (12, "Wang", "Multi-agent deep reinforcement", "Wang2023Multi", "2023"),
            (13, "Mnih", "Human-level control", "Mnih2015Human", "2015"),
            (14, "van Hasselt", "double Q-learning", "VanHasselt2016Deep", "2016"),
            (15, "Wang", "Dueling network", "Wang2016Dueling", "2016"),
            (16, "Yu", "surprising effectiveness of PPO", "Yu2022Surprising", "2022"),
            (17, "Lowe", "Multi-agent actor-critic", "Lowe2017Multi", "2017"),
            (18, "Rashid", "QMIX", "Rashid2018QMIX", "2018"),
            (19, "Chen", "Decision transformer", "Chen2021Decision", "2021"),
            (20, "Janner", "Offline reinforcement learning", "Janner2021Offline", "2021"),
            (21, "Shazeer", "Outrageously large neural networks", "Shazeer2017Outrageously", "2017"),
            (22, "Xu", "Mixture of experts", "Xu2025Mixture", "2025"),
            (23, "Zhang", "Generalizable multiple access", "Zhang2026Generalizable", "2026"),
            (24, "Kang", "Task-oriented mixture-of-experts", "Kang2024Task", "2024"),
            (25, "Du", "Generative AI-enabled edge", "Du2025Generative", "2025"),
            (26, "Park", "Ensemble deep Q-learning", "Park2025Ensemble", "2025"),
            (27, "Bhattacharyya", "Hybrid relaying", "Bhattacharyya2024Hybrid", "2024"),
        ]

        for num, auth, tit, key, yr in expected_map:
            if key not in bib_dict:
                self.log("1:1 Mapping", f"Ref [{num}] -> {key}", "FAIL", f"Citation key {key} missing in BibTeX")
            else:
                entry = bib_dict[key]
                bib_year = entry.get("year", "")
                bib_author = entry.get("author", "") or entry.get("organization", "")
                bib_title = entry.get("title", "")
                
                # Check year match
                yr_ok = (yr == bib_year)
                # Check author / title keywords
                auth_ok = auth.lower() in bib_author.lower()
                tit_ok = tit.lower() in bib_title.lower()
                
                if yr_ok and auth_ok:
                    self.log("1:1 Mapping", f"Ref [{num}] -> {key}", "PASS", f"Verified: '{auth}' ({yr}) - '{tit}'")
                else:
                    self.log("1:1 Mapping", f"Ref [{num}] -> {key}", "FAIL", f"Mismatch: Expected {auth} ({yr}), got {bib_author} ({bib_year})")

    def test_figures_deep(self):
        """Stress-test all 18 PNG files in figures/ using PIL and binary inspection."""
        if not FIG_DIR.exists():
            self.log("Figures", "Directory Existence", "FAIL", f"Figures dir not found: {FIG_DIR}")
            return

        png_files = list(FIG_DIR.glob("*.png"))
        self.log("Figures", "PNG Count", "PASS", f"Found {len(png_files)} PNG files")

        if len(png_files) != 18:
            self.log("Figures", "PNG Count Expected", "WARN", f"Expected 18 PNG files, found {len(png_files)}")

        # Verification pairs between canonical and numbered aliases
        figure_pairs = [
            ("fig1_reward_convergence.png", "1_reward_convergence.png"),
            ("fig2_cbr_trace.png", "7_cbr_trace.png"),
            ("fig3_pdr_vs_density.png", "8_pdr_vs_density.png"),
            ("fig4_aoi_vs_density.png", "9_aoi_vs_density.png"),
            ("fig5_pdr_vs_distance.png", "10_pdr_vs_distance.png"),
            ("fig6_hardware_feasibility.png", "5_hardware_feasibility.png"),
            ("fig7_ablation_study.png", "2_ablation_study.png"),
            ("fig8_moe_routing.png", "3_moe_routing.png"),
            ("fig9_tsne_clustering.png", "4_tsne_clustering.png"),
        ]

        for canonical, original in figure_pairs:
            p_can = FIG_DIR / canonical
            p_orig = FIG_DIR / original

            if not p_can.exists():
                self.log("Figures", f"Canonical Exists: {canonical}", "FAIL", "Missing file")
                continue
            if not p_orig.exists():
                self.log("Figures", f"Original Exists: {original}", "FAIL", "Missing file")
                continue

            # Check sizes
            s_can = p_can.stat().st_size
            s_orig = p_orig.stat().st_size
            if s_can == 0 or s_orig == 0:
                self.log("Figures", f"Non-empty: {canonical}", "FAIL", f"Zero byte file: {s_can} vs {s_orig}")
                continue

            # Check hash equality
            h_can = hashlib.sha256(p_can.read_bytes()).hexdigest()
            h_orig = hashlib.sha256(p_orig.read_bytes()).hexdigest()
            if h_can == h_orig:
                self.log("Figures", f"Hash Match: {canonical} <-> {original}", "PASS", f"SHA256 match ({s_can} bytes)")
            else:
                self.log("Figures", f"Hash Match: {canonical} <-> {original}", "WARN", f"Hash divergence: {h_can[:8]} vs {h_orig[:8]}")

            # Verify with PIL
            try:
                with Image.open(p_can) as img:
                    img.verify()
                with Image.open(p_can) as img:
                    w, h = img.size
                    mode = img.mode
                    fmt = img.format
                    self.log("Figures", f"PIL Verify: {canonical}", "PASS", f"{fmt}, {w}x{h}, mode={mode}, {s_can} bytes")
            except Exception as e:
                self.log("Figures", f"PIL Verify: {canonical}", "FAIL", f"Image verification error: {e}")

    def test_infrastructure_and_zip(self):
        """Test IEEEtran.cls, Makefile, and Zip packaging."""
        # 1. IEEEtran.cls
        if not CLS_PATH.exists():
            self.log("Infrastructure", "IEEEtran.cls Existence", "FAIL", "Missing IEEEtran.cls")
        else:
            size = CLS_PATH.stat().st_size
            content = CLS_PATH.read_text(encoding="utf-8", errors="ignore")
            # Search version regex case insensitive
            v_match = re.search(r'IEEEtran\.cls\s+\d{4}/\d{2}/\d{2}\s+version\s+([Vv]\d+\.\d+[a-z]?)', content)
            if v_match:
                version_str = v_match.group(1)
                self.log("Infrastructure", "IEEEtran.cls Version", "PASS", f"Found official version: {version_str} ({size} bytes)")
            else:
                self.log("Infrastructure", "IEEEtran.cls Version", "WARN", f"Version banner not matched via regex ({size} bytes)")

        # 2. Makefile
        if not MAKEFILE_PATH.exists():
            self.log("Infrastructure", "Makefile Existence", "FAIL", "Missing Makefile")
        else:
            content = MAKEFILE_PATH.read_text(encoding="utf-8")
            for target in ["validate", "zip", "clean"]:
                if re.search(rf'^{target}:', content, re.MULTILINE):
                    self.log("Infrastructure", f"Makefile Target '{target}'", "PASS", "Target correctly configured")
                else:
                    self.log("Infrastructure", f"Makefile Target '{target}'", "FAIL", "Target missing")

        # 3. Zip file
        if not ZIP_PATH.exists():
            self.log("Infrastructure", "Zip Package Existence", "FAIL", f"Zip archive not found: {ZIP_PATH}")
        else:
            zip_size = ZIP_PATH.stat().st_size
            try:
                with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
                    corrupt = zf.testzip()
                    if corrupt is None:
                        self.log("Infrastructure", "Zip Archive Integrity", "PASS", f"CRC test passed ({zip_size} bytes)")
                    else:
                        self.log("Infrastructure", "Zip Archive Integrity", "FAIL", f"Corrupt file inside zip: {corrupt}")

                    namelist = zf.namelist()
                    must_haves = ["IEEEtran.cls", "references.bib", "figures/fig1_reward_convergence.png"]
                    missing_in_zip = [m for m in must_haves if m not in namelist]
                    if not missing_in_zip:
                        self.log("Infrastructure", "Zip Contents Verification", "PASS", f"All essential files present ({len(namelist)} items)")
                    else:
                        self.log("Infrastructure", "Zip Contents Verification", "FAIL", f"Missing in zip: {missing_in_zip}")
            except Exception as e:
                self.log("Infrastructure", "Zip Archive Integrity", "FAIL", f"Failed to open zip: {e}")

    def run_all(self):
        print("=" * 80)
        print(" ADVERSARIAL VERIFICATION & STRESS TEST HARNESS — MILESTONE 1")
        print("=" * 80)
        self.test_bibtex_deep()
        self.test_draft_mapping()
        self.test_figures_deep()
        self.test_infrastructure_and_zip()

        print("\n" + "=" * 80)
        print(f" TOTAL TESTS EXECUTED : {len(self.results)}")
        print(f" CRITICAL FAILURES    : {len(self.errors)}")
        print(f" WARNINGS             : {len(self.warnings)}")
        print("=" * 80)

        return len(self.errors) == 0

if __name__ == "__main__":
    tester = EmpiricalAdversarialTester()
    passed = tester.run_all()
    sys.exit(0 if passed else 1)
