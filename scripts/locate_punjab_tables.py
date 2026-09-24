from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Punjab"
PATTERN = re.compile(r"statement\s+(?:iv|v)|civic.{0,50}amenit|medical.{0,50}amenit|educational.{0,50}amenit|abstract.{0,50}amenit|amenit.{0,50}abstract|nature\s+of\s+amenit|taluk|taluka|tahsil|tehsil|appendix", re.I)


def main() -> None:
    for source in sorted(SOURCE_DIR.glob("1971 *.pdf"), key=lambda p: p.name.lower()):
        reader = PdfReader(str(source), strict=False)
        print(f"=== {source.name} pages={len(reader.pages)} ===", flush=True)
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
            hits = [line for line in lines if line and PATTERN.search(line)]
            if hits and (number <= 140 or any(re.search(r"statement\s+(?:iv|v)|appendix|abstract.{0,50}amenit|amenit.{0,50}abstract", line, re.I) for line in hits)):
                print(f"p{number}: " + " | ".join(hits[:12]), flush=True)


if __name__ == "__main__":
    main()
