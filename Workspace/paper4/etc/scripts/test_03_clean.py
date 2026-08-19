import sys
sys.path.append('etc/scripts')
from update_03_clean import update_03_system_model
import re

with open('/home/imnyj/Workspace/paper4/paper/03_system_model.md', 'r') as f:
    orig = f.read()

rev = update_03_system_model(orig)
lines = rev.split('\n')

all_paras = []
curr_para = []
curr_para_start = 1
in_code = False

for idx, line in enumerate(lines, 1):
    stripped = line.strip()
    if stripped.startswith("```"):
        in_code = not in_code
        if curr_para:
            all_paras.append((curr_para_start, idx - 1, '\n'.join(curr_para)))
            curr_para = []
        continue
    if in_code:
        continue

    is_special = (
        stripped.startswith('#') or
        stripped.startswith('---') or
        stripped.startswith('|') or
        stripped.startswith('$$') or
        stripped.startswith('<') or
        stripped.startswith('**저자') or
        stripped.startswith('**소속') or
        stripped.startswith('**연락처') or
        stripped.startswith('**타깃') or
        stripped.startswith('**색인어') or
        stripped.startswith('**표 ') or
        stripped.startswith('**그림 ') or
        stripped.startswith('*표 ') or
        stripped.startswith('*그림 ') or
        stripped.startswith('- ') or
        stripped.startswith('* ') or
        stripped.startswith('1. ') or
        stripped.startswith('2. ') or
        stripped.startswith('3. ') or
        stripped.startswith('4. ') or
        stripped.startswith('5. ') or
        stripped.startswith('6. ') or
        stripped.startswith('7. ') or
        stripped.startswith('8. ') or
        stripped == ''
    )
    if is_special:
        if curr_para:
            all_paras.append((curr_para_start, idx - 1, '\n'.join(curr_para)))
            curr_para = []
    else:
        if not curr_para:
            curr_para_start = idx
        curr_para.append(stripped)
if curr_para:
    all_paras.append((curr_para_start, len(lines), '\n'.join(curr_para)))

short_paras = []
for start_l, end_l, p_text in all_paras:
    clean_text = re.sub(r'et al\.', 'et al', p_text)
    clean_text = re.sub(r'e\.g\.', 'eg', clean_text)
    clean_text = re.sub(r'i\.e\.', 'ie', clean_text)
    clean_text = re.sub(r'(\d+)\.(\d+)', r'\1_\2', clean_text)
    sentences = [s.strip() for s in re.split(r'[\.\?\!](?:\s*\[[\d\s,–\-]+\])?\s+', clean_text) if len(s.strip()) > 5]
    if len(sentences) < 5:
        short_paras.append((start_l, end_l, len(sentences), p_text, sentences))

print(f'Total prose paragraphs in 03_system_model: {len(all_paras)}')
print(f'Short paragraphs in 03_system_model: {len(short_paras)}')
for idx, (sl, el, sc, p_text, sents) in enumerate(short_paras, 1):
    print(f'=== [{idx}] Lines {sl}-{el} ({sc} sentences) ===')
    print(repr(p_text))

assert len(short_paras) == 0, f"Short paras remaining in 03: {len(short_paras)}"
print("03_system_model: 100% PERFECT PASS!")
