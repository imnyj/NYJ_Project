import sys
import re

def verify_on_disk():
    with open('/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md', 'r', encoding='utf-8') as f:
        text = f.read()
    lines = text.split('\n')

    print("=================================================================")
    print("=== 1. REFERENCES & CITATIONS BIJECTIVE MAPPING VERIFICATION ===")
    print("=================================================================")
    ref_sec_idx = -1
    for idx, line in enumerate(lines):
        if idx > 100 and ("# 참고문헌" in line or "# References" in line or "## 참고문헌" in line):
            ref_sec_idx = idx
            break
    
    print(f"References section at line {ref_sec_idx + 1}")
    ref_defs = {}
    for idx in range(ref_sec_idx, len(lines)):
        m = re.match(r'^\s*\[(\d+)\]\s+(.+)', lines[idx])
        if m:
            ref_defs[int(m.group(1))] = m.group(2).strip()
    
    print(f"Total References defined: {len(ref_defs)} (1..{len(ref_defs)})")

    citation_matches = []
    for idx, line in enumerate(lines[:ref_sec_idx], 1):
        line_clean = re.sub(r'\$\$[^\$]+\$\$', '', line)
        parts = line_clean.split('$')
        outside_math = " ".join([parts[k] for k in range(0, len(parts), 2)])
        
        matches = re.finditer(r'\[([\d\s,–\-\~]+)\](?!\()', outside_math)
        for m in matches:
            citation_matches.append((idx, m.group(1)))
    
    cited_numbers = set()
    for line_no, token in citation_matches:
        for p in re.split(r'[,]', token):
            p = p.strip()
            if not p:
                continue
            range_match = re.match(r'(\d+)\s*[–\-\~]\s*(\d+)', p)
            if range_match:
                for n in range(int(range_match.group(1)), int(range_match.group(2)) + 1):
                    cited_numbers.add(n)
            elif re.match(r'^\d+$', p):
                cited_numbers.add(int(p))
    
    print(f"Total Unique Citation Numbers: {len(cited_numbers)} (Citations: {sorted(list(cited_numbers))})")
    print(f"Missing in text: {set(ref_defs.keys()) - cited_numbers}")
    print(f"Missing in refs: {cited_numbers - set(ref_defs.keys())}")
    assert set(ref_defs.keys()) == cited_numbers, "Bijective citation mapping failed!"
    print("--> Bijective citation mapping: 100% PERFECT PASS")

    print("\n=================================================================")
    print("=== 2. LATEX FORMULAS & MATH SYNTAX INTEGRITY VERIFICATION ======")
    print("=================================================================")
    math_errors = []
    in_display = False
    for idx, line in enumerate(lines, 1):
        s = line.strip()
        if s == "$$":
            in_display = not in_display
            continue
        if s.startswith("$$") and s.endswith("$$") and len(s) > 2:
            continue
        if "$$" in s:
            if s.count("$$") % 2 != 0:
                math_errors.append((idx, f"Odd $$: {s}"))
        if not in_display:
            temp = re.sub(r'\$\$', '', s)
            temp = re.sub(r'\\\$', '', temp)
            if temp.count('$') % 2 != 0:
                math_errors.append((idx, f"Unmatched single $: {s[:100]}"))
    
    print(f"LaTeX Delimiter Errors: {len(math_errors)}")
    for err in math_errors:
        print(f"  Line {err[0]}: {err[1]}")
    assert len(math_errors) == 0, "LaTeX delimiter error detected!"

    nakagami_errors = [(i+1, l) for i, l in enumerate(lines) if "Nakagami-$ " in l or "Nakagami-$\n" in l or "Nakagami-$ 페" in l]
    print(f"Nakagami broken syntax: {len(nakagami_errors)}")
    assert len(nakagami_errors) == 0, "Broken Nakagami syntax detected!"
    print("--> LaTeX syntax & delimiters: 100% PERFECT PASS")

    print("\n=================================================================")
    print("=== 3. MARKDOWN TABLES RENDERING INTEGRITY ======================")
    print("=================================================================")
    tables = []
    cur_t = []
    cur_start = 0
    for idx, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            if not cur_t:
                cur_start = idx
            cur_t.append((idx, s))
        else:
            if cur_t:
                tables.append((cur_start, idx - 1, cur_t))
                cur_t = []
    if cur_t:
        tables.append((cur_start, len(lines), cur_t))
    
    print(f"Total Markdown tables: {len(tables)}")
    table_errors = []
    for t_idx, (start, end, t_lines) in enumerate(tables, 1):
        def parse_cols(l):
            inner = l.strip()[1:-1]
            return [c.strip() for c in inner.split("|")]
        num_cols = len(parse_cols(t_lines[0][1]))
        for l_num, l_str in t_lines:
            cols = parse_cols(l_str)
            if len(cols) != num_cols:
                table_errors.append((t_idx, l_num, num_cols, len(cols), l_str))
    
    print(f"Table rendering errors: {len(table_errors)}")
    for err in table_errors:
        print(f"  Table {err[0]} Line {err[1]}: expected {err[2]} cols, got {err[3]} -> {err[4][:80]}")
    assert len(table_errors) == 0, "Markdown table column mismatch detected!"
    print("--> Markdown table rendering: 100% PERFECT PASS")

    print("\n=================================================================")
    print("=== 4. EXAGGERATED EXPRESSIONS & AI CLICHÉS AUDIT ===============")
    print("=================================================================")
    bad_words = ["완벽히", "완벽하게", "원천 차단", "독보적인", "획기적인", "경이로운"]
    found_bad = []
    for i, l in enumerate(lines[:ref_sec_idx], 1):
        for w in bad_words:
            if w in l:
                found_bad.append((i, w, l.strip()))
    print(f"Found exaggerated expressions: {len(found_bad)}")
    for fb in found_bad:
        print(f"  Line {fb[0]} [{fb[1]}]: {fb[2][:100]}")
    assert len(found_bad) == 0, f"Exaggerated expressions remaining: {len(found_bad)}"
    print("--> Academic tone & adverbs: 100% PERFECT PASS")

    print("\n=================================================================")
    print("=== 5. PARAGRAPH SENTENCE COUNT VERIFICATION (>= 5 SENTENCES) ===")
    print("=================================================================")
    all_paras = []
    curr_para = []
    curr_para_start = 1
    in_code = False

    for idx, line in enumerate(lines[:ref_sec_idx], 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            if curr_para:
                all_paras.append((curr_para_start, idx - 1, " ".join(curr_para)))
                curr_para = []
            continue
        if in_code:
            continue

        is_special = (
            stripped.startswith("#") or
            stripped.startswith("---") or
            stripped.startswith("|") or
            stripped.startswith("$$") or
            stripped.startswith("<") or
            stripped.startswith("**저자") or
            stripped.startswith("**소속") or
            stripped.startswith("**연락처") or
            stripped.startswith("**타깃") or
            stripped.startswith("**색인어") or
            stripped.startswith("**표 ") or
            stripped.startswith("**그림 ") or
            stripped.startswith("*표 ") or
            stripped.startswith("*그림 ") or
            stripped.startswith("- ") or
            stripped.startswith("* ") or
            stripped.startswith("1. ") or
            stripped.startswith("2. ") or
            stripped.startswith("3. ") or
            stripped.startswith("4. ") or
            stripped.startswith("5. ") or
            stripped.startswith("6. ") or
            stripped.startswith("7. ") or
            stripped.startswith("8. ") or
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

    short_paras = []
    for start_l, end_l, p_text in all_paras:
        clean_text = re.sub(r'et al\.', 'et al', p_text)
        clean_text = re.sub(r'e\.g\.', 'eg', clean_text)
        clean_text = re.sub(r'i\.e\.', 'ie', clean_text)
        clean_text = re.sub(r'(\d+)\.(\d+)', r'\1_\2', clean_text)
        sentences = [s.strip() for s in re.split(r'[\.\?\!](?:\s*\[[\d\s,–\-]+\])?\s+', clean_text) if len(s.strip()) > 5]
        if len(sentences) < 5:
            short_paras.append((start_l, end_l, len(sentences), p_text, sentences))

    print(f"Total prose paragraphs analyzed: {len(all_paras)}")
    print(f"Short paragraphs (< 5 sentences): {len(short_paras)}")
    for sl, el, sc, t, sents in short_paras:
        print(f"  Lines {sl}-{el} ({sc} sentences): {t[:100]}...")
    assert len(short_paras) == 0, f"Short paragraphs detected: {len(short_paras)}"
    print("--> Paragraph length compliance (>= 5 sentences): 100% PERFECT PASS")

    print("\n=================================================================")
    print("=== 6. NUMERICAL & NOTATION CONSISTENCY VERIFICATION ===========")
    print("=================================================================")
    assert "76.4%" not in text, "Outdated PDR 76.4% found in text!"
    assert "10만 개 미만" not in text, "Outdated param count '10만 개 미만' found in text!"
    assert "마이크로초 단위의" not in text, "Outdated latency '마이크로초 단위의' found in text!"
    print("--> Outdated numbers: NONE (All removed & updated)")

    cbr_issues = []
    for i, l in enumerate(lines, 1):
        parts = l.split('$')
        if len(parts) >= 3:
            for pi in range(1, len(parts), 2):
                m = parts[pi]
                if 'CBR' in m and r'\text{CBR}' not in m:
                    cbr_issues.append((i, m))
    print(f"CBR non-romanized in math: {len(cbr_issues)}")
    assert len(cbr_issues) == 0, "CBR non-romanized in math found!"

    print("--> Math notation consistency: 100% PERFECT PASS")
    print("\n=================================================================")
    print("=== ON-DISK DELIVERABLE VALIDATION: 100% PERFECT PASS! ==========")
    print("=================================================================")

if __name__ == '__main__':
    verify_on_disk()
