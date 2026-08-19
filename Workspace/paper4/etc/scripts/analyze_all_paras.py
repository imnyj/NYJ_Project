import re

with open('/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find references section
ref_sec_idx = -1
for idx, line in enumerate(lines):
    if idx > 100 and ("# 참고문헌" in line or "# References" in line or "## 참고문헌" in line):
        ref_sec_idx = idx
        break

all_paras = []
curr_para = []
curr_para_start = 1

for idx, line in enumerate(lines[:ref_sec_idx], 1):
    stripped = line.strip()
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

print(f"Total prose paragraphs: {len(all_paras)}")

short_paras = []
for start_l, end_l, text in all_paras:
    # Clean abbreviations and floating numbers
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
    clean_text = re.sub(r'(\d+)\.(\d+)', r'\1_\2', clean_text)
    
    sentences = [s.strip() for s in re.split(r'[\.\?\!](?:\s*\[[\d\s,–\-]+\])?\s+', clean_text) if len(s.strip()) > 5]
    s_count = len(sentences)
    if s_count < 5:
        short_paras.append((start_l, end_l, s_count, text, sentences))

print(f"Short paragraphs (< 5 sentences): {len(short_paras)}")
for start_l, end_l, s_count, text, sents in short_paras:
    print(f"\n--- Lines {start_l}-{end_l} ({s_count} sentences) ---")
    print(text)
    print("Sentences detected:")
    for si, s in enumerate(sents, 1):
        print(f"  [{si}] {s}")
