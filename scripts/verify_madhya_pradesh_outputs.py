from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

from extract_madhya_pradesh_tables import OUTPUT_DIR, PAGE_MAP, ROOT, output_path


def box_tuple(box) -> tuple[float, float, float, float]:
    return tuple(round(float(value), 6) for value in box)


def rotation(page) -> int:
    return int(page.get("/Rotate", 0) or 0)


def page_has_content(page) -> bool:
    contents = page.get("/Contents")
    resources = page.get("/Resources")
    return contents is not None or resources is not None


def main() -> None:
    manifest_path = OUTPUT_DIR / "1971_Madhya_Pradesh_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_outputs = {
        output_path(Path(source_name).stem.removeprefix("1971 ").strip(), table_key).name
        for source_name, tables in PAGE_MAP.items()
        for table_key in tables
    }
    actual_outputs = {path.name for path in OUTPUT_DIR.glob("*.pdf")}
    if actual_outputs != expected_outputs:
        raise ValueError(
            f"output inventory mismatch; missing={sorted(expected_outputs - actual_outputs)}, "
            f"unexpected={sorted(actual_outputs - expected_outputs)}"
        )
    if len(manifest) != 129:
        raise ValueError(f"manifest has {len(manifest)} entries, expected 129")
    manifest_keys = {(entry["source"], entry["table"], tuple(entry["source_pages"])) for entry in manifest}
    expected_manifest_keys = {
        (str(Path("1971") / "Madhya Pradesh" / source_name), table_key, tuple(source_pages))
        for source_name, tables in PAGE_MAP.items()
        for table_key, source_pages in tables.items()
    }
    if manifest_keys != expected_manifest_keys:
        raise ValueError("manifest entries do not match the Madhya Pradesh page map")

    checks = 0
    total_pages = 0
    for source_name, tables in PAGE_MAP.items():
        source_path = ROOT / "1971" / "Madhya Pradesh" / source_name
        source_reader = PdfReader(str(source_path), strict=False)
        district = Path(source_name).stem.removeprefix("1971 ").strip()
        for table_key, source_pages in tables.items():
            target = output_path(district, table_key)
            output_reader = PdfReader(str(target), strict=False)
            if len(output_reader.pages) != len(source_pages):
                raise ValueError(f"{target.name}: page count {len(output_reader.pages)} != {len(source_pages)}")
            for source_number, output_page in zip(source_pages, output_reader.pages):
                source_page = source_reader.pages[source_number - 1]
                if box_tuple(source_page.mediabox) != box_tuple(output_page.mediabox):
                    raise ValueError(f"{target.name}: MediaBox mismatch for source page {source_number}")
                if box_tuple(source_page.cropbox) != box_tuple(output_page.cropbox):
                    raise ValueError(f"{target.name}: CropBox mismatch for source page {source_number}")
                if rotation(source_page) != rotation(output_page):
                    raise ValueError(f"{target.name}: rotation mismatch for source page {source_number}")
                if not page_has_content(output_page):
                    raise ValueError(f"{target.name}: empty page for source page {source_number}")
            checks += 1
            total_pages += len(source_pages)

    print(f"Verified {checks} Madhya Pradesh PDFs, {total_pages} pages, source geometry, rotation, content, and manifest")


if __name__ == "__main__":
    main()
