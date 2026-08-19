#!/usr/bin/env python3
"""
Extended Stress Testing Script for Challenger 2
- Test 1: Seed reproducibility and distribution variance of SUMO random generation
- Test 2: Data validity and completeness across all 11 core CSVs
- Test 3: Visualizer deliverables (9 Graph pairs PDF/PNG + 2 Table pairs CSV/TeX = 22 artifacts)
"""

import os
import sys
import hashlib
import tempfile
import pandas as pd
import xml.etree.ElementTree as ET

WORKSPACE = "/home/imnyj/Workspace/paper4"
CONFIG_PATH = os.path.join(WORKSPACE, "config.md")
DATA_DIR = os.path.join(WORKSPACE, "data")
VIS_DIR = os.path.join(WORKSPACE, "visualizer")

sys.path.insert(0, os.path.join(WORKSPACE, "code"))
from sim_engine import load_config, generate_sumonetsim_files

def stress_test_sumo_randomness():
    print("=" * 60)
    print("STRESS TEST 1: SUMO Random Generation Reproducibility & Variance")
    print("=" * 60)
    
    config_0 = {
        "AV_SPEED": 0,
        "DENSITY": 0,
        "NUM_BLOCKS": 6,
        "MAX_STEPS": 3600.0,
        "OUTAGE_ZONE": 800,
        "RSU_RANGE": 800.0,
        "COMM_RANGE_M": 300.0,
        "DATA_RATE_BPS": 3000000,
        "NUM_LANES": 2,
        "SEED": 42
    }
    
    with tempfile.TemporaryDirectory(dir=os.path.join(WORKSPACE, "etc/temp")) as tmp1, \
         tempfile.TemporaryDirectory(dir=os.path.join(WORKSPACE, "etc/temp")) as tmp2, \
         tempfile.TemporaryDirectory(dir=os.path.join(WORKSPACE, "etc/temp")) as tmp3:
        
        # Run 1 with seed=42
        generate_sumonetsim_files(tmp1, config_0, seed=42)
        with open(os.path.join(tmp1, "generated.net.xml"), 'rb') as f:
            hash1 = hashlib.md5(f.read()).hexdigest()
            
        # Run 2 with seed=42 (should be identical hash)
        generate_sumonetsim_files(tmp2, config_0, seed=42)
        with open(os.path.join(tmp2, "generated.net.xml"), 'rb') as f:
            hash2 = hashlib.md5(f.read()).hexdigest()
            
        # Run 3 with seed=999 (should be different hash)
        generate_sumonetsim_files(tmp3, config_0, seed=999)
        with open(os.path.join(tmp3, "generated.net.xml"), 'rb') as f:
            hash3 = hashlib.md5(f.read()).hexdigest()
            
        print(f"[+] Deterministic Reproducibility (seed=42 vs seed=42): {hash1} vs {hash2} -> {'MATCH' if hash1 == hash2 else 'MISMATCH'}")
        assert hash1 == hash2, "Seed reproducibility failed!"
        
        print(f"[+] Random Divergence (seed=42 vs seed=999): {hash1} vs {hash3} -> {'DIFFERENT' if hash1 != hash3 else 'IDENTICAL'}")
        assert hash1 != hash3, "Random divergence failed! Different seeds produced identical net."

    # Test fixed speed / fixed density
    config_fixed = dict(config_0)
    config_fixed["AV_SPEED"] = 60
    config_fixed["DENSITY"] = 20
    with tempfile.TemporaryDirectory(dir=os.path.join(WORKSPACE, "etc/temp")) as tmp_fix:
        generate_sumonetsim_files(tmp_fix, config_fixed, seed=42)
        tree_edg = ET.parse(os.path.join(tmp_fix, "generated.edg.xml"))
        speeds = [float(e.get("speed")) * 3.6 for e in tree_edg.getroot().findall("edge")]
        min_s, max_s, avg_s = min(speeds), max(speeds), sum(speeds)/len(speeds)
        print(f"[+] Fixed Speed (AV_SPEED=60): Min={min_s:.2f} km/h, Max={max_s:.2f} km/h, Avg={avg_s:.2f} km/h")
        assert 48.0 <= min_s and max_s <= 72.0, f"Fixed speed out of 20% tolerance: [{min_s}, {max_s}]"
        
        tree_rou = ET.parse(os.path.join(tmp_fix, "generated.rou.xml"))
        probs = [float(fl.get("probability")) for fl in tree_rou.getroot().findall("flow")]
        unique_probs = len(set(probs))
        print(f"[+] Fixed Density (DENSITY=20): Flow count={len(probs)}, Unique probs={unique_probs} (expected 1 constant flow rate)")
        assert unique_probs == 1, "Fixed density generated varying flow rates!"
        
    print("[✓] SUMO Stress Test PASSED.")

