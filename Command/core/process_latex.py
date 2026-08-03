import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Apply H-ST-MBN replacements
    content = content.replace("H-ST-MBAN", "H-ST-MBN")
    content = content.replace("Hybrid Spatio-Temporal Multi-Branch Attention Network", "Hybrid Spatio-Temporal Multi-Branch Network")
    content = content.replace("Hybrid Multi-Branch Attention Network", "Hybrid Multi-Branch Network")

    # Introduction replacements to meet 5 sentence rules and CCVN context
    
    with open(filepath, 'w') as f:
        f.write(content)

process_file('/home/imnyj/papers/paper1/paper/draft/main.tex')
