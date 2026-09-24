from pathlib import Path
import re

cache = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\madhya-locate")
for p in sorted(cache.glob('1971_*.txt')):
    pages = [re.sub(r'\s+', ' ', x.replace('\u00ad', ' ')).strip() for x in p.read_text(encoding='utf-8', errors='replace').split('\f')]
    found = [(i, x) for i, x in enumerate(pages[:12], 1) if 'part a' in x.lower() and ('village' in x.lower() or 'town' in x.lower())]
    if found:
        i, x = found[0]
        print(f"=== {p.stem} p{i} ===\n{x[:1700]}\n")
