import os
import glob

files = glob.glob("/home/imnyj/papers/paper4/paper/data/SA*_results.csv")

for filepath in files:
    with open(filepath, "r") as f:
        lines = f.readlines()

    if not lines: continue

    is_sa1 = "SA1" in filepath

    new_lines = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        fields = line.split(',')
        
        if is_sa1:
            # SA1 needs 14 columns (with 'method' at the end)
            if i == 0:
                if fields[-1] != "method":
                    fields.append("method")
            else:
                if len(fields) == 13:
                    fields.append("ReactDCC") # fallback
                elif len(fields) > 14:
                    fields = fields[:14]
        else:
            # SA2, SA3, SA4 only need 13 columns
            if i == 0:
                if fields[-1] == "method":
                    fields = fields[:-1]
            else:
                if len(fields) > 13:
                    fields = fields[:13]
        
        new_lines.append(','.join(fields))

    with open(filepath, "w") as f:
        for line in new_lines:
            f.write(line + "\n")

print("Fixed all CSVs.")
