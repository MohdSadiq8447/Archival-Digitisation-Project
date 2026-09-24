from pathlib import Path
import re

CACHE_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\rajasthan-locate")
key = re.compile(r"district.{0,8}tehsil|primary|dispens|hospital|health|maternity|family|college|amenit", re.I)
for path in sorted(CACHE_DIR.glob("1971_*.txt")):
    pages = path.read_text(encoding="utf-8", errors="replace").split("\f")
    print(f"=== {path.stem} ===")
    for num, page in enumerate(pages, start=1):
        if num < 30 or num > 220:
            continue
        lines = [re.sub(r"\s+", " ", line).strip() for line in page.splitlines()]
        hits = [line for line in lines if line and key.search(line)]
        if hits and any(re.search(r"district.{0,8}tehsil|primary middle|dispens|hospital|health", line, re.I) for line in hits):
            print(f"p{num}: " + " | ".join(hits[:7]))
