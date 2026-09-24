from __future__ import annotations

import re
from pathlib import Path


CACHE_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\kerala-locate")


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u00ad", " ")).strip()


def main() -> None:
    terms = (
        "civic and other", "statement iv", "medical, educational", "statement v",
        "medical educational", "medical facilities", "educational facilities",
        "talukwise abstract", "tehsilwise abstract", "amenities abstract",
        "abstract of amenities", "appendix", "amenities", "taluk", "tehsil",
    )
    for path in sorted(CACHE_DIR.glob("1971_*.txt")):
        pages = [compact(page) for page in path.read_text(encoding="utf-8", errors="replace").split("\f")]
        print(f"=== {path.stem} pages={len(pages)-1} ===")
        hits = []
        for i, text in enumerate(pages, 1):
            low = text.lower()
            if i <= 12 or any(term in low for term in terms):
                hits.append((i, text))
        shown = set()
        for i, text in hits:
            for page_no in range(max(1, i - 1), min(len(pages), i + 2)):
                if page_no in shown:
                    continue
                shown.add(page_no)
                page_text = pages[page_no - 1]
                if page_no <= 12 or any(term in page_text.lower() for term in terms):
                    print(f"p{page_no}: {page_text[:500]}")


if __name__ == "__main__":
    main()
