from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Bihar"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Bihar"

TABLE_SUFFIX = {
    "civic_amenities": "civic_amenities",
    "medical_educational_amenities": "medical_educational_amenities",
    "tehsil_appendix": "tehsil_appendix",
}

# Source page numbers are one-based. These spans were checked against the
# printed Statement IV/V headings, continuation columns, and the complete
# Appendix to Village Directory immediately before Part B. The appendix is
# called a Development Blockwise Abstract of Educational, Medical and Other
# Amenities in these Bihar volumes.
DISTRICTS: dict[str, dict[str, object]] = {
    "Bhagalpur": {
        "source": "24656_1971_BHA.pdf",
        "civic_amenities": [41],
        "medical_educational_amenities": [41],
        "tehsil_appendix": [213, 214],
    },
    "Dhanbad": {
        "source": "24912_1971_DHA.pdf",
        "civic_amenities": [33, 34],
        "medical_educational_amenities": [35, 36],
        "tehsil_appendix": [113, 114],
    },
    "Hazaribagh": {
        "source": "25098_1971_HAZ.pdf",
        "civic_amenities": [63, 64],
        "medical_educational_amenities": [65, 66],
        "tehsil_appendix": [393, 394, 395, 396],
    },
    "Ranchi": {
        "source": "25194_1971_RAN.pdf",
        "civic_amenities": [45, 46],
        "medical_educational_amenities": [47, 48],
        "tehsil_appendix": [247, 248, 249, 250],
    },
    "Monghyr": {
        "source": "25257_1971_MON.pdf",
        "civic_amenities": [50],
        "medical_educational_amenities": [51],
        "tehsil_appendix": [264, 265, 266, 267],
    },
    "Patna": {
        "source": "25312_1971_PAT.pdf",
        "civic_amenities": [34, 35],
        "medical_educational_amenities": [36, 37],
        "tehsil_appendix": [186, 187, 188, 189],
    },
    "Champaran": {
        "source": "25599_1971_CHA.pdf",
        "civic_amenities": [37],
        "medical_educational_amenities": [37],
        "tehsil_appendix": [197, 198, 199, 200],
    },
    "Saharsa": {
        "source": "26051_1971_SAH.pdf",
        "civic_amenities": [33, 34],
        "medical_educational_amenities": [35, 36],
        "tehsil_appendix": [121, 122],
    },
    "Purnea": {
        "source": "40512_1971_PUR.pdf",
        "civic_amenities": [47, 48],
        "medical_educational_amenities": [49, 50],
        "tehsil_appendix": [265, 266, 267, 268],
    },
    "Singhbhum": {
        "source": "41339_1971_SIN.pdf",
        "civic_amenities": [51, 52],
        "medical_educational_amenities": [53, 54],
        "tehsil_appendix": [277, 278, 279],
    },
    "Palamau": {
        "source": "41344_1971_PAL.pdf",
        "civic_amenities": [40],
        "medical_educational_amenities": [41],
        "tehsil_appendix": [209, 210, 211],
    },
    "Saran": {
        "source": "41669_1971_SAR.pdf",
        "civic_amenities": [48],
        "medical_educational_amenities": [49],
        "tehsil_appendix": [291, 292, 293, 294],
    },
    "Gaya": {
        "source": "43128_1971_GAY.pdf",
        "civic_amenities": [59, 60],
        "medical_educational_amenities": [61, 62],
        "tehsil_appendix": [385, 386, 387, 388],
    },
    "Darbhanga": {
        "source": "43891_1971_DAR.pdf",
        "civic_amenities": [45, 46],
        "medical_educational_amenities": [45, 46],
        "tehsil_appendix": [234, 235, 236, 237],
    },
    "Santal Parganas": {
        "source": "47756_1971_SAN.pdf",
        "civic_amenities": [84, 85],
        "medical_educational_amenities": [86, 87],
        "tehsil_appendix": [634, 635, 636, 637],
    },
}

# This file is a Part X-C administrative/statistical volume, not the Part X-A
# Town & Village Directory, so it is not a substitute for the DCHB Saran file
# above. It is intentionally excluded from the Bihar district inventory.
EXCLUDED_SOURCES = {
    "1971 Saran .pdf": "Part X-C administrative/statistical volume; replaced for this extraction by the newly supplied Part X-A/Part X-B Saran DCHB (41669_1971_SAR.pdf).",
}

# Shahabad is also a Part X-C volume and contains no requested Town Directory
# Statement IV/V or Village Directory amenities appendix.
REVIEW_RECORDS: list[dict[str, object]] = [
    {
        "source": "41313_1971_SHA.pdf",
        "table": table,
        "status": "review",
        "reason": "The supplied Shahabad volume is Part X-C Administrative Statistics and District Census Tables, not the Part X-A Town & Village Directory; the requested Statement IV, Statement V, and equivalent Village Directory amenities appendix are absent.",
    }
    for table in TABLE_SUFFIX
]


def box_tuple(box) -> tuple[float, float, float, float]:
    return tuple(round(float(value), 6) for value in box)


def output_path(district: str, table_key: str) -> Path:
    return OUTPUT_DIR / f"1971_{district}_{TABLE_SUFFIX[table_key]}.pdf"


def extract_one(
    district: str,
    source_name: str,
    reader: PdfReader,
    table_key: str,
    page_numbers: list[int],
) -> dict[str, object]:
    if not page_numbers or min(page_numbers) < 1 or max(page_numbers) > len(reader.pages):
        raise ValueError(f"invalid page selection for {district}: {table_key} {page_numbers}")

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
        "source": str((SOURCE_DIR / source_name).relative_to(ROOT)),
        "output": str(target.relative_to(ROOT)),
        "source_pages": page_numbers,
        "output_pages": len(reopened.pages),
        "page_sizes": page_sizes,
    }


def main() -> None:
    expected_sources = {str(spec["source"]) for spec in DISTRICTS.values()} | {"41313_1971_SHA.pdf"}
    actual_sources = {path.name for path in SOURCE_DIR.glob("*1971_*.pdf")}
    if actual_sources != expected_sources:
        raise ValueError(
            "Bihar DCHB source inventory mismatch; "
            f"missing={sorted(expected_sources - actual_sources)}, "
            f"unexpected={sorted(actual_sources - expected_sources)}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for district, spec in DISTRICTS.items():
        source_name = str(spec["source"])
        source_path = SOURCE_DIR / source_name
        reader = PdfReader(str(source_path), strict=False)
        for table_key, page_numbers in spec.items():
            if table_key == "source":
                continue
            manifest.append(extract_one(district, source_name, reader, table_key, list(page_numbers)))

    expected = len(DISTRICTS) * len(TABLE_SUFFIX)
    if len(manifest) != expected:
        raise ValueError(f"expected {expected} Bihar outputs, generated {len(manifest)}")

    manifest_path = OUTPUT_DIR / "1971_Bihar_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    review_path = OUTPUT_DIR / "1971_Bihar_review.json"
    review_path.write_text(json.dumps(REVIEW_RECORDS, indent=2), encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} Bihar PDFs in {OUTPUT_DIR}")
    print(manifest_path)
    print(review_path)


if __name__ == "__main__":
    main()
