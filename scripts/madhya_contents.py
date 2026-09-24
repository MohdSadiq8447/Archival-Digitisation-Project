from pathlib import Path
import re

root = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\madhya-locate")
for p in sorted(root.glob("1971_*.txt")):
    pages = [re.sub(r"\s+", " ", x.replace("\u00ad", " ")).strip() for x in p.read_text(encoding="utf-8", errors="replace").split("\f")]
    print(f"=== {p.stem} ===")
    for i, text in enumerate(pages[:8], 1):
        low = text.lower()
        if "contents" in low or "town directory" in low or "appendix" in low:
            print(f"p{i}: {text[:1800]}")
