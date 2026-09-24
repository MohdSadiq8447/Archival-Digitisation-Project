from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Jammu & Kashmir"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Jammu & Kashmir"

DISTRICTS = {
    "Anantnag": {
        "source": "1971 Anantnag.pdf",
        "civic_amenities": [44],
        "medical_educational_amenities": [45],
        "tehsil_appendix": [161, 162],
    },
    "Baramula": {
        "source": "1971 Baramula.pdf",
        "civic_amenities": [37],
        "medical_educational_amenities": [38],
        "tehsil_appendix": [44, 45, 46],
    },
    "Doda": {
        "source": "1971 Doda.pdf",
        "civic_amenities": [44],
        "medical_educational_amenities": [45],
        "tehsil_appendix": [97, 98],
    },
    "Jammu": {
        "source": "1971 Jammu.pdf",
        "civic_amenities": [42],
        "medical_educational_amenities": [43],
        "tehsil_appendix": [130, 131, 132],
    },
    "Kathua": {
        "source": "1971 Kathua.pdf",
        "civic_amenities": [38],
        "medical_educational_amenities": [39],
        "tehsil_appendix": [95, 96],
    },
    "Ladakh": {
        "source": "1971 Ladakh.pdf",
        "civic_amenities": [33],
        "medical_educational_amenities": [34],
        "tehsil_appendix": [62, 63, 64],
    },
    "Punch": {
        "source": "1971 Punch.pdf",
        "civic_amenities": [30],
        "medical_educational_amenities": [31],
        "tehsil_appendix": [54, 55, 56],
    },
    "Rajauri": {
        "source": "1971 Rajauri.pdf",
        "civic_amenities": [33],
        "medical_educational_amenities": [34],
        "tehsil_appendix": [70, 71, 72],
    },
    "Srinagar": {
        "source": "1971 Srinagar.pdf",
        "civic_amenities": [33],
        "medical_educational_amenities": [34],
        "tehsil_appendix": [40, 41, 42],
    },
    "Udhampur": {
        "source": "1971 Udhampur.pdf",
        "civic_amenities": [37],
        "medical_educational_amenities": [38],
        "tehsil_appendix": [92, 93],
    },
}

TABLE_SUFFIX = {
    "civic_amenities": "civic_amenities",
    "medical_educational_amenities": "medical_educational_amenities",
    "tehsil_appendix": "tehsil_appendix",
}


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
        for table_key in TABLE_SUFFIX:
            pages = list(spec[table_key])
            manifest.append(extract_one(district, source_name, reader, table_key, pages))

    expected = len(DISTRICTS) * len(TABLE_SUFFIX)
    if len(manifest) != expected:
        raise ValueError(f"expected {expected} Jammu & Kashmir outputs, generated {len(manifest)}")
    manifest_path = OUTPUT_DIR / "1971_Jammu_and_Kashmir_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    review_path = OUTPUT_DIR / "1971_Jammu_and_Kashmir_review.json"
    review_path.write_text("[]\n", encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} Jammu & Kashmir PDFs in {OUTPUT_DIR}")
    print(manifest_path)
    print(review_path)


if __name__ == "__main__":
    main()
