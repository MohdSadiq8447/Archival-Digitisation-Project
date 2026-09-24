from __future__ import annotations

from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "West Bengal"
TERMS = (
    "STATEMENT IV",
    "STATEMENT V",
    "TABLE IV",
    "TABLE V",
    "TOWN DIRECTORY",
    "CIVIC AND OTHER AMENITIES",
    "MEDICAL, EDUCATIONAL",
    "TEHSIL-WISE ABSTRACT",
    "TAHSIL-WISE ABSTRACT",
    "TALUK-WISE ABSTRACT",
    "TALUKWISE ABSTRACT",
    "SUB-DIVISION WISE ABSTRACT",
    "ABSTRACT OF AMENITIES",
    "AMENITIES ABSTRACT",
    "TEHSIL",
    "TAHSIL",
    "TALUK",
    "SUBDIVISION",
)


def main() -> None:
    for source_path in sorted(SOURCE_DIR.glob("*.pdf")):
        print(f"\n### {source_path.name}", flush=True)
        document = fitz.open(str(source_path))
        for index, page in enumerate(document, start=1):
            text = page.get_text("text")
            normalized = " ".join(text.split())
            upper = normalized.upper()
            hits = [term for term in TERMS if term in upper]
            if hits:
                print(f"{index}: {','.join(hits)} | {normalized[:500]}", flush=True)


if __name__ == "__main__":
    main()
