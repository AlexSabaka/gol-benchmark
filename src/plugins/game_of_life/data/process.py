import os
from pathlib import Path

DIR = 'known_patterns'
OUT_DIR = 'sorted_patterns'

os.makedirs(OUT_DIR, exist_ok=True)

for filename in os.listdir(DIR):
    in_file = Path(DIR) / filename
    with open(in_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        width = len(lines[0].strip())
        height = len(lines)
        out_file = in_file.with_name(f"{width}x{height}.txt")
        with open(Path(OUT_DIR) / out_file.name, 'w', encoding='utf-8') as out_f:
            out_f.writelines(lines)

