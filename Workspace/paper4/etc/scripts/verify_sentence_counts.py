import re
import os

def analyze_paragraphs(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    paragraphs = text.split('\n\n')
    print(f"=== Analyzing {filepath} ===")
    p_num = 0
    for i, p in enumerate(paragraphs):
        p_clean = p.strip()
        if not p_clean or p_clean.startswith('#') or p_clean.startswith('|') or p_clean.startswith('```') or p_clean.startswith('$$') or p_clean.startswith('---') or p_clean.startswith('*표') or p_clean.startswith('*Figure') or p_clean.startswith('<br>'):
            continue
        p_num += 1
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', p_clean) if len(s.strip()) > 5]
        print(f"Paragraph {p_num}: {len(sentences)} sentences | {p_clean[:60]}...")

files = [
    '/home/imnyj/Workspace/paper4/paper/01_introduction.md',
    '/home/imnyj/Workspace/paper4/paper/02_related_works.md',
    '/home/imnyj/Workspace/paper4/paper/03_system_model.md',
    '/home/imnyj/Workspace/paper4/paper/04_scenario_flow.md',
    '/home/imnyj/Workspace/paper4/paper/05_performance_evaluation.md',
    '/home/imnyj/Workspace/paper4/paper/06_conclusion.md',
]

for f in files:
    if os.path.exists(f):
        analyze_paragraphs(f)
