from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

from extract_dadra_nagar_haveli_tables import PAGE_MAP, ROOT, SOURCE_DIR, OUTPUT_DIR, SOURCE_NAME, box_tuple, output_path


def main() -> None:
    manifest = json.loads((OUTPUT_DIR / "1971_Dadra_and_Nagar_Haveli_manifest.json").read_text(encoding="utf-8"))
    review = json.loads((OUTPUT_DIR / "1971_Dadra_and_Nagar_Haveli_review.json").read_text(encoding="utf-8"))
    if len(manifest) != 3 or len(review) != 2:
        raise ValueError("Dadra & Nagar Haveli manifest/review count mismatch")
    source = PdfReader(str(SOURCE_DIR / SOURCE_NAME), strict=False)
    for item in manifest:
        target = PdfReader(str(ROOT / item["output"]), strict=False)
        for source_number, output_page in zip(item["source_pages"], target.pages):
            source_page = source.pages[source_number - 1]
            if box_tuple(source_page.mediabox) != box_tuple(output_page.mediabox) or box_tuple(source_page.cropbox) != box_tuple(output_page.cropbox):
                raise ValueError(f"{Path(item['output']).name}: geometry changed")
            if int(source_page.get("/Rotate", 0)) != int(output_page.get("/Rotate", 0)):
                raise ValueError(f"{Path(item['output']).name}: rotation changed")
            if not (output_page.extract_text() or "").strip():
                raise ValueError(f"{Path(item['output']).name}: unreadable page")
    expected = {output_path(key).name for key in PAGE_MAP}
    actual = {p.name for p in OUTPUT_DIR.glob("1971_*.pdf")}
    if actual != expected:
        raise ValueError(f"output mismatch: missing={expected-actual}, extra={actual-expected}")
    print(f"Verified {len(manifest)} Dadra & Nagar Haveli PDFs, {sum(item['output_pages'] for item in manifest)} pages, source geometry, rotation, content, manifest, and review records")


if __name__ == "__main__":
    main()
