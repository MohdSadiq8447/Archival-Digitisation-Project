from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from extract_madhya_pradesh_tables import OUTPUT_DIR, ROOT, box_tuple, output_path


def main() -> None:
    source_path = ROOT / "1971" / "Madhya Pradesh" / "1971 Guna.pdf"
    source_pages = [169, 170]
    target = output_path("Guna", "tehsil_appendix")
    source_reader = PdfReader(str(source_path), strict=False)
    writer = PdfWriter()
    for number in source_pages:
        writer.add_page(source_reader.pages[number - 1])
    with target.open("wb") as handle:
        writer.write(handle)

    reopened = PdfReader(str(target), strict=False)
    if len(reopened.pages) != len(source_pages):
        raise ValueError("Guna appendix page count mismatch after repair")
    page_sizes = []
    for number, source_page, output_page in zip(source_pages, [source_reader.pages[n - 1] for n in source_pages], reopened.pages):
        if box_tuple(source_page.mediabox) != box_tuple(output_page.mediabox) or box_tuple(source_page.cropbox) != box_tuple(output_page.cropbox):
            raise ValueError(f"Guna appendix geometry mismatch on source page {number}")
        page_sizes.append({"source_page": number, "mediabox": box_tuple(output_page.mediabox), "cropbox": box_tuple(output_page.cropbox)})

    manifest_path = OUTPUT_DIR / "1971_Madhya_Pradesh_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest:
        if entry["source"].replace("\\", "/") == "1971/Madhya Pradesh/1971 Guna.pdf" and entry["table"] == "tehsil_appendix":
            entry["source_pages"] = source_pages
            entry["output_pages"] = len(source_pages)
            entry["page_sizes"] = page_sizes
            break
    else:
        raise ValueError("Guna appendix manifest entry not found")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Repaired {target}")


if __name__ == "__main__":
    main()
