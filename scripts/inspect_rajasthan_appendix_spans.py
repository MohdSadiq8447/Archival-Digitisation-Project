from pathlib import Path
import re

CACHE_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\rajasthan-locate")
for path in sorted(CACHE_DIR.glob("1971_*.txt")):
    pages = path.read_text(encoding="utf-8", errors="replace").split("\f")
    start = None
    for number, page in enumerate(pages, start=1):
        if re.search(r"Nature of Amenities", page, re.I):
            start = number
            break
    if not start:
        print(f"=== {path.stem}: no appendix ===")
        continue
    print(f"=== {path.stem} start={start} ===")
    for number in range(start, min(start + 7, len(pages) + 1)):
        lines = [re.sub(r"\s+", " ", line).strip() for line in pages[number-1].splitlines() if line.strip()]
        print(f"p{number}: " + " | ".join(lines[:8]))
