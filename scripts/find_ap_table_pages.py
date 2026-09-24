from pathlib import Path
import re


CACHE_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\ap-locate")


def compact(text: str) -> str:
    return " ".join(text.split()).lower()


for path in sorted(CACHE_DIR.glob("1971_*.txt")):
    pages = path.read_text(encoding="utf-8", errors="ignore").split("\f")
    print(path.stem)
    for page_index, page_text in enumerate(pages, start=1):
        if page_index < 50:
            continue
        normalized = compact(page_text)
        labels = []
        if "statement iv" in normalized and "civic" in normalized and "amenities" in normalized:
            labels.append("IV")
        if "statement v" in normalized and "medical" in normalized and "educational" in normalized:
            labels.append("V")
        if "talukwise abstract" in normalized and "educational" in normalized:
            labels.append("APP")
        if labels:
            print(f"  {page_index}: {','.join(labels)}")
