from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from extract_andhra_tables import OUTPUT_DIR, OUTPUT_SUFFIX, PAGE_MAP, SOURCE_DIR, box_tuple


def main() -> None:
    expected = set()
    for source_name, table_map in PAGE_MAP.items():
        district = Path(source_name).stem.removeprefix("1971 ").strip()
        source_reader = PdfReader(str(SOURCE_DIR / source_name))
        for table_key, suffix in OUTPUT_SUFFIX.items():
            output_path = OUTPUT_DIR / f"1971_{district}_{suffix}.pdf"
            expected.add(output_path.name)
            if not output_path.exists():
                raise FileNotFoundError(output_path)
            output_reader = PdfReader(str(output_path))
            page_numbers = table_map[table_key]
            if len(output_reader.pages) != len(page_numbers):
                raise ValueError(f"{output_path.name}: expected {len(page_numbers)} pages")
            for out_page, source_number in zip(output_reader.pages, page_numbers):
                source_page = source_reader.pages[source_number - 1]
                if box_tuple(out_page.mediabox) != box_tuple(source_page.mediabox):
                    raise ValueError(f"{output_path.name}: media box mismatch")
                if box_tuple(out_page.cropbox) != box_tuple(source_page.cropbox):
                    raise ValueError(f"{output_path.name}: crop box mismatch")

    actual = {path.name for path in OUTPUT_DIR.glob("*.pdf")}
    if actual != expected:
        raise ValueError(f"output inventory mismatch: expected {len(expected)}, found {len(actual)}")

    counts = Counter(len(PdfReader(str(OUTPUT_DIR / name)).pages) for name in actual)
    print(f"verified_pdfs={len(actual)}")
    print(f"page_count_distribution={dict(sorted(counts.items()))}")
    print(f"total_output_pages={sum(count * amount for count, amount in counts.items())}")


if __name__ == "__main__":
    main()
