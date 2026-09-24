from pathlib import Path
import re

cache = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\madhya-locate")
missing = set('Betul Bhind Bilaspur Chhindwara Dewas Dhar Durg Guna Gwalior Hoshangabad Indore Jabalpur Jhabua Khandwa Khargone Mandla Mandsaur Morena Panna Raigarh Raisen Rajgarh Rewa Satna Sehore Seoni Shahapur Sidhi Surguja Vidisha Balaghat'.split())
for p in sorted(cache.glob('1971_*.txt')):
    name = p.stem.removeprefix('1971_')
    if name not in missing:
        continue
    pages = [re.sub(r'\s+', ' ', x.replace('\u00ad', ' ')).strip() for x in p.read_text(encoding='utf-8', errors='replace').split('\f')]
    for i, x in enumerate(pages[:8], 1):
        if 'contents' in x.lower() and 'town' in x.lower():
            print(f'=== {name} p{i} ===\n{x}\n')
