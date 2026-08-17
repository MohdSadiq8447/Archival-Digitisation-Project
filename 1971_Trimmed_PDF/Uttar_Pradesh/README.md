# Census Table Extraction Pipeline — Schema Stage

This directory captures the **schema-definition stage** of the Uttar Pradesh
1971 District Census Handbook table-extraction pipeline. It describes *what*
each table means and *where* it lives, so a later OCR/vision stage can read it
automatically. No OCR or API calls have been run yet.

## Coverage

Full English-language UP 1971 archive: **53 districts, 157 tables**
(53 × 3 formats, minus two missing tahsil appendices). Four Hindi-language
volumes are excluded (see "Known anomalies").

## Folder layout

```
census_extraction/
├── pdfs/                157 trimmed PDFs (one logical table per PDF, 2 pages)
├── metadata/
│   ├── documents.csv    one row per PDF (157 rows)
│   └── tables.csv       one row per logical table (157 rows)
├── schemas/             one YAML per table format
├── outputs/             reserved for the future OCR stage
└── notes/               reserved for working notes
```

## How the files relate

| File | Answers |
|------|---------|
| `metadata/documents.csv` | which PDFs exist (one row per trimmed PDF) |
| `metadata/tables.csv`     | where each logical table is located (anchor/continuation page) |
| `schemas/format_XXX.yaml` | what that table format means (columns, types, structure) |
| `pdf_listing.csv`         | flat human-readable listing of all 53 districts |

Each trimmed PDF is one logical table: page 1 is the **anchor page** (row
identities + first block of columns) and page 2 is the **continuation page**
(remaining columns for the same rows). This is the "column continuation"
structure described in the setup instructions.

## Table formats

Three recurring formats cover every district (structure is identical across
all 53; only page numbers, row counts, and scan quality differ).

### `format_001` — Civic and Other Amenities (TS-IV / UP1971_CIVIC)
- **Source:** *Town Statement — Civic and Other* (cols 1–8) + *Directory IV —
  Amenities, 1969* (cols 9–16). One row per town.
- **Anchor page (1–8):** Sl. No., Name of Town, Road length (PR/KR), System of
  Sewerage/Drainage, Number of Latrines (Water Borne / Service / Others),
  Method of Disposal of Night-soil.
- **Continuation page (9–16):** Protected Water Supply (Source / Capacity),
  Fire Fighting Service, Electrification (Domestic / Industrial / Commercial /
  Road Lighting / Others).
- **Parent headings:** Number of Latrines (5–7), Protected Water Supply
  (9–10), Electrification (12–16).
- **Row types:** ordinary, urban-agglomeration aggregate, component `(i)(ii)…`,
  and cross-reference ("See … Urban Agglomeration").

### `format_002` — Medical, Educational, Recreational & Cultural (TS-V / UP1971_MEDEDU)
- **Source:** *Town Statement — Medical, Educational, Recreational and*
  (cols 1–9) + *Directory V — Cultural Facilities in Towns, 1969* (cols
  10–17). One row per town.
- **Anchor page (1–9):** Sl. No., Name of Town, Medical Facilities
  (institutions / beds), then Educational columns (colleges, polytechnics,
  vocational institutes).
- **Continuation page (10–17):** schools (Higher Secondary / Junior / Primary /
  Others), then Stadia, Cinemas, Auditoria/Drama Halls, Public Libraries.
- **Parent heading:** Medical Facilities (3–4). EDUCATIONAL and RECREATIONAL &
  CULTURAL are section labels over standalone columns.
- **Row types:** same aggregate/component/cross-reference pattern as
  `format_001`.

### `format_003` — Tahsil-wise Abstract appendix (APP-TAHSIL / UP1971_TEHSIL)
- **Source:** *Appendix — Tahsil-wise Abstract of Educational, Medical and
  Other Amenities*. One row per tahsil, ending with a district-total row.
- **50 columns across six sections:** Educational (3–12), Medical (13–24),
  Power Supply (25–26), Drinking Water (27–38), Communications/Roads (39–42),
  Post & Telegraph (43–50).
- **Important:** the appendix is a two-page spread split into two horizontal
  bands, so columns are **non-contiguous** across pages:
  - Anchor page: 1–2 (identity), 3–12 (Educational), 25–38 (Power Supply +
    Drinking Water).
  - Continuation page: 13–24 (Medical), 39–50 (Communications + Post &
    Telegraph).
  The `printed_column` value in the schema is authoritative, not list order.

## Known anomalies

- **Excluded Hindi volumes.** Four Devanagari-text volumes are skipped by the
  trimmer: `1971 Aajmgrah.pdf`, `1971 Badha.pdf`, `1971 Bhrich.pdf`,
  `1971 Mirzapur (Hindi).pdf`. The 53 districts are the English volumes only.
- **Missing tahsil appendices.** The trimmer could not detect the appendix in
  `1971 Varanasi.pdf` and `1971 Mirzapur.pdf` (volumes appear truncated), so
  there are no `varanasi_tehsil_1971.pdf` / `mirzapur_tehsil_1971.pdf` rows.
- **Compressed handbooks.** In 19 districts the civic and mededu tables fall on
  the *same* source pages: Almora, Chamoli, Deoria, Gonda, Gorakhpur,
  Sultanpur, Bahraich, Baliya, Banda, Etawah, Fatehpur, Hamirpur, Kheri,
  Parthpgad, Peelibhit, Pithoragarh, Rae Bareli, Rampur, Uttar Kashi.
- **Stacked town statements.** In many districts the two-page spread carries
  Statement III (municipal finance) above the civic/mededu table, so the
  trimmed PDF page contains two tables. The extractor must isolate the civic
  (cols 1–8 / 9–16) or mededu (1–9 / 10–17) table and ignore Statement III.
- **Printed page numbers.** Reliable only for the original 20 districts (from
  `pdf_listing.csv`); the 33 newly added districts have blank
  `anchor_printed_page` / `continuation_printed_page` because their OCR
  page-number layer is unreliable. Source (actual) page numbers are always
  present.

## Provenance columns

- `documents.csv` keeps `source_pdf`, `source_page_start`, `source_page_end`
  so each trimmed PDF can be traced back to its page range in the original
  district volume.
- `tables.csv` keeps `anchor_printed_page` / `continuation_printed_page` (the
  printed page numbers on the scans), separate from the 1/2 PDF page indices
  used for extraction.

## District name note

District names are recorded in the scan/filename spelling (e.g. `Parthpgad`,
`Peelibhit`, `Baliya`, `Dehra Dun`, `Uttar Kashi`) to stay traceable to the
source PDFs. Likely canonical spellings: Parthpgad → Pratapgarh, Peelibhit →
Pilibhit, Baliya → Ballia, Dehra Dun → Dehradun, Uttar Kashi → Uttarkashi.
