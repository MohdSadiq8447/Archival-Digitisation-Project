from pathlib import Path
from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Andra Pradesh"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Andra Pradesh"


# Source page numbers are 1-based. These spans were checked against the
# printed statement headings and the appendix continuation pages.
PAGE_MAP = {
    "1971 Adilabad .pdf": {
        "civic_amenities": [173],
        "medical_educational_amenities": [174],
        "tehsil_appendix": [160, 161],
    },
    "1971 Anantapur.pdf": {
        "civic_amenities": [143],
        "medical_educational_amenities": [144],
        "tehsil_appendix": [132, 133],
    },
    "1971 Chittoor.pdf": {
        "civic_amenities": [159],
        "medical_educational_amenities": [160],
        "tehsil_appendix": [148, 149],
    },
    "1971 Cuddapah.pdf": {
        "civic_amenities": [129],
        "medical_educational_amenities": [130],
        "tehsil_appendix": [118, 119],
    },
    "1971 East Godavari.pdf": {
        "civic_amenities": [191],
        "medical_educational_amenities": [192, 193],
        "tehsil_appendix": [178, 179],
    },
    "1971 Guntur.pdf": {
        "civic_amenities": [111],
        "medical_educational_amenities": [112, 113],
        "tehsil_appendix": [100, 101],
    },
    "1971 Hyderabad.pdf": {
        "civic_amenities": [148, 149],
        "medical_educational_amenities": [150, 151],
        "tehsil_appendix": [126, 127],
    },
    "1971 Karimnagar.pdf": {
        "civic_amenities": [130],
        "medical_educational_amenities": [131],
        "tehsil_appendix": [119, 120],
    },
    "1971 Khammam.pdf": {
        "civic_amenities": [142],
        "medical_educational_amenities": [143],
        "tehsil_appendix": [130, 131],
    },
    "1971 Krishna.pdf": {
        "civic_amenities": [121],
        "medical_educational_amenities": [122, 123],
        "tehsil_appendix": [110, 111],
    },
    "1971 Kurnool.pdf": {
        "civic_amenities": [141],
        "medical_educational_amenities": [142],
        "tehsil_appendix": [128, 129],
    },
    "1971 Mahbubnagar.pdf": {
        "civic_amenities": [173],
        "medical_educational_amenities": [174],
        "tehsil_appendix": [160, 161],
    },
    "1971 Medak.pdf": {
        "civic_amenities": [139],
        "medical_educational_amenities": [140],
        "tehsil_appendix": [128, 129],
    },
    "1971 Nalgonda.pdf": {
        "civic_amenities": [133],
        "medical_educational_amenities": [134],
        "tehsil_appendix": [122, 123],
    },
    "1971 Nellore.pdf": {
        "civic_amenities": [139],
        "medical_educational_amenities": [140],
        "tehsil_appendix": [126, 127],
    },
    "1971 Nizamabad.pdf": {
        "civic_amenities": [115],
        "medical_educational_amenities": [116],
        "tehsil_appendix": [102, 103, 104, 105],
    },
    "1971 Ongole (Prakasam).pdf": {
        "civic_amenities": [139],
        "medical_educational_amenities": [140],
        "tehsil_appendix": [126, 127],
    },
    "1971 Srikakulam.pdf": {
        "civic_amenities": [271],
        "medical_educational_amenities": [272],
        "tehsil_appendix": [256, 257, 258, 259],
    },
    "1971 Visakhapatnam.pdf": {
        "civic_amenities": [381],
        "medical_educational_amenities": [382, 383],
        "tehsil_appendix": [362, 363, 364, 365],
    },
    "1971 Warangal.pdf": {
        "civic_amenities": [125],
        "medical_educational_amenities": [126],
        "tehsil_appendix": [114, 115],
    },
    "1971 West Godavari.pdf": {
        "civic_amenities": [121],
        "medical_educational_amenities": [122],
        "tehsil_appendix": [108, 109, 110, 111],
    },
}


OUTPUT_SUFFIX = {
    "civic_amenities": "civic_amenities",
    "medical_educational_amenities": "medical_educational_amenities",
    "tehsil_appendix": "tehsil_appendix",
}


def box_tuple(box):
    return tuple(round(float(value), 6) for value in box)


def extract_one(source_path: Path, district: str, table_key: str, page_numbers: list[int]) -> Path:
    reader = PdfReader(str(source_path))
    if len(reader.pages) < max(page_numbers):
        raise ValueError(
            f"{source_path.name}: requested page {max(page_numbers)} but source has {len(reader.pages)} pages"
        )

    writer = PdfWriter()
    source_pages = [reader.pages[number - 1] for number in page_numbers]
    for page in source_pages:
        writer.add_page(page)

    output_path = OUTPUT_DIR / f"1971_{district}_{OUTPUT_SUFFIX[table_key]}.pdf"
    with output_path.open("wb") as handle:
        writer.write(handle)

    reopened = PdfReader(str(output_path))
    if len(reopened.pages) != len(page_numbers):
        raise ValueError(f"{output_path.name}: page count changed after writing")
    for index, source_page in enumerate(source_pages):
        output_page = reopened.pages[index]
        if box_tuple(source_page.mediabox) != box_tuple(output_page.mediabox):
            raise ValueError(f"{output_path.name}: media box changed on page {index + 1}")
        if box_tuple(source_page.cropbox) != box_tuple(output_page.cropbox):
            raise ValueError(f"{output_path.name}: crop box changed on page {index + 1}")

    return output_path


def main() -> None:
    source_paths = sorted(SOURCE_DIR.glob("*.pdf"), key=lambda path: path.name.lower())
    expected_names = set(PAGE_MAP)
    actual_names = {path.name for path in source_paths}
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        unexpected = sorted(actual_names - expected_names)
        raise ValueError(f"source inventory mismatch; missing={missing}, unexpected={unexpected}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_paths = []
    for source_path in source_paths:
        district = source_path.stem.removeprefix("1971 ").strip()
        for table_key in OUTPUT_SUFFIX:
            output_paths.append(
                extract_one(source_path, district, table_key, PAGE_MAP[source_path.name][table_key])
            )

    if len(output_paths) != 63:
        raise ValueError(f"expected 63 outputs, generated {len(output_paths)}")

    print(f"Generated and verified {len(output_paths)} PDFs in {OUTPUT_DIR}")
    for output_path in output_paths:
        print(output_path)


if __name__ == "__main__":
    main()
