import re
import sys

with open('/home/imnyj/Workspace/paper1/writer/final/main.tex', 'r') as f:
    content = f.read()

# Remove comments
content = re.sub(r'%.*?\n', '\n', content)

# Split into paragraphs
paras = content.split('\n\n')

for i, p in enumerate(paras):
    p = p.strip()
    # Skip equations, tables, figures, empty, etc.
    if not p or p.startswith('\\begin{') or p.startswith('\\end{') or p.startswith('\\') and not p.startswith('\\IEEEPARstart'):
        continue
        
    # Count sentences roughly by splitting on . ? ! followed by space or end
    sentences = re.split(r'[.?!](?:\s+|$)', p)
    sentences = [s for s in sentences if s.strip()]
    if len(sentences) < 5:
        print(f"Paragraph has {len(sentences)} sentences:\n{p}\n")
