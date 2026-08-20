# 1971 Census Extraction Pipeline

This pipeline extracts the 157 trimmed Uttar Pradesh District Census Handbook tables with deterministic geometry and Novita-hosted `deepseek/deepseek-ocr-2`. It is fail-closed: an incomplete or low-quality table is quarantined and never appears under `clean`.

The authoritative district spelling, format, source pages, table identifier, and printed-page provenance come from `1971_Trimmed_PDF/Uttar_Pradesh/metadata/document.xlsx`. Filenames are not used to invent metadata or silently select a schema.

## Install and configure

Python 3.11 or newer is required.

```powershell
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Set `NOVITA_API_KEY` in `.env`. The defaults are:

```ini
NOVITA_BASE_URL=https://api.novita.ai/openai/v1
NOVITA_MODEL=deepseek/deepseek-ocr-2
```

The integration follows Novita's [DeepSeek OCR guide](https://novita.ai/docs/guides/llm-deepseek-ocr), [model details](https://novita.ai/models-console/model-detail/deepseek-deepseek-ocr-2), and [chat-completion API](https://novita.ai/docs/api-reference/model-apis-llm-create-chat-completion). It uses the single-image, single-turn contract. Row crops keep Novita's `<|grounding|>OCR this image.` preset as the first line, followed by schema-specific archival context: the table description, physical panel, expected printed column numbers and names, data types, descriptions, and possible historical notation. The prompt explicitly forbids inventing or copying example values and requires exact visible transcription. If grounded output has no usable 0–1000 boxes or a cell fails parsing, only those cells are retried with padded, upscaled PNG crops beginning with the `Free OCR.` preset and the expected cell definition. Requests use `temperature=0`, `top_k=0`, and `max_tokens=2048`. Check Novita's model console for current pricing before starting a paid run; every uncached row or fallback cell is a billable request.

## Commands

Both forms are supported:

```powershell
python cli.py schemas
census-extract schemas
```

Geometry-only inspection never calls Novita and never writes clean table data:

```powershell
python cli.py geometry --pdf 1971_Trimmed_PDF/Uttar_Pradesh/pdfs/agra_civic_1971.pdf
python cli.py batch --dry-run --no-viz
```

Live extraction requires the key:

```powershell
python cli.py process --pdf 1971_Trimmed_PDF/Uttar_Pradesh/pdfs/agra_civic_1971.pdf --run-id pilot-001
python cli.py batch --run-id full-001 --concurrency 2 --pdf-workers 2
```

Resume after interruption with the same run manifest and response cache:

```powershell
python cli.py batch --resume full-001 --concurrency 2 --pdf-workers 2
```

Transient 429, timeout, and 5xx responses honor `Retry-After` or use exponential backoff with jitter. They are never cached. Crop PNGs and successful raw responses are keyed by PDF checksum, crop coordinates, model, prompt, prompt version, and crop checksum.

## Physical layout

- Civic: page 1 columns 1–8; page 2 columns 9–16.
- Medical/education: page 1 columns 1–9; page 2 columns 10–17.
- Tahsil: page 1 has an education panel (1–12) and a power/water panel (repeated 1–2 plus 25–38); page 2 has a medical panel (13–24) and a roads/communications panel (39–50).

Panels are selected from format headings and printed column-number sequences in the PDF text layer. Column centers come from those printed numbers. The anchor identity columns determine row bands; continuation panels are matched monotonically or projected affinely when the scan is too faint. Deskew applies the same transform to raster and embedded-word coordinates.

## Status and outputs

Each run is atomic and isolated:

```text
outputs/runs/<run_id>/
  clean/<pdf_id>/         # only SUCCESS tables
  quarantine/<pdf_id>/    # reviewable typed data and validation report
  audit/                  # exact raw OCR, boxes, attempts, usage, hashes, geometry
  viz/                    # optional panel overlays
  manifest.json
```

Statuses are `SUCCESS`, `QUARANTINED`, `ERROR`, and `DRY_RUN`. A clean table requires every panel and row alignment, no error finding, and a weighted geometry/OCR/parsing/semantic score of at least 0.95. Batch exit code `2` means review is required; exit code `1` means an operational error occurred.

Every exported schema field contains the exact OCR transcription for every row; normalization is used for validation but never replaces that source text. Each field has one adjacent `<variable>_flag`, and `requires_review` identifies rows containing ambiguous OCR. For example, `elec_domestic=2-0` is retained exactly with `elec_domestic_flag=AMBIGUOUS_OCR`. Ambiguous tables are quarantined. Cross-reference targets are retained while their data cells are intentionally empty so reference text cannot masquerade as measurements. Exact responses and bounding boxes also remain in audit JSONL. Civic output adds parsed `pucca_road_km` and `kutcha_road_km`. CSV, Parquet, and JSONL are written from the same raw-transcription records with timezone-aware UTC timestamps and workbook provenance.

The prototype's synthetic Agra artifacts are preserved under `outputs/legacy/pre_novita_mock/` and carry a warning marker. They must not be used as extracted census data.

## Verification

```powershell
python -m build
ruff check .
pyright
pytest
pip-audit
```

Tests use temporary output directories and mocked Novita transports. No automated test spends API credit. A paid pilot should cover Agra, Almora, Aligarh, Jhansi, and Uttar Kashi across every available format, followed by a stratified manual check of at least 200 cells before starting the complete batch.
