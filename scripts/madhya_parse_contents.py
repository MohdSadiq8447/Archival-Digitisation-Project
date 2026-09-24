from __future__ import annotations

import re
from pathlib import Path


CACHE_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\madhya-locate")


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u00ad", " ")).strip()


def first_num(patterns: list[str], text: str):
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I)
        if m:
            return tuple(int(x) for x in m.groups())
    return None


def main() -> None:
    for p in sorted(CACHE_DIR.glob("1971_*.txt")):
        pages = [compact(x) for x in p.read_text(encoding="utf-8", errors="replace").split("\f")]
        content = next((x for x in pages[:8] if "contents" in x.lower() and "town" in x.lower()), "")
        appendix = first_num([
            r"Appendix[^.]{0,50}?Village Directory\s+(\d{2,3})\s*[\-–—.]\s*(\d{2,3})",
            r"Appendix[^.]{0,50}?Village Directory\s+(\d{2,3})\s+(\d{2,3})",
        ], content)
        civic = first_num([
            r"Civic and other Amenities\s+(\d{2,3})",
            r"Civic and other Amenit(?:ies|ies)\s+(\d{2,3})",
        ], content)
        medical = first_num([
            r"Medical[, ]+Educationa?l[^.]{0,80}?Facilities in Towns\s+(\d{2,3})",
            r"Medical[, ]+Educational[, ]+Recreational[^.]{0,100}?Towns\s+(\d{2,3})",
        ], content)
        print(f"{p.stem}\tappendix={appendix}\tcivic={civic}\tmedical={medical}")


if __name__ == "__main__":
    main()
