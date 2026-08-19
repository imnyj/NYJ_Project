#!/usr/bin/env python3
"""
check_math.py
Extract and audit all display equations and inline math expressions in main.tex.
"""

import re
from pathlib import Path

MAIN_TEX = Path("/home/imnyj/Workspace/paper4/latex/main.tex")

def main():
    text = MAIN_TEX.read_text(encoding="utf-8")
    
    # 1. Extract display equations: equation, align, etc.
    disp_pattern = re.compile(r"\\begin\{(equation|align)\*?\}(.*?)\\end\{\1\*?\}", re.DOTALL)
    disp_matches = list(disp_pattern.finditer(text))
    print(f"Total display math environments found: {len(disp_matches)}")
    
    for idx, match in enumerate(disp_matches, 1):
        env_type = match.group(1)
        content = match.group(2).strip()
        # Find line number
        start_pos = match.start()
        line_no = text[:start_pos].count("\n") + 1
        print(f"\n--- [Display Math #{idx}] Env: {env_type}, Line: {line_no} ---")
        print(content)
        
        # Check brace balance inside content
        open_braces = content.count("{")
        close_braces = content.count("}")
        if open_braces != close_braces:
            print(f"  [ERROR] Unbalanced braces: open={open_braces}, close={close_braces}")
            
        # Check for naked multi-char subscripts like _abc instead of _{abc}
        naked_sub = re.findall(r"_[a-zA-Z0-9]{2,}", content)
        if naked_sub:
            print(f"  [WARNING] Possible naked multi-char subscript: {naked_sub}")
        naked_sup = re.findall(r"\^[a-zA-Z0-9]{2,}", content)
        if naked_sup:
            print(f"  [WARNING] Possible naked multi-char superscript: {naked_sup}")

    # 2. Extract inline math spans ($...$)
    # Careful to ignore escaped \$
    # Use regex for inline math
    inline_pattern = re.compile(r"(?<!\\)\$(.+?)(?<!\\)\$", re.DOTALL)
    inline_matches = list(inline_pattern.finditer(text))
    print(f"\n========================================================")
    print(f"Total inline math spans found: {len(inline_matches)}")
    
    suspicious_inline = []
    for idx, match in enumerate(inline_matches, 1):
        content = match.group(1).strip()
        start_pos = match.start()
        line_no = text[:start_pos].count("\n") + 1
        
        # Check brace balance
        if content.count("{") != content.count("}"):
            suspicious_inline.append((idx, line_no, content, "Unbalanced braces"))
            
        # Check naked multi-char sub/sup
        naked_sub = re.findall(r"_[a-zA-Z0-9]{2,}", content)
        if naked_sub:
            # check if it's preceded by a backslash like \_ or something
            suspicious_inline.append((idx, line_no, content, f"Naked subscript: {naked_sub}"))
        naked_sup = re.findall(r"\^[a-zA-Z0-9]{2,}", content)
        if naked_sup:
            suspicious_inline.append((idx, line_no, content, f"Naked superscript: {naked_sup}"))

    print(f"Suspicious inline math spans count: {len(suspicious_inline)}")
    for item in suspicious_inline:
        print(f"  Line {item[1]} [#{item[0]}]: {item[2]} --> {item[3]}")

if __name__ == "__main__":
    main()
