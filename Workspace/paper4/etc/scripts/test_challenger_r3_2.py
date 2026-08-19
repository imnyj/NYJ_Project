#!/usr/bin/env python3
"""
Empirical Challenger 2 Verification Script
- Task 1: config.md parsing & SUMO integration integrity (AV_SPEED=0, DENSITY=0 random sampling)
- Task 2: data/ vs coder/data/ 11 core CSV files byte-level exact identity
- Task 3: walkthrough.md 112 checklist items 100% completion scan
"""

import os
import sys
import hashlib
import re
import tempfile
import xml.etree.ElementTree as ET

WORKSPACE = "/home/imnyj/Workspace/paper4"
CONFIG_PATH = os.path.join(WORKSPACE, "config.md")
WALKTHROUGH_PATH = os.path.join(WORKSPACE, "walkthrough.md")
DATA_DIR = os.path.join(WORKSPACE, "data")
CODER_DATA_DIR = os.path.join(WORKSPACE, "coder/data")

def check_task1_sumo():
    print("=" * 60)
    print("TASK 1: config.md Parsing & SUMO Integration Integrity")
    print("=" * 60)
    
    # 1. Check config.md parsing using code/sim_engine.py load_config
    sys.path.insert(0, os.path.join(WORKSPACE, "code"))
    from sim_engine import load_config, generate_sumonetsim_files
    
    config = load_config(CONFIG_PATH)
    print(f"[+] Loaded config from {CONFIG_PATH}:")
    for k, v in config.items():
        print(f"    - {k}: {v} ({type(v).__name__})")
        
    assert "AV_SPEED" in config, "AV_SPEED missing from config"
    assert "DENSITY" in config, "DENSITY missing from config"
    
    # 2. Test empirical generation with AV_SPEED=0, DENSITY=0
    test_config = dict(config)
    test_config["AV_SPEED"] = 0
    test_config["DENSITY"] = 0
    test_config["SEED"] = 12345
    
    with tempfile.TemporaryDirectory(dir=os.path.join(WORKSPACE, "etc/temp")) as tmpdir:
        print(f"\n[+] Testing SUMO file generation with AV_SPEED=0, DENSITY=0 in {tmpdir}...")
        success = generate_sumonetsim_files(tmpdir, test_config, seed=12345)
        print(f"    - generate_sumonetsim_files return status: {success}")
        
        # Verify generated make_sumo_set.py
        gen_script = os.path.join(tmpdir, "make_sumo_set.py")
        assert os.path.exists(gen_script), "make_sumo_set.py not created"
        with open(gen_script, 'r') as f:
            script_code = f.read()
            
        print("    - Checking injected variables in generated make_sumo_set.py:")
        for var in ["AV_SPEED", "DENSITY", "NUM_BLOCKS", "RSU_RANGE", "OUTAGE_ZONE"]:
            match = re.search(rf"^{var}\s*=\s*(.*)", script_code, re.MULTILINE)
            print(f"      * {var} = {match.group(1) if match else 'NOT FOUND'}")
            
        # Check generated.edg.xml for edge speeds
        edg_path = os.path.join(tmpdir, "generated.edg.xml")
        assert os.path.exists(edg_path), f"{edg_path} does not exist"
        tree_edg = ET.parse(edg_path)
        speeds = [float(e.get("speed")) for e in tree_edg.getroot().findall("edge")]
        min_spd_kmh = min(speeds) * 3.6
        max_spd_kmh = max(speeds) * 3.6
        avg_spd_kmh = (sum(speeds) / len(speeds)) * 3.6
        unique_speeds = len(set(speeds))
        print(f"\n    - Generated {len(speeds)} edges:")
        print(f"      * Min speed: {min_spd_kmh:.2f} km/h (expected >= 10.0 km/h)")
        print(f"      * Max speed: {max_spd_kmh:.2f} km/h (expected <= 120.0 km/h)")
        print(f"      * Avg speed: {avg_spd_kmh:.2f} km/h")
        print(f"      * Unique speed count: {unique_speeds} (randomness verified)")
        assert min_spd_kmh >= 9.99 and max_spd_kmh <= 120.01, f"Speed out of bounds: [{min_spd_kmh}, {max_spd_kmh}]"
        assert unique_speeds > 10, "Speed randomization failed (all speeds identical)"
        
        # Check generated.rou.xml for flow probabilities
        rou_path = os.path.join(tmpdir, "generated.rou.xml")
        assert os.path.exists(rou_path), f"{rou_path} does not exist"
        tree_rou = ET.parse(rou_path)
        flows = tree_rou.getroot().findall("flow")
        probs = [float(fl.get("probability")) for fl in flows]
        unique_probs = len(set(probs))
        print(f"\n    - Generated {len(flows)} traffic flows:")
        print(f"      * Min flow probability: {min(probs):.6f}")
        print(f"      * Max flow probability: {max(probs):.6f}")
        print(f"      * Unique probability count: {unique_probs} (density randomization verified)")
        assert unique_probs > 1, "Density randomization failed (all probabilities identical)"
        
        # Check generated.net.xml
        net_path = os.path.join(tmpdir, "generated.net.xml")
        assert os.path.exists(net_path), f"{net_path} does not exist"
        print(f"    - generated.net.xml size: {os.path.getsize(net_path)} bytes")

    print("\n[✓] Task 1 PASSED: config.md parsing and SUMO random sampling (AV_SPEED=0, DENSITY=0) fully verified.")

