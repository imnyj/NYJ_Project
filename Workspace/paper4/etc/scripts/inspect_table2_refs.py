import re

with open("/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("=== TABLE 2 LINES ===")
for i in range(440, 475):
    if i < len(lines):
        print(f"{i+1}: {repr(lines[i])}")

print("\n=== REFERENCES SECTION ===")
for i in range(850, len(lines)):
    print(f"{i+1}: {lines[i].rstrip()}")
