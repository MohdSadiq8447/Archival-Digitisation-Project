from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from extract_rajasthan_tables import OUTPUT_DIR, PAGE_MAP, SOURCE_DIR, OUTPUT_SUFFIX, box_tuple, output_path


ROOT = Path(__file__).resolve().parents[1]


def source_name_to_district(source_name: str) -> str:
    return Path(source_name).stem.removeprefix("1971 ").strip()


def page_text(source_path: Path, page_number: int) -> str:
    cache_dir = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\rajasthan-locate")
    cache = cache_dir / (re.sub(r"[^A-Za-z0-9]+", "_", source_path.stem) + ".txt")
    return cache.read_text(encoding="utf-8", errors="replace").split("\f")[page_number - 1]


def expected_names() -> set[str]:
    return {
        output_path(source_name_to_district(source), table_key).name
        for source, tables in PAGE_MAP.items()
        for table_key in tables
    }


def main() -> None:
    actual = {path.name for path in OUTPUT_DIR.glob("*.pdf")}
    expected = expected_names()
    if actual != expected:
        raise ValueError(f"Rajasthan output inventory mismatch: missing={sorted(expected - actual)}, extra={sorted(actual - expected)}")

    total_pages = 0
    for source_name, table_map in PAGE_MAP.items():
        source_path = SOURCE_DIR / source_name
        source_reader = PdfReader(str(source_path), strict=False)
        district = source_name_to_district(source_name)
        for table_key, page_numbers in table_map.items():
            target = output_path(district, table_key)
            output_reader = PdfReader(str(target), strict=False)
            if len(output_reader.pages) != len(page_numbers):
                raise ValueError(f"{target.name}: expected {len(page_numbers)} pages, found {len(output_reader.pages)}")
            for output_page, source_page_number in zip(output_reader.pages, page_numbers):
                source_page = source_reader.pages[source_page_number - 1]
                if box_tuple(output_page.mediabox) != box_tuple(source_page.mediabox):
                    raise ValueError(f"{target.name}: media box differs at source page {source_page_number}")
                if box_tuple(output_page.cropbox) != box_tuple(source_page.cropbox):
                    raise ValueError(f"{target.name}: crop box differs at source page {source_page_number}")

            first = page_text(source_path, page_numbers[0]).lower()
            last = page_text(source_path, page_numbers[-1]).lower()
            if table_key == "civic_amenities":
                if not any(token in first for token in ("statement iv", "statement jv", "civic", "amenities", "protected water supply", "electrification")):
                    raise ValueError(f"{target.name}: first page does not identify Statement IV/civic amenities")
            elif table_key == "medical_educational_amenities":
                if "statement v" not in first and "medical" not in first:
                    raise ValueError(f"{target.name}: first page does not identify Statement V/medical amenities")
            elif table_key == "tehsil_appendix":
                appendix_marker = any(token in first for token in ("appendix", "append", "appen", "appbndix", "apbndix"))
                if not appendix_marker or ("amenit" not in first and "abstract" not in first):
                    raise ValueError(f"{target.name}: first page does not identify the amenities appendix")
                if "land utilis" in last:
                    raise ValueError(f"{target.name}: last page is the land-utilisation appendix, not amenities")
            total_pages += len(output_reader.pages)

    print(f"Verified {len(actual)} Rajasthan PDFs and {total_pages} output pages; inventory, page counts, geometry, and source headings are valid.")


if __name__ == "__main__":
    main()
