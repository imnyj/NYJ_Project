import re
import shutil
import time

wrong_file = '/home/imnyj/papers/paper1/paper/draft/main.tex'
correct_file = '/home/imnyj/Workspace/paper1/writer/draft/main.tex'

with open(wrong_file, 'r', encoding='utf-8') as f:
    wrong_content = f.read()

sec4_match = re.search(r'(\\section\{H-ST-MBAN Based Content Precaching\}.*?)(?=\\section\{Experiments and Results\})', wrong_content, re.DOTALL)
if not sec4_match:
    sec4_match = re.search(r'(\\section\{ST-MBAN Architecture\}.*?)(?=\\section\{Experiments and Results\})', wrong_content, re.DOTALL)

if sec4_match:
    sec4_text = sec4_match.group(1)
else:
    print("Failed to find Section 4 in wrong file.")
    exit(1)

with open(correct_file, 'r', encoding='utf-8') as f:
    correct_content = f.read()

correct_match = re.search(r'\\section\{Proposed Precaching Scheme\}\\label\{sec:architecture\}.*?(?=\\section\{Experiments and Results\})', correct_content, re.DOTALL)
if correct_match:
    correct_content = correct_content.replace(correct_match.group(0), sec4_text)
else:
    print("Failed to find target Section in correct file.")
    exit(1)

# Fix emphasis
correct_content = re.sub(r'\\emph\{([^}]+)\}', r'\1', correct_content)
# Fix packets
correct_content = re.sub(r'Interest [pP]acket[s]?', r'\\(INTEREST\\) packet', correct_content)
correct_content = re.sub(r'\\texttt\{\[INFO REQ\]\}', r'\\([INFO\\_REQ]\\)', correct_content)
correct_content = re.sub(r'\\texttt\{\[INFO HELLO\]\}', r'\\([INFO\\_HELLO]\\)', correct_content)
correct_content = re.sub(r'\\texttt\{\[INFO REP\]\}', r'\\([INFO\\_REP]\\)', correct_content)
correct_content = re.sub(r'Precache [pP]acket', r'\\(PRECACHE\\) packet', correct_content)

backup_path = f"/home/imnyj/Workspace/paper1/writer/draft/backup/main.tex.{int(time.time())}.bak"
shutil.copy2(correct_file, backup_path)

with open(correct_file, 'w', encoding='utf-8') as f:
    f.write(correct_content)

print("Fix completed successfully.")
