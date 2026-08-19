#!/usr/bin/env python3
"""
inspect_inline_math.py
Detailed inspection of all inline math spans in main.tex
"""

import re
from pathlib import Path

MAIN_TEX = Path("/home/imnyj/Workspace/paper4/latex/main.tex")
text = MAIN_TEX.read_text(encoding="utf-8")

# Extract all inline math
matches = list(re.finditer(r"(?<!\\)\$(.+?)(?<!\\)\$", text))
print(f"Total inline math spans: {len(matches)}")

for i, m in enumerate(matches, 1):
    content = m.group(1).strip()
    line_no = text[:m.start()].count("\n") + 1
    print(f"[{i:03d} | L{line_no:04d}] ${content}$")
