import re

with open('/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md', 'r', encoding='utf-8') as f:
    text = f.read()

# Sections
sections = re.split(r'\n(?=#+ )', text)
print(f"Total Sections found: {len(sections)}")

for s_idx, sec in enumerate(sections):
    sec_lines = sec.strip().split('\n')
    header = sec_lines[0]
    print(f"\n--- Section: {header} ---")
    
    # Extract paragraphs inside this section
    raw_paras = sec.split('\n\n')
    for p_idx, p in enumerate(raw_paras):
        p_clean = p.strip()
        if not p_clean:
            continue
        if p_clean.startswith('#') or p_clean.startswith('---') or p_clean.startswith('|') or p_clean.startswith('```') or p_clean.startswith('*표') or p_clean.startswith('**표') or p_clean.startswith('**Algorithm') or p_clean.startswith('**저자') or p_clean.startswith('**소속') or p_clean.startswith('**연락처') or p_clean.startswith('**타깃') or p_clean.startswith('**색인어') or p_clean.startswith('- **') or p_clean.startswith('[1]') or p_clean.startswith('1.') or p_clean.startswith('2.') or p_clean.startswith('3.') or p_clean.startswith('4.') or p_clean.startswith('5.') or p_clean.startswith('6.') or p_clean.startswith('7.'):
            continue
        
        # Clean inline math and split by sentence ending
        # Pattern for Korean/English sentences: period followed by space or newline
        # Avoid splitting on decimal points like 0.60 or e.g.
        sents = re.split(r'(?<=[가-힣a-zA-Z0-9\)])\.\s+(?=[가-힣A-Z0-9\(\[\$])', p_clean)
        count = len(sents)
        if count < 5:
            print(f"  [SHORT PARA] Para {p_idx} ({count} sents): {p_clean[:100]}...")
        else:
            print(f"  [OK] Para {p_idx} ({count} sents): {p_clean[:60]}...")
