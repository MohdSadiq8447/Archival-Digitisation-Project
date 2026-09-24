import json
from pathlib import Path
from pypdf import PdfReader, PdfWriter

ROOT = Path("F:/1971-20260725T134344Z-1-001")
SOURCE_DIR = ROOT / "1971" / "Gujarat"
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Gujarat"

PAGE_MAP = {
    "Ahmadabad": {"civic_amenities": [55, 56], "medical_educational_amenities": [57, 58], "tehsil_appendix": [121, 122]},
    "Amreli": {"civic_amenities": [49], "medical_educational_amenities": [50], "tehsil_appendix": [129, 130]},
    "Banas Kantha": {"civic_amenities": [55], "medical_educational_amenities": [56], "tehsil_appendix": [193, 194]},
    "Bharuch": {"civic_amenities": [55], "medical_educational_amenities": [56], "tehsil_appendix": [167, 168]},
    "Bhavnagar": {"civic_amenities": [52], "medical_educational_amenities": [53, 54], "tehsil_appendix": [151, 152]},
    "Gandhinagar": {"civic_amenities": [37], "medical_educational_amenities": [38], "tehsil_appendix": [49, 50]},
    "Jamnagar": {"civic_amenities": [51], "medical_educational_amenities": [52], "tehsil_appendix": [139, 140]},
    "Kheda": {"civic_amenities": [52, 53], "medical_educational_amenities": [54, 55], "tehsil_appendix": [135, 136]},
    "Kutch": {"civic_amenities": [53], "medical_educational_amenities": [54], "tehsil_appendix": [169, 170]},
    "Mahesana": {"civic_amenities": [54], "medical_educational_amenities": [55], "tehsil_appendix": [161, 162]},
    "Panch Mahals": {"civic_amenities": [65], "medical_educational_amenities": [66], "tehsil_appendix": [241]},
    "Rajkot": {"civic_amenities": [55], "medical_educational_amenities": [56], "tehsil_appendix": [167, 168]},
    "Sabar Kantha": {"civic_amenities": [57], "medical_educational_amenities": [58], "tehsil_appendix": [191, 192]},
    "Surat": {"civic_amenities": [63], "medical_educational_amenities": [64], "tehsil_appendix": [209, 210]},
    "Surendranagar": {"civic_amenities": [49], "medical_educational_amenities": [50], "tehsil_appendix": [131, 132]},
    "Vadodara": {"civic_amenities": [56], "medical_educational_amenities": [57], "tehsil_appendix": [210, 211]},
    "Valsad": {"civic_amenities": [52], "medical_educational_amenities": [53], "tehsil_appendix": [141, 142]},
}

SUFFIX = {
    "civic_amenities": "civic_amenities",
    "medical_educational_amenities": "medical_educational_amenities",
    "tehsil_appendix": "tehsil_appendix",
}

source_files = {p.stem.removeprefix("1971 "): p for p in SOURCE_DIR.glob("1971 *.pdf")}
# The replacement Dangs file is a numbered Town Directory publication rather
# than a file using the normal `1971 <district>.pdf` name.  It is the only
# current source for The Dangs; the removed/old source must not be reused.
source_files["The Dangs"] = SOURCE_DIR / "39986_1971_TD.pdf"
expected_source_names = {
    "Ahmadabad", "Amreli", "Banas Kantha", "Bharuch", "Bhavnagar", "Gandhinagar", "Jamnagar", "Junagadh", "Kheda", "Kutch", "Mahesana", "Panch Mahals", "Rajkot", "Sabar Kantha", "Surat", "Surendranagar", "The Dangs", "Vadodara", "Valsad"
}
assert set(source_files) == expected_source_names, (set(source_files) ^ expected_source_names)
assert source_files["The Dangs"].exists(), source_files["The Dangs"]
assert "Junagadh" not in PAGE_MAP, "Junagadh is the Part C full-count volume, not a Town/Village Directory volume"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
written = []
review = []
for district, tables in PAGE_MAP.items():
    source_path = source_files[district]
    reader = PdfReader(str(source_path))
    for table_kind, page_numbers in tables.items():
        assert page_numbers == sorted(set(page_numbers)), (district, table_kind, page_numbers)
        assert all(1 <= page <= len(reader.pages) for page in page_numbers), (district, table_kind, page_numbers, len(reader.pages))
        writer = PdfWriter()
        for page_number in page_numbers:
            writer.add_page(reader.pages[page_number - 1])
        output_path = OUTPUT_DIR / f"1971_{district.replace(' ', '_')}_{SUFFIX[table_kind]}.pdf"
        with output_path.open("wb") as handle:
            writer.write(handle)
        check = PdfReader(str(output_path))
        assert len(check.pages) == len(page_numbers), (output_path, len(check.pages), page_numbers)
        for out_page, source_page_number in zip(check.pages, page_numbers):
            src_page = reader.pages[source_page_number - 1]
            src_box = tuple(float(v) for v in src_page.mediabox)
            out_box = tuple(float(v) for v in out_page.mediabox)
            assert src_box == out_box, (output_path, src_box, out_box)
        written.append(output_path)

for table_kind in SUFFIX:
    review.append(
        {
            "source": source_files["Junagadh"].name,
            "table": table_kind,
            "status": "review",
            "reason": "The supplied Junagadh volume is the 1971 Part C full-count/statistical publication; the requested Town Directory Statement IV/V and equivalent tehsil/taluk amenities appendix are absent.",
        }
    )
    review.append(
        {
            "source": source_files["The Dangs"].name,
            "table": table_kind,
            "status": "review",
            "reason": "The replacement Dangs source is the Gujarat Town Directory (Part VIA), not a district Part X-A/B Town/Village Directory volume; it states that The Dangs has no urban area and contains no district Statement IV/V or equivalent tehsil/taluk amenities appendix.",
        }
    )

assert len(written) == 51, len(written)
assert len(review) == 6, len(review)
(OUTPUT_DIR / "1971_Gujarat_manifest.json").write_text(json.dumps([], indent=2), encoding="utf-8")
(OUTPUT_DIR / "1971_Gujarat_review.json").write_text(json.dumps(review, indent=2), encoding="utf-8")
print(f"Wrote {len(written)} Gujarat table PDFs for {len(PAGE_MAP)} directory volumes.")
print("Excluded Junagadh: Part C full-count/statistical volume; no requested tables present.")
print("Excluded The Dangs: replacement numbered Town Directory publication has no requested district tables or equivalent appendix.")
