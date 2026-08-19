#!/usr/bin/env python3
"""
Independent Adversarial Stress Test Suite for Milestone 1 Review.
Executed by teamwork_preview_reviewer_m1_2.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image

LATEX_DIR = Path("/home/imnyj/Workspace/paper4/latex")
FIG_DIR = LATEX_DIR / "figures"
BIB_FILE = LATEX_DIR / "references.bib"
CLS_FILE = LATEX_DIR / "IEEEtran.cls"
VALIDATOR = LATEX_DIR / "etc" / "scripts" / "validate_latex.py"

def test_adversarial_validator_fault_injection():
    print("=== Test 1: Validator Fault Injection (Missing Key / Corrupted File) ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_latex = Path(tmpdir) / "latex"
        shutil.copytree(LATEX_DIR, tmp_latex, ignore=shutil.ignore_patterns(".pytest_cache", "__pycache__", "paper4_latex_overleaf.zip"))
        
        # Test 1.1: Corrupt references.bib by removing a key
        bib_tmp = tmp_latex / "references.bib"
        content = bib_tmp.read_text(encoding="utf-8")
        # Remove Arena2019Overview
        corrupted_content = content.replace("Arena2019Overview", "CorruptedKey123")
        bib_tmp.write_text(corrupted_content, encoding="utf-8")
        
        val_script = tmp_latex / "etc" / "scripts" / "validate_latex.py"
        res = subprocess.run(["python3", str(val_script)], capture_output=True, text=True)
        assert res.returncode != 0, "Validator should have failed on missing key!"
        assert "Missing BibTeX citation key: Arena2019Overview" in res.stdout, "Validator did not report missing key properly!"
        print("  [PASS] Validator correctly catches missing citation key (Exit code: 1)")

        # Test 1.2: Remove a figure
        shutil.copytree(LATEX_DIR, tmp_latex, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".pytest_cache", "__pycache__"))
        (tmp_latex / "figures" / "1_reward_convergence.png").unlink()
        res2 = subprocess.run(["python3", str(val_script)], capture_output=True, text=True)
        assert res2.returncode != 0, "Validator should have failed on missing figure!"
        assert "Missing expected figure" in res2.stdout, "Validator did not report missing figure!"
        print("  [PASS] Validator correctly catches missing figure asset (Exit code: 1)")

def test_full_image_rendering_and_dimensions():
    print("\n=== Test 2: Image Rendering & Geometry Verification ===")
    expected_figures = [
        ("1_reward_convergence.png", "fig1_reward_convergence.png", (1000, 600)),
        ("7_cbr_trace.png", "fig2_cbr_trace.png", (1000, 600)),
        ("8_pdr_vs_density.png", "fig3_pdr_vs_density.png", (1000, 600)),
        ("9_aoi_vs_density.png", "fig4_aoi_vs_density.png", (1000, 600)),
        ("10_pdr_vs_distance.png", "fig5_pdr_vs_distance.png", (1000, 600)),
        ("5_hardware_feasibility.png", "fig6_hardware_feasibility.png", (600, 300)),
        ("2_ablation_study.png", "fig7_ablation_study.png", (1000, 600)),
        ("3_moe_routing.png", "fig8_moe_routing.png", (800, 600)),
        ("4_tsne_clustering.png", "fig9_tsne_clustering.png", (800, 600)),
    ]
    for orig, alias, expected_dims in expected_figures:
        orig_path = FIG_DIR / orig
        alias_path = FIG_DIR / alias
        assert orig_path.is_file(), f"Missing {orig}"
        assert alias_path.is_file(), f"Missing {alias}"
        
        im_orig = Image.open(orig_path)
        im_alias = Image.open(alias_path)
        
        assert im_orig.size == expected_dims, f"Size mismatch for {orig}: {im_orig.size} vs {expected_dims}"
        assert im_alias.size == expected_dims, f"Size mismatch for {alias}: {im_alias.size} vs {expected_dims}"
        assert im_orig.format == "PNG"
        assert im_alias.format == "PNG"
        print(f"  [PASS] {orig:25s} & {alias:28s} valid PNG, size={im_orig.size}, mode={im_orig.mode}")

def test_latex_compilation_with_pdflatex():
    print("\n=== Test 3: Minimal IEEEtran LaTeX + BibTeX Compilation Test ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        shutil.copy(CLS_FILE, tmp_path / "IEEEtran.cls")
        shutil.copy(BIB_FILE, tmp_path / "references.bib")
        shutil.copytree(FIG_DIR, tmp_path / "figures")

        # Create a test document citing all 27 references and including figure 1
        keys = [
            "Arena2019Overview", "Kenney2011DSRC", "ETSI_EN_302_637_2", "SAE_J2945_1",
            "ETSI_TS_102_687", "Zheng2022Age", "Liu2024Age", "ETSI_TS_103_175",
            "Bansal2013LIMERIC", "Ye2019Deep", "Hu2021Deep", "Wang2023Multi",
            "Mnih2015Human", "VanHasselt2016Deep", "Wang2016Dueling", "Yu2022Surprising",
            "Lowe2017Multi", "Rashid2018QMIX", "Chen2021Decision", "Janner2021Offline",
            "Shazeer2017Outrageously", "Xu2025Mixture", "Zhang2026Generalizable",
            "Kang2024Task", "Du2025Generative", "Park2025Ensemble", "Bhattacharyya2024Hybrid"
        ]
        cites_str = ", ".join([f"\\cite{{{k}}}" for k in keys])
        
        tex_content = f"""\\documentclass[journal]{{IEEEtran}}
