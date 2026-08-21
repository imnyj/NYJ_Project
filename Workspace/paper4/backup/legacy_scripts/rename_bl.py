import os
import glob

replacements = {
    "ReactDCC": "ReactDCC",
    "AdaptDCC": "AdaptDCC",
    "Heuristic": "Heuristic",
    "Fixed10Hz": "Fixed10Hz"
}

files = glob.glob("/home/imnyj/papers/paper4/sim/*.py")
files += glob.glob("/home/imnyj/papers/paper4/paper/idea/*.md")

for filepath in files:
    with open(filepath, "r") as f:
        content = f.read()
    
    new_content = content
    for old, new in replacements.items():
        new_content = new_content.replace(old, new)
        
    if content != new_content:
        with open(filepath, "w") as f:
            f.write(new_content)
        print(f"Updated {filepath}")
