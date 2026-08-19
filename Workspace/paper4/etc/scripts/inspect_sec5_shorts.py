import sys
sys.path.append('etc/scripts')
import check_prose_paras

print("=== Section 5 Short Paragraphs ===")
sec5_shorts = [p for p in check_prose_paras.short_paras if p[0] >= 507]
for idx, (sl, el, sc, text, sents) in enumerate(sec5_shorts, 1):
    print(f"\n--- [Sec 5 Short #{idx}] Lines {sl}-{el} ({sc} sentences) ---")
    print(text)
