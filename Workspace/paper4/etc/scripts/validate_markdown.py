with open('/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('Total lines:', len(lines))
code_open = False
math_open = False
table_count = 0

for idx, line in enumerate(lines, 1):
    stripped = line.strip()
    if stripped.startswith('```'):
        code_open = not code_open
    if stripped.startswith('$$'):
        cnt = stripped.count('$$')
        if cnt % 2 == 1:
            math_open = not math_open
    if stripped.startswith('|'):
        table_count += 1

print('Code blocks balanced:', not code_open)
print('Math blocks balanced:', not math_open)
print('Table rows count:', table_count)
