from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Karnataka"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Karnataka"


# Source page numbers are one-based. They were checked against the printed
# Statement IV/V headings, table continuations, and the Talukwise Appendix II
# amenities abstract pages. Blank separator pages and following appendices are
# intentionally excluded.
PAGE_MAP: dict[str, dict[str, list[int]]] = {
    "1971 Bangalore.pdf": {
        "civic_amenities": [31, 32],
        "medical_educational_amenities": [33, 34, 35, 36],
        "tehsil_appendix": [277, 278],
    },
    "1971 Belgaum.pdf": {
        "civic_amenities": [25, 26],
        "medical_educational_amenities": [27, 28],
        "tehsil_appendix": [141, 142],
    },
    "1971 Bellary.pdf": {
        "civic_amenities": [25, 26],
        "medical_educational_amenities": [27, 28],
        "tehsil_appendix": [104, 105],
    },
    "1971 Bijapur.pdf": {
        "civic_amenities": [25, 26],
        "medical_educational_amenities": [27, 28],
        "tehsil_appendix": [155, 156],
    },
    "1971 Chikmagalur.pdf": {
        "civic_amenities": [23, 24],
        "medical_educational_amenities": [25, 26],
        "tehsil_appendix": [131, 132],
    },
    "1971 Chitradurga.pdf": {
        "civic_amenities": [22, 23],
        "medical_educational_amenities": [24, 25],
        "tehsil_appendix": [146, 147],
    },
    "1971 Coorg.pdf": {
        "civic_amenities": [22, 23],
        "medical_educational_amenities": [24, 25],
        "tehsil_appendix": [60, 61],
    },
    "1971 Gulbarga.pdf": {
        "civic_amenities": [24, 25],
        "medical_educational_amenities": [26, 27, 28],
        "tehsil_appendix": [156, 157],
    },
    "1971 Hassan.pdf": {
        "civic_amenities": [25, 26],
        "medical_educational_amenities": [27, 28],
        "tehsil_appendix": [207, 208],
    },
    "1971 Kolar.pdf": {
        "civic_amenities": [25, 26],
        "medical_educational_amenities": [27, 28, 29, 30],
        "tehsil_appendix": [285, 286],
    },
    "1971 Mandya.pdf": {
        "civic_amenities": [23, 24],
        "medical_educational_amenities": [25, 26],
        "tehsil_appendix": [147, 148],
    },
    "1971 Mysore.pdf": {
        "civic_amenities": [25, 26],
        "medical_educational_amenities": [27, 28],
        "tehsil_appendix": [195, 196, 197, 198],
    },
    "1971 North Kanara.pdf": {
        "civic_amenities": [25, 26],
        "medical_educational_amenities": [27, 28, 29],
        "tehsil_appendix": [145, 146],
    },
    "1971 Raichur.pdf": {
        "civic_amenities": [24, 25],
        "medical_educational_amenities": [26, 27],
        "tehsil_appendix": [168, 169],
    },
    "1971 Shimoga.pdf": {
        "civic_amenities": [24, 25],
        "medical_educational_amenities": [26, 27],
        "tehsil_appendix": [196, 197],
    },
    "1971 South Kanara.pdf": {
        "civic_amenities": [25, 26],
        "medical_educational_amenities": [27, 28, 29, 30],
        "tehsil_appendix": [97, 98],
    },
    "1971 Tumkur.pdf": {
        "civic_amenities": [23, 24],
        "medical_educational_amenities": [25, 26],
        "tehsil_appendix": [247, 248],
    },
}


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
        page_sizes.append(
            {
                "source_page": source_page_number,
                "mediabox": box_tuple(output_page.mediabox),
                "cropbox": box_tuple(output_page.cropbox),
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
            f"1971 Karnataka source inventory mismatch; "
            f"missing={sorted(expected_names - actual_names)}, "
            f"unexpected={sorted(actual_names - expected_names)}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for source_path in source_paths:
        district = source_path.stem.removeprefix("1971 ").strip()
        for table_key, page_numbers in PAGE_MAP[source_path.name].items():
            manifest.append(extract_one(source_path, district, table_key, page_numbers))

    if len(manifest) != 51:
        raise ValueError(f"expected 51 Karnataka outputs, generated {len(manifest)}")
    manifest_path = OUTPUT_DIR / "1971_Karnataka_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} Karnataka PDFs in {OUTPUT_DIR}")
    print(manifest_path)


if __name__ == "__main__":
    main()
