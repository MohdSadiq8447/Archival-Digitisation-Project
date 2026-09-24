from pathlib import Path
import re

cache = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\madhya-locate")
for p in sorted(cache.glob('1971_*.txt')):
    pages = [re.sub(r'\s+', ' ', x.replace('\u00ad', ' ')).strip() for x in p.read_text(encoding='utf-8', errors='replace').split('\f')]
    hits = []
    for i, x in enumerate(pages[:15], 1):
        low=x.lower()
        if 'village directory' in low or 'town directory' in low or 'contents' in low:
            hits.append(f"p{i}:{x[:170]}")
    print(f"{p.stem}\t" + " || ".join(hits))
