import re

with open("/home/imnyj/Workspace/paper4/latex/main.tex", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Unmatched braces
open_braces = 0
for i, line in enumerate(text.splitlines(), 1):
    c_open = line.count('{')
    c_close = line.count('}')
    if line.strip().startswith('%'):
        continue
    # remove comments
    clean_line = re.sub(r'(?<!\\)%.*$', '', line)
    open_braces += clean_line.count('{') - clean_line.count('}')
    if open_braces < 0:
        print(f"Brace mismatch underflow at line {i}: {line}")
print(f"Final brace balance count (should be 0): {open_braces}")

# 2. Check for eq:loss_total references
refs = re.findall(r'\\(?:eq)?ref\{([^}]+)\}', text)
for r in refs:
    if "loss" in r:
        print(f"Found ref containing loss: {r}")

# 3. Check for double words
double_words = re.findall(r'\b([A-Za-z]+)\s+\1\b', text, re.IGNORECASE)
print(f"Double words found: {set(double_words)}")

# 4. Check for double periods/commas (excluding \dots, ... etc)
double_punct = re.findall(r'[a-zA-Z](\.\.|\,\,|\;\;)[a-zA-Z]', text)
print(f"Double punctuation: {double_punct}")
