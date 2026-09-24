from __future__ import annotations

import re
import sys
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Tamil Nadu"


def main() -> None:
    names = sys.argv[1:] or [p.stem.removeprefix("1971 ").strip() for p in sorted(SOURCE_DIR.glob("1971 *.pdf"))]
    for name in names:
        source = SOURCE_DIR / f"1971 {name}.pdf"
        if not source.exists():
            print(f"MISSING {source}")
            continue
        reader = PdfReader(str(source), strict=False)
        print(f"=== {source.name} pages={len(reader.pages)} ===", flush=True)
        for number, page in enumerate(reader.pages, 1):
            text = " ".join((page.extract_text() or "").split())
            if not text:
                continue
            appendix = re.search(r"appendix\s*-?\s*ii\b", text, re.I)
            civic = re.search(r"statement\s*(?:iv|4)\b.{0,140}(?:civic|amenit)", text, re.I)
            medical = re.search(r"statement\s*(?:v|5)\b.{0,180}medical", text, re.I)
            if appendix or civic or medical:
                tags = []
                for label, match in (("APP", appendix), ("CIVIC", civic), ("MED", medical)):
                    if match:
                        tags.append(f"{label}: {text[max(0, match.start()-80):match.start()+420]}")
                print(f"p{number}: " + " || ".join(tags), flush=True)


if __name__ == "__main__":
    main()
