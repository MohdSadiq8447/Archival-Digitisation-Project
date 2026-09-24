from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

from extract_meghalaya_tables import PAGE_MAP, REVIEW_RECORDS, ROOT, SOURCE_DIR, OUTPUT_DIR, output_path, box_tuple


def main() -> None:
    expected_sources = set(PAGE_MAP) | {"1971 Garo Hills.pdf"}
    actual_sources = {path.name for path in SOURCE_DIR.glob("1971 *.pdf")}
    if actual_sources != expected_sources:
        raise ValueError(f"source inventory mismatch: missing={expected_sources-actual_sources}, extra={actual_sources-expected_sources}")
    manifest = json.loads((OUTPUT_DIR / "1971_Meghalaya_manifest.json").read_text(encoding="utf-8"))
    review = json.loads((OUTPUT_DIR / "1971_Meghalaya_review.json").read_text(encoding="utf-8"))
    if len(manifest) != 3:
        raise ValueError(f"expected 3 manifest entries, found {len(manifest)}")
    if review != REVIEW_RECORDS:
        raise ValueError("review records differ from the state extraction record")
    seen = set()
    for item in manifest:
        source_name = Path(item["source"]).name
        seen.add((source_name, item["table"]))
        source_reader = PdfReader(str(ROOT / item["source"]), strict=False)
        target_reader = PdfReader(str(ROOT / item["output"]), strict=False)
        if len(target_reader.pages) != len(item["source_pages"]):
            raise ValueError(f"{item['output']}: page count mismatch")
        for source_number, target_page in zip(item["source_pages"], target_reader.pages):
            source_page = source_reader.pages[source_number - 1]
            if box_tuple(source_page.mediabox) != box_tuple(target_page.mediabox) or box_tuple(source_page.cropbox) != box_tuple(target_page.cropbox):
                raise ValueError(f"{item['output']}: page geometry changed on source page {source_number}")
            if int(source_page.get("/Rotate", 0)) != int(target_page.get("/Rotate", 0)):
                raise ValueError(f"{item['output']}: rotation changed on source page {source_number}")
            if "/Contents" not in target_page and "/Resources" not in target_page:
                raise ValueError(f"{item['output']}: page has no content or resources")
    expected_seen = {(source_name, table_key) for source_name, tables in PAGE_MAP.items() for table_key in tables}
    if seen != expected_seen:
        raise ValueError(f"manifest key mismatch: missing={expected_seen-seen}, extra={seen-expected_seen}")
    expected_files = {output_path(Path(source_name).stem.removeprefix("1971 ").strip(), table_key).name for source_name, tables in PAGE_MAP.items() for table_key in tables}
    actual_files = {path.name for path in OUTPUT_DIR.glob("1971_*.pdf")}
    if actual_files != expected_files:
        raise ValueError(f"output file mismatch: missing={expected_files-actual_files}, extra={actual_files-expected_files}")
    print(f"Verified {len(manifest)} Meghalaya PDFs, {sum(item['output_pages'] for item in manifest)} pages, source geometry, rotation, content, manifest, and review records")


if __name__ == "__main__":
    main()
