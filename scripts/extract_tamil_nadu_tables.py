from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Tamil Nadu"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Tamil Nadu"


# One-based source page numbers. Town-directory ranges are complete Statement
# IV/V spans. The appendix lists contain the one-page Appendix II abstract for
# each taluk, in source order; district-wide abstracts are intentionally omitted.
PAGE_MAP: dict[str, dict[str, list[int]]] = {
    "1971 Chengalpattu.pdf": {
        "civic_amenities": list(range(377, 393)),
        "medical_educational_amenities": list(range(393, 413)),
        "tehsil_appendix": [48, 74, 90, 116, 130, 142, 169, 190, 226, 254, 274, 318],
    },
    "1971 Coimbatore.pdf": {
        "civic_amenities": list(range(209, 221)),
        "medical_educational_amenities": list(range(221, 233)),
        "tehsil_appendix": [34, 52, 78, 94, 110, 122, 134, 150, 168],
    },
    "1971 Dharmapuri.pdf": {
        "civic_amenities": [217, 218],
        "medical_educational_amenities": [219, 220],
        "tehsil_appendix": [48, 64, 90, 124, 170, 186, 206],
    },
    "1971 Nilgiris.pdf": {},
    "1971 North Arcot.pdf": {
        "civic_amenities": list(range(346, 352)),
        "medical_educational_amenities": list(range(352, 359)),
        "tehsil_appendix": [37, 57, 79, 97, 115, 137, 149, 175, 203, 235, 267, 301, 321],
    },
    "1971 Ramanathapuram.pdf": {
        "civic_amenities": list(range(287, 293)),
        "medical_educational_amenities": list(range(293, 300)),
        "tehsil_appendix": [36, 46, 66, 78, 90, 108, 120, 134, 146, 156, 170, 190, 216, 230, 246, 256, 264],
    },
    "1971 Salem.pdf": {
        "civic_amenities": list(range(182, 190)),
        "medical_educational_amenities": list(range(190, 196)),
        "tehsil_appendix": [29, 43, 53, 71, 83, 95, 111, 131, 155],
    },
    "1971 South Arcot.pdf": {},
    "1971 Thanjavur.pdf": {
        "civic_amenities": list(range(329, 335)),
        "medical_educational_amenities": list(range(335, 341)),
        "tehsil_appendix": [32, 52, 72, 100, 126, 152, 170, 190, 208, 228, 252, 270, 298],
    },
    "1971 Tiruchchirappalli.pdf": {
        "civic_amenities": list(range(310, 316)),
        "medical_educational_amenities": list(range(316, 322)),
        "tehsil_appendix": [41, 61, 81, 105, 119, 135, 151, 167, 183, 195, 225, 253, 281],
    },
    "1971 Tirunelveli.pdf": {
        "civic_amenities": list(range(253, 263)),
        "medical_educational_amenities": list(range(263, 273)),
        "tehsil_appendix": [34, 52, 66, 74, 88, 110, 128, 134, 152, 176, 192, 210, 220],
    },
}

REVIEW_RECORDS = [
    {
        "source": source,
        "table": table,
        "status": "review",
        "reason": reason,
    }
    for source, reason in (
        (
            "1971 Nilgiris.pdf",
            "This volume is Part X-C, District Census Tables. It does not contain the Part X-A Village and Town Directory pages for the requested statements or taluk amenities appendix.",
        ),
        (
            "1971 South Arcot.pdf",
            "This volume is Part IX-B, Village and Townwise Primary Census Abstract. It does not contain the Part X-A Village and Town Directory pages for the requested statements or taluk amenities appendix.",
        ),
    )
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


def extract_one(source_path: Path, district: str, table_key: str, page_numbers: list[int], reader: PdfReader) -> dict[str, object]:
    if not page_numbers or min(page_numbers) < 1 or max(page_numbers) > len(reader.pages):
        raise ValueError(f"invalid page selection for {source_path.name}: {page_numbers}")

    writer = PdfWriter()
    source_pages = [reader.pages[number - 1] for number in page_numbers]
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
        raise ValueError(
            f"1971 Tamil Nadu source inventory mismatch: missing={set(PAGE_MAP)-{p.name for p in source_paths}}, extra={ {p.name for p in source_paths}-set(PAGE_MAP)}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for source_path in source_paths:
        district = source_path.stem.removeprefix("1971 ").strip()
        reader = PdfReader(str(source_path), strict=False)
        for table_key, page_numbers in PAGE_MAP[source_path.name].items():
            manifest.append(extract_one(source_path, district, table_key, page_numbers, reader))

    if len(manifest) != 27:
        raise ValueError(f"expected 27 Tamil Nadu outputs, generated {len(manifest)}")
    manifest_path = OUTPUT_DIR / "1971_Tamil_Nadu_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    review_path = OUTPUT_DIR / "1971_Tamil_Nadu_review.json"
    review_path.write_text(json.dumps(REVIEW_RECORDS, indent=2), encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} Tamil Nadu PDFs in {OUTPUT_DIR}")
    print(manifest_path)
    print(review_path)


if __name__ == "__main__":
    main()
