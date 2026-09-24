from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Sikkim"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Sikkim"

PAGE_MAP = {
    "1971 Sikkim.pdf": {
        "civic_amenities": [13],
        "medical_educational_amenities": [14, 15],
    }
}

REVIEW_RECORDS = [
    {
        "source": "1971 Sikkim.pdf",
        "table": "tehsil_appendix",
        "status": "review",
        "reason": "The Sikkim Village Directory is presented at Block Panchayat level and contains no separate tehsil/taluk-wise amenities abstract equivalent to the requested appendix.",
    }
]

OUTPUT_SUFFIX = {
    "civic_amenities": "civic_amenities",
    "medical_educational_amenities": "medical_educational_amenities",
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
        if "/Contents" not in output_page and "/Resources" not in output_page:
            raise ValueError(f"{target.name}: page has no readable content or resources")
        page_sizes.append({
            "source_page": source_page_number,
            "mediabox": box_tuple(output_page.mediabox),
            "cropbox": box_tuple(output_page.cropbox),
            "rotate": int(output_page.get("/Rotate", 0)),
        })
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
    if {path.name for path in source_paths} != set(PAGE_MAP):
        raise ValueError("1971 Sikkim source inventory mismatch")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for source_path in source_paths:
        district = source_path.stem.removeprefix("1971 ").strip()
        for table_key, page_numbers in PAGE_MAP[source_path.name].items():
            manifest.append(extract_one(source_path, district, table_key, page_numbers))
    if len(manifest) != 2:
        raise ValueError(f"expected 2 Sikkim outputs, generated {len(manifest)}")
    (OUTPUT_DIR / "1971_Sikkim_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "1971_Sikkim_review.json").write_text(json.dumps(REVIEW_RECORDS, indent=2), encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} Sikkim PDFs in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
