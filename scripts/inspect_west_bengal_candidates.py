from __future__ import annotations

from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "West Bengal"
CANDIDATES = {
    "Birbhum": [47, 49],
    "Burdwan": [61],
    "Calcutta": [13, 15],
    "Dinajpur": [60, 62],
    "Haora": [41, 45, 47],
    "Hugli": [55],
    "Jalapiguri": [33, 35],
    "Murshidabad": [51, 53],
    "Purullia": [57, 59],
    "Twentyfour Parganas": [108, 110, 112, 114, 116, 118, 120, 122],
}


def main() -> None:
    for district, page_numbers in CANDIDATES.items():
        source_path = next(SOURCE_DIR.glob(f"1971 {district}*.pdf"))
        document = fitz.open(str(source_path))
        print(f"\n### {source_path.name}")
        seen: set[int] = set()
        for page_number in page_numbers:
            for number in range(max(1, page_number - 1), min(len(document), page_number + 1) + 1):
                if number in seen:
                    continue
                seen.add(number)
                text = " ".join(document[number - 1].get_text("text").split())
                print(f"p{number}: {text[:260]}")


if __name__ == "__main__":
    main()
