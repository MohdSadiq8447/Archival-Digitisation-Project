from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Punjab"


def main() -> None:
    for source in sorted(SOURCE_DIR.glob("1971 *.pdf"), key=lambda p: p.name.lower()):
        reader = PdfReader(str(source), strict=False)
        print(f"=== {source.name} pages={len(reader.pages)} ===")
        for number, page in enumerate(reader.pages[:10], 1):
            text = re.sub(r"\s+", " ", page.extract_text() or "").strip()
            if re.search(r"contents|appendix|statement|amenit", text, re.I):
                lines = [line.strip() for line in (page.extract_text() or "").splitlines() if re.search(r"appendix|statement|amenit", line, re.I)]
                print(f"p{number}: " + " | ".join(lines))


if __name__ == "__main__":
    main()