def check_task2_csv_integrity():
    print("\n" + "=" * 60)
    print("TASK 2: data/ vs coder/data/ 11 Core CSV Files Byte-Level Identity")
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
    
    # Also check if hardware_feasibility.csv exists
    all_csvs = sorted(list(set(target_11_csvs + ["hardware_feasibility.csv", "optuna_sensitivity.csv"])))
    
    results = []
    all_11_identical = True
    
    print(f"{'Filename':<32} | {'data/ Bytes':<11} | {'coder/ Bytes':<12} | {'Byte Match':<10} | {'MD5 (data/)':<32}")
    print("-" * 105)
    
    for filename in all_csvs:
        p1 = os.path.join(DATA_DIR, filename)
        p2 = os.path.join(CODER_DATA_DIR, filename)
        
        exists1 = os.path.exists(p1)
        exists2 = os.path.exists(p2)
        
        if not exists1 or not exists2:
            print(f"{filename:<32} | {'MISSING' if not exists1 else os.path.getsize(p1):<11} | {'MISSING' if not exists2 else os.path.getsize(p2):<12} | {'NO':<10} | -")
            if filename in target_11_csvs:
                all_11_identical = False
            continue
            
        with open(p1, 'rb') as f1, open(p2, 'rb') as f2:
            c1 = f1.read()
            c2 = f2.read()
            
        md5_1 = hashlib.md5(c1).hexdigest()
        md5_2 = hashlib.md5(c2).hexdigest()
        byte_match = (c1 == c2)
        
        is_target = filename in target_11_csvs
        if is_target and not byte_match:
            all_11_identical = False
            
        tag = "[11-TARGET]" if is_target else "[EXTRA]"
        print(f"{filename:<32} | {len(c1):<11} | {len(c2):<12} | {('EXACT' if byte_match else 'DIFF'):<10} | {md5_1:<32} {tag}")
        
    print(f"\n[+] 11 Core CSV 100% Byte-Level Identity Result: {'PASSED (100% Identical)' if all_11_identical else 'FAILED'}")
    assert all_11_identical, "11 Core CSV files are not 100% byte identical between data/ and coder/data/!"
    print("[✓] Task 2 PASSED: All 11 core CSV files are 100% byte-for-byte identical.")

def check_task3_walkthrough():
    print("\n" + "=" * 60)
    print("TASK 3: walkthrough.md 112 Checklist Items Full Scan")
    print("=" * 60)
    
    assert os.path.exists(WALKTHROUGH_PATH), f"{WALKTHROUGH_PATH} missing"
    
    with open(WALKTHROUGH_PATH, 'r') as f:
        lines = f.readlines()
        
    checklist_pattern = re.compile(r'^\s*[-*]\s*\[([ xX])\]\s*(.*)$')
    
    items = []
    for line_idx, line in enumerate(lines, start=1):
        m = checklist_pattern.match(line)
        if m:
            box = m.group(1)
            desc = m.group(2).strip()
            status = 'checked' if box in ['x', 'X'] else 'unchecked'
            items.append({
                'line': line_idx,
                'status': status,
                'desc': desc
            })
            
    total_count = len(items)
    checked_count = sum(1 for it in items if it['status'] == 'checked')
    unchecked_count = sum(1 for it in items if it['status'] == 'unchecked')
    
    print(f"[+] Total checklist items scanned: {total_count}")
    print(f"    - Checked ([x]): {checked_count}")
    print(f"    - Unchecked ([ ]): {unchecked_count}")
    
    print("\n[+] Full Breakdown by Category in walkthrough.md:")
    curr_cat = "General"
    cat_counts = {}
    
    for line_idx, line in enumerate(lines, start=1):
        if line.startswith("## ") or line.startswith("### ") or line.startswith("1.") or line.startswith("2.") or line.startswith("3.") or line.startswith("4.") or line.startswith("5.") or line.startswith("6.") or line.startswith("7.") or line.startswith("8.") or line.startswith("9.") or line.startswith("10.") or line.startswith("11."):
            clean_head = line.strip()
            if not checklist_pattern.match(line):
                curr_cat = clean_head
                if curr_cat not in cat_counts:
                    cat_counts[curr_cat] = {'checked': 0, 'unchecked': 0}
        m = checklist_pattern.match(line)
        if m:
            box = m.group(1)
            if curr_cat not in cat_counts:
                cat_counts[curr_cat] = {'checked': 0, 'unchecked': 0}
            if box in ['x', 'X']:
                cat_counts[curr_cat]['checked'] += 1
            else:
                cat_counts[curr_cat]['unchecked'] += 1
                
    for cat, cnts in cat_counts.items():
        if cnts['checked'] + cnts['unchecked'] > 0:
            print(f"    * {cat}: {cnts['checked']}/{cnts['checked'] + cnts['unchecked']} checked")
            
    if unchecked_count > 0:
        print("\n[-] UNCHECKED ITEMS FOUND:")
        for it in items:
            if it['status'] == 'unchecked':
                print(f"    Line {it['line']}: [ ] {it['desc']}")
        assert False, f"Walkthrough contains {unchecked_count} unchecked items!"
    else:
        print(f"\n[✓] Task 3 PASSED: All {total_count} checklist items (112 expected) are 100% completed with [x].")

if __name__ == "__main__":
    check_task1_sumo()
    check_task2_csv_integrity()
    check_task3_walkthrough()
    print("\n" + "=" * 60)
    print("ALL EMPIRICAL CHALLENGER 2 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
