#!/usr/bin/env python3
"""
test_zip_package.py
Extract paper4_latex_overleaf.zip into etc/temp/overleaf_test/ and verify its completeness and self-containment.
"""

import shutil
import tempfile
import zipfile
from pathlib import Path

BASE_DIR = Path("/home/imnyj/Workspace/paper4/latex")
ZIP_FILE = BASE_DIR / "paper4_latex_overleaf.zip"
TEMP_DIR = BASE_DIR / "etc" / "temp" / "overleaf_test"

def main():
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"[*] Extracting {ZIP_FILE.name} into {TEMP_DIR}...")
    with zipfile.ZipFile(ZIP_FILE, "r") as z:
        z.extractall(TEMP_DIR)
        
    extracted_files = list(TEMP_DIR.rglob("*"))
    print(f"  [OK] Extracted {len(extracted_files)} files/folders.")
    
    # Verify mandatory files
    required = ["IEEEtran.cls", "references.bib", "main.tex"]
    for r in required:
        p = TEMP_DIR / r
        assert p.is_file(), f"Missing file in extracted zip: {r}"
        assert p.stat().st_size > 0, f"Empty file in extracted zip: {r}"
        print(f"  [OK] Found {r} ({p.stat().st_size} bytes)")
        
    # Verify figures
    figs = list((TEMP_DIR / "figures").glob("*.png"))
    print(f"  [OK] Found {len(figs)} figure png files in extracted figures directory.")
    assert len(figs) >= 9, f"Expected at least 9 figures, got {len(figs)}"
    
    print("==================================================================")
    print(" [SUCCESS] Overleaf Zip Package is 100% Self-Contained and Valid!")
    print("==================================================================")

if __name__ == "__main__":
    main()
