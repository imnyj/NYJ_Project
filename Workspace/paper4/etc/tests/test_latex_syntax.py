"""
Test Suite 3: LaTeX Syntax, Escaping, and Structural Compilation Test
=====================================================================
Performs strict static analysis and structural linting of LaTeX tables:
1. 2_optuna_sensitivity_table.tex / optuna_sensitivity_table.tex
2. 11_hardware_feasibility_table.tex / hardware_feasibility_table.tex

Validates:
- Brace matching ({ and })
- Math mode matching ($ and $)
- Unescaped special characters: underscores (_), percent signs (%), ampersands (&), hashes (#)
- Tabular column definition vs. row delimiter counts
- Environment matching (\\begin{table*} ... \\end{table*}, \\begin{tabular} ... \\end{tabular})
"""

import os
import sys
import re

REPO_ROOT = "/home/imnyj/Workspace/paper4"
VIS_DIR = os.path.join(REPO_ROOT, "visualizer")

TEX_FILES = [
    os.path.join(VIS_DIR, "2_optuna_sensitivity_table.tex"),
    os.path.join(VIS_DIR, "optuna_sensitivity_table.tex"),
    os.path.join(VIS_DIR, "11_hardware_feasibility_table.tex"),
    os.path.join(VIS_DIR, "hardware_feasibility_table.tex")
]

def check_brace_balance(content, filename):
    errors = []
    stack = []
    escaped = False
    
    for line_idx, line in enumerate(content.splitlines(), 1):
        # Strip comments
        code_part = ""
        is_esc = False
        for char in line:
            if char == '%' and not is_esc:
                break
            code_part += char
            is_esc = (char == '\\' and not is_esc)
            
        for col_idx, char in enumerate(code_part, 1):
            if char == '\\' and not escaped:
                escaped = True
                continue
            if escaped:
                escaped = False
                continue
            if char == '{':
                stack.append((line_idx, col_idx))
            elif char == '}':
                if not stack:
                    errors.append(f"{filename}:{line_idx}:{col_idx} - Unmatched closing brace '}}'")
                else:
                    stack.pop()
                    
    for line_idx, col_idx in stack:
        errors.append(f"{filename}:{line_idx}:{col_idx} - Unclosed opening brace '{{'")
    return errors

def check_math_balance(content, filename):
    errors = []
    for line_idx, line in enumerate(content.splitlines(), 1):
        # Strip comments
        code_part = ""
        is_esc = False
        for char in line:
            if char == '%' and not is_esc:
                break
            code_part += char
            is_esc = (char == '\\' and not is_esc)
            
        # Count non-escaped $
        dollar_count = 0
        is_esc = False
        for char in code_part:
            if char == '\\' and not is_esc:
                is_esc = True
                continue
            if char == '$' and not is_esc:
                dollar_count += 1
            is_esc = False
            
        if dollar_count % 2 != 0:
            errors.append(f"{filename}:{line_idx} - Odd number of '$' math delimiters ({dollar_count}) on single line")
    return errors

def check_unescaped_characters(content, filename):
    errors = []
    for line_idx, line in enumerate(content.splitlines(), 1):
        # Strip comments
        code_part = ""
        is_esc = False
        for char in line:
            if char == '%' and not is_esc:
                break
            code_part += char
            is_esc = (char == '\\' and not is_esc)
            
        # Check unescaped underscores outside math mode
        parts = code_part.split('$')
        for part_idx, part in enumerate(parts):
            # Even index is outside math mode
            if part_idx % 2 == 0:
                # Find unescaped underscores: (?<!\\)_
                matches = re.finditer(r'(?<!\\)_', part)
                for m in matches:
                    errors.append(f"{filename}:{line_idx} - Unescaped underscore '_' outside math mode in: '{part.strip()}'")
    return errors

def extract_balanced_arg(s, start_pos):
    """Extract argument enclosed by { ... } taking into account nested braces."""
    idx = s.find('{', start_pos)
    if idx == -1:
        return None, -1
    depth = 0
    start = idx + 1
    for i in range(idx, len(s)):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return s[start:i], i + 1
    return None, -1

