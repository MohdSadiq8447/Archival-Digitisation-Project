from pathlib import Path
import re

CACHE = Path(r"C:\\Users\\USER\\.codex\\visualizations\\2026\\09\\07\\01a07b9c-e77d-7511-9f66-aafc92441f90\\gujarat-locate")
for path in sorted(CACHE.glob("*.txt")):
    pages = path.read_text(encoding="utf-8", errors="replace").split("\f")
    print(f"{path.stem}: total={len(pages)}")
    for i, page in enumerate(pages, start=1):
        compact = " ".join(page.split())
        if re.search(r"abstract\s+of\s+amenit", compact, re.I):
            print(f"  appendix {i}: {compact[:180]}")
        if re.search(r"statement\s+iv", compact, re.I) and i > 40:
            print(f"  stmtIV {i}: {compact[:180]}")
        if re.search(r"statement\s+v\b", compact, re.I) and i > 40:
            print(f"  stmtV {i}: {compact[:180]}")
