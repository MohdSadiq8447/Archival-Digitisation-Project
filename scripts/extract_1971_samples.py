from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "output" / "pdf" / "1971_trimmed"


# These spans were located and visually verified against the source scans.
# Page numbers are one-based source PDF page numbers.
SAMPLES = [
    {
        "state_dir": "Andra Pradesh",
        "state_label": "Andra Pradesh",
        "district": "Adilabad",
        "source": "1971 Adilabad .pdf",
        "pages": {
            "civic_amenities": [173],
            "medical_educational_amenities": [174],
            "tehsil_appendix": [160, 161],
        },
    },
    {
        "state_dir": "Gujarat",
        "state_label": "Gujarat",
        "district": "Ahmadabad",
        "source": "1971 Ahmadabad.pdf",
        "pages": {
            "civic_amenities": [55, 56],
            "medical_educational_amenities": [57, 58],
            "tehsil_appendix": [121, 122],
        },
    },
    {
        "state_dir": "Rajasthan",
        "state_label": "Rajasthan",
        "district": "Ajmer",
        "source": "1971 Ajmer.pdf",
        "pages": {
            "civic_amenities": [40],
            "medical_educational_amenities": [41],
            "tehsil_appendix": [92, 93],
        },
    },
]


TABLE_LABELS = {
    "civic_amenities": "civic_amenities",
    "medical_educational_amenities": "medical_educational_amenities",
    "tehsil_appendix": "tehsil_appendix",
}


def output_name(district: str, table_key: str) -> str:
    return f"1971_{district}_{TABLE_LABELS[table_key]}.pdf"


def page_box(page, box_name: str) -> tuple[float, float, float, float]:
    box = getattr(page, box_name)
    return tuple(round(float(value), 4) for value in (box.left, box.bottom, box.right, box.top))


def extract_pages(source_path: Path, page_numbers: list[int], output_path: Path) -> None:
    source_reader = PdfReader(str(source_path), strict=False)
    if not page_numbers:
        raise ValueError(f"No pages selected for {source_path}")
    if min(page_numbers) < 1 or max(page_numbers) > len(source_reader.pages):
        raise ValueError(
            f"Page selection {page_numbers} is outside {source_path} "
            f"({len(source_reader.pages)} pages)"
        )

    writer = PdfWriter()
    for page_number in page_numbers:
        writer.add_page(source_reader.pages[page_number - 1])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as stream:
        writer.write(stream)


def verify_output(
    source_path: Path, output_path: Path, page_numbers: list[int]
) -> dict[str, object]:
    source_reader = PdfReader(str(source_path), strict=False)
    output_reader = PdfReader(str(output_path), strict=False)

    if len(output_reader.pages) != len(page_numbers):
        raise ValueError(
            f"{output_path}: expected {len(page_numbers)} pages, "
            f"found {len(output_reader.pages)}"
        )

    for output_page, source_page_number in zip(output_reader.pages, page_numbers):
        source_page = source_reader.pages[source_page_number - 1]
        for box_name in ("mediabox", "cropbox"):
            if page_box(output_page, box_name) != page_box(source_page, box_name):
                raise ValueError(
                    f"{output_path}: {box_name} differs from source page "
                    f"{source_page_number}"
                )

    return {
        "source": str(source_path.relative_to(ROOT)),
        "output": str(output_path.relative_to(ROOT)),
        "source_pages": page_numbers,
        "output_pages": len(output_reader.pages),
        "page_sizes": [
            {
                "mediabox": page_box(page, "mediabox"),
                "cropbox": page_box(page, "cropbox"),
            }
            for page in output_reader.pages
        ],
    }


def main() -> None:
    manifest: list[dict[str, object]] = []
    for sample in SAMPLES:
        source_path = ROOT / "1971" / sample["state_dir"] / sample["source"]
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        if sample["state_dir"] == "Uttar Pradesh":
            raise ValueError("Uttar Pradesh is out of scope")

        state_output_dir = OUTPUT_ROOT / sample["state_label"]
        for table_key, page_numbers in sample["pages"].items():
            output_path = state_output_dir / output_name(sample["district"], table_key)
            extract_pages(source_path, page_numbers, output_path)
            record = verify_output(source_path, output_path, page_numbers)
            record.update(
                {
                    "state": sample["state_label"],
                    "district": sample["district"],
                    "table": table_key,
                }
            )
            manifest.append(record)

    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
