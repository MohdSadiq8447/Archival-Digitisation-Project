from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

from extract_jammu_kashmir_tables import DISTRICTS, OUTPUT_DIR, ROOT, SOURCE_DIR, TABLE_SUFFIX, box_tuple, output_path


def main() -> None:
    manifest = json.loads((OUTPUT_DIR / "1971_Jammu_and_Kashmir_manifest.json").read_text(encoding="utf-8"))
    review = json.loads((OUTPUT_DIR / "1971_Jammu_and_Kashmir_review.json").read_text(encoding="utf-8"))
    expected_count = len(DISTRICTS) * len(TABLE_SUFFIX)
    if len(manifest) != expected_count or review != []:
        raise ValueError("Jammu & Kashmir manifest/review record mismatch")

    seen: set[tuple[str, str]] = set()
    for item in manifest:
        district = str(item["district"])
        table = str(item["table"])
        seen.add((district, table))
        source = PdfReader(str(ROOT / item["source"]), strict=False)
        target = PdfReader(str(ROOT / item["output"]), strict=False)
        pages = [int(value) for value in item["source_pages"]]
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

    expected_pairs = {(district, table) for district in DISTRICTS for table in TABLE_SUFFIX}
    if seen != expected_pairs:
        raise ValueError(f"table mismatch: missing={expected_pairs - seen}, extra={seen - expected_pairs}")
    expected_files = {output_path(district, table).name for district in DISTRICTS for table in TABLE_SUFFIX}
    actual_files = {path.name for path in OUTPUT_DIR.glob("1971_*.pdf")}
    if actual_files != expected_files:
        raise ValueError(f"output mismatch: missing={expected_files - actual_files}, extra={actual_files - expected_files}")
    print(
        f"Verified {len(manifest)} Jammu & Kashmir PDFs, "
        f"{sum(item['output_pages'] for item in manifest)} pages, source geometry, rotation, content, manifest, and review records"
    )


if __name__ == "__main__":
    main()
