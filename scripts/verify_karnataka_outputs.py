from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

from extract_karnataka_tables import OUTPUT_DIR, PAGE_MAP, ROOT, output_path


def box_tuple(box) -> tuple[float, float, float, float]:
    return tuple(round(float(value), 6) for value in box)


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00ad", " ")).strip().lower()


def main() -> None:
    manifest_path = OUTPUT_DIR / "1971_Karnataka_manifest.json"
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
    if len(manifest) != 51:
        raise ValueError(f"manifest has {len(manifest)} entries, expected 51")

    checks = 0
    for source_name, tables in PAGE_MAP.items():
        source_path = ROOT / "1971" / "Karnataka" / source_name
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

            first_text = normalized(output_reader.pages[0].extract_text() or "")
            last_text = normalized(output_reader.pages[-1].extract_text() or "")
            if table_key == "civic_amenities":
                if "civ" not in first_text and "ciy" not in first_text:
                    raise ValueError(f"{target.name}: first page does not identify Civic and Other Amenities")
            elif table_key == "medical_educational_amenities":
                if "medical" not in first_text or "educ" not in first_text:
                    raise ValueError(f"{target.name}: first page does not identify Medical/Educational facilities")
            else:
                if "appendix" not in first_text and "educ" not in first_text and "medical" not in first_text:
                    raise ValueError(f"{target.name}: first page does not identify the amenities appendix")
                if "educ" not in first_text + " " + last_text and "medical" not in first_text + " " + last_text:
                    raise ValueError(f"{target.name}: appendix text does not identify educational/medical amenities")
                if "land use particulars" in last_text and not any(token in last_text for token in ("medical", "amenit", "educ")):
                    raise ValueError(f"{target.name}: last page is land-use material, not amenities")
            checks += 1

    print(f"Verified {checks} Karnataka PDFs: counts, MediaBox/CropBox, table identifiers, and appendix boundaries")


if __name__ == "__main__":
    main()
