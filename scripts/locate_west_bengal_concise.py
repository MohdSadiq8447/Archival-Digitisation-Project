from __future__ import annotations

import re
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "West Bengal"


def compact(text: str) -> str:
    return " ".join(text.split())


def main() -> None:
    for source_path in sorted(SOURCE_DIR.glob("*.pdf")):
        print(f"\n### {source_path.name}", flush=True)
        document = fitz.open(str(source_path))
        for index, page in enumerate(document, start=1):
            text = compact(page.get_text("text"))
            upper = text.upper()
            kind = None
            if ("STATEMENT IV" in upper or "TABLE IV" in upper) and "CIVIC" in upper:
                kind = "CIVIC"
            elif ("STATEMENT V" in upper or "TABLE V" in upper) and "MEDICAL" in upper:
                kind = "MEDICAL"
            elif re.search(r"(VILLAGE|TALUK|TEHSIL|TAHSIL).{0,40}AMENITIES", upper):
                kind = "AMENITIES"
            if kind:
                print(f"{index}: {kind} | {text[:280]}", flush=True)


if __name__ == "__main__":
    main()
