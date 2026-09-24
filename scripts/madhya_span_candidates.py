from pathlib import Path
import re

root = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\madhya-locate")
for p in sorted(root.glob("1971_*.txt")):
    pages = [re.sub(r"\s+", " ", x.replace("\u00ad", " ")).strip() for x in p.read_text(encoding="utf-8", errors="replace").split("\f")]
    print(f"=== {p.stem} pages={len(pages)-1} ===")
    for i, text in enumerate(pages, 1):
        low = text.lower()
        tags = []
        if ("latrine" in low or "latrines" in low) and ("road length" in low or "road" in low):
            tags.append("CIVIC")
        if ("protected water" in low or "fire fighting" in low) and ("electrification" in low or "road lighting" in low):
            tags.append("CIVIC_CONT")
        if ("medical facilities" in low or "hospitals" in low or "dispensaries" in low) and ("engineering" in low or "polytechnic" in low or "arts" in low):
            tags.append("MED")
        if ("tahsil-wise abstract" in low or "tahsilwise abstract" in low or "tehsil-wise abstract" in low or "tehsilwise abstract" in low or "nature of" in low and "educational" in low and "medical" in low):
            tags.append("APP")
        if tags:
            print(f"p{i} {','.join(tags)}: {text[:260]}")
