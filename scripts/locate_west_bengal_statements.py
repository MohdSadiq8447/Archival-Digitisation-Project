from __future__ import annotations

from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "West Bengal"


def main() -> None:
    for source_path in sorted(SOURCE_DIR.glob("*.pdf")):
        document = fitz.open(str(source_path))
        civic: list[int] = []
        medical: list[int] = []
        for index, page in enumerate(document, start=1):
            text = " ".join(page.get_text("text").split()).upper()
            if "CIVIC" in text and ("TABLE IV" in text or "STATEMENT IV" in text):
                civic.append(index)
            if "MEDICAL" in text and ("TABLE V" in text or "STATEMENT V" in text):
                medical.append(index)
        print(f"{source_path.name}: civic={civic} medical={medical}", flush=True)


if __name__ == "__main__":
    main()
