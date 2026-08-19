import re

with open('/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md') as f:
    text = f.read()

lines = text.split('\n')

print("=== Math notation scan line by line ===")
for idx, line in enumerate(lines, 1):
    # Find all substrings between $ and $
    parts = line.split('$')
    if len(parts) >= 3:
        # Every odd index is inside $...$
        for i in range(1, len(parts), 2):
            math_expr = parts[i]
            # Check for non-romanized CBR
            if 'CBR' in math_expr and r'\text{CBR}' not in math_expr:
                print(f"Line {idx}: CBR without \\text: '${math_expr}'")
            if 'AoI' in math_expr and r'\text{AoI}' not in math_expr:
                print(f"Line {idx}: AoI without \\text: '${math_expr}'")
            if 'PDR' in math_expr and r'\text{PDR}' not in math_expr:
                print(f"Line {idx}: PDR without \\text: '${math_expr}'")
            if 'GenCAM' in math_expr:
                print(f"Line {idx}: GenCAM: '${math_expr}'")
            if 's_t' in math_expr and r'\mathbf{s}_t' not in math_expr:
                # check if s_{t, or s_t
                if re.search(r'\bs_t\b|\bs_t\^|\bs_t\(', math_expr):
                    print(f"Line {idx}: non-bold s_t: '${math_expr}'")
            if 'P_{tx}' in math_expr or 'P_tx' in math_expr:
                print(f"Line {idx}: non-romanized P_tx: '${math_expr}'")
