from pathlib import Path

from pypdf import PdfReader


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
    "APPENDIX",
)


def main() -> None:
    for source_path in sorted(SOURCE_DIR.glob("*.pdf")):
        print(f"\n### {source_path.name}")
        reader = PdfReader(str(source_path), strict=False)
        for index, page in enumerate(reader.pages, start=1):
            text = " ".join((page.extract_text() or "").split())
            upper = text.upper()
            hits = [term for term in TERMS if term in upper]
            if hits:
                print(f"{index}: {','.join(hits)} | {text[:360]}")


if __name__ == "__main__":
    main()
