# 1981 Trimmed PDF Datasets

This document details the organization of the 1981 District Census Handbook trimmed tables and schemas across all 22 states and union territories.

---

## Directory Structure

```text
1981_Trimmed_PDF/
├── Andhra_Pradesh/       # State tables (civic, mededu, tehsil) & schemas/pdf_formats.yaml
├── Arunachal_Pradesh/    # State tables & schemas/pdf_formats.yaml
├── Bihar/                # State tables & schemas/pdf_formats.yaml
├── Dadra_&_Nagar_Haveli/ # Union territory tables & schemas/pdf_formats.yaml
├── Daman_&_Diu/          # Union territory tables & schemas/pdf_formats.yaml
├── Gujarat/              # State tables & schemas/pdf_formats.yaml
├── Jammu_&_Kashmir/      # State tables & schemas/pdf_formats.yaml
├── Karnataka/            # State tables & schemas/pdf_formats.yaml
├── Kerala/               # State tables & schemas/pdf_formats.yaml
├── Madhya_Pradesh/       # State tables & schemas/pdf_formats.yaml
├── Maharashtra/          # State tables & schemas/pdf_formats.yaml
├── Manipur/              # State tables & schemas/pdf_formats.yaml
├── Meghalaya/            # State tables & schemas/pdf_formats.yaml
├── Mizoram/              # State tables & schemas/pdf_formats.yaml
├── Nagaland/             # State tables & schemas/pdf_formats.yaml
├── Orissa/               # State tables & schemas/pdf_formats.yaml
├── Punjab/               # State tables & schemas/pdf_formats.yaml
├── Rajasthan/            # State tables & schemas/pdf_formats.yaml
├── Sikkim/               # State tables & schemas/pdf_formats.yaml
├── Tamil_Nadu/           # State tables & schemas/pdf_formats.yaml
├── Uttar_Pradesh/        # State tables & schemas/pdf_formats.yaml
└── West_Bengal/          # State tables & schemas/pdf_formats.yaml
```

---

## Related Locations

- **Audit & Results**: Located at root [`audit/`](file:///e:/Archival-Digitisation-Project/audit) (all `1981_<State>_results.csv`, `1981_<State>_results.json`, inventories, and summary docx files).
- **Processing Scripts**: Located at root [`scripts/`](file:///e:/Archival-Digitisation-Project/scripts) (`1981_trim.py`, `generate_1981_schemas.py`, etc.).
- **Helper & Diagnostic Scripts**: Located at [`scripts/1981_helpers/`](file:///e:/Archival-Digitisation-Project/scripts/1981_helpers) (state-specific header fixes and column extraction helpers).
- **Diagnostic Crops & Temp Artifacts**: Consolidated into [`scratch/1981_debug_crops/`](file:///e:/Archival-Digitisation-Project/scratch/1981_debug_crops) and [`scratch/1981_tmp/`](file:///e:/Archival-Digitisation-Project/scratch/1981_tmp) (gitignored).

---

## State Workspace Organization

1. **Uniform State Hierarchy**:
   - Each state folder contains trimmed tables sorted into standard category directories:
     - `civic amenities/`
     - `mededu/`
     - `tehsil appendix/`
   - Each state folder contains a dedicated `schemas/` directory with three split format definitions:
     - `format_001.yaml`: Civic and Other Amenities
     - `format_002.yaml`: Medical and Educational Amenities
     - `format_003.yaml`: Tehsil / Taluk Appendix
