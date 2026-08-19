import re

with open("/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md", "r", encoding="utf-8") as f:
    text = f.read()
    lines = text.split("\n")

print("=== CHECK NUMERICAL CONSISTENCY ACROSS SECTIONS ===")

# Key claims in Abstract / Intro:
# 1. 14 RL algorithms + 7 baselines = 21 models
# 2. CBR: 0.3442 (std 0.1008, 0.60 violation 0.0%)
# 3. High density (100 veh/km) PDR: 73.41% (or 76.4% in line 65 vs 73.41% in line 15/Table 7)
# Let's search all occurrences of PDR numbers for REMO-DQN:
pdr_matches = [(i+1, l) for i, l in enumerate(lines) if "76.4" in l or "73.41" in l or "76.54" in l]
print("PDR occurrences:")
for l_no, l_str in pdr_matches:
    print(f"  Line {l_no}: {l_str.strip()[:100]}")

# 4. AoI numbers: 373.21 ms vs 373.2 ms
aoi_matches = [(i+1, l) for i, l in enumerate(lines) if "373." in l]
print("\nAoI occurrences:")
for l_no, l_str in aoi_matches:
    print(f"  Line {l_no}: {l_str.strip()[:100]}")

# 5. Hardware MACs / Latency: 3.8M MACs, 1.2 ms, 350K params
hw_matches = [(i+1, l) for i, l in enumerate(lines) if "3.8M" in l or "1.2 ms" in l or "350K" in l or "10만" in l]
print("\nHardware occurrences:")
for l_no, l_str in hw_matches:
    print(f"  Line {l_no}: {l_str.strip()[:100]}")
