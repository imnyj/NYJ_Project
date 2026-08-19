#!/usr/bin/env python3
"""
deep_math_audit.py
Perform deep consistency and syntax checks across all display and inline math.
"""

import re
from pathlib import Path

MAIN_TEX = Path("/home/imnyj/Workspace/paper4/latex/main.tex")
text = MAIN_TEX.read_text(encoding="utf-8")

errors = []
warnings = []

# 1. Check all inline math
inline_matches = list(re.finditer(r"(?<!\\)\$(.+?)(?<!\\)\$", text))
for i, m in enumerate(inline_matches, 1):
    c = m.group(1)
    line = text[:m.start()].count("\n") + 1
    
    # Brace balance
    if c.count("{") != c.count("}"):
        errors.append(f"L{line}: Inline math #{i} unbalanced braces: ${c}$")
        
    # Unescaped percent inside math
    # In math mode, % will comment out the rest of the line unless escaped as \%
    if "%" in c:
        # Check if preceded by backslash
        unescaped_pc = re.findall(r"(?<!\\)%", c)
        if unescaped_pc:
            errors.append(f"L{line}: Inline math #{i} unescaped % inside math: ${c}$")
            
    # Check for empty math $$
    if not c.strip():
        errors.append(f"L{line}: Inline math #{i} empty math span: $$")
        
    # Check for double subscripts like a_b_c
    if re.search(r"_[a-zA-Z0-9\{\}]+_[a-zA-Z0-9\{\}]+", c):
        warnings.append(f"L{line}: Double subscript in inline math: ${c}$")
        
    # Check for double superscripts like a^b^c
    if re.search(r"\^[a-zA-Z0-9\{\}]+\^[a-zA-Z0-9\{\}]+", c):
        warnings.append(f"L{line}: Double superscript in inline math: ${c}$")

# 2. Check all display math
disp_pattern = re.compile(r"\\begin\{(equation|align)\*?\}(.*?)\\end\{\1\*?\}", re.DOTALL)
disp_matches = list(disp_pattern.finditer(text))
for i, m in enumerate(disp_matches, 1):
    env = m.group(1)
    c = m.group(2)
    line = text[:m.start()].count("\n") + 1
    
    # Brace balance
    if c.count("{") != c.count("}"):
        errors.append(f"L{line}: Display math #{i} ({env}) unbalanced braces")
        
    # Unescaped % inside display math (excluding comments if any)
    lines = c.split("\n")
    for subline in lines:
        stripped = subline.strip()
        if stripped.startswith("%"):
            continue # comment line
        if "%" in stripped:
            unescaped_pc = re.findall(r"(?<!\\)%", stripped)
            if unescaped_pc:
                errors.append(f"L{line}: Display math #{i} unescaped %: {stripped}")

# 3. Check vector/matrix notation consistency:
# Check if \mathbf{s}_t is consistently bold, or s_t is used
# Let's count instances of state vector notations
vec_s_bold = len(re.findall(r"\\mathbf\{s\}", text))
vec_s_plain = len(re.findall(r"(?<!\\mathbf\{)(?<![a-zA-Z])s_t", text))

print("=== MATH AUDIT SUMMARY ===")
print(f"Total inline math spans: {len(inline_matches)}")
print(f"Total display math environments: {len(disp_matches)}")
print(f"Errors found: {len(errors)}")
print(f"Warnings found: {len(warnings)}")
print(f"State vector \\mathbf{{s}}: {vec_s_bold} instances, plain s_t: {vec_s_plain} instances")

if errors:
    print("\n--- ERRORS ---")
    for e in errors:
        print(" ", e)

if warnings:
    print("\n--- WARNINGS ---")
    for w in warnings:
        print(" ", w)
