# 1971 Trimmed PDF State Scripts

This directory contains standalone automation, rendering, verification, and audit scripts for the 1971 District Census Handbook trimmed tables across all Indian states.

> **Path Note**: Scripts are kept in a flat directory to preserve relative path references (`ROOT = Path(__file__).resolve().parents[1]`) that locate `output/pdf/1971_trimmed` and `output/audit/`.

---

## Script Categories

### 1. Verification Scripts (`verify_*.py`)
Validate rendered table outputs, page ranges, and metadata for specific states against the trimmed source tables:
- `verify_andhra_outputs.py` (Andhra Pradesh)
- `verify_arunachal_outputs.py` (Arunachal Pradesh)
- `verify_dadra_nagar_haveli_outputs.py` (Dadra & Nagar Haveli)
- `verify_daman_diu_outputs.py` (Daman & Diu)
- `verify_gujarat_outputs.py` (Gujarat)
- `verify_jammu_kashmir_outputs.py` (Jammu & Kashmir)
- `verify_karnataka_outputs.py` (Karnataka)
- `verify_kerala_outputs.py` (Kerala)
- `verify_madhya_pradesh_outputs.py` (Madhya Pradesh)
- `verify_maharashtra_outputs.py` (Maharashtra)
- `verify_manipur_outputs.py` (Manipur)
- `verify_meghalaya_outputs.py` (Meghalaya)
- `verify_nagaland_outputs.py` (Nagaland)
- `verify_orissa_outputs.py` (Orissa)
- `verify_punjab_outputs.py` (Punjab)
- `verify_rajasthan_outputs.py` (Rajasthan)
- `verify_sikkim_outputs.py` (Sikkim)
- `verify_tamil_nadu_outputs.py` (Tamil Nadu)
- `verify_tripura_outputs.py` (Tripura)
- `verify_west_bengal_outputs.py` (West Bengal)

### 2. Output Rendering Scripts (`render_*.py`)
Render table spans, bounding boxes, or contact sheets from source PDFs for visual QA:
- **Andhra Pradesh**: `make_ap_contact_sheets.py`, `make_ap_last_sheets.py`, `make_ap_next_sheet.py`, `render_ap_next_pages.py`
- **Arunachal Pradesh**: `render_arunachal_outputs.py`
- **Gujarat**: `render_gujarat_candidates.py`, `render_gujarat_extra.py`, `render_gujarat_outputs.py`
- **Jammu & Kashmir**: `render_jammu_kashmir_outputs.py`
- **Karnataka**: `render_karnataka_outputs.py`
- **Kerala**: `render_kerala_outputs.py`, `render_kerala_sources.py`
- **Madhya Pradesh**: `render_madhya_fronts.py`, `render_madhya_pradesh_outputs.py`, `render_madhya_range.py`
- **Maharashtra**: `render_maharashtra_outputs.py`, `render_maharashtra_range.py`
- **Manipur**: `render_manipur_outputs.py`, `render_manipur_range.py`
- **Meghalaya**: `render_meghalaya_outputs.py`, `render_meghalaya_range.py`
- **Nagaland**: `render_nagaland_outputs.py`, `render_nagaland_range.py`
- **Orissa**: `render_orissa_outputs.py`, `render_orissa_range.py`
- **Punjab**: `render_punjab_outputs.py`, `render_punjab_range.py`
- **Rajasthan**: `render_rajasthan_outputs.py`
- **Sikkim**: `render_sikkim_outputs.py`
- **Tamil Nadu**: `render_tamil_nadu_outputs.py`
- **West Bengal**: `render_west_bengal_candidates.py`, `render_west_bengal_outputs.py`

### 3. Auditing, Summaries & Reorganization
Cross-state audit utilities, table-of-contents parsers, and inventory builders:
- `reorganize_1971_trimmed.py`: Standardizes PDF naming and category folder hierarchy (`civic amenities/`, `medical_educational_amenities/`, `tehsil_appendix/`) and writes audit inventory CSVs.
- `render_1971_trim_summary_doc.py`: Generates the national summary docx report from audit data.
- `summarize_gujarat_toc.py`, `summarize_gujarat_table_pages.py`: Gujarat TOC inspection.
- `summarize_rajasthan_toc.py`, `summarize_rajasthan_table_pages.py`, `rajasthan_section_headings.py`, `show_rajasthan_pages.py`: Rajasthan table discovery.
- `summarize_karnataka_spans.py`, `summarize_kerala_spans.py`: Span validation.
- `scan_ap_page_text.py`: Andhra text layer scanner.
- `punjab_contents_full.py`: Punjab TOC reader.
- `maharashtra_statement_candidates.py`: Candidate table discovery for Maharashtra.
- `repair_madhya_guna_appendix.py`: Targeted repair script for Guna district appendix.
- `print_kerala_pages.py`: Page inspection helper.
