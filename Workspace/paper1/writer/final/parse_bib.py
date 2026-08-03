import re
with open('/home/imnyj/.gemini/antigravity-cli/brain/bff0f4a2-6bd4-4508-ae14-d560f3f05914/writer_instructions.md', 'r') as f:
    text = f.read()
bib = re.search(r'```latex\n(.*?)```', text, re.DOTALL)
if bib:
    with open('bib_extracted.txt', 'w') as f2:
        f2.write(bib.group(1))
