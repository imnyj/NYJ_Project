import re
import os
import pandas as pd
import numpy as np

main_tex_path = "/home/imnyj/Workspace/paper4/latex/main.tex"
korean_draft_path = "/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md"
data_dir = "/home/imnyj/Workspace/paper4/coder/data"

with open(main_tex_path, "r", encoding="utf-8") as f:
    main_tex = f.read()

with open(korean_draft_path, "r", encoding="utf-8") as f:
    korean_draft = f.read()

print("--- 1. Check Label & Ref Consistency ---")
labels = re.findall(r'\\label\{([^}]+)\}', main_tex)
bad_labels = re.findall(r'\\label:([^}]+)\}', main_tex)
print(f"Total valid labels: {len(labels)}")
print(f"Malformed labels (e.g. \\label:): {bad_labels}")

refs = re.findall(r'\\(?:eq)?ref\{([^}]+)\}', main_tex)
print(f"Total refs: {len(refs)}")
missing_refs = [r for r in refs if r not in labels]
print(f"Missing refs: {missing_refs}")

print("\n--- 2. Check Figures Inclusions ---")
figures = re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', main_tex)
print(f"Total \\includegraphics: {len(figures)}")
for fig in figures:
    full_path = os.path.join("/home/imnyj/Workspace/paper4/latex", fig)
    exists = os.path.exists(full_path)
    print(f"  Figure: {fig} -> Exists: {exists}")

print("\n--- 3. Check Tables in main.tex ---")
tables = re.findall(r'\\begin\{(?:table|table\*)\}(.*?)\\end\{(?:table|table\*)\}', main_tex, re.DOTALL)
print(f"Total table environments in main.tex: {len(tables)}")
for i, tab in enumerate(tables, 1):
    cap = re.search(r'\\caption\{([^}]+)\}', tab)
    caption = cap.group(1) if cap else "No Caption"
    lbl = re.search(r'\\label\{([^}]+)\}', tab)
    label = lbl.group(1) if lbl else "No Label"
    is_wide = "table*" in main_tex.split(tab)[0][-20:]
    print(f"  Table {i}: Label={label}, Caption={caption[:50]}...")

print("\n--- 4. Check Key Quantitative Numbers ---")
key_numbers = [
    ("PDR (100 veh/km)", "73.41%"),
    ("PDR drop", "3.13%p"),
    ("PDR mean", "75.02%"),
    ("Mean AoI", "373.21 ms"),
    ("Mean CBR", "0.3442"),
    ("CBR Std", "0.1008"),
    ("CBR Violation", "0.0%"),
    ("MACs", "3.8 M"),
    ("Params", "350 K"),
    ("Inference Latency", "1.2 ms"),
    ("100ms DCC duty", "1.2%"),
    ("Energy savings vs 10Hz", "59.15%"),
    ("Energy consumption", "2.61 mJ/km"),
    ("Nakagami shape m", "3.0"),
    ("Nakagami m=3", "m=3"),
    ("SNR threshold", "5.0 dB"),
    ("Reward w1", "0.01"),
    ("Reward w2", "1.0"),
    ("Reward w3", "0.10"),
    ("Load balance lambda", "0.01"),
]

for name, val in key_numbers:
    in_tex = val in main_tex
    print(f"  Check '{name}' ({val}): in main.tex = {in_tex}")
