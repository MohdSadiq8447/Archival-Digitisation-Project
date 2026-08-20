from __future__ import annotations

import asyncio
import json

import httpx
import pandas as pd

from census_extractor.metadata import MetadataRegistry
from census_extractor.normalization import normalize_rows
from census_extractor.ocr.client import NovitaDeepSeekOCRClient
from census_extractor.pipeline.exporter import RunLayout, TableExporter
from census_extractor.pipeline.runner import PipelineRunner
from census_extractor.schemas import SchemaRegistry
from census_extractor.validation.validator import TableValidator


def test_atomic_typed_export_and_provenance(project_config, tmp_path):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    metadata = MetadataRegistry(project_config.metadata_path).get_for_pdf(
        project_config.pdfs_dir / "agra_civic_1971.pdf"
    )
    rows = normalize_rows(
        [
            {
                "sl_no": "1",
                "town_name": "Agra",
                "water_borne_latrines": "1,200",
                "fire_service": "Nil",
            }
        ],
        schema,
    )
    assert rows[0].values["water_borne_latrines"] == 1200
    assert rows[0].values["fire_service"] is None
    report = TableValidator().validate(
        "agra",
        schema,
        rows,
        panels_complete=True,
        aligned_row_counts={"a": 1, "b": 1},
        panel_scores=[1, 1],
        ocr_row_successes=2,
        ocr_row_total=2,
    )
    exporter = TableExporter(RunLayout.create(tmp_path / "runs", "r1"))
    paths = exporter.export_table(metadata, schema, rows, report, "SUCCESS", "f" * 64)
    parquet = pd.read_parquet(paths["parquet"])
    payload = json.loads(paths["jsonl"].read_text(encoding="utf-8"))
    assert parquet.loc[0, "water_borne_latrines"] == "1,200"
    assert parquet.loc[0, "fire_service"] == "Nil"
    assert pd.isna(parquet.loc[0, "water_borne_latrines_flag"])
    assert not parquet.loc[0, "requires_review"]
    assert payload["water_borne_latrines"] == "1,200"
    assert payload["fire_service"] == "Nil"
    assert payload["water_borne_latrines_flag"] is None
    assert payload["requires_review"] is False
    assert payload["district"] == "Agra"
    assert payload["metadata_workbook_sha256"] == metadata.workbook_sha256
    assert not list(paths["csv"].parent.glob("*.tmp"))


def test_quarantine_export_preserves_ambiguous_ocr_with_flag(project_config, tmp_path):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    metadata = MetadataRegistry(project_config.metadata_path).get_for_pdf(
        project_config.pdfs_dir / "agra_civic_1971.pdf"
    )
    rows = normalize_rows(
        [{"sl_no": "1", "town_name": "Swamibagh", "elec_domestic": "2-0"}], schema
    )
    report = TableValidator().validate(
        "agra",
        schema,
        rows,
        panels_complete=True,
        aligned_row_counts={"a": 1, "b": 1},
        panel_scores=[1, 1],
        ocr_row_successes=2,
        ocr_row_total=2,
    )
    paths = TableExporter(RunLayout.create(tmp_path / "runs", "flagged")).export_table(
        metadata, schema, rows, report, "QUARANTINED", "f" * 64
    )
    csv = pd.read_csv(paths["csv"], keep_default_na=False)
    parquet = pd.read_parquet(paths["parquet"])
    payload = json.loads(paths["jsonl"].read_text(encoding="utf-8"))

    assert csv.loc[0, "elec_domestic"] == "2-0"
    assert csv.loc[0, "elec_domestic_flag"] == "AMBIGUOUS_OCR"
    assert bool(csv.loc[0, "requires_review"])
    assert parquet.loc[0, "elec_domestic"] == "2-0"
    assert parquet.loc[0, "elec_domestic_flag"] == "AMBIGUOUS_OCR"
    assert bool(parquet.loc[0, "requires_review"])
    assert payload["elec_domestic"] == "2-0"
    assert payload["elec_domestic_flag"] == "AMBIGUOUS_OCR"
    assert payload["requires_review"] is True


def test_dry_run_never_calls_ocr_or_writes_clean(project_config, tmp_path):
    def forbidden(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"Unexpected OCR request: {request.url}")

    config = project_config.with_overrides(
        output_dir=tmp_path,
        cache_path=tmp_path / "cache",
        novita_api_key="test-key-valid",
        render_dpi=150,
    )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(forbidden)) as http:
            client = NovitaDeepSeekOCRClient(config, http)
            runner = PipelineRunner(config, run_id="dry", ocr_client=client)
            return await runner.process_pdf_async(
                config.pdfs_dir / "agra_civic_1971.pdf", save_viz=False, is_dry_run=True
            )

    summary = asyncio.run(run())
    assert summary.status == "DRY_RUN"
    assert summary.total_rows == 21
    assert not any((tmp_path / "runs" / "dry" / "clean").iterdir())
    assert "geometry" in summary.exported_files


def test_end_to_end_uses_mocked_novita_and_quarantines_invalid_rows(project_config, tmp_path):
    calls = 0
    requests_seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        payload = json.loads(request.read())
        messages = payload["messages"]
        system_context = next(
            (message["content"] for message in messages if message["role"] == "system"),
            "",
        )
        user_message = next(message for message in messages if message["role"] == "user")
        user_prompt = next(
            item["text"] for item in user_message["content"] if item["type"] == "text"
        )
        requests_seen.append((system_context, user_prompt))
        content = "<|ref|>1<|/ref|><|det|>[[10,100,90,900]]<|/det|><|ref|>Agra<|/ref|><|det|>[[100,100,300,900]]<|/det|>"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": content}}], "usage": {"total_tokens": 4}},
            request=request,
        )

    config = project_config.with_overrides(
        output_dir=tmp_path,
        cache_path=tmp_path / "cache",
        novita_api_key="test-key-valid",
        render_dpi=150,
        auto_deskew=False,
    )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = NovitaDeepSeekOCRClient(config, http)
            runner = PipelineRunner(config, run_id="mock-live", ocr_client=client)
            return await runner.process_pdf_async(
                config.pdfs_dir / "agra_civic_1971.pdf", save_viz=False
            )

    summary = asyncio.run(run())
    assert calls > 0
    assert any(
        user_prompt == "<|grounding|>OCR this image."
        and "Table: civic_amenities_1971" in system_context
        and "Expected printed columns" in system_context
        for system_context, user_prompt in requests_seen
    )
    assert summary.status == "QUARANTINED"
    assert "csv" in summary.exported_files
    assert "quarantine" in str(summary.exported_files["csv"])
    assert not any((tmp_path / "runs" / "mock-live" / "clean").iterdir())
    manifest = json.loads(
        (tmp_path / "runs" / "mock-live" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["results"]["agra_civic_1971"]["status"] == "QUARANTINED"