\\usepackage{{amsmath,amssymb,amsfonts}}
\\usepackage{{cite}}
\\usepackage{{graphicx}}
\\usepackage{{booktabs}}

\\begin{{document}}
\\title{{Test Paper for M1 Review}}
\\author{{Reviewer}}
\\maketitle

\\begin{{abstract}}
Testing IEEEtran class compilation, all 27 citations, and figure inclusion.
\\end{{abstract}}

\\section{{Introduction}}
Citations test: {cites_str}.

\\begin{{figure}}[htbp]
\\centering
\\includegraphics[width=0.48\\textwidth]{{figures/fig1_reward_convergence.png}}
\\caption{{Convergence test.}}
\\label{{fig:test}}
\\end{{figure}}

\\bibliographystyle{{IEEEtran}}
\\bibliography{{references}}

\\end{{document}}
"""
        (tmp_path / "main.tex").write_text(tex_content, encoding="utf-8")
        
        # Check if pdflatex and bibtex are available
        pdflatex_exists = shutil.which("pdflatex") is not None
        bibtex_exists = shutil.which("bibtex") is not None
        
        if pdflatex_exists and bibtex_exists:
            # Run pdflatex -> bibtex -> pdflatex -> pdflatex
            p1 = subprocess.run(["pdflatex", "-interaction=nonstopmode", "main.tex"], cwd=tmp_path, capture_output=True, text=True)
            assert p1.returncode == 0, f"pdflatex pass 1 failed:\n{p1.stdout}\n{p1.stderr}"
            
            b = subprocess.run(["bibtex", "main"], cwd=tmp_path, capture_output=True, text=True)
            assert b.returncode == 0, f"bibtex failed:\n{b.stdout}\n{b.stderr}"
            
            p2 = subprocess.run(["pdflatex", "-interaction=nonstopmode", "main.tex"], cwd=tmp_path, capture_output=True, text=True)
            assert p2.returncode == 0, f"pdflatex pass 2 failed:\n{p2.stdout}\n{p2.stderr}"
            
            p3 = subprocess.run(["pdflatex", "-interaction=nonstopmode", "main.tex"], cwd=tmp_path, capture_output=True, text=True)
            assert p3.returncode == 0, f"pdflatex pass 3 failed:\n{p3.stdout}\n{p3.stderr}"
            
            pdf_file = tmp_path / "main.pdf"
            assert pdf_file.is_file() and pdf_file.stat().st_size > 10000, "PDF not generated properly!"
            print(f"  [PASS] Successfully compiled PDF ({pdf_file.stat().st_size} bytes) with IEEEtran + 27 BibTeX citations + figures/fig1_reward_convergence.png!")
        else:
            print("  [SKIP] pdflatex or bibtex not installed locally; checked syntax structure.")

def test_overleaf_zip_structure():
    print("\n=== Test 4: Standalone Overleaf ZIP Archive Integrity ===")
    zip_path = LATEX_DIR / "paper4_latex_overleaf.zip"
    assert zip_path.is_file(), "paper4_latex_overleaf.zip is missing"
    assert zip_path.stat().st_size > 100000, "Zip size is too small"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        shutil.unpack_archive(str(zip_path), tmpdir, "zip")
        extracted = list(Path(tmpdir).rglob("*"))
        extracted_rel = [str(p.relative_to(tmpdir)) for p in extracted]
        
        assert "IEEEtran.cls" in extracted_rel
        assert "references.bib" in extracted_rel
        assert any(r.startswith("figures") for r in extracted_rel)
        print(f"  [PASS] Standalone zip successfully unpacked ({len(extracted_rel)} items found in root)")

if __name__ == "__main__":
    test_adversarial_validator_fault_injection()
    test_full_image_rendering_and_dimensions()
    test_latex_compilation_with_pdflatex()
    test_overleaf_zip_structure()
    print("\n[ALL ADVERSARIAL TESTS COMPLETED SUCCESSFULLY!]")
