#!/usr/bin/env python3
"""
Unit tests for Milestone 1: Bibliography & LaTeX Infrastructure Setup.
"""

import os
import re
import sys
import subprocess
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LATEX_DIR = BASE_DIR
FIG_DIR = LATEX_DIR / "figures"
BIB_FILE = LATEX_DIR / "references.bib"
CLS_FILE = LATEX_DIR / "IEEEtran.cls"
MAKEFILE = LATEX_DIR / "Makefile"
VALIDATOR = LATEX_DIR / "etc" / "scripts" / "validate_latex.py"

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

EXPECTED_ORIGINAL_FIGURES = [
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

EXPECTED_STANDARDIZED_FIGURES = [
    "fig1_reward_convergence.png",
    "fig2_cbr_trace.png",
    "fig3_pdr_vs_density.png",
    "fig4_aoi_vs_density.png",
    "fig5_pdr_vs_distance.png",
    "fig6_hardware_feasibility.png",
    "fig7_ablation_study.png",
    "fig8_moe_routing.png",
    "fig9_tsne_clustering.png",
]


def test_directory_structure():
    assert LATEX_DIR.is_dir(), f"LaTeX directory missing: {LATEX_DIR}"
    assert FIG_DIR.is_dir(), f"Figures directory missing: {FIG_DIR}"
    assert (LATEX_DIR / "etc" / "scripts").is_dir(), "etc/scripts/ missing"
    assert (LATEX_DIR / "etc" / "logs").is_dir(), "etc/logs/ missing"


def test_ieeetran_cls():
    assert CLS_FILE.is_file(), f"IEEEtran.cls missing at {CLS_FILE}"
    content = CLS_FILE.read_text(encoding="utf-8", errors="ignore")
    assert "IEEEtran.cls" in content, "IEEEtran.cls file does not contain class identifier"
    assert "V1.8b" in content or "1.8" in content, "IEEEtran.cls version mismatch"
    assert CLS_FILE.stat().st_size > 200000, "IEEEtran.cls file size is suspiciously small"


def test_figures_exist_and_are_valid_png():
    PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
    for fname in EXPECTED_ORIGINAL_FIGURES:
        fpath = FIG_DIR / fname
        assert fpath.is_file(), f"Missing original figure: {fname}"
        with open(fpath, "rb") as f:
            header = f.read(8)
            assert header == PNG_MAGIC, f"File {fname} is not a valid PNG"
        assert fpath.stat().st_size > 1000, f"File {fname} size is too small"

    for fname in EXPECTED_STANDARDIZED_FIGURES:
        fpath = FIG_DIR / fname
        assert fpath.is_file(), f"Missing standardized figure alias: {fname}"
        with open(fpath, "rb") as f:
            header = f.read(8)
            assert header == PNG_MAGIC, f"File {fname} is not a valid PNG"
        assert fpath.stat().st_size > 1000, f"File {fname} size is too small"


def test_references_bib_entries():
    assert BIB_FILE.is_file(), f"references.bib missing at {BIB_FILE}"
    content = BIB_FILE.read_text(encoding="utf-8")
    
    entry_pattern = re.compile(r"@(\w+)\s*\{\s*([^,]+),", re.MULTILINE)
    matches = entry_pattern.findall(content)
    found_keys = [m[1].strip() for m in matches]

    assert len(found_keys) == 27, f"Expected exactly 27 BibTeX entries, found {len(found_keys)}"
    assert len(set(found_keys)) == 27, "Duplicate citation keys detected"

    for expected_key in EXPECTED_27_KEYS:
        assert expected_key in found_keys, f"Missing citation key: {expected_key}"

    # Check that required fields exist in bib content
    assert "author" in content
    assert "title" in content
    assert "year" in content


def test_makefile():
    assert MAKEFILE.is_file(), f"Makefile missing at {MAKEFILE}"
    content = MAKEFILE.read_text(encoding="utf-8")
    for target in ["all:", "validate:", "check:", "zip:", "compile:", "clean:"]:
        assert target in content, f"Makefile missing target: {target}"


def test_validate_latex_script_execution():
    assert VALIDATOR.is_file(), f"Validator missing at {VALIDATOR}"
    res = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Validator script failed with output:\n{res.stdout}\n{res.stderr}"
    assert "ALL INTEGRITY & VALIDATION CHECKS PASSED" in res.stdout
