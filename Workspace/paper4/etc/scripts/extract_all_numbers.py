import re
import pandas as pd

with open("/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md", "r", encoding="utf-8") as f:
    text = f.read()

# Find all occurrences of numbers followed by units or percentages in Section V
lines = text.split("\n")
sec5_lines = []
in_sec5 = False
for idx, line in enumerate(lines):
    if "# 제5장 성능 평가" in line or "# V. 성능 평가" in line or "## 5." in line:
        in_sec5 = True
    if in_sec5:
        if line.startswith("# VI.") or line.startswith("# 제6장"):
            in_sec5 = False
            break
        sec5_lines.append((idx + 1, line))

print(f"Captured {len(sec5_lines)} lines from Section 5.")

# Extract all numeric claims with contexts
print("\n--- All Numeric Claims in Section 5 ---")
pattern = re.compile(r'(\-?\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:%p|%|ms|veh/km|mJ/km|mJ|km/h|dBm|dB|MHz|GHz|MACs|K|M|s|Bytes|bits|m|회|배))?)')

claims = []
for line_num, line in sec5_lines:
    if line.strip().startswith("|") or line.strip().startswith("*표"):
        continue  # Skip table rows for now to focus on narrative text
    matches = pattern.findall(line)
    if matches:
        claims.append((line_num, line.strip(), matches))

print(f"Found {len(claims)} narrative lines containing numerical claims in Section 5.")
for line_num, line_text, numbers in claims[:25]:
    print(f"L{line_num:03d}: {line_text}")

