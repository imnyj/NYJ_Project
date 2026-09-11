import re
with open('main.tex', 'r') as f:
    text = f.read()

for m in re.finditer(r'\$([^$]*=.*?)\$', text):
    content = m.group(1).strip()
    # Let's filter out very short ones or ones that are just variable assignments
    if len(content) > 15:
        print(content)
