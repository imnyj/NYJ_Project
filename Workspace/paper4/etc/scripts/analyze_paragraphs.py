import re

with open("/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md", "r", encoding="utf-8") as f:
    text = f.read()
    lines = text.split("\n")

print("=== DETAILED SECTION-BY-SECTION PARAGRAPH ANALYSIS ===")

# Identify all sections
sections = []
curr_sec = "Header"
curr_lines = []
for idx, l in enumerate(lines, 1):
    if l.startswith("# ") or l.startswith("## ") or l.startswith("### "):
        if curr_lines:
            sections.append((curr_sec, curr_lines))
        curr_sec = f"{idx}: {l.strip()}"
        curr_lines = []
    else:
        curr_lines.append((idx, l))
if curr_lines:
    sections.append((curr_sec, curr_lines))

for s_title, s_lines in sections:
    print(f"\n=======================================================")
    print(f"SECTION: {s_title}")
    # group into prose paragraphs
    paras = []
    curr_p = []
    p_start = 0
    for l_num, l_str in s_lines:
        s = l_str.strip()
        is_sp = (
            s.startswith("#") or s.startswith("---") or s.startswith("|") or 
            s.startswith("$$") or s.startswith("```") or s.startswith("<") or 
            s.startswith("**저자") or s.startswith("**소속") or s.startswith("**연락처") or 
            s.startswith("**타깃") or s.startswith("**색인어") or s.startswith("**표 ") or 
            s.startswith("**그림 ") or s.startswith("- ") or s.startswith("* ") or 
            s.startswith("1. ") or s.startswith("2. ") or s.startswith("3. ") or 
            s.startswith("4. ") or s.startswith("5. ") or s.startswith("### Algorithm") or
            s == ""
        )
        if is_sp:
            if curr_p:
                paras.append((p_start, l_num - 1, " ".join(curr_p)))
                curr_p = []
        else:
            if not curr_p:
                p_start = l_num
            curr_p.append(s)
    if curr_p:
        paras.append((p_start, s_lines[-1][0], " ".join(curr_p)))

    print(f"Total prose paragraphs: {len(paras)}")
    for p_idx, (st, en, p_text) in enumerate(paras, 1):
        clean_text = re.sub(r'et al\.', 'et al', p_text)
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
        clean_text = re.sub(r'(\d+)\.(\d+)', r'\1_\2', clean_text)
        
        sentences = [s.strip() for s in re.split(r'[\.\?\!](?:\s*\[[\d\s,–\-]+\])?\s+', clean_text) if len(s.strip()) > 5]
        status = "OK" if len(sentences) >= 5 else f"SHORT ({len(sentences)} sentences)"
        print(f"  P{p_idx} [Lines {st}-{en}] ({status}): {p_text[:80]}...")
