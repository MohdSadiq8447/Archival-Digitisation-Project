from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Arunachal Pradesh"
TERMS = (
    "STATEMENT IV",
    "STATEMENT V",
    "CIVIC AND OTHER AMENITIES",
    "MEDICAL, EDUCATIONAL",
    "TEHSIL-WISE ABSTRACT",
    "TALUK-WISE ABSTRACT",
    "TALUKWISE ABSTRACT",
    "SUB-DIVISION WISE ABSTRACT",
    "ABSTRACT OF AMENITIES",
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
                print(f"{index}: {','.join(hits)} | {text[:260]}")


if __name__ == "__main__":
    main()
