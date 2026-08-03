import csv

filepath = "/home/imnyj/papers/paper4/paper/data/SA1_results.csv"

with open(filepath, "r") as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    line = line.strip()
    if not line:
        continue
    fields = line.split(',')
    
    # Header
    if i == 0:
        if fields[-1] != "method":
            fields.append("method")
        new_lines.append(','.join(fields))
        continue
        
    # Data rows
    # Some have 13 fields, some have 14. 
    # For SA1, all rows before the patch were ReactDCC.
    if len(fields) == 13:
        fields.append("ReactDCC")
    elif len(fields) > 14:
        # Just in case
        fields = fields[:14]
    
    new_lines.append(','.join(fields))

with open(filepath, "w") as f:
    for line in new_lines:
        f.write(line + "\n")

print("Fixed CSV.")
