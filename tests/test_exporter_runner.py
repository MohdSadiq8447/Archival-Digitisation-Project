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
        [{"sl_no": "1", "town_name": "Agra", "water_borne_latrines": "12"}], schema
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
    exporter = TableExporter(RunLayout.create(tmp_path / "runs", "r1"))
    paths = exporter.export_table(metadata, schema, rows, report, "SUCCESS", "f" * 64)
    parquet = pd.read_parquet(paths["parquet"])
    payload = json.loads(paths["jsonl"].read_text(encoding="utf-8"))
    assert parquet.loc[0, "water_borne_latrines"] == 12
    assert payload["water_borne_latrines"] == 12
    assert payload["district"] == "Agra"
    assert payload["metadata_workbook_sha256"] == metadata.workbook_sha256
    assert not list(paths["csv"].parent.glob("*.tmp"))


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
    prompts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        payload = json.loads(request.read())
        prompts.append(payload["messages"][0]["content"][0]["text"])
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
        prompt.startswith("<|grounding|>OCR this image.")
        and "Table: civic_amenities_1971" in prompt
        and "Expected printed columns" in prompt
        for prompt in prompts
    )
    assert summary.status == "QUARANTINED"
    assert "csv" in summary.exported_files
    assert "quarantine" in str(summary.exported_files["csv"])
    assert not any((tmp_path / "runs" / "mock-live" / "clean").iterdir())
    manifest = json.loads(
        (tmp_path / "runs" / "mock-live" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["results"]["agra_civic_1971"]["status"] == "QUARANTINED"
