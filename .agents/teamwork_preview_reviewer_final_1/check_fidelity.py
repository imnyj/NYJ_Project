import re

korean_draft_path = "/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md"
tex_path = "/home/imnyj/Workspace/paper4/latex/main.tex"

with open(korean_draft_path, "r", encoding="utf-8") as f:
    k_text = f.read()

with open(tex_path, "r", encoding="utf-8") as f:
    t_text = f.read()

def normalize(text):
    # remove LaTeX backslashes, extra spaces, etc.
    text = text.replace('\\%', '%').replace('\\,', '').replace('\\ ', ' ').replace('~', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text

norm_k = normalize(k_text)
norm_t = normalize(t_text)

metrics = [
    # CBR
    ("0.3442", "REMO-DQN mean CBR"),
    ("0.1008", "REMO-DQN std CBR"),
    ("0.1238", "REMO-DQN min CBR"),
    ("0.5898", "REMO-DQN max CBR"),
    # PDR
    ("76.54%", "REMO-DQN low density PDR"),
    ("75.11%", "REMO-DQN med density PDR"),
    ("73.41%", "REMO-DQN high density PDR"),
    ("75.02%", "REMO-DQN mean PDR"),
    ("3.13%p", "REMO-DQN drop"),
    # AoI
    ("138.56 ms", "REMO-DQN low density AoI"),
    ("380.60 ms", "REMO-DQN med density AoI"),
    ("579.52 ms", "REMO-DQN high density AoI"),
    ("373.21 ms", "REMO-DQN mean AoI"),
    ("440.95 ms", "REMO-DQN increase AoI"),
    # Hardware
    ("3.8 M", "MACs"),
    ("350 K", "Params"),
    ("1.2 ms", "Latency"),
    ("1.2%", "100ms Duty"),
    # Energy
    ("2.61 mJ/km", "REMO-DQN energy"),
    ("59.15%", "Energy savings"),
    # PDR distance
    ("71.67%", "REMO-DQN 300m PDR"),
    ("+4.93%p", "REMO-DQN 300m vs Vanilla"),
    # MoE weights
    ("80%", "Expert 1 at 20 veh/km"),
    ("85%", "Expert 3 at 160 veh/km"),
    # t-SNE
    ("-0.225", "t-SNE low traffic mean x"),
    ("+5.018", "t-SNE med traffic mean x"),
    ("+1.961", "t-SNE high traffic mean x"),
    # Multi-objective weights
    ("0.01", "w1"),
    ("1.0", "w2"),
    ("0.10", "w3"),
    # Nakagami
    ("3.0", "m shape parameter"),
    # Load balancing
    ("0.01", "lambda_LB"),
]

print("--- Normalized Numerical Fidelity Verification ---")
all_matched = True
for val, desc in metrics:
    in_k = val in norm_k
    in_t = val in norm_t
    status = "MATCH" if in_k and in_t else "MISMATCH"
    if not (in_k and in_t):
        all_matched = False
    print(f"[{status}] {desc} ('{val}'): Draft={in_k}, TeX={in_t}")

print(f"\nOverall Numerical Fidelity Result: {'100% PERFECT' if all_matched else 'SOME MISMATCHES FOUND'}")
