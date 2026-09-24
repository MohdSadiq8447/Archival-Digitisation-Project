from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Madhya Pradesh"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Madhya Pradesh"


# Source page numbers are one-based. These are complete source pages selected
# from the printed Statement IV/V and Appendix-to-Village-Directory spans.
PAGE_MAP: dict[str, dict[str, list[int]]] = {
    "1971 Balaghat.pdf": {"civic_amenities": [109], "medical_educational_amenities": [110], "tehsil_appendix": [105, 106]},
    "1971 Bastar.pdf": {"civic_amenities": [238], "medical_educational_amenities": [239], "tehsil_appendix": [234, 235]},
    "1971 Betul.pdf": {"civic_amenities": [120], "medical_educational_amenities": [120], "tehsil_appendix": [116, 117]},
    "1971 Bhind.pdf": {"civic_amenities": [102], "medical_educational_amenities": [103], "tehsil_appendix": [97, 98]},
    "1971 Bilaspur.pdf": {"civic_amenities": [269], "medical_educational_amenities": [270], "tehsil_appendix": [263, 264]},
    "1971 Chhatarpur.pdf": {"civic_amenities": [101], "medical_educational_amenities": [102], "tehsil_appendix": [96, 97]},
    "1971 Chhindwara.pdf": {"civic_amenities": [141], "medical_educational_amenities": [142], "tehsil_appendix": [135, 136]},
    "1971 Damoh.pdf": {"civic_amenities": [98], "medical_educational_amenities": [99], "tehsil_appendix": [95, 96]},
    "1971 Datia.pdf": {"civic_amenities": [53], "medical_educational_amenities": [54], "tehsil_appendix": [50, 51]},
    "1971 Dewas.pdf": {"civic_amenities": [120], "medical_educational_amenities": [121], "tehsil_appendix": [115, 116]},
    "1971 Dhar.pdf": {"civic_amenities": [138], "medical_educational_amenities": [139], "tehsil_appendix": [133, 134]},
    "1971 Durg.pdf": {"civic_amenities": [307], "medical_educational_amenities": [308], "tehsil_appendix": [301, 302]},
    "1971 Guna.pdf": {"civic_amenities": [184], "medical_educational_amenities": [185], "tehsil_appendix": [169, 170]},
    "1971 Gwalior.pdf": {"civic_amenities": [88], "medical_educational_amenities": [88], "tehsil_appendix": [84, 85]},
    "1971 Hoshangabad.pdf": {"civic_amenities": [136], "medical_educational_amenities": [137], "tehsil_appendix": [130, 131]},
    "1971 Indore.pdf": {"civic_amenities": [83], "medical_educational_amenities": [84], "tehsil_appendix": [78, 79]},
    "1971 Jabalpur.pdf": {"civic_amenities": [196], "medical_educational_amenities": [197, 198], "tehsil_appendix": [189, 190]},
    "1971 Jhabua.pdf": {"civic_amenities": [120], "medical_educational_amenities": [121], "tehsil_appendix": [115, 116]},
    "1971 Khandwa.pdf": {"civic_amenities": [107], "medical_educational_amenities": [108], "tehsil_appendix": [104, 105]},
    "1971 Khargone.pdf": {"civic_amenities": [185], "medical_educational_amenities": [186], "tehsil_appendix": [179, 180]},
    "1971 Mandla.pdf": {"civic_amenities": [168], "medical_educational_amenities": [168], "tehsil_appendix": [164, 165]},
    "1971 Mandsaur.pdf": {"civic_amenities": [164], "medical_educational_amenities": [165], "tehsil_appendix": [158, 159]},
    "1971 Morena.pdf": {"civic_amenities": [118], "medical_educational_amenities": [119], "tehsil_appendix": [113, 114]},
    "1971 Narsimhapur.pdf": {"civic_amenities": [89], "medical_educational_amenities": [89], "tehsil_appendix": [84, 85]},
    "1971 Panna.pdf": {"civic_amenities": [92], "medical_educational_amenities": [93], "tehsil_appendix": [89, 90]},
    "1971 Raigarh.pdf": {"civic_amenities": [164], "medical_educational_amenities": [165], "tehsil_appendix": [159, 160]},
    "1971 Raipur.pdf": {"civic_amenities": [255], "medical_educational_amenities": [256], "tehsil_appendix": [249, 250]},
    "1971 Raisen.pdf": {"civic_amenities": [119], "medical_educational_amenities": [120], "tehsil_appendix": [116, 117]},
    "1971 Rajgarh.pdf": {"civic_amenities": [132], "medical_educational_amenities": [133], "tehsil_appendix": [127, 128]},
    "1971 Ratlam.pdf": {"civic_amenities": [89], "medical_educational_amenities": [90], "tehsil_appendix": [86, 87]},
    "1971 Rewa.pdf": {"civic_amenities": [179], "medical_educational_amenities": [180], "tehsil_appendix": [176, 177]},
    "1971 Sagar.pdf": {"civic_amenities": [145], "medical_educational_amenities": [146], "tehsil_appendix": [140, 141]},
    "1971 Satna.pdf": {"civic_amenities": [171], "medical_educational_amenities": [171], "tehsil_appendix": [166, 167]},
    "1971 Sehore.pdf": {"civic_amenities": [130], "medical_educational_amenities": [131], "tehsil_appendix": [125, 126]},
    "1971 Seoni.pdf": {"civic_amenities": [129], "medical_educational_amenities": [130], "tehsil_appendix": [126, 127]},
    "1971 Shahapur.pdf": {"civic_amenities": [109], "medical_educational_amenities": [110], "tehsil_appendix": [104, 105]},
    "1971 Shahdol.pdf": {"civic_amenities": [148], "medical_educational_amenities": [149], "tehsil_appendix": [142, 143]},
    "1971 Shajapur.pdf": {"civic_amenities": [96], "medical_educational_amenities": [97], "tehsil_appendix": [91, 92]},
    "1971 Sidhi.pdf": {"civic_amenities": [128], "medical_educational_amenities": [129], "tehsil_appendix": [125, 126]},
    "1971 Surguja.pdf": {"civic_amenities": [198], "medical_educational_amenities": [199], "tehsil_appendix": [192, 193]},
    "1971 Tikamgarh.pdf": {"civic_amenities": [82], "medical_educational_amenities": [83], "tehsil_appendix": [79, 80]},
    "1971 Ujjain.pdf": {"civic_amenities": [98], "medical_educational_amenities": [99], "tehsil_appendix": [93, 94]},
    "1971 Vidisha.pdf": {"civic_amenities": [115], "medical_educational_amenities": [116], "tehsil_appendix": [112, 113]},
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
    actual_names = {path.name for path in source_paths}
    expected_names = set(PAGE_MAP)
    if actual_names != expected_names:
        raise ValueError(f"Madhya Pradesh source inventory mismatch; missing={sorted(expected_names - actual_names)}, unexpected={sorted(actual_names - expected_names)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for source_path in source_paths:
        district = source_path.stem.removeprefix("1971 ").strip()
        for table_key, page_numbers in PAGE_MAP[source_path.name].items():
            manifest.append(extract_one(source_path, district, table_key, page_numbers))

    if len(manifest) != 129:
        raise ValueError(f"expected 129 Madhya Pradesh outputs, generated {len(manifest)}")
    manifest_path = OUTPUT_DIR / "1971_Madhya_Pradesh_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated and reopened/verified {len(manifest)} Madhya Pradesh PDFs in {OUTPUT_DIR}")
    print(manifest_path)


if __name__ == "__main__":
    main()
