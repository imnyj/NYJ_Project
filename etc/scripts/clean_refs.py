import re

file_path = 'Workspace/paper1/writer/final/main.tex'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

cites = re.findall(r'\\cite\{([^}]+)\}', content)
cited_keys = set()
for cite_grp in cites:
    keys = [k.strip() for k in cite_grp.split(',')]
    cited_keys.update(keys)

bib_block_match = re.search(r'(\\begin\{thebibliography\}.*?\})(.*?)(\\end\{thebibliography\})', content, re.DOTALL)
if not bib_block_match:
    print("Could not find thebibliography.")
    exit(1)

bib_content = bib_block_match.group(2)
bibitems = re.findall(r'(\\bibitem\{([^}]+)\})(.*?)(?=\\bibitem|\n\s*\\end\{thebibliography\}|$)', bib_content, re.DOTALL)

content_to_key = {}
key_mapping = {} 
unused_keys = set()

for bib_prefix, key, body in bibitems:
    if key not in cited_keys:
        unused_keys.add(key)
        continue
    
    title_match = re.search(r"``(.*?)''", body)
    if title_match:
        norm_title = re.sub(r'[^a-zA-Z0-9]', '', title_match.group(1).lower())
    else:
        norm_title = re.sub(r'[^a-zA-Z0-9]', '', body.lower())
        
    if norm_title in content_to_key:
        primary_key = content_to_key[norm_title]
        key_mapping[key] = primary_key
        unused_keys.add(key)
    else:
        content_to_key[norm_title] = key

def replace_cite(match):
    inner = match.group(1)
    old_ids = [x.strip() for x in inner.split(',')]
    new_ids = []
    for x in old_ids:
        curr = x
        while curr in key_mapping:
            curr = key_mapping[curr]
        if curr not in new_ids:
            new_ids.append(curr)
    return "\\cite{" + ", ".join(new_ids) + "}"

if key_mapping:
    content = re.sub(r'\\cite\{([^}]+)\}', replace_cite, content)

bib_block_match = re.search(r'(\\begin\{thebibliography\}.*?\})(.*?)(\\end\{thebibliography\})', content, re.DOTALL)
bib_content = bib_block_match.group(2)
bibitems_new = re.findall(r'(\\bibitem\{([^}]+)\}.*?)(?=\\bibitem|\n\s*\\end\{thebibliography\}|$)', bib_content, re.DOTALL)

new_bib_content = "\n"
for full_item, key in bibitems_new:
    if key in unused_keys:
        commented = "\n".join("% " + line if line.strip() else line for line in full_item.strip().split("\n"))
        new_bib_content += commented + "\n\n"
    else:
        new_bib_content += full_item.strip() + "\n\n"

new_content = content[:bib_block_match.start(2)] + new_bib_content + content[bib_block_match.start(3):]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Unused or duplicated keys commented out: {unused_keys}")
print(f"Duplicate mapping: {key_mapping}")
