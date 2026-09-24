from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

from extract_tripura_tables import PAGE_MAP, ROOT, SOURCE_DIR, OUTPUT_DIR, SOURCE_NAME, box_tuple, output_path


def main() -> None:
    manifest = json.loads((OUTPUT_DIR / "1971_Tripura_manifest.json").read_text(encoding="utf-8"))
    review = json.loads((OUTPUT_DIR / "1971_Tripura_review.json").read_text(encoding="utf-8"))
    if len(manifest) != 3 or review != []:
        raise ValueError("Tripura manifest/review record mismatch")
    source = PdfReader(str(SOURCE_DIR / SOURCE_NAME), strict=False)
    seen = set()
    for item in manifest:
        seen.add(item["table"])
        target = PdfReader(str(ROOT / item["output"]), strict=False)
        pages = item["source_pages"]
        if len(target.pages) != len(pages):
            raise ValueError(f"{Path(item['output']).name}: page count mismatch")
        for source_number, output_page in zip(pages, target.pages):
            source_page = source.pages[source_number - 1]
            if box_tuple(source_page.mediabox) != box_tuple(output_page.mediabox):
                raise ValueError(f"{Path(item['output']).name}: media box changed")
            if box_tuple(source_page.cropbox) != box_tuple(output_page.cropbox):
                raise ValueError(f"{Path(item['output']).name}: crop box changed")
            if int(source_page.get("/Rotate", 0)) != int(output_page.get("/Rotate", 0)):
                raise ValueError(f"{Path(item['output']).name}: rotation changed")
            if "/Contents" not in output_page and "/Resources" not in output_page:
                raise ValueError(f"{Path(item['output']).name}: missing content")
            if not (output_page.extract_text() or "").strip():
                raise ValueError(f"{Path(item['output']).name}: missing readable text")
    if seen != set(PAGE_MAP):
        raise ValueError(f"table mismatch: {seen}")
    expected_files = {output_path(key).name for key in PAGE_MAP}
    actual_files = {path.name for path in OUTPUT_DIR.glob("1971_*.pdf")}
    if actual_files != expected_files:
        raise ValueError(f"output mismatch: missing={expected_files-actual_files}, extra={actual_files-expected_files}")
    print(f"Verified {len(manifest)} Tripura PDFs, {sum(item['output_pages'] for item in manifest)} pages, source geometry, rotation, content, manifest, and review records")


if __name__ == "__main__":
    main()
