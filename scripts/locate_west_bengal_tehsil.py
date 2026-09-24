from __future__ import annotations

from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "West Bengal"


def main() -> None:
    for source_path in sorted(SOURCE_DIR.glob("*.pdf")):
        document = fitz.open(str(source_path))
        hits: list[int] = []
        for index, page in enumerate(document, start=1):
            text = " ".join(page.get_text("text").split()).upper()
            if "APPENDIX" in text and ("AMENITIES" in text or ("EDUCATIONAL" in text and "MEDICAL" in text)):
                hits.append(index)
        print(f"{source_path.name}: appendix_amenities={hits}", flush=True)


if __name__ == "__main__":
    main()
