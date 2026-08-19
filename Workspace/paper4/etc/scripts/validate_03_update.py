import re
import sys
sys.path.append('etc/scripts')
from test_update_03 import update_03_system_model

text = update_03_system_model()
lines = text.split('\n')

all_paras = []
curr_para = []
curr_para_start = 1

for idx, line in enumerate(lines, 1):
    stripped = line.strip()
    is_special = (
        stripped.startswith('#') or
        stripped.startswith('---') or
        stripped.startswith('|') or
        stripped.startswith('$$') or
        stripped.startswith('```') or
        stripped.startswith('<') or
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
        stripped == ''
    )
    if is_special:
        if curr_para:
            all_paras.append((curr_para_start, idx - 1, ' '.join(curr_para)))
            curr_para = []
    else:
        if not curr_para:
            curr_para_start = idx
        curr_para.append(stripped)
if curr_para:
    all_paras.append((curr_para_start, len(lines), ' '.join(curr_para)))

print(f'Total prose paras: {len(all_paras)}')
short_paras = []
for start_l, end_l, p_text in all_paras:
    clean_text = re.sub(r'et al\.', 'et al', p_text)
    clean_text = re.sub(r'e\.g\.', 'eg', clean_text)
    clean_text = re.sub(r'i\.e\.', 'ie', clean_text)
    clean_text = re.sub(r'(\d+)\.(\d+)', r'\1_\2', clean_text)
    sentences = [s.strip() for s in re.split(r'[\.\?\!](?:\s*\[[\d\s,–\-]+\])?\s+', clean_text) if len(s.strip()) > 5]
    if len(sentences) < 5:
        short_paras.append((start_l, end_l, len(sentences), p_text, sentences))

print(f'Short paragraphs (< 5 sentences): {len(short_paras)}')
for sl, el, sc, t, sents in short_paras:
    print(f'  Line {sl}-{el} ({sc} sentences): {t[:100]}...')
    for si, s in enumerate(sents, 1):
        print(f'    [{si}] {s}')
