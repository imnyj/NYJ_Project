#!/usr/bin/env python3
"""
deep_paragraph_audit.py
Accurate paragraph extraction and sentence counting across all sections of main.tex.
"""

import re
from pathlib import Path

MAIN_TEX = Path("/home/imnyj/Workspace/paper4/latex/main.tex")

def clean_latex(text):
    # Remove comments
    text = re.sub(r"(?<!\\)%.*$", "", text, flags=re.MULTILINE)
    # Remove equation environments
    text = re.sub(r"\\begin\{equation\*?\}.*?\\end\{equation\*?\}", " [EQUATION] ", text, flags=re.DOTALL)
    text = re.sub(r"\\begin\{align\*?\}.*?\\end\{align\*?\}", " [EQUATION] ", text, flags=re.DOTALL)
    text = re.sub(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", " [TABLE] ", text, flags=re.DOTALL)
    text = re.sub(r"\\begin\{figure\*?\}.*?\\end\{figure\*?\}", " [FIGURE] ", text, flags=re.DOTALL)
    text = re.sub(r"\\begin\{itemize\}.*?\\end\{itemize\}", " [ITEMIZE] ", text, flags=re.DOTALL)
    text = re.sub(r"\\begin\{enumerate\}.*?\\end\{enumerate\}", " [ENUMERATE] ", text, flags=re.DOTALL)
    text = re.sub(r"\\begin\{tabular\*?\}.*?\\end\{tabular\*?\}", " [TABULAR] ", text, flags=re.DOTALL)
    return text

def split_sentences(text):
    # Replace math blocks
    s = re.sub(r"\$[^$]+\$", "MATH_VAR", text)
    # Remove common latex commands like \textbf{...}, \emph{...}, \cite{...}, \ref{...}, \eqref{...}
    s = re.sub(r"\\cite\{[^}]+\}", "[CIT]", s)
    s = re.sub(r"\\ref\{[^}]+\}", "[REF]", s)
    s = re.sub(r"\\eqref\{[^}]+\}", "[EQREF]", s)
    s = re.sub(r"\\(textbf|textit|emph|underline|text|mathrm)\{([^}]+)\}", r"\2", s)
    s = re.sub(r"\\IEEEPARstart\{([^}]+)\}\{([^}]+)\}", r"\1\2", s)
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = re.sub(r"~", " ", s)
    # Replace abbreviation dots to avoid false sentence splits
    abbrs = ["e.g.", "i.e.", "Fig.", "Eq.", "Ref.", "al.", "vs.", "dB.", "sec.", "ms.", "Hz.", "GHz.", "MHz.", "km/h.", "No.", "Vol.", "pp."]
    for a in abbrs:
        s = s.replace(a, a.replace(".", "@DOT@"))
    # Match sentences ending with . ! ? followed by space/quote/newline or end of text
    raw_sentences = re.split(r"(?<=[.!?])\s+", s)
    final_sentences = []
    for sent in raw_sentences:
        sent = sent.replace("@DOT@", ".").strip()
        # filter out empty or trivial
        if len(sent) > 5 and re.search(r"[a-zA-Z]", sent):
            final_sentences.append(sent)
    return final_sentences

def main():
    content = MAIN_TEX.read_text(encoding="utf-8")
    lines = content.splitlines()
    
    # Let's inspect block by block
    # We split by double newlines or section headings
    raw_blocks = re.split(r"\n\s*\n", content)
    
    print(f"Total raw blocks: {len(raw_blocks)}")
    
    narrative_paragraphs = []
    
    for idx, block in enumerate(raw_blocks, 1):
        # find line range in main.tex
        block_cleaned = clean_latex(block).strip()
        if not block_cleaned:
            continue
        
        # Check if block is preamble, macro, title, author, abstract header, or keywords
        if block_cleaned.startswith("\\documentclass") or block_cleaned.startswith("\\usepackage") or block_cleaned.startswith("\\newcolumntype"):
            continue
        if block_cleaned.startswith("\\title") or block_cleaned.startswith("\\author") or block_cleaned.startswith("\\maketitle"):
            continue
        if block_cleaned.startswith("\\begin{IEEEkeywords}") or block_cleaned.startswith("\\begin{abstract}"):
            # Let's check abstract separately
            pass
        if block_cleaned.startswith("\\bibliographystyle") or block_cleaned.startswith("\\bibliography"):
            continue
        if block_cleaned == "[TABLE]" or block_cleaned == "[FIGURE]" or block_cleaned == "[EQUATION]" or block_cleaned == "[ITEMIZE]":
            continue
            
        # Strip section headers from text
        header_match = re.match(r"^\\(section|subsection|subsubsection|paragraph)\*?\{([^}]+)\}\s*", block_cleaned)
        header_name = ""
        if header_match:
            header_name = f"\\{header_match.group(1)}{{{header_match.group(2)}}}"
            block_cleaned = block_cleaned[header_match.end():].strip()
        
        # If what remains is just whitespace or a table/figure placeholder, skip
        if not block_cleaned or block_cleaned in ["[TABLE]", "[FIGURE]", "[EQUATION]", "[ITEMIZE]"]:
            continue
            
        sentences = split_sentences(block_cleaned)
        narrative_paragraphs.append((idx, header_name, block_cleaned, sentences))

    print(f"Total narrative paragraphs extracted: {len(narrative_paragraphs)}")
    
    short_count = 0
    for idx, header, text, sents in narrative_paragraphs:
        s_count = len(sents)
        status = "OK" if s_count >= 5 else "SHORT (<5)"
        if s_count < 5:
            short_count += 1
        print(f"\n--- Block {idx} [{status}] ({s_count} sentences) ---")
        if header:
            print(f"Heading: {header}")
        print(f"First 100 chars: {text[:100]}...")
        for s_idx, s in enumerate(sents, 1):
            print(f"  ({s_idx}) {s}")

    print("\n" + "="*60)
    print(f"TOTAL PARAGRAPHS: {len(narrative_paragraphs)}")
    print(f"PARAGRAPHS >= 5 SENTENCES: {len(narrative_paragraphs) - short_count}")
    print(f"PARAGRAPHS < 5 SENTENCES: {short_count}")
    print("="*60)

if __name__ == "__main__":
    main()