def stress_test_csv_contents():
    print("\n" + "=" * 60)
    print("STRESS TEST 2: Data Validity & Completeness across 11 CSVs")
    print("=" * 60)
    
    target_11_csvs = [
        "ablation_study.csv",
        "optuna_sensitivity_table.csv",
        "reward_convergence.csv",
        "tsne_clustering.csv",
        "moe_routing.csv",
        "cbr_trace.csv",
        "pdr_vs_density.csv",
        "aoi_vs_density.csv",
        "pdr_vs_distance.csv",
        "aoi_vs_distance.csv",
        "hardware_feasibility_table.csv"
    ]
    
    for f in target_11_csvs:
        p = os.path.join(DATA_DIR, f)
        df = pd.read_csv(p)
        null_count = df.isnull().sum().sum()
        shape = df.shape
        print(f"[+] {f:<32}: Shape={str(shape):<10} | Nulls={null_count:<3} | Columns={list(df.columns[:4])}...")
        assert null_count == 0, f"CSV {f} contains null/NaN values!"
        assert shape[0] > 0 and shape[1] > 0, f"CSV {f} is empty!"
        
    print("[✓] All 11 CSV Data Integrity & Cleanliness Verified.")

def stress_test_visualizer_outputs():
    print("\n" + "=" * 60)
    print("STRESS TEST 3: Visualizer Deliverables (9 Graph Pairs + 2 Table Pairs = 22 Artifacts)")
    print("=" * 60)
    
    graph_outputs = [
        ("ablation_study", "pdf", "png"),
        ("reward_convergence", "pdf", "png"),
        ("tsne_clustering", "pdf", "png"),
        ("moe_routing", "pdf", "png"),
        ("cbr_trace", "pdf", "png"),
        ("pdr_vs_density", "pdf", "png"),
        ("aoi_vs_density", "pdf", "png"),
        ("pdr_vs_distance", "pdf", "png"),
        ("aoi_vs_distance", "pdf", "png"),
    ]
    
    table_outputs = [
        ("optuna_sensitivity_table", "csv", "tex"),
        ("hardware_feasibility_table", "csv", "tex"),
    ]
    
    missing = []
    
    print("--- 9 Graph Deliverables (PDF & PNG) ---")
    for name, ext1, ext2 in graph_outputs:
        f1 = os.path.join(VIS_DIR, f"{name}.{ext1}")
        f2 = os.path.join(VIS_DIR, f"{name}.{ext2}")
        
        ok1 = os.path.exists(f1) and os.path.getsize(f1) > 1000
        ok2 = os.path.exists(f2) and os.path.getsize(f2) > 1000
        
        sz1 = os.path.getsize(f1) if os.path.exists(f1) else 0
        sz2 = os.path.getsize(f2) if os.path.exists(f2) else 0
        
        print(f"[+] {name:<25} | {ext1.upper()}: {('OK ('+str(sz1)+' B)' if ok1 else 'MISSING')} | {ext2.upper()}: {('OK ('+str(sz2)+' B)' if ok2 else 'MISSING')}")
        if not ok1: missing.append(f"{name}.{ext1}")
        if not ok2: missing.append(f"{name}.{ext2}")
        
    print("\n--- 2 Table Deliverables (CSV & TeX) ---")
    for name, ext1, ext2 in table_outputs:
        f1 = os.path.join(VIS_DIR, f"{name}.{ext1}")
        f2 = os.path.join(VIS_DIR, f"{name}.{ext2}")
        
        ok1 = os.path.exists(f1) and os.path.getsize(f1) > 500
        ok2 = os.path.exists(f2) and os.path.getsize(f2) > 500
        
        sz1 = os.path.getsize(f1) if os.path.exists(f1) else 0
        sz2 = os.path.getsize(f2) if os.path.exists(f2) else 0
        
        print(f"[+] {name:<25} | {ext1.upper()}: {('OK ('+str(sz1)+' B)' if ok1 else 'MISSING')} | {ext2.upper()}: {('OK ('+str(sz2)+' B)' if ok2 else 'MISSING')}")
        if not ok1: missing.append(f"{name}.{ext1}")
        if not ok2: missing.append(f"{name}.{ext2}")
            
    assert len(missing) == 0, f"Missing visualizer artifacts: {missing}"
    print(f"\n[✓] All 22 visualizer artifacts (18 graph files + 4 table files) present and verified.")

if __name__ == "__main__":
    stress_test_sumo_randomness()
    stress_test_csv_contents()
    stress_test_visualizer_outputs()
    print("\n" + "=" * 60)
    print("ALL EXTENDED STRESS TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
