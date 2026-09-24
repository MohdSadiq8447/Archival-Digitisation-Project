from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Rajasthan"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Rajasthan"


# Source page numbers are one-based and were checked against the printed
# Statement IV/V and Appendix III-A headings, including continuations.
PAGE_MAP: dict[str, dict[str, list[int]]] = {
    "1971 Ajmer.pdf": {
        "civic_amenities": [40],
        "medical_educational_amenities": [41],
        "tehsil_appendix": [92, 93],
    },
    "1971 Alwar.pdf": {
        "civic_amenities": [42],
        "medical_educational_amenities": [43],
        "tehsil_appendix": [138, 139],
    },
    "1971 Banswara.pdf": {
        "civic_amenities": [39],
        "medical_educational_amenities": [40],
        "tehsil_appendix": [110, 111],
    },
    "1971 Barmer.pdf": {
        "civic_amenities": [38],
        "medical_educational_amenities": [39],
        "tehsil_appendix": [85, 86],
    },
    "1971 Bharatpur.pdf": {
        "civic_amenities": [42],
        "medical_educational_amenities": [43],
        "tehsil_appendix": [140, 141],
    },
    "1971 Bhilwara.pdf": {
        "civic_amenities": [43],
        "medical_educational_amenities": [44],
        "tehsil_appendix": [122, 123, 124, 125],
    },
    "1971 Bikaner.pdf": {
        "civic_amenities": [36],
        "medical_educational_amenities": [37],
        "tehsil_appendix": [76, 77],
    },
    "1971 Bundi.pdf": {
        "civic_amenities": [33],
        "medical_educational_amenities": [34],
        "tehsil_appendix": [74, 75],
    },
    "1971 Chittaurgarh.pdf": {
        "civic_amenities": [43],
        "medical_educational_amenities": [44],
        "tehsil_appendix": [157, 158, 159, 160],
    },
    "1971 Churu.pdf": {
        "civic_amenities": [36],
        "medical_educational_amenities": [37],
        "tehsil_appendix": [85, 86],
    },
    "1971 Dungarpur.pdf": {
        "civic_amenities": [34],
        "medical_educational_amenities": [35],
        "tehsil_appendix": [77, 78],
    },
    "1971 Ganganagar.pdf": {
        "civic_amenities": [44],
        "medical_educational_amenities": [45, 46],
        "tehsil_appendix": [193, 194, 195, 196],
    },
    "1971 Jaipur.pdf": {
        "civic_amenities": [49],
        "medical_educational_amenities": [50, 51],
        "tehsil_appendix": [186, 187, 188, 189],
    },
    "1971 Jaisalmer.pdf": {
        "civic_amenities": [40],
        "medical_educational_amenities": [41],
        "tehsil_appendix": [69, 70],
    },
    "1971 Jhalawar.pdf": {
        "civic_amenities": [43],
        "medical_educational_amenities": [44],
        "tehsil_appendix": [121, 122],
    },
    "1971 Jhunjhunun.pdf": {
        "civic_amenities": [46],
        "medical_educational_amenities": [47, 48],
        "tehsil_appendix": [87, 88],
    },
    "1971 Jodhpur.pdf": {
        "civic_amenities": [42],
        "medical_educational_amenities": [43],
        "tehsil_appendix": [80, 81],
    },
    "1971 Kota.pdf": {
        "civic_amenities": [46],
        "medical_educational_amenities": [47],
        "tehsil_appendix": [152, 153],
    },
    "1971 Nagaur.pdf": {
        "civic_amenities": [45],
        "medical_educational_amenities": [46],
        "tehsil_appendix": [111, 112],
    },
    "1971 Pali.pdf": {
        "civic_amenities": [43],
        "medical_educational_amenities": [44],
        "tehsil_appendix": [89, 90],
    },
    "1971 Sawai Madhopur.pdf": {
        "civic_amenities": [44],
        "medical_educational_amenities": [45],
        "tehsil_appendix": [128, 129, 130, 131],
    },
    "1971 Sikar.pdf": {
        "civic_amenities": [44],
        "medical_educational_amenities": [45],
        "tehsil_appendix": [90, 91],
    },
    "1971 Sirohi.pdf": {
        "civic_amenities": [43],
        "medical_educational_amenities": [44],
        "tehsil_appendix": [73, 74],
    },
    "1971 Tonk.pdf": {
        "civic_amenities": [42],
        "medical_educational_amenities": [43],
        "tehsil_appendix": [100, 101],
    },
    "1971 Udaipur.pdf": {
        "civic_amenities": [41],
        "medical_educational_amenities": [42],
        "tehsil_appendix": [190, 191, 192, 193],
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
            f"1971 Rajasthan source inventory mismatch; "
            f"missing={sorted(expected_names - actual_names)}, "
            f"unexpected={sorted(actual_names - expected_names)}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for source_path in source_paths:
        district = source_path.stem.removeprefix("1971 ").strip()
        for table_key, page_numbers in PAGE_MAP[source_path.name].items():
            manifest.append(extract_one(source_path, district, table_key, page_numbers))

    if len(manifest) != 75:
        raise ValueError(f"expected 75 Rajasthan outputs, generated {len(manifest)}")
    manifest_path = OUTPUT_DIR / "1971_Rajasthan_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} Rajasthan PDFs in {OUTPUT_DIR}")
    print(manifest_path)


if __name__ == "__main__":
    main()
