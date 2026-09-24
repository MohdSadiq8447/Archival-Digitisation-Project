from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Dadra & Nagar Haveli"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Dadra & Nagar Haveli"
SOURCE_NAME = "1971 Dadra & Nagar Haveli.pdf"
PAGE_MAP = {
    "civic_amenities": [48],
    "medical_educational_amenities": [49, 50],
    "tehsil_appendix": [27, 28],
}
OUTPUT_SUFFIX = {
    "civic_amenities": "civic_amenities",
    "medical_educational_amenities": "medical_educational_amenities",
    "tehsil_appendix": "tehsil_appendix",
}


def box_tuple(box) -> tuple[float, float, float, float]:
    return tuple(round(float(value), 6) for value in box)


def output_path(table_key: str) -> Path:
    return OUTPUT_DIR / f"1971_Dadra_and_Nagar_Haveli_{OUTPUT_SUFFIX[table_key]}.pdf"


def extract_one(reader: PdfReader, table_key: str, page_numbers: list[int]) -> dict[str, object]:
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
        if box_tuple(source_page.mediabox) != box_tuple(output_page.mediabox) or box_tuple(source_page.cropbox) != box_tuple(output_page.cropbox):
            raise ValueError(f"{target.name}: page geometry changed")
        if int(source_page.get("/Rotate", 0)) != int(output_page.get("/Rotate", 0)):
            raise ValueError(f"{target.name}: rotation changed")
        if "/Contents" not in output_page and "/Resources" not in output_page:
            raise ValueError(f"{target.name}: missing content")
        page_sizes.append({"source_page": source_page_number, "mediabox": box_tuple(output_page.mediabox), "cropbox": box_tuple(output_page.cropbox), "rotate": int(output_page.get("/Rotate", 0))})
    return {"district": "Dadra & Nagar Haveli", "table": table_key, "source": str((SOURCE_DIR / SOURCE_NAME).relative_to(ROOT)), "output": str(target.relative_to(ROOT)), "source_pages": page_numbers, "output_pages": len(reopened.pages), "page_sizes": page_sizes}


def main() -> None:
    source = SOURCE_DIR / SOURCE_NAME
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(source), strict=False)
    manifest = [extract_one(reader, key, pages) for key, pages in PAGE_MAP.items()]
    (OUTPUT_DIR / "1971_Dadra_and_Nagar_Haveli_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    review = [{"source": SOURCE_NAME, "table": key, "status": "note", "reason": "The volume states that Dadra and Nagar Haveli has no urban town; Statement IV/V are retained as the supplied Town Directory appendix formats rather than populated town data."} for key in ("civic_amenities", "medical_educational_amenities")]
    (OUTPUT_DIR / "1971_Dadra_and_Nagar_Haveli_review.json").write_text(json.dumps(review, indent=2), encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} Dadra & Nagar Haveli PDFs in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
