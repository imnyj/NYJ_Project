import re

with open("/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

table_blocks = []
curr_t = []
curr_start = 0

for idx, line in enumerate(lines, 1):
    if line.strip().startswith("|") and line.strip().endswith("|"):
        if not curr_t:
            curr_start = idx
        curr_t.append((idx, line.strip()))
    else:
        if curr_t:
            table_blocks.append((curr_start, idx - 1, curr_t))
            curr_t = []
if curr_t:
    table_blocks.append((curr_start, len(lines), curr_t))

print(f"Total table blocks found: {len(table_blocks)}")
for t_idx, (s, e, t_lines) in enumerate(table_blocks, 1):
    print(f"\n--- TABLE {t_idx} (Lines {s}-{e}) ---")
    header = t_lines[0][1]
    print(f"Header: {header}")
    # check each row
    for row_num, row_str in t_lines:
        # if unescaped pipes inside math
        # let's find pipes
        pipes = row_str.split("|")
        # count non-empty cells
        cells = [c.strip() for c in pipes[1:-1]]
        if t_idx == 2:
            print(f"  Row {row_num}: {len(cells)} cells -> {cells}")
        else:
            if len(cells) != len([c for c in t_lines[0][1].split("|")[1:-1]]):
                print(f"  MISMATCH Row {row_num}: expected {len([c for c in t_lines[0][1].split('|')[1:-1]])}, got {len(cells)} -> {row_str}")
