from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Arunachal Pradesh"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Arunachal Pradesh"

TABLE_SUFFIX = {
    "civic_amenities": "civic_amenities",
    "medical_educational_amenities": "medical_educational_amenities",
    "tehsil_appendix": "tehsil_appendix",
}

# Source page numbers are 1-based. The circle-wise abstracts are part of the
# Village Directory and are retained as complete source pages. Siang's page
# numbers in the printed volume are 60 (Statements IV/V) and 68-69 (the
# circle-wise abstract); in the PDF these are source pages 80 and 88-89.
DISTRICTS = {
    "Kameng": {
        "source": "1971 Kameng.pdf",
        "civic_amenities": [59],
        "medical_educational_amenities": [59],
        "tehsil_appendix": [67, 68],
    },
    "Lohit": {
        "source": "1971 Lohit.pdf",
        "civic_amenities": [70],
        "medical_educational_amenities": [71],
        "tehsil_appendix": [76, 77],
    },
    "Subansiri": {
        "source": "1971 Subansiri.pdf",
        "tehsil_appendix": [72, 73],
    },
    "Tirap": {
        "source": "1971 Tirap .pdf",
        "tehsil_appendix": [76, 77],
    },
    "Siang": {
        "source": "1971 Siang.pdf",
        "civic_amenities": [80],
        "medical_educational_amenities": [80],
        "tehsil_appendix": [88, 89],
    },
}

REVIEW_RECORDS: list[dict[str, object]] = [
    {
        "source": "1971 Subansiri.pdf",
        "table": table,
        "status": "review",
        "reason": "No separate town Statement IV/V page was located in the inspected district volume; the available amenities abstract is the Circle-wise Village Directory appendix, which was extracted as tehsil_appendix.",
    }
    for table in ("civic_amenities", "medical_educational_amenities")
] + [
    {
        "source": "1971 Tirap .pdf",
        "table": table,
        "status": "review",
        "reason": "No separate town Statement IV/V page was located in the inspected district volume; the available amenities abstract is the Circle-wise Village Directory appendix, which was extracted as tehsil_appendix.",
    }
    for table in ("civic_amenities", "medical_educational_amenities")
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
            raise ValueError(f"{target.name}: media box changed")
        if box_tuple(source_page.cropbox) != box_tuple(output_page.cropbox):
            raise ValueError(f"{target.name}: crop box changed")
        if int(source_page.get("/Rotate", 0)) != int(output_page.get("/Rotate", 0)):
            raise ValueError(f"{target.name}: rotation changed")
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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for district, spec in DISTRICTS.items():
        source_name = str(spec["source"])
        source_path = SOURCE_DIR / source_name
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        reader = PdfReader(str(source_path), strict=False)
        for table_key, page_numbers in spec.items():
            if table_key == "source":
                continue
            manifest.append(extract_one(district, source_name, reader, table_key, list(page_numbers)))

    expected = 11
    if len(manifest) != expected:
        raise ValueError(f"expected {expected} Arunachal Pradesh outputs, generated {len(manifest)}")

    manifest_path = OUTPUT_DIR / "1971_Arunachal_Pradesh_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    review_path = OUTPUT_DIR / "1971_Arunachal_Pradesh_review.json"
    review_path.write_text(json.dumps(REVIEW_RECORDS, indent=2), encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} Arunachal Pradesh PDFs in {OUTPUT_DIR}")
    print(manifest_path)
    print(review_path)


if __name__ == "__main__":
    main()
