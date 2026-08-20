# How the Census Extraction Pipeline Works

The pipeline turns each two-page historical census PDF into a validated table. It uses deterministic PDF geometry to decide where rows and columns are, and Novita only to transcribe cropped images.

```text
CLI
 ↓
Authoritative workbook metadata + YAML schema
 ↓
Render and deskew PDF
 ↓
Locate physical panels and printed column numbers
 ↓
Detect anchor rows and align continuation panels
 ↓
Novita OCR on each panel-row crop
 ↓
Assign grounded text boxes to columns
 ↓
Normalize and type values
 ↓
Validate the complete table
 ↓
SUCCESS → clean outputs
QUARANTINED → review outputs
ERROR → manifest failure
```

## 1. Command and run setup

The entry point is [`src/census_extractor/cli.py`](src/census_extractor/cli.py).

Available commands are:

- `process`: process one PDF.
- `batch`: process multiple PDFs.
- `geometry` or `--dry-run`: inspect layout without calling Novita.
- `schemas`: show the registered formats and panels.

A live run requires `NOVITA_API_KEY`. Every run receives a run ID and writes under:

```text
outputs/runs/<run_id>/
```

Batch processing has two concurrency limits:

- `--pdf-workers` controls how many PDFs are prepared concurrently.
- `--concurrency` controls the global number of Novita requests, defaulting to two.

## 2. Authoritative metadata selection

Before reading the PDF, the pipeline looks up its filename in `metadata/document.xlsx`.

The workbook supplies:

- Exact district spelling.
- Format ID.
- Table ID.
- Census year and state.
- Original source pages.
- Printed page numbers.
- Workbook provenance and checksum.

The implementation is in [`src/census_extractor/metadata.py`](src/census_extractor/metadata.py).

If the PDF is absent from the workbook, the pipeline stops with `ERROR`. It does not guess the district or format from the filename.

## 3. Schema and physical-panel selection

The workbook's `format_id` selects one YAML schema:

- `format_001`: civic amenities, 16 logical columns.
- `format_002`: medical and educational facilities, 17 columns.
- `format_003`: tahsil abstract, 50 columns across four physical panels.

Each schema describes:

- Printed column number.
- Column heading.
- Internal variable name.
- Expected data type.
- Historical meaning.
- Possible printed forms and abbreviations.
- Physical page and panel placement.

Schema loading is fail-closed in [`src/census_extractor/schemas.py`](src/census_extractor/schemas.py). An unknown format never silently becomes a civic table.

## 4. PDF rendering and deskewing

The PDF is rendered at 300 DPI by default by [`src/census_extractor/preprocessing/pdf_loader.py`](src/census_extractor/preprocessing/pdf_loader.py).

For every page, it creates:

- A high-resolution colour image.
- Grayscale and binary images for geometry detection.
- Embedded PDF text.
- Embedded word bounding boxes.
- An estimated skew angle.

If the raster is deskewed, the embedded word coordinates are transformed by the same rotation. This keeps the text layer and image pixels synchronized.

Unexpected page counts fail immediately.

## 5. Panel and column detection

The pipeline searches the embedded text layer for printed column-number rows such as:

```text
1 2 3 4 5 6 7 8
```

It compares observed numbers with the schema's expected sequence while checking nearby headings. This distinguishes the requested statement from another table compressed onto the same page.

For example:

- Civic page 1 expects columns 1–8.
- Civic page 2 expects columns 9–16.
- Tahsil page 1 contains two separate panels: 1–12 and 1–2/25–38.

Actual column centres come from the printed numbers. Missing centres can be interpolated between known numbers, but the pipeline does not spread columns evenly across the page as a blind fallback.

This logic is in [`src/census_extractor/geometry/panel_detector.py`](src/census_extractor/geometry/panel_detector.py).

If the embedded text is too corrupted:

- Live mode sends the full page to Novita for grounded text boxes, then retries panel detection.
- Dry-run mode reports the unresolved geometry because it is forbidden from calling Novita.

## 6. Row detection and cross-panel alignment

The schema identifies one anchor panel containing row identities such as serial number plus town or tahsil name.

The pipeline detects horizontal ink bands inside that panel's body. If table ruling overwhelms the raster projection, it falls back to bands made from embedded PDF words.

Titles, printed column-number rows, footnotes, and later page sections are outside the detected table body or removed after conspicuous section gaps.

Continuation-panel rows are then matched to anchor rows using their normalized vertical positions:

- Equal counts are paired in order.
- Unequal counts use monotonic sequence alignment.
- If matching remains incomplete, anchor row bands are projected affinely onto the continuation panel.

The result is one shared logical row index across every physical panel. See [`src/census_extractor/geometry/row_segmenter.py`](src/census_extractor/geometry/row_segmenter.py) and [`src/census_extractor/geometry/aligner.py`](src/census_extractor/geometry/aligner.py).

