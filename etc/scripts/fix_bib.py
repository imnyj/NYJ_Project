import re

with open('Workspace/paper1/writer/final/main.tex', 'r', encoding='utf-8') as f:
    content = f.read()

bib_block_match = re.search(r'(\\begin\{thebibliography\}.*?\\end\{thebibliography\})', content, re.DOTALL)
if not bib_block_match:
    print("Could not find thebibliography.")
    exit(1)

bib_block = bib_block_match.group(1)

bibitems = re.findall(r'\\bibitem\{([^}]+)\}\s*(.*?)(?=\\bibitem|\n\s*\\end\{thebibliography\})', bib_block, re.DOTALL)

id_mapping = {}
used_new_ids = set()

for old_id, text in bibitems:
    first_author_part = text.split(',', 1)[0].split(' and ')[0].strip()
    words = first_author_part.split()
    last_name = words[-1].lower() if words else "unknown"
    last_name = re.sub(r'[^a-z]', '', last_name)
    
    year_match = re.search(r'\b(19\d\d|20\d\d)\b', text)
    year = year_match.group(1) if year_match else "year"
    
    base_new_id = f"{last_name}{year}"
    new_id = base_new_id
    counter = 1
    while new_id in used_new_ids:
        counter += 1
        new_id = f"{base_new_id}_{counter}"
    
    used_new_ids.add(new_id)
    id_mapping[old_id] = new_id

def replace_cite(match):
    inner = match.group(1)
    old_ids = [x.strip() for x in inner.split(',')]
    new_ids = [id_mapping.get(x, x) for x in old_ids]
    return "\\cite{" + ", ".join(new_ids) + "}"

new_content = re.sub(r'\\cite\{([^}]+)\}', replace_cite, content)

def replace_bibitem(match):
    old_id = match.group(1)
    new_id = id_mapping.get(old_id, old_id)
    return f"\\bibitem{{{new_id}}}"

new_content = re.sub(r'\\bibitem\{([^}]+)\}', replace_bibitem, new_content)

with open('Workspace/paper1/writer/final/main.tex', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Updated references in main.tex")
