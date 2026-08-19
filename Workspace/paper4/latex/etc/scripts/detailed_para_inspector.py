#!/usr/bin/env python3
"""
detailed_para_inspector.py (Fixed)
Inspects all narrative paragraphs in main.tex with line numbers and exact text.
"""

import re
from pathlib import Path

MAIN_TEX = Path("/home/imnyj/Workspace/paper4/latex/main.tex")

EXCLUDED_ENVS = {"equation", "equation*", "align", "align*", "figure", "figure*", "table", "table*", "tabular", "tabularx", "itemize", "enumerate"}

def main():
    lines = MAIN_TEX.read_text(encoding="utf-8").splitlines()
    
    paragraphs = []
    current_para_lines = []
    in_env = []
    
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Check comments
        if stripped.startswith("%"):
            continue
            
        # Check environment begins / ends
        begins = re.findall(r"\\begin\{([a-zA-Z0-9_\*]+)\}", stripped)
        ends = re.findall(r"\\end\{([a-zA-Z0-9_\*]+)\}", stripped)
        
        for b in begins:
            if b in EXCLUDED_ENVS:
                in_env.append(b)
        
        # Check section headings
        is_heading = bool(re.match(r"^\\(section|subsection|subsubsection|paragraph)\*?\{", stripped))
        is_preamble = bool(re.match(r"^\\(documentclass|usepackage|newcolumntype|title|author|maketitle|IEEEtitleabstractindextext|begin\{IEEEkeywords\}|end\{IEEEkeywords\}|begin\{document\}|end\{document\}|bibliographystyle|bibliography|balance)", stripped))
        
        if is_preamble:
            continue
            
        if is_heading or stripped == "" or len(in_env) > 0:
            if current_para_lines:
                text = " ".join(l for _, l in current_para_lines)
                start_l = current_para_lines[0][0]
                end_l = current_para_lines[-1][0]
                paragraphs.append((start_l, end_l, text))
                current_para_lines = []
        else:
            current_para_lines.append((idx, stripped))
            
        for e in ends:
            if e in in_env:
                in_env.remove(e)
                    
    if current_para_lines:
        text = " ".join(l for _, l in current_para_lines)
        start_l = current_para_lines[0][0]
        end_l = current_para_lines[-1][0]
        paragraphs.append((start_l, end_l, text))

    print(f"Total extracted narrative paragraphs: {len(paragraphs)}")
    
    def count_sents(text):
        s = re.sub(r"\$[^$]+\$", "MATH", text)
        s = re.sub(r"\\cite\{[^}]+\}", "[CIT]", s)
        s = re.sub(r"\\ref\{[^}]+\}", "[REF]", s)
        s = re.sub(r"\\eqref\{[^}]+\}", "[EQREF]", s)
        s = re.sub(r"\\(textbf|textit|emph|underline|text|mathrm)\{([^}]+)\}", r"\2", s)
        s = re.sub(r"\\IEEEPARstart\{([^}]+)\}\{([^}]+)\}", r"\1\2", s)
        s = re.sub(r"\\[a-zA-Z]+", " ", s)
        s = re.sub(r"~", " ", s)
        abbrs = ["e.g.", "i.e.", "Fig.", "Eq.", "Ref.", "al.", "vs.", "dB.", "sec.", "ms.", "Hz.", "GHz.", "MHz.", "km/h.", "No.", "Vol.", "pp."]
        for a in abbrs:
            s = s.replace(a, a.replace(".", "@DOT@"))
        raw = re.split(r"(?<=[.!?])\s+", s)
        sents = [sent.replace("@DOT@", ".").strip() for sent in raw if len(sent.strip()) > 3 and re.search(r"[a-zA-Z]", sent)]
        return len(sents), sents

    short_list = []
    ok_list = []
    
    for start_l, end_l, text in paragraphs:
        cnt, sents = count_sents(text)
        if cnt < 5:
            short_list.append((start_l, end_l, cnt, text, sents))
        else:
            ok_list.append((start_l, end_l, cnt, text, sents))

    print(f"Paragraphs >= 5 sentences: {len(ok_list)}")
    print(f"Paragraphs < 5 sentences: {len(short_list)}")
    
    print("\n" + "="*80)
    print("ALL SHORT PARAGRAPHS (< 5 SENTENCES):")
    print("="*80)
    for start_l, end_l, cnt, text, sents in short_list:
        print(f"\n[Lines {start_l:>3}-{end_l:>3}] Count: {cnt}")
        print(f"Text snippet: {text[:150]}...")
        for i, st in enumerate(sents, 1):
            print(f"   ({i}) {st}")

if __name__ == "__main__":
    main()