## 7. Novita row OCR

Every detected row is cropped separately for each physical panel.

The prompt includes:

- Novita's grounding preset.
- Historical-table description.
- Schema and panel name.
- Expected columns in left-to-right order.
- Column types, descriptions, and example printed forms.
- Instructions to transcribe only visible text.

The request uses:

```text
model: deepseek/deepseek-ocr-2
temperature: 0
top_k: 0
max_tokens: 2048
```

Novita returns text with `<|ref|>` tokens and `<|det|>` bounding boxes using a 0–1000 coordinate system.

Prompt construction is in [`src/census_extractor/ocr/prompts.py`](src/census_extractor/ocr/prompts.py), and the HTTP integration is in [`src/census_extractor/ocr/client.py`](src/census_extractor/ocr/client.py).

For a civic table with 21 rows, the normal first pass is approximately:

```text
21 rows × 2 panels = 42 row OCR requests
```

A tahsil table uses four panel-row requests per logical row.

## 8. Bounding-box column assignment

The 0–1000 Novita boxes are scaled back into the row crop's pixel coordinates.

The horizontal centre of each token determines which detected physical column contains it. Tokens within a column are joined left-to-right.

There is deliberately no "first OCR value goes into first column" fallback. A token without trustworthy geometry is not silently shifted into a neighbouring field.

This happens in [`src/census_extractor/ocr/column_assigner.py`](src/census_extractor/ocr/column_assigner.py).

## 9. Cell-level fallback

If grounded row OCR has no usable boxes, the pipeline does not discard the table. It crops each affected cell separately, adds padding, doubles the resolution, and retries with:

```text
Free OCR.
```

The retry prompt includes that particular column's:

- Name.
- Variable.
- Data type.
- Description.
- Possible historical notation.

After initial validation, only cells implicated in missing identity, parsing, or OCR-completeness failures are retried again.

## 10. Caching and network retries

Every OCR request is cached using:

- PDF checksum.
- Crop coordinates.
- Crop PNG checksum.
- Model.
- Exact prompt.
- Prompt version.
- Page and panel.

The cached directory contains both the crop PNG and successful raw response. Changing the schema prompt invalidates the cache.

The client retries:

- HTTP 429.
- Timeouts and network failures.
- HTTP 5xx.

It honours `Retry-After`; otherwise, it uses exponential backoff with jitter. Transient failures are never cached.

`--resume` reopens the existing manifest and uses cached OCR results for identical crops. It reruns deterministic geometry; it does not currently skip every PDF already recorded in the manifest.

## 11. Normalization

The exact OCR transcription remains in the audit output. A separate clean representation is created in [`src/census_extractor/normalization.py`](src/census_extractor/normalization.py).

Normalization includes:

- `Nil`, blanks, dashes and ellipses → null.
- Integer columns → nullable integers.
- Numeric OCR `O`/`o` corrections when parsing numeric fields.
- Civic `PR` and `KR` road lengths → derived pucca/kutcha kilometre fields.
- Classification of ordinary, aggregate, component, total and cross-reference rows.
- Cross-reference targets retained while their data cells are cleared.

The archival spelling is not modernized.

## 12. Validation and status decision

Validation checks:

- Every required panel was found.
- Every panel has the same logical row count.
- OCR returned usable results.
- Required identity fields are present.
- Values match declared types.
- Serial numbers progress correctly.
- Ordinary identities are not duplicated.
- Counts are nonnegative.
- Cross-reference rows contain no ordinary data.
- Rows and columns are not completely empty.
- Tahsil district totals equal contributing rows when all values are numeric.

Quality is weighted:

```text
30% geometry
35% OCR
15% parsing
20% semantics
```

A table receives `SUCCESS` only when:

- All required panels are present.
- Row alignment is complete.
- There are no error-level findings.
- Overall quality is at least 0.95.

Otherwise, it is `QUARANTINED`, not placed in clean output. Validation is implemented in [`src/census_extractor/validation/validator.py`](src/census_extractor/validation/validator.py).

## 13. Outputs and audit trail

Successful tables go to `clean`; reviewable failures go to `quarantine`.

Each table receives:

- Typed CSV.
- Typed Parquet.
- Typed JSONL.
- Validation report.
- Geometry JSON.
- OCR audit JSONL.
- Optional geometry visualizations.

The audit includes the exact prompt, raw Novita response, parsed tokens, bounding boxes, attempts, token usage, response hash, model, cache status, and parse issues.

Writes use temporary files followed by atomic replacement, preventing half-written tables after interruption. Export handling is in [`src/census_extractor/pipeline/exporter.py`](src/census_extractor/pipeline/exporter.py).

The complete orchestration is concentrated in [`src/census_extractor/pipeline/runner.py`](src/census_extractor/pipeline/runner.py).
