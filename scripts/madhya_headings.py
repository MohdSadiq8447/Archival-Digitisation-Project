from pathlib import Path
import re

root = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\madhya-locate")
terms = (
    "civic and other", "civic and ot", "statement iv", "statement v",
    "medical, educational", "medical educational", "abstract of amenities",
    "amenities abstract", "appendix to village", "appendix iii", "appendix ii",
    "tahsil-wise", "tehsil-wise", "taluk-wise", "talukwise", "tahsilwise",
)
for p in sorted(root.glob("1971_*.txt")):
    pages = [re.sub(r"\s+", " ", x.replace("\u00ad", " ")).strip() for x in p.read_text(encoding="utf-8", errors="replace").split("\f")]
    print(f"=== {p.stem} pages={len(pages)-1} ===")
    for i, text in enumerate(pages, 1):
        low = text.lower()
        if any(term in low for term in terms):
            print(f"p{i}: {text[:480]}")
