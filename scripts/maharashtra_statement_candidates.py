from __future__ import annotations

import re
from pathlib import Path


CACHE = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\maharashtra-locate")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00ad", " ")).strip()


for path in sorted(CACHE.glob("1971_*.txt")):
    pages = path.read_text(encoding="utf-8", errors="replace").split("\f")
    print(f"=== {path.stem.removeprefix('1971_')} ===")
    for index, page in enumerate(pages[:-1]):
        lines = [clean(line) for line in page.splitlines() if clean(line)]
        hits = [line for line in lines if re.search(r"statement|civic|medical|educational|cultural", line, re.I)]
        if hits and any(re.search(r"statement\s+(?:iv|v|vi)|civic|medical|educational", line, re.I) for line in hits):
            print(f"p{index + 1}: " + " | ".join(hits[:10]))
