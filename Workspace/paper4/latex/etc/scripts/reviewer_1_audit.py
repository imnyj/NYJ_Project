#!/usr/bin/env python3
"""
reviewer_1_audit.py
Independent audit script for Reviewer 1 (R1 and R2 verification).
"""

import re
import sys
from pathlib import Path

BASE_DIR = Path("/home/imnyj/Workspace/paper4/latex")
MAIN_TEX = BASE_DIR / "main.tex"

def main():
    print("=== REVIEWER 1 INDEPENDENT AUDIT ===")
    content = MAIN_TEX.read_text(encoding="utf-8")
    lines = content.splitlines()
    print(f"Total lines in main.tex: {len(lines)}")

    # 1. Prohibited / Hyperbolic Vocabulary Check
    prohibited_patterns = {
        "elucidate": r"\belucidat\w*\b",
        "seamless": r"\bseamless\w*\b",
        "vital": r"\bvital\w*\b",
        "fosters": r"\bfoster\w*\b",
        "comprehensive": r"\bcomprehensive\w*\b",
        "significantly / significant": r"\bsignificant\w*\b",
        "substantially / substantial": r"\bsubstantial\w*\b",
    }

    print("\n--- 1. Prohibited / Exaggerated Words ---")
    for name, pattern in prohibited_patterns.items():
        matches = []
        for line_idx, line in enumerate(lines, 1):
            for m in re.finditer(pattern, line, re.IGNORECASE):
                matches.append((line_idx, m.group(), line.strip()))
        if matches:
            print(f"[FOUND] {name}: {len(matches)} occurrences")
            for line_idx, word, line_text in matches:
                print(f"  Line {line_idx} [{word}]: {line_text[:100]}...")
        else:
            print(f"[CLEAN] {name}: 0 occurrences")

    # 2. AI Clichés Check
    ai_cliches = {
        "leverage": r"\bleverag\w*\b",
        "utilizing / utilize": r"\butiliz\w*\b",
        "subsequently / subsequent": r"\bsubsequent\w*\b",
        "systematically / systematic": r"\bsystematic\w*\b",
        "effectively / effective": r"\beffective\w*\b",
        "encapsulates": r"\bencapsulat\w*\b",
        "autonomously": r"\bautonomously\b",
        "autonomous (non-domain)": r"\bautonomous\b",
    }

    print("\n--- 2. AI Clichés ---")
    for name, pattern in ai_cliches.items():
        matches = []
        for line_idx, line in enumerate(lines, 1):
            for m in re.finditer(pattern, line, re.IGNORECASE):
                matches.append((line_idx, m.group(), line.strip()))
        if matches:
            print(f"[FOUND] {name}: {len(matches)} occurrences")
            for line_idx, word, line_text in matches:
                print(f"  Line {line_idx} [{word}]: {line_text[:100]}...")
        else:
            print(f"[CLEAN] {name}: 0 occurrences")

    # 3. Filename Mentions Check
    filename_patterns = [
        r"\b\w+\.tex\b",
        r"\b\w+\.py\b",
        r"\b\w+\.csv\b",
        r"\b\w+\.json\b",
        r"\b\w+\.mat\b",
        r"\b\w+\.npz\b",
        r"\b\w+\.log\b",
        r"\b\w+\.sh\b",
        r"sim_engine",
    ]
    print("\n--- 3. Filename / Source code references ---")
    fn_matches = []
    for line_idx, line in enumerate(lines, 1):
        # Ignore comments or graphic paths
        if line.strip().startswith("%") or "\\includegraphics" in line or "\\bibliography" in line:
            continue
        for pat in filename_patterns:
            for m in re.finditer(pat, line, re.IGNORECASE):
                # ignore standard abbreviations or domain terms like 5.9~GHz or Fig. 1
                matched = m.group()
                if matched.lower() in ["fig.tex"]:
                    continue
                fn_matches.append((line_idx, matched, line.strip()))
    if fn_matches:
        print(f"[FOUND] Filename references: {len(fn_matches)}")
        for line_idx, word, line_text in fn_matches:
            print(f"  Line {line_idx} [{word}]: {line_text[:100]}...")
    else:
        print("[CLEAN] Filename references: 0 occurrences")

    # 4. Duplicate Acronym Definitions Check
    print("\n--- 4. Duplicate Acronym Definitions ---")
    acronym_def_pattern = re.compile(r"\b([A-Z][a-zA-Z0-9\s\-]+)\s+\(([A-Z]{2,}[a-zA-Z0-9\-]*)\)")
    acronyms = {}
    for line_idx, line in enumerate(lines, 1):
        # skip comments
        if line.strip().startswith("%"):
            continue
        for m in acronym_def_pattern.finditer(line):
            full_term, acr = m.group(1), m.group(2)
            if acr not in acronyms:
                acronyms[acr] = []
            acronyms[acr].append((line_idx, full_term, m.group()))
    
    for acr, occs in acronyms.items():
        if len(occs) > 1:
            print(f"[DUPLICATE ACRONYM] {acr} defined {len(occs)} times:")
            for line_idx, full_term, matched in occs:
                print(f"  Line {line_idx}: {matched}")
        else:
            # Defined once
            pass

    # 5. Narrative Paragraph Length Check (Sentence Count >= 5)
    print("\n--- 5. Paragraph Sentence Counts ---")
    # Identify paragraphs
    # Paragraphs in LaTeX are separated by blank lines or section headings.
    # Exclude environments: equation, figure, table, itemize, tabular, abstract preamble, etc.
    in_environment = []
    paragraphs = []
    current_para = []
    start_line = 1

    for line_idx, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Check environment begins/ends
        env_begins = re.findall(r"\\begin\{([a-zA-Z0-9_\*]+)\}", stripped)
        env_ends = re.findall(r"\\end\{([a-zA-Z0-9_\*]+)\}", stripped)
        
        # Section commands start a new paragraph
        is_heading = bool(re.match(r"\\(section|subsection|subsubsection|paragraph)\{", stripped))
        
        if env_begins:
            in_environment.extend(env_begins)
        
        # If blank line or heading and not inside figure/table/equation
        if (stripped == "" or is_heading) and not in_environment:
            if current_para:
                para_text = " ".join(current_para)
                paragraphs.append((start_line, line_idx - 1, para_text))
                current_para = []
            if is_heading:
                start_line = line_idx + 1
            else:
                start_line = line_idx + 1
        else:
            if not in_environment:
                # Exclude lines starting with \IEEEtitleabstractindextext, \maketitle, \begin{abstract}, etc.
                if not stripped.startswith("%") and not stripped.startswith("\\documentclass") and not stripped.startswith("\\usepackage") and not stripped.startswith("\\IEEE"):
                    if not current_para:
                        start_line = line_idx
                    current_para.append(stripped)

        if env_ends:
            for e in env_ends:
                if e in in_environment:
                    in_environment.remove(e)

    if current_para:
        para_text = " ".join(current_para)
        paragraphs.append((start_line, len(lines), para_text))

    print(f"Extracted {len(paragraphs)} narrative paragraphs.")
    
    # Sentence splitter
    def count_sentences(text):
        # Clean LaTeX commands and math
        clean = re.sub(r"\$[^$]+\$", "MATH", text)
        clean = re.sub(r"\\[a-zA-Z]+(\[[^\]]*\])?(\{[^}]*\})*", "", clean)
        clean = re.sub(r"~", " ", clean)
        # Avoid splitting on e.g., i.e., Fig., Eq., Ref., al., etc.
        clean = re.sub(r"\b(e\.g\.|i\.e\.|Fig\.|Eq\.|Ref\.|al\.|vs\.|dB\.|sec\.|ms\.|Hz\.|GHz\.|MHz\.|km/h\.)", "ABBR", clean)
        # Split by punctuation . ! ? followed by space or end
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip() and len(s.strip()) > 3]
        return len(sentences), sentences

    short_paras = []
    for s_line, e_line, p_text in paragraphs:
        # Check if paragraph is just title or maketitle or abstract start
        if "\\maketitle" in p_text or "\\title" in p_text:
            continue
        s_count, s_list = count_sentences(p_text)
        if s_count < 5:
            short_paras.append((s_line, e_line, s_count, p_text, s_list))
        print(f"Lines {s_line:>3}-{e_line:>3} | Sentences: {s_count:>2} | Starts: {p_text[:60]}...")

    print(f"\nTotal short paragraphs (< 5 sentences): {len(short_paras)}")
    for s_line, e_line, s_count, p_text, s_list in short_paras:
        print(f"\n[SHORT PARA] Lines {s_line}-{e_line} (Count: {s_count}):")
        for idx, s in enumerate(s_list, 1):
            print(f"    {idx}. {s}")
        print(f"  Raw: {p_text[:150]}...")

    # 6. R2: Introduction Contributions itemize check
    print("\n--- 6. R2: Introduction Contributions Check ---")
    intro_start = False
    intro_lines = []
    for line_idx, line in enumerate(lines, 1):
        if "\\section{Introduction}" in line:
            intro_start = True
        elif "\\section{" in line and intro_start:
            intro_start = False
            break
        if intro_start:
            intro_lines.append((line_idx, line))

    intro_text = "\n".join(l[1] for l in intro_lines)
    if "\\begin{itemize}" in intro_text and "\\end{itemize}" in intro_text:
        print("[OK] Introduction contains \\begin{itemize} ... \\end{itemize}")
        items = re.findall(r"\\item\s+(.*?)(?=(?:\\item|\\end\{itemize\}))", intro_text, re.DOTALL)
        print(f"Found {len(items)} bullet contribution items:")
        for idx, item in enumerate(items, 1):
            cleaned_item = " ".join(item.strip().split())
            print(f"  Item {idx}: {cleaned_item[:120]}...")
    else:
        print("[FAIL] Introduction does NOT contain \\begin{itemize} ... \\end{itemize}")

if __name__ == "__main__":
    main()
