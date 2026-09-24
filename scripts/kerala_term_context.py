from pathlib import Path
import re

root = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\kerala-locate")
for p in sorted(root.glob("1971_*.txt")):
    pages = [re.sub(r"\s+", " ", x.replace("\u00ad", " ")).strip() for x in p.read_text(encoding="utf-8", errors="replace").split("\f")]
    print(f"=== {p.stem} ===")
    for i, text in enumerate(pages, 1):
        if not (15 <= i <= 35):
            continue
        low = text.lower()
        for term in ("civic", "iv amenities", "medical,", "medical educational", "statement v", "cultural facilities"):
            at = low.find(term)
            if at >= 0:
                print(f"p{i} {term}: ...{text[max(0,at-100):at+220]}...")
