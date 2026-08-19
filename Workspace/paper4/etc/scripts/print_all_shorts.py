import sys
sys.path.append('etc/scripts')
import check_prose_paras

print(f"Total short paragraphs in paper: {len(check_prose_paras.short_paras)}")
for idx, (sl, el, sc, text, sents) in enumerate(check_prose_paras.short_paras, 1):
    print(f"\n==================================================")
    print(f"[Short #{idx}] Lines {sl}-{el} ({sc} sentences)")
    print(f"==================================================")
    print(text)
