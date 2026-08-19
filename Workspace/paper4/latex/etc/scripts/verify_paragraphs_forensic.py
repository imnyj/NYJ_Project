#!/usr/bin/env python3
import re
from pathlib import Path

text = Path("/home/imnyj/Workspace/paper4/latex/main.tex").read_text(encoding="utf-8")

clean_lines = []
for line in text.splitlines():
    stripped = line.strip()
    if stripped.startswith("%"):
        continue
    m = re.search(r"(?<!\\)%", line)
    clean_lines.append(line[:m.start()] if m else line)
clean_text = "\n".join(clean_lines)

paras = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
print(f"Total raw blocks: {len(paras)}")

narrative_paras = []
for p in paras:
    if any(p.startswith(prefix) for prefix in [
        "\\begin{equation}", "\\begin{align}", "\\begin{figure}", "\\begin{table}",
        "\\title", "\\author", "\\maketitle", "\\begin{IEEEkeywords}", "\\IEEEtitleabstractindextext",
        "\\bibliographystyle", "\\bibliography", "\\begin{itemize}", "\\item"
    ]):
        continue
    narrative_paras.append(p)

print(f"Narrative paragraphs count: {len(narrative_paras)}")

for idx, p in enumerate(narrative_paras, 1):
    p_clean = re.sub(r"\$[^$]+\$", "MATH", p)
    p_clean = re.sub(r"\\cite\{[^}]+\}", "CITE", p_clean)
    p_clean = re.sub(r"\\ref\{[^}]+\}", "REF", p_clean)
    p_clean = re.sub(r"\\eqref\{[^}]+\}", "EQREF", p_clean)
    p_clean = re.sub(r"\\textbf\{([^}]+)\}", r"\1", p_clean)
    p_clean = re.sub(r"\\textit\{([^}]+)\}", r"\1", p_clean)
    p_clean = re.sub(r"\\section\{[^}]+\}", "", p_clean)
    p_clean = re.sub(r"\\subsection\{[^}]+\}", "", p_clean)
    p_clean = re.sub(r"\\subsubsection\{[^}]+\}", "", p_clean)
    p_clean = re.sub(r"\b(Fig|Tab|Sec|Eq|Ref|al|vs|e\.g|i\.e|approx)\.\s*", r"\1_DOT_", p_clean)
    p_clean = p_clean.strip()
    if not p_clean:
        continue
    # Split sentences by period followed by space
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", p_clean) if s.strip()]
    first_few = " ".join(p_clean.split()[:8])
    print(f"Para #{idx:02d} | Sentences: {len(sentences):2d} | {first_few}...")
