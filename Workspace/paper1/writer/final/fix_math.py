import re

with open('main.tex', 'r') as f:
    text = f.read()

maths = []
for m in re.finditer(r'\$([^\$]+=.*?)\$', text):
    if len(m.group(1)) > 30 and "\\text{" in m.group(1) or "\\mathbb" in m.group(1):
        print("Found:", m.group(1).strip())
