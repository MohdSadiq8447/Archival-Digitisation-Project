from pathlib import Path
import re

cache = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\madhya-locate")
for p in sorted(cache.glob('1971_*.txt')):
    pages=[re.sub(r'\s+',' ',x.replace('\u00ad',' ')).strip() for x in p.read_text(encoding='utf-8',errors='replace').split('\f')]
    hits=[]
    for i,x in enumerate(pages,1):
        low=x.lower()
        tags=[]
        if 'statement iv' in low or ('civic and other' in low and 'town' in low): tags.append('civic')
        if 'statement v' in low or ('medical, educational' in low and 'town' in low): tags.append('medical')
        if ('nature of' in low and 'dispensary' in low) or ('tahsil-wise abstract' in low) or ('tahsilwise abstract' in low): tags.append('appendix')
        if tags: hits.append(f"p{i}:{'+'.join(tags)}:{x[:180]}")
    print(p.stem+'\t'+' || '.join(hits))
