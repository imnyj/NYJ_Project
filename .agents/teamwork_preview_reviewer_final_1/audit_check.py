import re

tex_path = "/home/imnyj/Workspace/paper4/latex/main.tex"
bib_path = "/home/imnyj/Workspace/paper4/latex/references.bib"

with open(tex_path, "r", encoding="utf-8") as f:
    tex_content = f.read()
    tex_lines = tex_content.splitlines()

with open(bib_path, "r", encoding="utf-8") as f:
    bib_content = f.read()

print("--- 1. Check Malformed Commands/Labels ---")
for i, line in enumerate(tex_lines, 1):
    # check for \label without {
    if re.search(r'\\label[^{]', line):
        print(f"Malformed \\label at line {i}: {line}")
    # check for \ref without {
    if re.search(r'\\ref[^{]', line):
        print(f"Malformed \\ref at line {i}: {line}")
    # check for \cite without {
    if re.search(r'\\cite[^{]', line):
        print(f"Malformed \\cite at line {i}: {line}")
    # check for \eqref without {
    if re.search(r'\\eqref[^{]', line):
        print(f"Malformed \\eqref at line {i}: {line}")

print("\n--- 2. Extract and Cross-Check Labels and Refs ---")
labels = set(re.findall(r'\\label\{([^}]+)\}', tex_content))
refs = set(re.findall(r'\\ref\{([^}]+)\}', tex_content))
eqrefs = set(re.findall(r'\\eqref\{([^}]+)\}', tex_content))

all_refs = refs.union(eqrefs)
missing_labels = all_refs - labels
print(f"Total labels defined: {len(labels)}")
print(f"Total refs/eqrefs used: {len(all_refs)}")
if missing_labels:
    print(f"[!] Missing labels referenced: {missing_labels}")
else:
    print("[OK] All referenced labels exist!")

unused_labels = labels - all_refs
print(f"Unreferenced labels ({len(unused_labels)}): {unused_labels}")

print("\n--- 3. Extract and Cross-Check BibTeX Entries and In-Text Citations ---")
bib_keys = set(re.findall(r'@\w+\s*\{\s*([^,\s]+),', bib_content))
raw_cites = re.findall(r'\\cite\{([^}]+)\}', tex_content)
cited_keys = set()
for c in raw_cites:
    for k in c.split(','):
        cited_keys.add(k.strip())

print(f"Total BibTeX keys in references.bib: {len(bib_keys)}")
print(f"Total Unique Keys Cited in main.tex: {len(cited_keys)}")

uncited_bib_keys = bib_keys - cited_keys
if uncited_bib_keys:
    print(f"[!] BibTeX keys never cited in main.tex: {uncited_bib_keys}")
else:
    print("[OK] All 27 BibTeX keys are cited in main.tex!")

missing_bib_keys = cited_keys - bib_keys
if missing_bib_keys:
    print(f"[!] Citations in main.tex missing from references.bib: {missing_bib_keys}")
else:
    print("[OK] All cited keys exist in references.bib!")

print("\n--- 4. Check for AI Clichés and Prohibited Words ---")
cliches = [
    'elucidate', 'seamless', 'vital', 'fosters', 'comprehensive', 
    'significantly', 'substantially', 'leveraging', 'leverages', 
    'utilizing', 'utilizes', 'subsequently', 'systematically', 
    'effectively', 'autonomously', 'encapsulates'
]
cliche_counts = {}
for word in cliches:
    matches = re.findall(rf'\b{word}\b', tex_content, re.IGNORECASE)
    if matches:
        cliche_counts[word] = len(matches)

print(f"AI clichés / Prohibited words found: {cliche_counts}")
for word, count in cliche_counts.items():
    print(f"  - '{word}': {count} occurrences")
    for i, line in enumerate(tex_lines, 1):
        if re.search(rf'\b{word}\b', line, re.IGNORECASE):
            print(f"     Line {i}: {line.strip()[:100]}...")

print("\n--- 5. Check Paragraph Sentence Counts ---")
# Split by sections and paragraphs
paragraphs = [p.strip() for p in re.split(r'\n\s*\n', tex_content) if p.strip()]
print(f"Total blocks/paragraphs: {len(paragraphs)}")

