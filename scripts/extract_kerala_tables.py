from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Kerala"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Kerala"


# Source page numbers are one-based.  Kerala's Town Directory statements are
# sometimes packed together on one page; the full original page is retained.
# The Taluk-wise amenities abstract is the Kerala equivalent of the requested
# tehsil appendix.
PAGE_MAP: dict[str, dict[str, list[int]]] = {
    "1971 Alleppey.pdf": {
        "civic_amenities": [24, 25],
        "medical_educational_amenities": [26, 27],
        "tehsil_appendix": [50, 51, 52],
    },
    "1971 Cannanore.pdf": {
        "civic_amenities": [24, 25],
        "medical_educational_amenities": [26, 27],
        "tehsil_appendix": [56, 57, 58],
    },
    "1971 Kottayam.pdf": {
        "civic_amenities": [24],
        "medical_educational_amenities": [24, 25],
        "tehsil_appendix": [50, 51, 52],
    },
    "1971 Kozhikode.pdf": {
        "civic_amenities": [22, 23],
        "medical_educational_amenities": [24, 25],
        "tehsil_appendix": [46, 47, 48],
    },
    "1971 Malappuram.pdf": {
        "civic_amenities": [23, 24],
        "medical_educational_amenities": [23, 24],
        "tehsil_appendix": [43, 44],
    },
    "1971 Palghat.pdf": {
        "civic_amenities": [22, 23],
        "medical_educational_amenities": [22, 23],
        "tehsil_appendix": [48, 49],
    },
    "1971 Quilon.pdf": {
        "civic_amenities": [22, 23],
        "medical_educational_amenities": [22, 23],
        "tehsil_appendix": [44, 45, 46],
    },
    "1971 Trichur.pdf": {
        "civic_amenities": [22, 23],
        "medical_educational_amenities": [24, 25],
        "tehsil_appendix": [62, 63],
    },
    "1971 Trivandrum.pdf": {
        "civic_amenities": [25, 26],
        "medical_educational_amenities": [27, 28],
        "tehsil_appendix": [47, 48],
    },
    # Idikki is a later district handbook, but it does contain the two
    # requested Town Directory statements.  Only the taluk-wise village
    # directory is present; there is no separate aggregate amenities appendix.
    "1971 Idikki.pdf": {
        "civic_amenities": [22],
        "medical_educational_amenities": [23, 24],
    },
}


REVIEW_ITEMS = [
    {
        "source": "1971 Ernakulam.pdf",
        "status": "skipped",
        "reason": "Part X-C Census Tables volume; no Town and Village Directory Statement IV/V or Taluk-wise amenities abstract found.",
    },
    {
        "source": "1971 Idikki.pdf",
        "table": "tehsil_appendix",
        "status": "skipped",
        "reason": "The Idikki handbook contains Statement IV on source p. 22 and Statement V on source p. 23, but no separate taluk-wise aggregate amenities appendix; the Village Directory pages are per-village tables.",
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
        page_sizes.append({"source_page": source_page_number, "mediabox": box_tuple(output_page.mediabox), "cropbox": box_tuple(output_page.cropbox)})
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
    if expected_names - actual_names:
        raise ValueError(f"missing Kerala sources: {sorted(expected_names - actual_names)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for source_path in source_paths:
        if source_path.name not in PAGE_MAP:
            continue
        district = source_path.stem.removeprefix("1971 ").strip()
        for table_key, page_numbers in PAGE_MAP[source_path.name].items():
            manifest.append(extract_one(source_path, district, table_key, page_numbers))

    expected_count = sum(len(tables) for tables in PAGE_MAP.values())
    if len(manifest) != expected_count:
        raise ValueError(f"expected {expected_count} Kerala outputs, generated {len(manifest)}")
    manifest_path = OUTPUT_DIR / "1971_Kerala_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    review_path = OUTPUT_DIR / "1971_Kerala_review.json"
    review_path.write_text(json.dumps(REVIEW_ITEMS, indent=2), encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} Kerala PDFs in {OUTPUT_DIR}")
    print(manifest_path)
    print(review_path)


if __name__ == "__main__":
    main()
