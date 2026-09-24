from pathlib import Path
import re

CACHE_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\rajasthan-locate")

for path in sorted(CACHE_DIR.glob("1971_*.txt")):
    pages = path.read_text(encoding="utf-8", errors="replace").split("\f")
    print(f"=== {path.stem} ===")
    for number, page in enumerate(pages[:15], start=1):
        lines = [re.sub(r"\s+", " ", line).strip() for line in page.splitlines()]
        useful = [line for line in lines if line and (re.search(r"Statement|Appendix|Amenities|Tehsil", line, re.I))]
        if useful:
            print(f"p{number}: " + " | ".join(useful[:15]))
