#!/usr/bin/env python3
import re
from pathlib import Path

MAIN_TEX = Path("/home/imnyj/Workspace/paper4/latex/main.tex")
text = MAIN_TEX.read_text(encoding="utf-8")

disp_pattern = re.compile(r"\\begin\{(equation|align)\*?\}(.*?)\\end\{\1\*?\}", re.DOTALL)
disp_matches = list(disp_pattern.finditer(text))

print(f"Total display math environments: {len(disp_matches)}")
for idx, match in enumerate(disp_matches, 1):
    env_type = match.group(1)
    content = match.group(2).strip()
    start_pos = match.start()
    line_no = text[:start_pos].count("\n") + 1
    print(f"\n==================== [Equation #{idx} | {env_type} | Line {line_no}] ====================")
    print(content)
