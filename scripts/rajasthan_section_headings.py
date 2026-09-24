from pathlib import Path
import re

CACHE_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\rajasthan-locate")
for path in sorted(CACHE_DIR.glob("1971_*.txt")):
    pages = path.read_text(encoding="utf-8", errors="replace").split("\f")
    print(f"=== {path.stem} ===")
    for num, page in enumerate(pages, start=1):
        lines = [re.sub(r"\s+", " ", line).strip() for line in page.splitlines() if line.strip()]
        matches = [line for line in lines if re.search(r"Statement\s+[IVX]+\s*[-:]|Statement VI", line, re.I)]
        if matches:
            print(f"p{num}: " + " | ".join(matches[:5]))