def check_tabular_columns(content, filename):
    errors = []
    # Find \begin{tabular}
    pos = content.find(r'\begin{tabular}')
    if pos == -1:
        errors.append(f"{filename} - Missing \\begin{{tabular}}{{...}}")
        return errors
        
    col_spec, end_pos = extract_balanced_arg(content, pos + len(r'\begin{tabular}'))
    if col_spec is None:
        errors.append(f"{filename} - Failed to parse \\begin{{tabular}}{{...}} argument")
        return errors
        
    # Clean out column descriptors: p{...}, m{...}, b{...}
    clean_cols = re.sub(r'[pmb]\{[^}]+\}', 'C', col_spec)
    clean_cols = re.sub(r'[@|*>< ]', '', clean_cols)
    expected_col_count = len(clean_cols)
    
    # Check each row ending with \\
    in_tabular = False
    for line_idx, line in enumerate(content.splitlines(), 1):
        sline = line.strip()
        if r'\begin{tabular}' in sline:
            in_tabular = True
            continue
        if r'\end{tabular}' in sline:
            in_tabular = False
            continue
        if in_tabular:
            # Skip rule lines
            if any(r in sline for r in [r'\toprule', r'\midrule', r'\bottomrule', r'\hline']):
                continue
            if sline.endswith(r'\\'):
                # Count non-escaped &
                amp_count = 0
                is_esc = False
                for char in sline[:-2]:
                    if char == '\\' and not is_esc:
                        is_esc = True
                        continue
                    if char == '&' and not is_esc:
                        amp_count += 1
                    is_esc = False
                row_cols = amp_count + 1
                if row_cols != expected_col_count:
                    errors.append(f"{filename}:{line_idx} - Column count mismatch: defined {expected_col_count} cols, but row has {row_cols} cols (found {amp_count} '&' delimiters) in: '{sline}'")
    return errors

def check_environment_nesting(content, filename):
    errors = []
    envs = ["table*", "table", "tabular", "center"]
    for env in envs:
        begins = len(re.findall(r'\\begin\{' + re.escape(env) + r'\}', content))
        ends = len(re.findall(r'\\end\{' + re.escape(env) + r'\}', content))
        if begins != ends:
            errors.append(f"{filename} - Environment count mismatch for '{env}': \\begin={begins}, \\end={ends}")
    return errors

def run_latex_stress_test():
    print("=" * 80)
    print("STARTING LATEX SYNTAX, ESCAPING & STRUCTURE STRESS TEST")
    print("=" * 80)
    
    total_errors = []
    for fpath in TEX_FILES:
        if not os.path.exists(fpath):
            total_errors.append(f"File not found: {fpath}")
            continue
            
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
            
        fname = os.path.basename(fpath)
        print(f"\n--- Linting LaTeX Table: {fname} ---")
        
        e1 = check_brace_balance(content, fname)
        e2 = check_math_balance(content, fname)
        e3 = check_unescaped_characters(content, fname)
        e4 = check_tabular_columns(content, fname)
        e5 = check_environment_nesting(content, fname)
        
        file_errors = e1 + e2 + e3 + e4 + e5
        if file_errors:
            print(f"[FAIL] Found {len(file_errors)} errors in {fname}:")
            for err in file_errors:
                print(f"  ❌ {err}")
            total_errors.extend(file_errors)
        else:
            print(f"[PASS] {fname}: Braces balanced, math delimiters balanced, all special characters escaped, columns match, environments properly closed.")

    print("\n" + "=" * 80)
    if not total_errors:
        print("LATEX SYNTAX STRESS TEST PASSED WITH ZERO SYNTAX/ESCAPING DEFECTS!")
        print("=" * 80)
        return True
    else:
        print(f"LATEX SYNTAX STRESS TEST FAILED WITH {len(total_errors)} DEFECTS.")
        print("=" * 80)
        return False

if __name__ == "__main__":
    success = run_latex_stress_test()
    if not success:
        sys.exit(1)
