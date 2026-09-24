from pathlib import Path
import re

root = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\kerala-locate")
for p in sorted(root.glob("1971_*.txt")):
    pages = [re.sub(r"\s+", " ", x.replace("\u00ad", " ")).strip() for x in p.read_text(encoding="utf-8", errors="replace").split("\f")]
    print(f"{p.stem} pages={len(pages)-1}")
    for i, t in enumerate(pages, 1):
        lo = t.lower()
        if any(x in lo for x in ("statement civic", "civic and other", "statement med", "medical, educational", "medical educational", "taluk-wise abstract", "talukwise abstract", "tehsilwise abstract", "amenities abstract")):
            print(f"  p{i}: {t[:240]}")
