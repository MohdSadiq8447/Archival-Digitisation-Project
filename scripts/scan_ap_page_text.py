from pathlib import Path
import re


CACHE_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\ap-locate")

PATTERNS = {
    "IV": re.compile(r"statement\s*iv|civic\s+and\s+other", re.I),
    "V": re.compile(r"statement\s*v\b|medical,?\s*educational", re.I),
    "APP": re.compile(r"talukwise\s+abstract|abstract\s+of\s+amenities|amenities\s+abstract", re.I),
}


for path in sorted(CACHE_DIR.glob("1971_*.txt")):
    pages = path.read_text(encoding="utf-8", errors="ignore").split("\f")
    hits = {key: [] for key in PATTERNS}
    for page_index, page_text in enumerate(pages, start=1):
        if page_index < 50:
            continue
        for key, pattern in PATTERNS.items():
            if pattern.search(page_text):
                snippets = [
                    " ".join(line.split())
                    for line in page_text.splitlines()
                    if pattern.search(line)
                ]
                hits[key].append((page_index, snippets[:3]))
    print(path.stem)
    for key in PATTERNS:
        print(f"  {key}: {hits[key][:12]}")
