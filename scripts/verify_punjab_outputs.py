from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

from extract_punjab_tables import PAGE_MAP, REVIEW_RECORDS, ROOT, SOURCE_DIR, OUTPUT_DIR, box_tuple, output_path


def main() -> None:
    source_names = {path.name for path in SOURCE_DIR.glob("1971 *.pdf")}
    if source_names != set(PAGE_MAP):
        raise ValueError(f"source inventory mismatch: missing={set(PAGE_MAP)-source_names}, extra={source_names-set(PAGE_MAP)}")

    manifest = json.loads((OUTPUT_DIR / "1971_Punjab_manifest.json").read_text(encoding="utf-8"))
    review = json.loads((OUTPUT_DIR / "1971_Punjab_review.json").read_text(encoding="utf-8"))
    if len(manifest) != 21:
        raise ValueError(f"expected 21 manifest entries, found {len(manifest)}")
    if review != REVIEW_RECORDS:
        raise ValueError("review records differ from the state extraction record")

    seen = set()
    for item in manifest:
        source_name = Path(item["source"]).name
        seen.add((source_name, item["table"]))
        source_reader = PdfReader(str(ROOT / item["source"]), strict=False)
        target_reader = PdfReader(str(ROOT / item["output"]), strict=False)
        expected_pages = item["source_pages"]
        if len(target_reader.pages) != len(expected_pages):
            raise ValueError(f"{Path(item['output']).name}: page count mismatch")
        for source_page_number, target_page in zip(expected_pages, target_reader.pages):
            source_page = source_reader.pages[source_page_number - 1]
            if box_tuple(source_page.mediabox) != box_tuple(target_page.mediabox):
                raise ValueError(f"{Path(item['output']).name}: media box changed")
            if box_tuple(source_page.cropbox) != box_tuple(target_page.cropbox):
                raise ValueError(f"{Path(item['output']).name}: crop box changed")
            if int(source_page.get("/Rotate", 0)) != int(target_page.get("/Rotate", 0)):
                raise ValueError(f"{Path(item['output']).name}: rotation changed")
            if "/Contents" not in target_page and "/Resources" not in target_page:
                raise ValueError(f"{Path(item['output']).name}: page has no content or resources")

    expected_seen = {(source_name, table_key) for source_name, tables in PAGE_MAP.items() for table_key in tables}
    if seen != expected_seen:
        raise ValueError(f"manifest key mismatch: missing={expected_seen-seen}, extra={seen-expected_seen}")
    expected_files = {
        output_path(Path(source_name).stem.removeprefix("1971 ").strip(), table_key).name
        for source_name, tables in PAGE_MAP.items()
        for table_key in tables
    }
    actual_files = {path.name for path in OUTPUT_DIR.glob("1971_*.pdf")}
    if actual_files != expected_files:
        raise ValueError(f"output file mismatch: missing={expected_files-actual_files}, extra={actual_files-expected_files}")
    print(f"Verified {len(manifest)} Punjab PDFs, {sum(item['output_pages'] for item in manifest)} pages, source geometry, rotation, content, manifest, and review records")


if __name__ == "__main__":
    main()
