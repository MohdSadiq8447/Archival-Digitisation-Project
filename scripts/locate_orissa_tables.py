from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "1971" / "Orissa" / "1971 Puri.pdf"


def main() -> None:
    reader = PdfReader(str(SOURCE), strict=False)
    print(f"{SOURCE.name}: pages={len(reader.pages)}")
    pattern = re.compile(r"statement\s+(?:iv|v)|civic.{0,40}amenit|medical.{0,40}amenit|educational.{0,40}amenit|abstract.{0,40}amenit|amenit.{0,40}abstract|nature\s+of\s+amenit|taluk|taluka|tahsil|tehsil|appendix|sub.?division", re.I)
    for index, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        hits = [line for line in lines if line and pattern.search(line)]
        if hits and (index < 220 or any(re.search(r"statement\s+(?:iv|v)|appendix|abstract.{0,40}amenit|amenit.{0,40}abstract", line, re.I) for line in hits)):
            print(f"p{index}: " + " | ".join(hits[:12]))


if __name__ == "__main__":
    main()
