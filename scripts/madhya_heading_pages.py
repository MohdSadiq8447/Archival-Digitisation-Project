from pathlib import Path
import re

cache = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\madhya-locate")
for p in sorted(cache.glob('1971_*.txt')):
    pages = [re.sub(r'\s+', ' ', x.replace('\u00ad', ' ')).strip() for x in p.read_text(encoding='utf-8', errors='replace').split('\f')]
    print(f"=== {p.stem} ===")
    for i, x in enumerate(pages, 1):
        low = x.lower()
        tags = []
        if 'civic' in low or 'other amenities' in low:
            tags.append('CIV')
        if 'medical' in low and ('educ' in low or 'town' in low):
            tags.append('MED')
        if 'appendix' in low and ('village' in low or 'abstract' in low or 'amenit' in low):
            tags.append('APP')
        if tags:
            print(f"p{i} {','.join(tags)}: {x[:420]}")
