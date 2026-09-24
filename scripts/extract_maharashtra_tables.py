from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Maharashtra"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Maharashtra"


# Source page numbers are one-based. Statement IV/V spans were checked against
# the printed headings and the following Statement VI page. The previously
# generated Maharashtra tehsil-appendix outputs were audited and found to be
# incorrect; no tehsil appendix output is retained until a correct span is
# established separately.
PAGE_MAP: dict[str, dict[str, list[int]]] = {
    "1971 Ahmadnagar.pdf": {"civic_amenities": [39], "medical_educational_amenities": [40]},
    "1971 Akola.pdf": {"civic_amenities": [34], "medical_educational_amenities": [35]},
    "1971 Amravati.pdf": {"civic_amenities": [35], "medical_educational_amenities": [36]},
    "1971 Bhandara.pdf": {"civic_amenities": [26], "medical_educational_amenities": [27]},
    "1971 Bhir.pdf": {"civic_amenities": [29], "medical_educational_amenities": [30]},
    "1971 Buldana.pdf": {"civic_amenities": [27], "medical_educational_amenities": [28]},
    "1971 Chandrapur.pdf": {"civic_amenities": [38], "medical_educational_amenities": [39]},
    "1971 Dhulia.pdf": {"civic_amenities": [35], "medical_educational_amenities": [36]},
    "1971 Jalgaon.pdf": {"civic_amenities": [41], "medical_educational_amenities": [42]},
    "1971 Kolaba.pdf": {"civic_amenities": [43], "medical_educational_amenities": [44]},
    "1971 Kolhapur.pdf": {"civic_amenities": [39], "medical_educational_amenities": [40]},
    "1971 Nagpur.pdf": {"civic_amenities": [33], "medical_educational_amenities": [34]},
    "1971 Nanded.pdf": {"civic_amenities": [31], "medical_educational_amenities": [32]},
    "1971 Nasik.pdf": {"civic_amenities": [41], "medical_educational_amenities": [42, 43]},
    "1971 Osmanabad.pdf": {"civic_amenities": [37], "medical_educational_amenities": [38]},
    "1971 Parbhani.pdf": {"civic_amenities": [31], "medical_educational_amenities": [32]},
    "1971 Pune.pdf": {"civic_amenities": [43], "medical_educational_amenities": [44, 45]},
    "1971 Ratnagiri.pdf": {"civic_amenities": [45], "medical_educational_amenities": [46]},
    "1971 Sangli.pdf": {"civic_amenities": [12], "medical_educational_amenities": [13]},
    "1971 Satara.pdf": {"civic_amenities": [37], "medical_educational_amenities": [38]},
    "1971 Sholapur.pdf": {"civic_amenities": [38], "medical_educational_amenities": [39]},
    "1971 Thane.pdf": {"civic_amenities": [41], "medical_educational_amenities": [42, 43]},
    "1971 Wardha.pdf": {"civic_amenities": [25], "medical_educational_amenities": [26]},
    "1971 Yavatmal.pdf": {"civic_amenities": [35], "medical_educational_amenities": [36]},
    "44875_1971_AUR.pdf": {"civic_amenities": [39], "medical_educational_amenities": [40]},
}

DISTRICT_FOR_SOURCE = {"44875_1971_AUR.pdf": "Aurangabad"}

REVIEW_RECORDS = [
    {
        "source": "1971 Greater Maharashtra.pdf",
        "table": table,
        "status": "review",
        "reason": "This is a Greater Maharashtra municipal-corporation volume and does not contain the relevant district Town Directory Statement IV/V or a tehsil amenities abstract.",
    }
    for table in ("civic_amenities", "medical_educational_amenities", "tehsil_appendix")
] + [
    {
        "source": source,
        "table": "tehsil_appendix",
        "status": "review",
        "reason": "The previously generated Maharashtra tehsil-appendix output was removed after audit because its page span was incorrect; no replacement appendix is retained.",
    }
    for source in PAGE_MAP
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
    source_paths = sorted(list(SOURCE_DIR.glob("1971 *.pdf")) + [SOURCE_DIR / "44875_1971_AUR.pdf"], key=lambda path: path.name.lower())
    expected_names = set(PAGE_MAP) | {"1971 Greater Maharashtra.pdf"}
    actual_names = {path.name for path in source_paths}
    if actual_names != expected_names:
        raise ValueError(
            f"1971 Maharashtra source inventory mismatch; "
            f"missing={sorted(expected_names - actual_names)}, "
            f"unexpected={sorted(actual_names - expected_names)}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for source_path in source_paths:
        if source_path.name not in PAGE_MAP:
            continue
        district = DISTRICT_FOR_SOURCE.get(source_path.name, source_path.stem.removeprefix("1971 ").strip())
        for table_key, page_numbers in PAGE_MAP[source_path.name].items():
            manifest.append(extract_one(source_path, district, table_key, page_numbers))

    if len(manifest) != 50:
        raise ValueError(f"expected 50 Maharashtra outputs, generated {len(manifest)}")
    manifest_path = OUTPUT_DIR / "1971_Maharashtra_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    review_path = OUTPUT_DIR / "1971_Maharashtra_review.json"
    review_path.write_text(json.dumps(REVIEW_RECORDS, indent=2), encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} Maharashtra PDFs in {OUTPUT_DIR}")
    print(manifest_path)
    print(review_path)


if __name__ == "__main__":
    main()
