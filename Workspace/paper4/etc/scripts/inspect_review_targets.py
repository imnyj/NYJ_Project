import re

def inspect():
    with open('/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        content = "".join(lines)

    print("=== 1. Table III-1 lines ===")
    for i, l in enumerate(lines, 1):
        if "Table III-1" in l or ("|" in l and 440 <= i <= 470):
            print(f"{i}: {l.rstrip()}")

    print("\n=== 2. Abstract Nakagami ===")
    for i, l in enumerate(lines[:30], 1):
        if "Nakagami" in l:
            print(f"{i}: {l.rstrip()}")

    print("\n=== 3. PDR numbers ===")
    for i, l in enumerate(lines, 1):
        if any(term in l for term in ["76.4%", "76.54%", "73.41%", "75.02%"]):
            print(f"{i}: {l.rstrip()}")

    print("\n=== 4. Hardware / MACs / Params / Latency ===")
    for i, l in enumerate(lines, 1):
        if any(term in l for term in ["10만", "350K", "35만", "3.8M", "1.2 ms", "마이크로초"]):
            print(f"{i}: {l.rstrip()}")

    print("\n=== 5. Exaggerated adverbs / expressions ===")
    words = ["완벽히", "완벽하게", "원천 차단", "독보적인", "획기적인", "경이로운", "원천적", "극적인"]
    for i, l in enumerate(lines, 1):
        found = [w for w in words if w in l]
        if found:
            print(f"{i} [{', '.join(found)}]: {l.rstrip()}")

    print("\n=== 6. Math Notation check ===")
    # Check for $s_t$, $CBR$, $AoI$, $PDR$, $P_{tx}$, $T_{\text{GenCAM}}$, $CBR_{\text{smooth}}$
    patterns = [
        (r'\$s_t\$', r'$\mathbf{s}_t$'),
        (r'\$s_t\^', r'$\mathbf{s}_t^'),
        (r'\$s_0\^', r'$\mathbf{s}_0^'),
        (r'\$s_\{t', r'$\mathbf{s}_{t'),
        (r'(?<!\\text\{)CBR(?!\w)', 'CBR without \\text{}'),
        (r'(?<!\\text\{)AoI(?!\w)', 'AoI without \\text{}'),
        (r'(?<!\\text\{)PDR(?!\w)', 'PDR without \\text{}'),
        (r'P_\{tx\}', 'P_{tx} vs P_{\\text{tx}}'),
        (r'T_\{GenCAM\}', 'T_{GenCAM} vs T_{\\text{GenCam}}'),
        (r'CBR_\{smooth\}', 'CBR_{smooth} vs \\text{CBR}_{\\text{smoothed}}')
    ]
    for p, desc in patterns:
        matches = [(i+1, l) for i, l in enumerate(lines) if re.search(p, l)]
        print(f"Pattern '{p}' ({desc}): {len(matches)} matches")
        for lno, l in matches[:3]:
            print(f"  Line {lno}: {l.strip()[:100]}")

if __name__ == '__main__':
    inspect()
