import re

with open('Workspace/paper1/writer/final/main.tex', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract all cite keys in order of appearance
cites = re.findall(r'\\cite\{([^}]+)\}', content)
ordered_keys = []
seen = set()
for cite_grp in cites:
    keys = [k.strip() for k in cite_grp.split(',')]
    for k in keys:
        if k not in seen:
            seen.add(k)
            ordered_keys.append(k)

# Extract bibliography block
bib_block_match = re.search(r'(\\begin\{thebibliography\}\{.*?\})(.*?)(\\end\{thebibliography\})', content, re.DOTALL)
if not bib_block_match:
    print("Could not find thebibliography.")
    exit(1)

pre_bib = bib_block_match.group(1)
bib_content = bib_block_match.group(2)
post_bib = bib_block_match.group(3)

# Extract individual bibitems
bibitems_raw = re.split(r'\\bibitem\{([^}]+)\}', bib_content)
bib_dict = {}

# bibitems_raw will be: [preamble, key1, content1, key2, content2, ...]
# preamble might just be whitespace
for i in range(1, len(bibitems_raw), 2):
    key = bibitems_raw[i]
    val = bibitems_raw[i+1]
    bib_dict[key] = val

# Reconstruct bib_content
new_bib_content = "\n"
for k in ordered_keys:
    if k in bib_dict:
        new_bib_content += f"\\bibitem{{{k}}}{bib_dict[k]}"

# If there are any bibitems not cited, append them at the end
for k in bib_dict:
    if k not in ordered_keys:
        new_bib_content += f"\\bibitem{{{k}}}{bib_dict[k]}"

new_content = content[:bib_block_match.start(2)] + new_bib_content + content[bib_block_match.start(3):]

with open('Workspace/paper1/writer/final/main.tex', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Reordered bibliography in main.tex")
