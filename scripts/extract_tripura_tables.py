from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Tripura"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Tripura"
SOURCE_NAME = "1971 Tripura.pdf"

PAGE_MAP = {
    "civic_amenities": [130, 131],
    "medical_educational_amenities": [132, 133],
    "tehsil_appendix": [116, 117],
}

OUTPUT_SUFFIX = {
    "civic_amenities": "civic_amenities",
    "medical_educational_amenities": "medical_educational_amenities",
    "tehsil_appendix": "tehsil_appendix",
}


def box_tuple(box) -> tuple[float, float, float, float]:
    return tuple(round(float(value), 6) for value in box)


def output_path(table_key: str) -> Path:
    return OUTPUT_DIR / f"1971_Tripura_{OUTPUT_SUFFIX[table_key]}.pdf"


def extract_one(reader: PdfReader, table_key: str, page_numbers: list[int]) -> dict[str, object]:
    if min(page_numbers) < 1 or max(page_numbers) > len(reader.pages):
        raise ValueError(f"invalid page selection for {SOURCE_NAME}: {page_numbers}")
    writer = PdfWriter()
    source_pages = [reader.pages[number - 1] for number in page_numbers]
    for page in source_pages:
        writer.add_page(page)
    target = output_path(table_key)
    with target.open("wb") as handle:
        writer.write(handle)
    reopened = PdfReader(str(target), strict=False)
    if len(reopened.pages) != len(page_numbers):
        raise ValueError(f"{target.name}: output page count changed")
    page_sizes = []
    for source_page, output_page, source_page_number in zip(source_pages, reopened.pages, page_numbers):
        if box_tuple(source_page.mediabox) != box_tuple(output_page.mediabox):
            raise ValueError(f"{target.name}: media box changed")
        if box_tuple(source_page.cropbox) != box_tuple(output_page.cropbox):
            raise ValueError(f"{target.name}: crop box changed")
        if int(source_page.get("/Rotate", 0)) != int(output_page.get("/Rotate", 0)):
            raise ValueError(f"{target.name}: rotation changed")
        if "/Contents" not in output_page and "/Resources" not in output_page:
            raise ValueError(f"{target.name}: page has no readable content or resources")
        page_sizes.append({"source_page": source_page_number, "mediabox": box_tuple(output_page.mediabox), "cropbox": box_tuple(output_page.cropbox), "rotate": int(output_page.get("/Rotate", 0))})
    return {
        "district": "Tripura",
        "table": table_key,
        "source": str((SOURCE_DIR / SOURCE_NAME).relative_to(ROOT)),
        "output": str(target.relative_to(ROOT)),
        "source_pages": page_numbers,
        "output_pages": len(reopened.pages),
        "page_sizes": page_sizes,
    }


def main() -> None:
    source_path = SOURCE_DIR / SOURCE_NAME
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(source_path), strict=False)
    manifest = [extract_one(reader, table_key, pages) for table_key, pages in PAGE_MAP.items()]
    if len(manifest) != 3:
        raise ValueError(f"expected 3 Tripura outputs, generated {len(manifest)}")
    manifest_path = OUTPUT_DIR / "1971_Tripura_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    review_path = OUTPUT_DIR / "1971_Tripura_review.json"
    review_path.write_text("[]\n", encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} Tripura PDFs in {OUTPUT_DIR}")
    print(manifest_path)
    print(review_path)


if __name__ == "__main__":
    main()
