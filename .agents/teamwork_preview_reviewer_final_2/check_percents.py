import re
import os
import pandas as pd
import numpy as np

main_tex_path = "/home/imnyj/Workspace/paper4/latex/main.tex"
with open(main_tex_path, "r", encoding="utf-8") as f:
    main_tex = f.read()

# Let's check the escaped percent signs
checks = [
    ("73.41\\%", "73.41% in main.tex"),
    ("3.13\\%p", "3.13%p in main.tex"),
    ("75.02\\%", "75.02% in main.tex"),
    ("373.21~ms", "373.21 ms in main.tex"),
    ("0.3442", "0.3442 in main.tex"),
    ("0.1008", "0.1008 in main.tex"),
    ("0.0\\%", "0.0% in main.tex"),
    ("3.8M", "3.8M in main.tex"),
    ("350K", "350K in main.tex"),
    ("1.2~ms", "1.2 ms in main.tex"),
    ("59.15\\%", "59.15% in main.tex"),
]

for val, desc in checks:
    print(f"{desc}: {val in main_tex}")
