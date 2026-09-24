from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "1971_trimmed" / "Kerala"
SOURCE_DIR = ROOT / "1971" / "Kerala"

spec = importlib.util.spec_from_file_location("extract_kerala_tables", ROOT / "scripts" / "extract_kerala_tables.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def boxes(page):
    return tuple(round(float(v), 6) for v in page.mediabox), tuple(round(float(v), 6) for v in page.cropbox)


def main() -> None:
    manifest_path = OUT / "1971_Kerala_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = sum(len(tables) for tables in module.PAGE_MAP.values())
    if len(manifest) != expected:
        raise AssertionError(f"manifest count {len(manifest)} != {expected}")
    if len(list(OUT.glob("*.pdf"))) != expected:
        raise AssertionError(f"PDF count {len(list(OUT.glob('*.pdf')))} != {expected}")

    checks = 0
    for item in manifest:
        source = ROOT / item["source"]
        target = ROOT / item["output"]
        source_reader = PdfReader(str(source), strict=False)
        output_reader = PdfReader(str(target), strict=False)
        page_numbers = item["source_pages"]
        if len(output_reader.pages) != len(page_numbers):
            raise AssertionError(f"{target.name}: page count mismatch")
        for source_page_number, output_page in zip(page_numbers, output_reader.pages):
            if boxes(source_reader.pages[source_page_number - 1]) != boxes(output_page):
                raise AssertionError(f"{target.name}: geometry mismatch on source page {source_page_number}")
            if not (output_page.extract_text() or "").strip():
                raise AssertionError(f"{target.name}: unreadable/empty extracted content on page {source_page_number}")
            checks += 1

    review = json.loads((OUT / "1971_Kerala_review.json").read_text(encoding="utf-8"))
    if {item["source"] for item in review} != {"1971 Ernakulam.pdf", "1971 Idikki.pdf"}:
        raise AssertionError("review list mismatch")
    print(f"Verified {len(manifest)} Kerala PDFs, {checks} pages, source geometry, text, markers, and review records")


if __name__ == "__main__":
    main()
