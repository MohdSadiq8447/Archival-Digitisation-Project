from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Punjab"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Punjab"


# One-based source page numbers, confirmed against the printed page numbers and
# the table headings in the original scans.
PAGE_MAP: dict[str, dict[str, list[int]]] = {
    "1971 Firozpur.pdf": {
        "civic_amenities": [121],
        "medical_educational_amenities": [122],
        "tehsil_appendix": [114, 115],
    },
    "1971 Hoshiarpur.pdf": {
        "civic_amenities": [123],
        "medical_educational_amenities": [124],
        "tehsil_appendix": [116, 117],
    },
    "1971 Jullundur.pdf": {
        "civic_amenities": [109],
        "medical_educational_amenities": [110],
        "tehsil_appendix": [102, 103],
    },
    "1971 Kapurthala.pdf": {},
    "1971 Ludhiana.pdf": {
        "civic_amenities": [91],
        "medical_educational_amenities": [92],
        "tehsil_appendix": [85, 86],
    },
    "1971 Patiala.pdf": {
        "civic_amenities": [118],
        "medical_educational_amenities": [119],
        "tehsil_appendix": [111, 112],
    },
    "1971 Rupnagar.pdf": {
        "civic_amenities": [90],
        "medical_educational_amenities": [91],
        "tehsil_appendix": [82, 83, 84],
    },
    "1971 Sangrur.pdf": {
        "civic_amenities": [92],
        "medical_educational_amenities": [93],
        "tehsil_appendix": [85, 86],
    },
}

REVIEW_RECORDS = [
    {
        "source": "1971 Kapurthala.pdf",
        "table": table,
        "status": "review",
        "reason": "The Kapurthala volume is Part X-C, District Census Tables, Administrative and Statistics. It does not contain the Part X-A Village and Town Directory pages with Town Directory Statement IV, Statement V, or a tehsil-wise amenities abstract.",
    }
    for table in ("civic_amenities", "medical_educational_amenities", "tehsil_appendix")
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
        if "/Contents" not in output_page and "/Resources" not in output_page:
            raise ValueError(f"{target.name}: page has no readable content or resources")
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
    if {path.name for path in source_paths} != set(PAGE_MAP):
        raise ValueError("1971 Punjab source inventory mismatch")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for source_path in source_paths:
        district = source_path.stem.removeprefix("1971 ").strip()
        for table_key, page_numbers in PAGE_MAP[source_path.name].items():
            manifest.append(extract_one(source_path, district, table_key, page_numbers))

    if len(manifest) != 21:
        raise ValueError(f"expected 21 Punjab outputs, generated {len(manifest)}")
    manifest_path = OUTPUT_DIR / "1971_Punjab_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    review_path = OUTPUT_DIR / "1971_Punjab_review.json"
    review_path.write_text(json.dumps(REVIEW_RECORDS, indent=2), encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} Punjab PDFs in {OUTPUT_DIR}")
    print(manifest_path)
    print(review_path)


if __name__ == "__main__":
    main()
