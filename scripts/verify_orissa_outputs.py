from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

from extract_orissa_tables import PAGE_MAP, REVIEW_RECORDS, ROOT, SOURCE_DIR, OUTPUT_DIR, output_path, box_tuple


def main() -> None:
    source_names = {path.name for path in SOURCE_DIR.glob("1971 *.pdf")}
    if source_names != set(PAGE_MAP):
        raise ValueError("source inventory mismatch")
    manifest = json.loads((OUTPUT_DIR / "1971_Orissa_manifest.json").read_text(encoding="utf-8"))
    review = json.loads((OUTPUT_DIR / "1971_Orissa_review.json").read_text(encoding="utf-8"))
    if len(manifest) != 3 or review != REVIEW_RECORDS:
        raise ValueError("manifest/review mismatch")
    seen = set()
    for item in manifest:
        source_name = Path(item["source"]).name
        seen.add((source_name, item["table"]))
        source_reader = PdfReader(str(ROOT / item["source"]), strict=False)
        target_reader = PdfReader(str(ROOT / item["output"]), strict=False)
        if len(target_reader.pages) != len(item["source_pages"]):
            raise ValueError(f"{item['output']}: page count mismatch")
        for number, target_page in zip(item["source_pages"], target_reader.pages):
            source_page = source_reader.pages[number - 1]
            if box_tuple(source_page.mediabox) != box_tuple(target_page.mediabox) or box_tuple(source_page.cropbox) != box_tuple(target_page.cropbox):
                raise ValueError(f"{item['output']}: page geometry changed")
            if int(source_page.get("/Rotate", 0)) != int(target_page.get("/Rotate", 0)):
                raise ValueError(f"{item['output']}: rotation changed")
            if "/Contents" not in target_page and "/Resources" not in target_page:
                raise ValueError(f"{item['output']}: page has no content/resources")
    expected_seen = {(source_name, key) for source_name, tables in PAGE_MAP.items() for key in tables}
    if seen != expected_seen:
        raise ValueError("manifest key mismatch")
    expected_files = {output_path(Path(name).stem.removeprefix("1971 ").strip(), key).name for name, tables in PAGE_MAP.items() for key in tables}
    actual_files = {path.name for path in OUTPUT_DIR.glob("1971_*.pdf")}
    if actual_files != expected_files:
        raise ValueError(f"output file mismatch: missing={expected_files-actual_files}, extra={actual_files-expected_files}")
    print(f"Verified {len(manifest)} Orissa PDFs, {sum(item['output_pages'] for item in manifest)} pages, source geometry, rotation, content, manifest, and review records")


if __name__ == "__main__":
    main()
