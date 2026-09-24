from pathlib import Path
import re

cache = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\madhya-locate")
for p in sorted(cache.glob('1971_*.txt')):
    pages = [re.sub(r'\s+', ' ', x.replace('\u00ad', ' ')).strip() for x in p.read_text(encoding='utf-8', errors='replace').split('\f')]
    for i, x in enumerate(pages[:10], 1):
        low = x.lower()
        if 'civic' in low and ('town' in low or 'appendix' in low or 'contents' in low):
            pos = low.find('appendix')
            if pos < 0 or pos > low.find('civic'):
                pos = max(0, low.find('contents'))
            print(f"{p.stem} p{i}: {x[pos:pos+1150]}")
