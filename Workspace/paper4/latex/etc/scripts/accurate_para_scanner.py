#!/usr/bin/env python3
"""
accurate_para_scanner.py
Comprehensive paragraph scanner for main.tex
"""

import re
from pathlib import Path

MAIN_TEX = Path("/home/imnyj/Workspace/paper4/latex/main.tex")

def count_sentences(text):
    # Remove citations, refs, math, formatting
    s = text
    s = re.sub(r"%.*$", "", s, flags=re.MULTILINE)
    s = re.sub(r"\$[^$]+\$", "MATH", s)
    s = re.sub(r"\\cite\{[^}]+\}", "[CIT]", s)
    s = re.sub(r"\\ref\{[^}]+\}", "[REF]", s)
    s = re.sub(r"\\eqref\{[^}]+\}", "[EQREF]", s)
    s = re.sub(r"\\(textbf|textit|emph|underline|text|mathrm|mathbf)\{([^}]*)\}", r"\2", s)
    s = re.sub(r"\\IEEEPARstart\{([^}]*)\}\{([^}]*)\}", r"\1\2", s)
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = re.sub(r"~", " ", s)
    abbrs = ["e.g.", "i.e.", "Fig.", "Eq.", "Ref.", "al.", "vs.", "dB.", "sec.", "ms.", "Hz.", "GHz.", "MHz.", "km/h.", "No.", "Vol.", "pp."]
    for a in abbrs:
        s = s.replace(a, a.replace(".", "@DOT@"))
    raw = re.split(r"(?<=[.!?])\s+", s)
    sents = [sent.replace("@DOT@", ".").strip() for sent in raw if len(sent.strip()) > 3 and re.search(r"[a-zA-Z]", sent)]
    return len(sents), sents

def main():
    content = MAIN_TEX.read_text(encoding="utf-8")
    lines = content.splitlines()
    
    # We want to identify distinct narrative paragraphs
    # An actual paragraph is a continuous block of text lines, separated by blank lines or section headings.
    # Exclude tabular, figure, table environments, etc.
    
    in_excluded_env = False
    excluded_stack = []
    
    curr_lines = []
    paragraphs = []
    
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Check environment tags
        for m in re.finditer(r"\\(begin|end)\{([a-zA-Z0-9_\*]+)\}", stripped):
            tag, name = m.group(1), m.group(2)
            if name in ["figure", "figure*", "table", "table*", "tabular", "tabularx", "itemize", "enumerate", "IEEEkeywords", "abstract"]:
                if tag == "begin":
                    excluded_stack.append(name)
                elif tag == "end" and name in excluded_stack:
                    excluded_stack.remove(name)
        
        is_preamble = bool(re.match(r"^\\(documentclass|usepackage|newcolumntype|title|author|maketitle|IEEEtitleabstractindextext|bibliographystyle|bibliography|balance)", stripped))
        is_heading = bool(re.match(r"^\\(section|subsection|subsubsection|paragraph)\*?\{", stripped))
        is_comment = stripped.startswith("%")
        is_blank = (stripped == "")
        
        if len(excluded_stack) > 0 or is_preamble or is_heading or is_blank:
            if curr_lines:
                p_text = " ".join(l for _, l in curr_lines)
                start_l = curr_lines[0][0]
                end_l = curr_lines[-1][0]
                paragraphs.append((start_l, end_l, p_text))
                curr_lines = []
        else:
            if not is_comment:
                curr_lines.append((idx, stripped))
                
    if curr_lines:
        p_text = " ".join(l for _, l in curr_lines)
        start_l = curr_lines[0][0]
        end_l = curr_lines[-1][0]
        paragraphs.append((start_l, end_l, p_text))

    print(f"Total non-environment text blocks found: {len(paragraphs)}")
    
    for start_l, end_l, p_text in paragraphs:
        cnt, sents = count_sentences(p_text)
        status = "PASS (>=5)" if cnt >= 5 else "SHORT (<5)"
        print(f"Lines {start_l:>3}-{end_l:>3} | Count: {cnt:>2} | {status} | Snippet: {p_text[:75]}...")

if __name__ == "__main__":
    main()
