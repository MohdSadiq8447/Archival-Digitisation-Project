from pathlib import Path
import re

CACHE_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\rajasthan-locate")
patterns = re.compile(r"abstract.{0,30}amenit|amenit.{0,30}abstract|primary\s+middle|medical.{0,30}educational|district/tehsil.*(primary|dispens)|tehsil.*total area", re.I)
for path in sorted(CACHE_DIR.glob("1971_*.txt")):
    pages = path.read_text(encoding="utf-8", errors="replace").split("\f")
    print(f"=== {path.stem} ===")
    for num, page in enumerate(pages, start=1):
        lines = [re.sub(r"\s+", " ", line).strip() for line in page.splitlines()]
        hits = [line for line in lines if line and patterns.search(line)]
        # The appendix is usually after the directory statements and before the PCA.
        if hits and 35 <= num <= min(len(pages), 220):
            print(f"p{num}: " + " | ".join(hits[:4]))
