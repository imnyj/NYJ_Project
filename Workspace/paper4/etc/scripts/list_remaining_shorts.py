import sys
sys.path.append('etc/scripts')
from build_full_paper import build_full_paper
import re

text = build_full_paper()
lines = text.split('\n')
ref_sec_idx = -1
for idx, line in enumerate(lines):
    if idx > 100 and ('# 참고문헌' in line or '# References' in line or '## 참고문헌' in line):
        ref_sec_idx = idx
        break

all_paras = []
curr_para = []
curr_para_start = 1

for idx, line in enumerate(lines[:ref_sec_idx], 1):
    stripped = line.strip()
    is_special = (
        stripped.startswith('#') or
        stripped.startswith('---') or
        stripped.startswith('|') or
        stripped.startswith('$$') or
        stripped.startswith('```') or
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
    all_paras.append((curr_para_start, ref_sec_idx - 1, '\n'.join(curr_para)))

short_paras = []
for start_l, end_l, p_text in all_paras:
    clean_text = re.sub(r'et al\.', 'et al', p_text)
    clean_text = re.sub(r'e\.g\.', 'eg', clean_text)
    clean_text = re.sub(r'i\.e\.', 'ie', clean_text)
    clean_text = re.sub(r'(\d+)\.(\d+)', r'\1_\2', clean_text)
    sentences = [s.strip() for s in re.split(r'[\.\?\!](?:\s*\[[\d\s,–\-]+\])?\s+', clean_text) if len(s.strip()) > 5]
    if len(sentences) < 5:
        short_paras.append((start_l, end_l, len(sentences), p_text, sentences))

print(f'Total short paragraphs: {len(short_paras)}')
for idx, (sl, el, sc, p_text, sents) in enumerate(short_paras, 1):
    print(f'=== [{idx}] Lines {sl}-{el} ({sc} sentences) ===')
    print(repr(p_text))
