from pathlib import Path
from pypdf import PdfReader

ROOT = Path("F:/1971-20260725T134344Z-1-001")
SRC = ROOT / "1971" / "Gujarat"
OUT = ROOT / "output" / "pdf" / "1971_trimmed" / "Gujarat"
EXPECTED = {
    "1971_Ahmadabad_civic_amenities.pdf": 2, "1971_Ahmadabad_medical_educational_amenities.pdf": 2, "1971_Ahmadabad_tehsil_appendix.pdf": 2,
    "1971_Amreli_civic_amenities.pdf": 1, "1971_Amreli_medical_educational_amenities.pdf": 1, "1971_Amreli_tehsil_appendix.pdf": 2,
    "1971_Banas_Kantha_civic_amenities.pdf": 1, "1971_Banas_Kantha_medical_educational_amenities.pdf": 1, "1971_Banas_Kantha_tehsil_appendix.pdf": 2,
    "1971_Bharuch_civic_amenities.pdf": 1, "1971_Bharuch_medical_educational_amenities.pdf": 1, "1971_Bharuch_tehsil_appendix.pdf": 2,
    "1971_Bhavnagar_civic_amenities.pdf": 1, "1971_Bhavnagar_medical_educational_amenities.pdf": 2, "1971_Bhavnagar_tehsil_appendix.pdf": 2,
    "1971_Gandhinagar_civic_amenities.pdf": 1, "1971_Gandhinagar_medical_educational_amenities.pdf": 1, "1971_Gandhinagar_tehsil_appendix.pdf": 2,
    "1971_Jamnagar_civic_amenities.pdf": 1, "1971_Jamnagar_medical_educational_amenities.pdf": 1, "1971_Jamnagar_tehsil_appendix.pdf": 2,
    "1971_Kheda_civic_amenities.pdf": 2, "1971_Kheda_medical_educational_amenities.pdf": 2, "1971_Kheda_tehsil_appendix.pdf": 2,
    "1971_Kutch_civic_amenities.pdf": 1, "1971_Kutch_medical_educational_amenities.pdf": 1, "1971_Kutch_tehsil_appendix.pdf": 2,
    "1971_Mahesana_civic_amenities.pdf": 1, "1971_Mahesana_medical_educational_amenities.pdf": 1, "1971_Mahesana_tehsil_appendix.pdf": 2,
    "1971_Panch_Mahals_civic_amenities.pdf": 1, "1971_Panch_Mahals_medical_educational_amenities.pdf": 1, "1971_Panch_Mahals_tehsil_appendix.pdf": 1,
    "1971_Rajkot_civic_amenities.pdf": 1, "1971_Rajkot_medical_educational_amenities.pdf": 1, "1971_Rajkot_tehsil_appendix.pdf": 2,
    "1971_Sabar_Kantha_civic_amenities.pdf": 1, "1971_Sabar_Kantha_medical_educational_amenities.pdf": 1, "1971_Sabar_Kantha_tehsil_appendix.pdf": 2,
    "1971_Surat_civic_amenities.pdf": 1, "1971_Surat_medical_educational_amenities.pdf": 1, "1971_Surat_tehsil_appendix.pdf": 2,
    "1971_Surendranagar_civic_amenities.pdf": 1, "1971_Surendranagar_medical_educational_amenities.pdf": 1, "1971_Surendranagar_tehsil_appendix.pdf": 2,
    "1971_Vadodara_civic_amenities.pdf": 1, "1971_Vadodara_medical_educational_amenities.pdf": 1, "1971_Vadodara_tehsil_appendix.pdf": 2,
    "1971_Valsad_civic_amenities.pdf": 1, "1971_Valsad_medical_educational_amenities.pdf": 1, "1971_Valsad_tehsil_appendix.pdf": 2,
}

actual = {p.name for p in OUT.glob("*.pdf")}
assert actual == set(EXPECTED), (actual ^ set(EXPECTED))
total_pages = 0
for name, expected_pages in sorted(EXPECTED.items()):
    reader = PdfReader(str(OUT / name))
    assert len(reader.pages) == expected_pages, (name, len(reader.pages), expected_pages)
    for page_no, page in enumerate(reader.pages, 1):
        assert page.mediabox.width > 0 and page.mediabox.height > 0, (name, page_no)
        assert page.cropbox.width > 0 and page.cropbox.height > 0, (name, page_no, "invalid cropbox")
    total_pages += len(reader.pages)
print(f"Verified {len(actual)} Gujarat PDFs and {total_pages} output pages; all counts, boxes, and readable page objects are valid.")
