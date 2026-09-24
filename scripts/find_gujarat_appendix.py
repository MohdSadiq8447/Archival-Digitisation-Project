from pathlib import Path
import re

CACHE = Path(r"C:\\Users\\USER\\.codex\\visualizations\\2026\\09\\07\\01a07b9c-e77d-7511-9f66-aafc92441f90\\gujarat-locate")
pat = re.compile(r"abstract.{0,40}amenit|amenit.{0,40}nature|nature.{0,30}educational", re.I)
for path in sorted(CACHE.glob("*.txt")):
    pages = path.read_text(encoding="utf-8", errors="replace").split("\f")
    hits=[]
    for i,page in enumerate(pages,1):
        compact=" ".join(page.split())
        if pat.search(compact): hits.append((i,compact[:200]))
    print(path.stem, hits[-8:])
