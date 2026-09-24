from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Manipur"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Manipur"


# Source page numbers are one-based. Central and South contain the actual
# Town Directory Statements IV/V; North and West contain no town tables, only
# the sub-division amenities abstract in the Village Directory section.
PAGE_MAP: dict[str, dict[str, list[int]]] = {
    "1971 Manipur Central.pdf": {
        "civic_amenities": [36],
        "medical_educational_amenities": [37, 38],
        "tehsil_appendix": [97, 98],
    },
    "1971 Manipur North.pdf": {
        "tehsil_appendix": [51, 52],
    },
    "1971 Manipur South.pdf": {
        "civic_amenities": [34],
        "medical_educational_amenities": [35, 36],
        "tehsil_appendix": [67, 68],
    },
    "1971 Manipur West.pdf": {
        "tehsil_appendix": [43, 44],
    },
}

REVIEW_RECORDS = [
    {
        "source": "1971 Manipur North.pdf",
        "table": "civic_amenities",
        "status": "review",
        "reason": "No actual Town Directory Statement IV table is present in this volume; the Town Directory section contains only the abbreviation/key material before the Village Directory begins.",
    },
    {
        "source": "1971 Manipur North.pdf",
        "table": "medical_educational_amenities",
        "status": "review",
        "reason": "No actual Town Directory Statement V table is present in this volume; the Town Directory section contains only the abbreviation/key material before the Village Directory begins.",
    },
    {
        "source": "1971 Manipur West.pdf",
        "table": "civic_amenities",
        "status": "review",
        "reason": "No actual Town Directory Statement IV table is present in this volume; the Town Directory section contains only the abbreviation/key material before the Village Directory begins.",
    },
    {
        "source": "1971 Manipur West.pdf",
        "table": "medical_educational_amenities",
        "status": "review",
        "reason": "No actual Town Directory Statement V table is present in this volume; the Town Directory section contains only the abbreviation/key material before the Village Directory begins.",
    },
]

OUTPUT_SUFFIX = {
    "civic_amenities": "civic_amenities",
    "medical_educational_amenities": "medical_educational_amenities",
    "tehsil_appendix": "tehsil_appendix",
}


def box_tuple(box) -> tuple[float, float, float, float]:
    return tuple(round(float(value), 6) for value in box)


def output_path(district: str, table_key: str) -> Path:
    return OUTPUT_DIR / f"1971_{district}_{OUTPUT_SUFFIX[table_key]}.pdf"


def extract_one(source_path: Path, district: str, table_key: str, page_numbers: list[int]) -> dict[str, object]:
    source_reader = PdfReader(str(source_path), strict=False)
    if not page_numbers or min(page_numbers) < 1 or max(page_numbers) > len(source_reader.pages):
        raise ValueError(f"invalid page selection for {source_path.name}: {page_numbers}")

    writer = PdfWriter()
    source_pages = [source_reader.pages[number - 1] for number in page_numbers]
    for page in source_pages:
        writer.add_page(page)

    target = output_path(district, table_key)
    with target.open("wb") as handle:
        writer.write(handle)

    reopened = PdfReader(str(target), strict=False)
    if len(reopened.pages) != len(page_numbers):
        raise ValueError(f"{target.name}: output page count changed")
    page_sizes = []
    for source_page, output_page, source_page_number in zip(source_pages, reopened.pages, page_numbers):
        if box_tuple(source_page.mediabox) != box_tuple(output_page.mediabox):
            raise ValueError(f"{target.name}: media box changed on source page {source_page_number}")
        if box_tuple(source_page.cropbox) != box_tuple(output_page.cropbox):
            raise ValueError(f"{target.name}: crop box changed on source page {source_page_number}")
        if int(source_page.get("/Rotate", 0)) != int(output_page.get("/Rotate", 0)):
            raise ValueError(f"{target.name}: rotation changed on source page {source_page_number}")
        page_sizes.append(
            {
                "source_page": source_page_number,
                "mediabox": box_tuple(output_page.mediabox),
                "cropbox": box_tuple(output_page.cropbox),
                "rotate": int(output_page.get("/Rotate", 0)),
            }
        )
    return {
        "district": district,
        "table": table_key,
        "source": str(source_path.relative_to(ROOT)),
        "output": str(target.relative_to(ROOT)),
        "source_pages": page_numbers,
        "output_pages": len(reopened.pages),
        "page_sizes": page_sizes,
    }


def main() -> None:
    source_paths = sorted(SOURCE_DIR.glob("1971 *.pdf"), key=lambda path: path.name.lower())
    expected_names = set(PAGE_MAP)
    actual_names = {path.name for path in source_paths}
    if actual_names != expected_names:
        raise ValueError(
            f"1971 Manipur source inventory mismatch; "
            f"missing={sorted(expected_names - actual_names)}, "
            f"unexpected={sorted(actual_names - expected_names)}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for source_path in source_paths:
        district = source_path.stem.removeprefix("1971 ").strip()
        for table_key, page_numbers in PAGE_MAP[source_path.name].items():
            manifest.append(extract_one(source_path, district, table_key, page_numbers))

    if len(manifest) != 8:
        raise ValueError(f"expected 8 Manipur outputs, generated {len(manifest)}")
    manifest_path = OUTPUT_DIR / "1971_Manipur_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    review_path = OUTPUT_DIR / "1971_Manipur_review.json"
    review_path.write_text(json.dumps(REVIEW_RECORDS, indent=2), encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} Manipur PDFs in {OUTPUT_DIR}")
    print(manifest_path)
    print(review_path)


if __name__ == "__main__":
    main()
