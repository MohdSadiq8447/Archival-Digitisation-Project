from __future__ import annotations

import sys
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    for name in sys.argv[1:]:
        source = ROOT / "1971" / "Punjab" / f"1971 {name}.pdf"
        reader = PdfReader(str(source), strict=False)
        print(f"=== {name} ===")
        for number in (5, 6):
            if number <= len(reader.pages):
                print(f"--- page {number} ---")
                print(reader.pages[number - 1].extract_text() or "")


if __name__ == "__main__":
    main()
