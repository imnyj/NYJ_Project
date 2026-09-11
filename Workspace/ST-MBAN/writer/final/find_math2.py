import re
with open('main.tex', 'r') as f:
    text = f.read()

for m in re.finditer(r'\$([^$]*[=+\-][^$]*)\$', text):
    content = m.group(1).strip()
    if len(content) > 15:
        print(content)
