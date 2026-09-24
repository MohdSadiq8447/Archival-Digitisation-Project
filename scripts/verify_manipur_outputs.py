from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

from extract_manipur_tables import PAGE_MAP, REVIEW_RECORDS, ROOT, SOURCE_DIR, OUTPUT_DIR, output_path, box_tuple


def main() -> None:
    source_names = {path.name for path in SOURCE_DIR.glob("1971 *.pdf")}
    if source_names != set(PAGE_MAP):
        raise ValueError(f"source inventory mismatch: missing={set(PAGE_MAP)-source_names}, extra={source_names-set(PAGE_MAP)}")

    manifest = json.loads((OUTPUT_DIR / "1971_Manipur_manifest.json").read_text(encoding="utf-8"))
    review = json.loads((OUTPUT_DIR / "1971_Manipur_review.json").read_text(encoding="utf-8"))
    if len(manifest) != 8:
        raise ValueError(f"expected 8 manifest entries, found {len(manifest)}")
    if review != REVIEW_RECORDS:
        raise ValueError("review records differ from the state extraction record")

    seen = set()
    for item in manifest:
        source_name = Path(item["source"]).name
        seen.add((source_name, item["table"]))
        source_path = ROOT / item["source"]
        target_path = ROOT / item["output"]
        source_reader = PdfReader(str(source_path), strict=False)
        target_reader = PdfReader(str(target_path), strict=False)
        expected_pages = item["source_pages"]
        if len(target_reader.pages) != len(expected_pages):
            raise ValueError(f"{target_path.name}: page count mismatch")
        for source_page_number, target_page in zip(expected_pages, target_reader.pages):
            source_page = source_reader.pages[source_page_number - 1]
            if box_tuple(source_page.mediabox) != box_tuple(target_page.mediabox):
                raise ValueError(f"{target_path.name}: media box changed on page {source_page_number}")
            if box_tuple(source_page.cropbox) != box_tuple(target_page.cropbox):
                raise ValueError(f"{target_path.name}: crop box changed on page {source_page_number}")
            if int(source_page.get("/Rotate", 0)) != int(target_page.get("/Rotate", 0)):
                raise ValueError(f"{target_path.name}: rotation changed on page {source_page_number}")
            if "/Contents" not in target_page and "/Resources" not in target_page:
                raise ValueError(f"{target_path.name}: page has no content or resources on page {source_page_number}")

    expected_seen = {(source_name, table_key) for source_name, tables in PAGE_MAP.items() for table_key in tables}
    if seen != expected_seen:
        raise ValueError(f"manifest key mismatch: missing={expected_seen-seen}, extra={seen-expected_seen}")
    expected_files = {output_path(Path(source_name).stem.removeprefix("1971 ").strip(), table_key).name for source_name, tables in PAGE_MAP.items() for table_key in tables}
    actual_files = {path.name for path in OUTPUT_DIR.glob("1971_*.pdf")}
    if actual_files != expected_files:
        raise ValueError(f"output file mismatch: missing={expected_files-actual_files}, extra={actual_files-expected_files}")
    print(f"Verified {len(manifest)} Manipur PDFs, {sum(item['output_pages'] for item in manifest)} pages, source geometry, rotation, content, manifest, and review records")


if __name__ == "__main__":
    main()
