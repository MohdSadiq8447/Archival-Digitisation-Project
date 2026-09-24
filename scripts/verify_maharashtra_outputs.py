from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

from extract_maharashtra_tables import PAGE_MAP, REVIEW_RECORDS, ROOT, SOURCE_DIR, OUTPUT_DIR, output_path, box_tuple


def main() -> None:
    source_names = {path.name for path in SOURCE_DIR.glob("1971 *.pdf")}
    source_names.add("44875_1971_AUR.pdf")
    expected_sources = set(PAGE_MAP) | {"1971 Greater Maharashtra.pdf"}
    if source_names != expected_sources:
        raise ValueError(f"source inventory mismatch: missing={expected_sources-source_names}, extra={source_names-expected_sources}")

    manifest_path = OUTPUT_DIR / "1971_Maharashtra_manifest.json"
    review_path = OUTPUT_DIR / "1971_Maharashtra_review.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if len(manifest) != 50:
        raise ValueError(f"expected 50 manifest entries, found {len(manifest)}")
    if review != REVIEW_RECORDS:
        raise ValueError("review records differ from the state extraction record")

    seen = set()
    for item in manifest:
        key = (item["source"].split("\\")[-1], item["table"])
        seen.add(key)
        source_path = ROOT / item["source"]
        target_path = ROOT / item["output"]
        if not source_path.exists() or not target_path.exists():
            raise ValueError(f"missing source or output: {item}")
        source_reader = PdfReader(str(source_path), strict=False)
        target_reader = PdfReader(str(target_path), strict=False)
        expected_pages = item["source_pages"]
        if len(target_reader.pages) != len(expected_pages):
            raise ValueError(f"{target_path.name}: page count mismatch")
        for source_page_number, source_page, target_page in zip(expected_pages, (source_reader.pages[i-1] for i in expected_pages), target_reader.pages):
            if box_tuple(source_page.mediabox) != box_tuple(target_page.mediabox):
                raise ValueError(f"{target_path.name}: media box changed")
            if box_tuple(source_page.cropbox) != box_tuple(target_page.cropbox):
                raise ValueError(f"{target_path.name}: crop box changed on page {source_page_number}")
            if int(source_page.get("/Rotate", 0)) != int(target_page.get("/Rotate", 0)):
                raise ValueError(f"{target_path.name}: rotation changed on page {source_page_number}")
            # Scanned source pages may expose an empty-looking decoded content
            # stream through pypdf while still carrying the actual page image
            # in /Resources. Require the page content/resources objects to be
            # present rather than treating get_contents() as a text test.
            if "/Contents" not in target_page and "/Resources" not in target_page:
                raise ValueError(f"{target_path.name}: page has no content or resources on page {source_page_number}")

    expected_seen = {(name, table) for name in PAGE_MAP for table in PAGE_MAP[name]}
    if seen != expected_seen:
        raise ValueError(f"manifest key mismatch: missing={expected_seen-seen}, extra={seen-expected_seen}")
    expected_files = {output_path(("Aurangabad" if name == "44875_1971_AUR.pdf" else name.removeprefix("1971 ").removesuffix(".pdf")), table).name for name in PAGE_MAP for table in PAGE_MAP[name]}
    actual_files = {path.name for path in OUTPUT_DIR.glob("1971_*.pdf")}
    if actual_files != expected_files:
        raise ValueError(f"output file mismatch: missing={expected_files-actual_files}, extra={actual_files-expected_files}")
    print(f"Verified {len(manifest)} Maharashtra PDFs, {sum(item['output_pages'] for item in manifest)} pages, source geometry, rotation, content, manifest, and review records")


if __name__ == "__main__":
    main()
