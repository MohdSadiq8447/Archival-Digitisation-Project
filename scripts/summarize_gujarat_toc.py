from pathlib import Path
import re


CACHE_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\gujarat-locate")
PATTERN = re.compile(r"statement\s+(?:iv|v)|abstract.*amenit|amenit.*abstract|taluk.*abstract|taluka.*abstract|mahal.*abstract", re.I)

for path in sorted(CACHE_DIR.glob("1971_*.txt")):
    print(path.stem)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines[:260], start=1):
        if PATTERN.search(line):
            print(f"  {index}: {' '.join(line.split())}")
