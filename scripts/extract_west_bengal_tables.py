from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "West Bengal"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "West Bengal"

TABLE_SUFFIX = {
    "civic_amenities": "civic_amenities",
    "medical_educational_amenities": "medical_educational_amenities",
    "tehsil_appendix": "tehsil_appendix",
}

# Source page numbers are 1-based. Statement IV includes the immediately
# following "Other Amenities" pages; Statement V includes the continuation
# pages headed "And Cultural Facilities".
DISTRICTS = {
    "Birbhum": {
        "source": "1971 Birbhum.pdf",
        "civic_amenities": [47, 48],
        "medical_educational_amenities": [49, 50],
    },
    "Burdwan": {
        "source": "1971 Burdwan.pdf",
        "civic_amenities": [59, 60],
        "medical_educational_amenities": [61, 62],
    },
    "Calcutta": {
        "source": "1971 Calcutta.pdf",
        "civic_amenities": [13, 14],
        "medical_educational_amenities": [15, 16],
    },
    "Dinajpur": {
        "source": "1971 Dinajpur .pdf",
        "civic_amenities": [60, 61],
        "medical_educational_amenities": [62, 63],
    },
    "Haora": {
        "source": "1971 Haora.pdf",
        "civic_amenities": [41, 42, 43, 44],
        "medical_educational_amenities": [45, 46, 47, 48],
    },
    "Hugli": {
        "source": "1971 Hugli.pdf",
        "civic_amenities": [53, 54],
        "medical_educational_amenities": [55, 56],
    },
    "Jalapiguri": {
        "source": "1971 Jalapiguri.pdf",
        "civic_amenities": [33, 34],
        "medical_educational_amenities": [35, 36],
    },
    "Murshidabad": {
        "source": "1971 Murshidabad.pdf",
        "civic_amenities": [51, 52],
        "medical_educational_amenities": [53, 54],
    },
    "Purullia": {
        "source": "1971 Purullia.pdf",
        "civic_amenities": [57, 58],
        "medical_educational_amenities": [59, 60],
    },
    "Twentyfour Parganas": {
        "source": "1971 Twentyfour Parganas.pdf",
        "civic_amenities": [106, 107, 108, 109, 110, 111, 112, 113, 114, 115],
        "medical_educational_amenities": [116, 117, 118, 119, 120, 121, 122, 123],
    },
}

NO_TOWN_DIRECTORY = {
    "Bankura": "1971 Bankura.pdf",
    "Cooch Behar": "1971 Cooch Behar.pdf",
    "Darjiling": "1971 Darjiling.pdf",
    "Maldah": "1971 Maldah.pdf",
    "Midnapore": "1971 Midnapore.pdf",
    "Nadia": "1971 Nadia.pdf",
}

REVIEW_RECORDS: list[dict[str, object]] = []
for district, spec in DISTRICTS.items():
    REVIEW_RECORDS.append(
        {
            "source": str(spec["source"]),
            "table": "tehsil_appendix",
            "status": "review",
            "reason": "No separate tahsil/tehsil/taluk-wise amenities abstract was located in this Part X-A & B volume; the inspected village amenities pages are per-village tables, not the requested aggregate appendix.",
        }
    )
for district, source in NO_TOWN_DIRECTORY.items():
    for table in TABLE_SUFFIX:
        REVIEW_RECORDS.append(
            {
                "source": source,
                "table": table,
                "status": "review",
                "reason": "This is a Part X-C District Census Tables volume and does not contain the Part X-A/B Town Directory Statement IV/V or an equivalent tehsil/taluk amenities appendix; no output was produced.",
            }
        )


def box_tuple(box) -> tuple[float, float, float, float]:
    return tuple(round(float(value), 6) for value in box)


def output_path(district: str, table_key: str) -> Path:
    safe_district = district.replace(" ", "_")
    return OUTPUT_DIR / f"1971_{safe_district}_{TABLE_SUFFIX[table_key]}.pdf"


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
            raise ValueError(f"{target.name}: media box changed")
        if box_tuple(source_page.cropbox) != box_tuple(output_page.cropbox):
            raise ValueError(f"{target.name}: crop box changed")
        if int(source_page.get("/Rotate", 0)) != int(output_page.get("/Rotate", 0)):
            raise ValueError(f"{target.name}: rotation changed")
        if "/Contents" not in output_page and "/Resources" not in output_page:
            raise ValueError(f"{target.name}: page has no readable content or resources")
        if not (output_page.extract_text() or "").strip():
            raise ValueError(f"{target.name}: page has no readable text")
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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for district, spec in DISTRICTS.items():
        source_name = str(spec["source"])
        source_path = SOURCE_DIR / source_name
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        reader = PdfReader(str(source_path), strict=False)
        for table_key in ("civic_amenities", "medical_educational_amenities"):
            manifest.append(extract_one(district, source_name, reader, table_key, list(spec[table_key])))

    expected = len(DISTRICTS) * 2
    if len(manifest) != expected:
        raise ValueError(f"expected {expected} West Bengal outputs, generated {len(manifest)}")

    manifest_path = OUTPUT_DIR / "1971_West_Bengal_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    review_path = OUTPUT_DIR / "1971_West_Bengal_review.json"
    review_path.write_text(json.dumps(REVIEW_RECORDS, indent=2), encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} West Bengal PDFs in {OUTPUT_DIR}")
    print(manifest_path)
    print(review_path)


if __name__ == "__main__":
    main()
