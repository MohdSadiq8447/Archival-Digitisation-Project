# 1971 Trimmed PDF Datasets

This document details the organization of the 1971 District Census Handbook trimmed tables and schemas across all 23 states and union territories.

---

## Directory Structure

```text
1971_Trimmed_PDF/
├── Andhra_Pradesh/       # State tables (civic, mededu, tehsil) and schemas/
├── Arunachal_Pradesh/    # State tables and schemas/
├── Bihar/                # State tables and schemas/
├── Dadra_&_Nagar_Haveli/ # Union territory tables and schemas/
├── Daman_&_Diu/          # Union territory tables and schemas/
├── Gujarat/              # State tables and schemas/
├── Haryana/              # State tables and schemas/
├── Jammu_&_Kashmir/      # State tables and schemas/
├── Karnataka/            # State tables and schemas/
├── Kerala/               # State tables and schemas/
├── Madhya_Pradesh/       # State tables and schemas/
├── Maharashtra/          # State tables and schemas/
├── Manipur/              # State tables and schemas/
├── Meghalaya/            # State tables and schemas/
├── Nagaland/             # State tables and schemas/
├── Orissa/               # State tables and schemas/
├── Punjab/               # State tables and schemas/
├── Rajasthan/            # State tables and schemas/
├── Sikkim/               # State tables and schemas/
├── Tamil_Nadu/           # State tables and schemas/
├── Tripura/              # State tables and schemas/
├── Uttar_Pradesh/        # Core pipeline state workspace
│   ├── merged_csvs/      # Final verified merged CSVs (Civic, MedEdu, Tehsils)
│   ├── metadata/         # Authoritative metadata (document.xlsx)
│   ├── notes/            # Historical & error notes
│   ├── outputs/          # Pipeline runs, response cache, and postprocessed runs
│   ├── pdfs/             # 157 trimmed PDF tables
│   ├── postprocessing/   # YAML correction ledgers
│   ├── reports/          # UP verification reports
│   ├── schemas/          # Schema definitions (format_001, 002, 003)
│   ├── scripts/          # 40+ district-specific manual verification scripts
│   └── tools/            # Ledger compilation tools
└── West_Bengal/          # State tables and schemas/
```

---

## Related Locations

- **Audit & Inventories**: Located at root [`audit/`](file:///e:/Archival-Digitisation-Project/audit) (`1971_trimmed_summary.csv`, `1971_trimmed_span_audit.json`, visual check overlays).
- **Processing Scripts**: Located at root [`scripts/`](file:///e:/Archival-Digitisation-Project/scripts) (70+ render, verify, and summary utilities). See [`scripts/README.md`](file:///e:/Archival-Digitisation-Project/scripts/README.md).

---

## State Workspace Organization

1. **Uniform State Structure**:
   - Every state folder contains the trimmed PDF tables organized by category (`civic amenities/`, `mededu/`, `tehsil appendix/`).
   - Every state folder has a `schemas/` directory containing three standardized schema definitions:
     - `format_001.yaml`: Civic and Other Amenities
     - `format_002.yaml`: Medical and Educational Amenities
     - `format_003.yaml`: Tehsil / Taluk Appendix (when historically present)

2. **Uttar Pradesh (`Uttar_Pradesh/`)**:
   - Primary pipeline state containing metadata, extraction pipeline artifacts, and final merged tables in `merged_csvs/`.
