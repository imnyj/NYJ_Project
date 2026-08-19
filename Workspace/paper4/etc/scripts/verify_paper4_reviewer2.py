import re
import sys

def verify_draft(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        content = "".join(lines)

    print("=================================================================")
    print("=== 1. REFERENCES & CITATIONS BIJECTIVE MAPPING VERIFICATION ===")
    print("=================================================================")
    # Find actual References section header (not Table of Contents)
    # The actual References section is usually near the bottom, e.g., # 참고문헌 (References) or # VI. 참고문헌 or # References
    ref_sec_idx = -1
    for idx, line in enumerate(lines):
        if idx > 100 and ("# 참고문헌" in line or "# References" in line or "## 참고문헌" in line or "## References" in line):
            ref_sec_idx = idx
            break
    
    print(f"References section header found at line {ref_sec_idx + 1 if ref_sec_idx != -1 else 'NOT FOUND'}")
    
    ref_defs = {}
    ref_raw_lines = {}
    if ref_sec_idx != -1:
        for idx in range(ref_sec_idx, len(lines)):
            line = lines[idx]
            m = re.match(r'^\s*\[(\d+)\]\s+(.+)', line)
            if m:
                num = int(m.group(1))
                ref_defs[num] = m.group(2).strip()
                ref_raw_lines[num] = idx + 1
    
    print(f"Total References defined: {len(ref_defs)} entries (Numbers: {sorted(list(ref_defs.keys()))})")

    # Extract all citations in main text before references section
    body_text = "".join(lines[:ref_sec_idx]) if ref_sec_idx != -1 else content
    
    # Let's find all citation patterns like [1], [1], [2], [1]-[3], [1]–[3], [11]–[13], [1], [3], [5]
    # Be careful not to match Markdown links [text](url) or [TBD]
    citation_matches = []
    for idx, line in enumerate(lines[:ref_sec_idx], 1):
        # Ignore markdown links like [text](...)
        # Find bracketed numbers
        # Pattern: [digits, dashes, commas, spaces] NOT followed by (
        matches = re.finditer(r'\[([\d\s,–\-\~]+)\](?!\()', line)
        for m in matches:
            token = m.group(1)
            citation_matches.append((idx, token, line.strip()))
    
    cited_numbers_with_loc = {}
    for line_no, token, raw_line in citation_matches:
        parts = re.split(r'[,]', token)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            range_match = re.match(r'(\d+)\s*[–\-\~]\s*(\d+)', p)
            if range_match:
                start, end = int(range_match.group(1)), int(range_match.group(2))
                for n in range(start, end + 1):
                    if n not in cited_numbers_with_loc:
                        cited_numbers_with_loc[n] = []
                    cited_numbers_with_loc[n].append(line_no)
            elif re.match(r'^\d+$', p):
                n = int(p)
                if n not in cited_numbers_with_loc:
                    cited_numbers_with_loc[n] = []
                cited_numbers_with_loc[n].append(line_no)
    
    cited_numbers = set(cited_numbers_with_loc.keys())
    print(f"Total Unique Citation Numbers in text: {len(cited_numbers)} (Numbers: {sorted(list(cited_numbers))})")
    
    # Bijective check
    missing_in_body = set(ref_defs.keys()) - cited_numbers
    missing_in_refs = cited_numbers - set(ref_defs.keys())
    
    print(f"--> References defined but never cited in body: {missing_in_body if missing_in_body else 'None (PERFECT)'}")
    print(f"--> Citations in body but missing in references: {missing_in_refs if missing_in_refs else 'None (PERFECT)'}")

    # Check for sequential reference definition
    expected_refs = set(range(1, len(ref_defs) + 1))
    if set(ref_defs.keys()) != expected_refs:
        print(f"--> Reference numbers are NOT contiguous 1..{len(ref_defs)}! Missing: {expected_refs - set(ref_defs.keys())}")
    else:
        print(f"--> Reference list is strictly contiguous from [1] to [{len(ref_defs)}].")

    print("\n=================================================================")
    print("=== 2. LATEX FORMULAS & MATH NOTATION INTEGRITY VERIFICATION ===")
    print("=================================================================")
    
    # 1. Delimiter balance check
    math_errors = []
    in_display_math = False
    display_start = 0
    
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Display math $$
        if stripped == "$$":
            if not in_display_math:
                in_display_math = True
                display_start = idx
            else:
                in_display_math = False
            continue
        
        if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 2:
            # Single line display math
            math_content = stripped[2:-2]
            # Check balance of \left and \right, { and }
            if math_content.count('{') != math_content.count('}'):
                math_errors.append((idx, f"Unbalanced braces {{}}: {stripped}"))
            if math_content.count(r'\left') != math_content.count(r'\right'):
                math_errors.append((idx, f"Unbalanced \\left and \\right: {stripped}"))
            continue

        if "$$" in stripped:
            # Inline display math
            count_dd = stripped.count("$$")
            if count_dd % 2 != 0:
                math_errors.append((idx, f"Odd number of $$ on line: {stripped}"))
        
        if not in_display_math:
            # Check single $
            temp = re.sub(r'\$\$', '', stripped)
            temp = re.sub(r'\\\$', '', temp)
            # Remove markdown table pipe if any
            count_s = temp.count('$')
            if count_s % 2 != 0:
                math_errors.append((idx, f"Unmatched single $ delimiter ({count_s} occurrences): {stripped[:100]}"))

    print(f"Found {len(math_errors)} LaTeX syntax / delimiter errors:")
    for err in math_errors:
        print(f"  Line {err[0]}: {err[1]}")

    # Specific math checks:
    # 2. Check for "Nakagami-$"
    for idx, line in enumerate(lines, 1):
        if "Nakagami-$ " in line or "Nakagami-$\n" in line or "Nakagami-$ 페" in line:
            print(f"  [CRITICAL SYNTAX ERROR] Line {idx}: Broken Nakagami formula: {line.strip()[:100]}")

    # 3. Check Notation Consistency across Equations and Text
    print("\n--- Notation Consistency Audit ---")
    # Let's inspect math formulas
    # Extract all inline and display math expressions
    inline_maths = re.findall(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', content)
    display_maths = re.findall(r'\$\$(.+?)\$\$', content, re.DOTALL)
    
    print(f"Extracted {len(inline_maths)} inline math expressions and {len(display_maths)} display math blocks.")
    
    # State notation in math:
    s_notations = set()
    for m in inline_maths + display_maths:
        found = re.findall(r'\b[sS](?:_t|\(t\)|_\{t\}|\b)', m)
        for f in found:
            s_notations.add(f)
    print(f"State notations in math: {s_notations}")

    # Action notation in math:
    a_notations = set()
    for m in inline_maths + display_maths:
        found = re.findall(r'\b[aA](?:_t|\(t\)|_\{t\}|\b)', m)
        for f in found:
            a_notations.add(f)
    print(f"Action notations in math: {a_notations}")

    # Reward notation in math:
    r_notations = set()
    for m in inline_maths + display_maths:
        found = re.findall(r'\b[rR](?:_t|\(t\)|_\{t\}|_1|_2|_3|_4|_5|\([^\)]+\)|\b)', m)
        for f in found:
            r_notations.add(f)
    print(f"Reward notations in math: {r_notations}")

    # Q-function notation:
    q_notations = set()
    for m in inline_maths + display_maths:
        found = re.findall(r'Q\([^\)]+\)', m)
        for f in found:
            q_notations.add(f)
    print(f"Q-function notations in math: {q_notations}")

    # CBR / AoI / PDR in math:
    cbr_math = set()
    aoi_math = set()
    pdr_math = set()
    for m in inline_maths + display_maths:
        if "CBR" in m:
            cbr_math.update(re.findall(r'[^\s\+\-\*\/\=\(\)\,\;]*CBR[^\s\+\-\*\/\=\(\)\,\;]*', m))
        if "AoI" in m:
            aoi_math.update(re.findall(r'[^\s\+\-\*\/\=\(\)\,\;]*AoI[^\s\+\-\*\/\=\(\)\,\;]*', m))
        if "PDR" in m:
            pdr_math.update(re.findall(r'[^\s\+\-\*\/\=\(\)\,\;]*PDR[^\s\+\-\*\/\=\(\)\,\;]*', m))
    print(f"CBR math terms: {cbr_math}")
    print(f"AoI math terms: {aoi_math}")
    print(f"PDR math terms: {pdr_math}")

    print("\n=================================================================")
    print("=== 3. MARKDOWN TABLES & ALGORITHM 1 RENDERING INTEGRITY ========")
    print("=================================================================")
    
    # Parse tables
    tables = []
    cur_table_lines = []
    cur_start = 0
    in_table = False
    
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                in_table = True
                cur_start = idx
                cur_table_lines = []
            cur_table_lines.append((idx, stripped))
        else:
            if in_table:
                in_table = False
                tables.append((cur_start, idx - 1, cur_table_lines))
                cur_table_lines = []
    if in_table:
        tables.append((cur_start, len(lines), cur_table_lines))
    
    print(f"Detected {len(tables)} Markdown tables in document.")
    for t_idx, (start, end, t_lines) in enumerate(tables, 1):
        header_line = t_lines[0]
        sep_line = t_lines[1] if len(t_lines) > 1 else None
        
        # Split cols
        def parse_cols(l):
            # Strip leading and trailing '|'
            inner = l.strip()[1:-1]
            return [c.strip() for c in inner.split("|")]
        
        header_cols = parse_cols(header_line[1])
        num_cols = len(header_cols)
        
        mismatches = []
        for l_num, l_str in t_lines:
            cols = parse_cols(l_str)
            if len(cols) != num_cols:
                mismatches.append((l_num, len(cols), l_str))
        
        print(f"Table {t_idx} (Lines {start}-{end}): Header columns = {num_cols}, Total rows = {len(t_lines)}")
        if mismatches:
            print(f"  [TABLE RENDERING DEFECT] {len(mismatches)} rows have column count mismatch!")
            for l_num, col_c, l_str in mismatches:
                print(f"    Line {l_num}: Expected {num_cols} cols, got {col_c} cols -> {l_str[:80]}")

    # Inspect Algorithm 1
    print("\n--- Algorithm 1 Structure & Pseudocode Audit ---")
    algo_start = -1
    algo_end = -1
    for idx, line in enumerate(lines, 1):
        if "Algorithm 1" in line:
            algo_start = idx
            break
    if algo_start != -1:
        for idx in range(algo_start, min(algo_start + 100, len(lines) + 1)):
            if lines[idx - 1].startswith("```"):
                if algo_end == -1:
                    algo_end = idx
                else:
                    algo_end = idx
                    break
        print(f"Algorithm 1 found around line {algo_start} to {algo_end}.")
        for idx in range(algo_start - 2, min(algo_end + 5, len(lines) + 1)):
            print(f"  {idx}: {lines[idx-1].rstrip()}")

    print("\n=================================================================")
    print("=== 4. ACADEMIC WRITING STYLE & PARAGRAPH ANALYSIS ==============")
    print("=================================================================")
    
    # Split text into major sections
    # Check section by section paragraph sentence count
    section_headers = []
    for idx, line in enumerate(lines, 1):
        if re.match(r'^#+\s+', line):
            section_headers.append((idx, line.strip()))
    
    print(f"Detected {len(section_headers)} Section Headers.")
    
    # Examine each paragraph between section headers
    sec_idx = 0
    all_paras = []
    curr_para = []
    curr_para_start = 1
    
    for idx, line in enumerate(lines[:ref_sec_idx], 1):
        stripped = line.strip()
        # Check if header, table, math block, list, blockquote, hr
        is_special = (
            stripped.startswith("#") or
            stripped.startswith("---") or
            stripped.startswith("|") or
            stripped.startswith("$$") or
            stripped.startswith("```") or
            stripped.startswith("<") or
            stripped.startswith("**저자") or
            stripped.startswith("**소속") or
            stripped.startswith("**연락처") or
            stripped.startswith("**타깃") or
            stripped.startswith("**색인어") or
            stripped.startswith("**표 ") or
            stripped.startswith("**그림 ") or
            stripped.startswith("- ") or
            stripped.startswith("* ") or
            stripped == ""
        )
        if is_special:
            if curr_para:
                all_paras.append((curr_para_start, idx - 1, " ".join(curr_para)))
                curr_para = []
        else:
            if not curr_para:
                curr_para_start = idx
            curr_para.append(stripped)
    if curr_para:
        all_paras.append((curr_para_start, ref_sec_idx - 1, " ".join(curr_para)))

    print(f"Total standard prose paragraphs analyzed in body: {len(all_paras)}")
    
    short_paras = []
    for start_l, end_l, text in all_paras:
        clean_text = re.sub(r'et al\.', 'et al', text)
        clean_text = re.sub(r'e\.g\.', 'eg', clean_text)
        clean_text = re.sub(r'i\.e\.', 'ie', clean_text)
        clean_text = re.sub(r'Fig\.', 'Fig', clean_text)
        clean_text = re.sub(r'Tab\.', 'Tab', clean_text)
        clean_text = re.sub(r'vs\.', 'vs', clean_text)
        clean_text = re.sub(r'Eq\.', 'Eq', clean_text)
        clean_text = re.sub(r'Sec\.', 'Sec', clean_text)
        clean_text = re.sub(r'Ref\.', 'Ref', clean_text)
        clean_text = re.sub(r'approx\.', 'approx', clean_text)
        clean_text = re.sub(r'No\.', 'No', clean_text)
        clean_text = re.sub(r'(\d+)\.(\d+)', r'\1_\2', clean_text) # numbers like 0.60
        
        # Split sentences
        sentences = [s.strip() for s in re.split(r'[\.\?\!](?:\s*\[[\d\s,–\-]+\])?\s+', clean_text) if len(s.strip()) > 5]
        s_count = len(sentences)
        if s_count < 5:
            short_paras.append((start_l, end_l, s_count, text))

    print(f"\nParagraphs with LESS THAN 5 SENTENCES (Violation of academic-writing-style requirement): {len(short_paras)}")
    for start_l, end_l, s_count, text in short_paras:
        print(f"  Line {start_l}-{end_l} ({s_count} sentences): {text[:120]}...")

    print("\n--- AI Clichés, Exaggerated Expressions & Parentheses Audit ---")
    adverbs_to_check = [
        "독보적인", "완벽히", "완벽하게", "원천 차단", "획기적인", "극적인", "경이로운",
        "elucidate", "seamless", "vital", "fosters", "comprehensive", "significantly", "substantially",
        "leveraging", "leverages", "utilizing", "subsequently", "systematically", "effectively", "autonomously", "encapsulates"
    ]
    for adv in adverbs_to_check:
        matches = [(idx, line.strip()) for idx, line in enumerate(lines[:ref_sec_idx], 1) if adv.lower() in line.lower()]
        if matches:
            print(f"  Word '{adv}': {len(matches)} occurrences")
            for idx, line in matches[:2]:
                print(f"    Line {idx}: {line[:90]}")

    # Parentheses count
    paren_matches = [(idx, line.strip()) for idx, line in enumerate(lines[:ref_sec_idx], 1) if "(" in line and ")" in line]
    print(f"\nLines with parentheses: {len(paren_matches)} out of {ref_sec_idx} lines.")

if __name__ == "__main__":
    verify_draft("/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md")
