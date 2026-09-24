from __future__ import annotations

import asyncio
import hashlib
import json
from types import SimpleNamespace
from typing import cast

import pandas as pd
import yaml
from PIL import Image

from census_extractor.autocorrection import (
    AUTO_UNRESOLVED_FLAG,
    AutomaticCandidate,
    AutomaticTranscriptionCorrector,
    AutoSelector,
    SuspiciousCell,
    canonical_value,
    detect_suspicious_cells,
)
from census_extractor.metadata import DocumentMetadata
from census_extractor.ocr.client import NovitaDeepSeekOCRClient, OCRResult, OCRToken
from census_extractor.postprocessing import CSVPostprocessor
from census_extractor.preprocessing.pdf_loader import RenderedPage
from census_extractor.schemas import SchemaRegistry


class FakeOCRClient:
    def __init__(self, values: list[str], *, cache_hits: set[int] | None = None):
        self.values = values
        self.calls: list[str] = []
        self.cache_hits = 0
        self.cache_misses = 0
        self._hit_indexes = cache_hits or set()

    @staticmethod
    def image_to_png(_image: Image.Image) -> bytes:
        return b"strict-cell"

    async def ocr_cell_async(self, _image, context):
        index = len(self.calls)
        self.calls.append(context.prompt)
        hit = index in self._hit_indexes
        self.cache_hits += int(hit)
        self.cache_misses += int(not hit)
        return OCRResult(
            row_index=context.row_index,
            page_number=context.page_number,
            raw_text=self.values[index],
            cache_hit=hit,
            cache_key=f"key-{index}",
            response_hash=f"response-{index}",
        )

    async def aclose(self):
        return None


def _flat_frame(schema, **overrides: str) -> pd.DataFrame:
    record: dict[str, str] = {}
    for variable in schema.get_all_variables():
        record[variable] = "..."
        record[f"{variable}_flag"] = ""
    record.update(
        sl_no="S",
        town_name="Reoti",
        row_index="0",
        district="Baliya",
        requires_review="False",
        row_type="ORDINARY",
        reference_target="",
        pdf_id="fixture",
        format_id=schema.format_id,
    )
    record.update(overrides)
    return pd.DataFrame([record])


def test_suspicious_detection_is_parent_scoped_for_inherited_mededu(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_002")
    records = []
    for subrow, hospital in enumerate(("H(1)", "D(1)")):
        record: dict[str, str] = {}
        for variable in schema.get_all_variables():
            record[variable] = "..."
            record[f"{variable}_flag"] = ""
        record.update(
            sl_no="1",
            town_name="Town",
            hospitals_dispensaries=hospital,
            medical_colleges="Medical Colleges Field: medical_colleges Number: 1 | 0",
            medical_colleges_flag="AMBIGUOUS_OCR",
            parent_row_index="0",
            subrow_index=str(subrow),
            subrow_count="2",
            row_index=str(subrow),
        )
        records.append(record)
    cells = detect_suspicious_cells(
        pd.DataFrame(records),
        schema,
        {"findings": []},
        district="Fixture",
    )
    medical = [cell for cell in cells if cell.variable == "medical_colleges"]
    assert len(medical) == 1
    assert medical[0].scope == "parent"
    assert medical[0].frame_indices == (0, 1)


def test_two_readings_agree_and_second_retry_stops_early(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_002")
    client = FakeOCRClient(["3", "unused"], cache_hits={0})
    corrector = AutomaticTranscriptionCorrector(
        project_config,
        max_cell_retries=2,
        ocr_client=cast(NovitaDeepSeekOCRClient, client),
    )
    page = SimpleNamespace(
        width=300,
        height=200,
        image=Image.new("RGB", (300, 200), "white"),
        pdf_words=[{"text": "3", "bbox": (20, 30, 30, 45)}],
    )
    geometry = {
        "panels": [
            {
                "panel_id": "mededu_anchor",
                "page": 1,
                "body_bbox": [0, 0, 300, 200],
                "column_spans": {"1": {"x_start": 0, "x_end": 50}},
                "rows": [{"row_index": 0, "bbox": [0, 20, 300, 60]}],
            }
        ]
    }
    cell = SuspiciousCell(
        selector=AutoSelector(parent_row_index=0),
        scope="parent",
        variable="sl_no",
        original="S",
        reasons=("invalid serial",),
        frame_indices=(0, 1, 2),
    )
    decision = asyncio.run(
        corrector._decide_cell(
            cast(DocumentMetadata, SimpleNamespace(pdf_id="fixture")),
            schema,
            geometry,
            [cast(RenderedPage, page)],
            cell,
            "A" * 64,
        )
    )
    assert decision.status == "AUTO_CORRECTED"
    assert decision.selected == "3"
    assert len(client.calls) == 1
    assert decision.candidates[-1].cache_hit
    assert "possible printed forms" not in client.calls[0].casefold()
    assert "expected value" not in client.calls[0].casefold()


def test_retry_disagreement_and_prompt_leakage_remain_unresolved(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_002")
    candidates = [
        AutomaticCandidate(
            source="retry_1",
            value="Medical Colleges Field: medical_colleges Number: 1 | 0",
            canonical="leak",
            valid=False,
            rejection_reason="prompt leakage",
        ),
        AutomaticCandidate(
            source="retry_2",
            value="1",
            canonical="1",
            valid=True,
        ),
    ]
    assert AutomaticTranscriptionCorrector._consensus(candidates) is None
    column = schema.get_column_by_var("medical_colleges")
    assert column is not None
    rejected = AutomaticTranscriptionCorrector._candidate(
        "retry_1",
        "Medical Colleges Field: medical_colleges Number: 1 | 0",
        column,
    )
    assert not rejected.valid


def test_visible_print_prevents_two_blank_retries_from_erasing_a_placeholder():
    image = Image.new("L", (100, 50), "white")
    for x in range(40, 61):
        image.putpixel((x, 25), 0)
    assert AutomaticTranscriptionCorrector._has_visible_ink(image)
    assert not AutomaticTranscriptionCorrector._has_visible_ink(
        Image.new("L", (100, 50), "white")
    )


def test_formula_like_historical_text_is_treated_as_literal(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_002")
    column = schema.get_column_by_var("degree_colleges")
    assert column is not None
    candidate = AutomaticTranscriptionCorrector._candidate(
        "retry_1", "=A(1)", column
    )
    assert candidate.valid
    assert candidate.value == "=A(1)"


def test_blank_ellipsis_and_dash_remain_distinct_consensus_values(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_002")
    column = schema.get_column_by_var("med_beds")
    assert column is not None
    assert {
        canonical_value("", column),
        canonical_value("...", column),
        canonical_value("-", column),
    } == {"<BLANK>", "<ELLIPSIS>", "<DASH>"}


def test_full_cell_consensus_uses_row_panel_then_strict_crop(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_002")

    class FullCellClient(FakeOCRClient):
        async def ocr_row_async(self, *_args, **kwargs):
            self.calls.append(kwargs["prompt"])
            return OCRResult(
                row_index=kwargs["row_index"],
                page_number=kwargs["page_number"],
                raw_text="3",
                tokens=[OCRToken("3", [10, 100, 100, 800])],
                cache_key="row-key",
                response_hash="row-response",
            )

    client = FullCellClient(["unused", "3"])
    corrector = AutomaticTranscriptionCorrector(
        project_config,
        max_cell_retries=2,
        ocr_client=cast(NovitaDeepSeekOCRClient, client),
    )
    page = SimpleNamespace(
        width=300,
        height=200,
        image=Image.new("RGB", (300, 200), "white"),
        pdf_words=[],
        page_number=1,
    )
    geometry = {
        "panels": [
            {
                "panel_id": "mededu_anchor",
                "page": 1,
                "body_bbox": [0, 0, 300, 200],
                "column_spans": {
                    str(number): {
                        "x_start": (number - 1) * 30,
                        "x_end": number * 30,
                    }
                    for number in range(1, 10)
                },
                "rows": [{"row_index": 0, "bbox": [0, 20, 300, 60]}],
            }
        ]
    }
    cell = SuspiciousCell(
        selector=AutoSelector(parent_row_index=0),
        scope="parent",
        variable="sl_no",
        original="S",
        reasons=("invalid serial",),
        frame_indices=(0,),
    )
    decision = asyncio.run(
        corrector._decide_cell(
            cast(DocumentMetadata, SimpleNamespace(pdf_id="fixture")),
            schema,
            geometry,
            [cast(RenderedPage, page)],
            cell,
            "A" * 64,
        )
    )
    assert decision.status == "AUTO_CORRECTED"
    assert decision.selected == "3"
    assert [candidate.crop_scope for candidate in decision.candidates][-2:] == [
        "row_panel",
        "strict_cell",
    ]
    assert len(client.calls) == 2


def test_automatic_postprocess_propagates_parent_and_retains_unresolved(
    project_config, tmp_path
):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_002")
    records = []
    for index, hospital in enumerate(("H(1)", "D(1)")):
        record: dict[str, str] = {}
        for variable in schema.get_all_variables():
            record[variable] = "..."
            record[f"{variable}_flag"] = ""
        record.update(
            sl_no="1",
            town_name="Town",
            hospitals_dispensaries=hospital,
            med_beds="10" if index == 0 else "...",
            medical_colleges="prompt Field: medical_colleges",
            medical_colleges_flag="AMBIGUOUS_OCR",
            polytechnics="... ...",
            polytechnics_flag="AMBIGUOUS_OCR",
            parent_row_index="0",
            subrow_index=str(index),
            subrow_count="2",
            row_index=str(index),
            requires_review="True",
            row_type="ORDINARY",
            reference_target="",
            pdf_id="fixture",
            district="Fixture",
            format_id="format_002",
        )
        records.append(record)
    frame = pd.DataFrame(records)
    source_root = tmp_path / "runs" / "source"
    source_csv = source_root / "quarantine" / "fixture" / "table.csv"
    geometry_path = source_root / "audit" / "fixture.geometry.json"
    report_path = source_root / "quarantine" / "fixture" / "validation.json"
    source_csv.parent.mkdir(parents=True)
    geometry_path.parent.mkdir(parents=True)
    frame.to_csv(source_csv, index=False, lineterminator="\n")
    geometry_path.write_text("{}", encoding="utf-8")
    report_path.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "row_index": 0,
                        "variable": "medical_colleges",
                        "message": "parse",
                    },
                    {"row_index": 0, "variable": "polytechnics", "message": "parse"},
                    {"row_index": 1, "variable": "polytechnics", "message": "parse"},
                ]
            }
        ),
        encoding="utf-8",
    )
    manifest_path = source_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "results": {
                    "fixture": {
                        "format_id": "format_002",
                        "district": "Fixture",
                        "exported_files": {
                            "csv": str(source_csv),
                            "geometry": str(geometry_path),
                            "report": str(report_path),
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    crop_hash = hashlib.sha256(b"crop").hexdigest().upper()
    ledger = {
        "version": 1,
        "mode": "automatic",
        "source_run_id": "source",
        "source_manifest_sha256": hashlib.sha256(manifest_path.read_bytes())
        .hexdigest()
        .upper(),
        "max_cell_retries": 2,
        "uncertain_policy": "keep_value_and_flag",
        "tables": {
            "fixture": {
                "pdf_id": "fixture",
                "format_id": "format_002",
                "source_csv_sha256": hashlib.sha256(source_csv.read_bytes())
                .hexdigest()
                .upper(),
                "geometry_sha256": hashlib.sha256(geometry_path.read_bytes())
                .hexdigest()
                .upper(),
                "source_pdf_sha256": "A" * 64,
                "expected_rows": 2,
                "expected_parent_rows": 1,
                "suspicious_cells": 2,
                "decisions": [
                    {
                        "selector": {"parent_row_index": 0},
                        "scope": "parent",
                        "variable": "medical_colleges",
                        "original": "prompt Field: medical_colleges",
                        "selected": "1",
                        "status": "AUTO_CORRECTED",
                        "confidence": 1.0,
                        "reasons": ["prompt contamination"],
                        "source_page": 1,
                        "panel_id": "mededu_anchor",
                        "bbox": [1, 1, 10, 10],
                        "crop_sha256": crop_hash,
                        "candidates": [
                            {
                                "source": "retry_1",
                                "value": "1",
                                "canonical": "1",
                                "valid": True,
                            },
                            {
                                "source": "retry_2",
                                "value": "1",
                                "canonical": "1",
                                "valid": True,
                            },
                        ],
                    },
                    {
                        "selector": {"parent_row_index": 0},
                        "scope": "parent",
                        "variable": "polytechnics",
                        "original": "... ...",
                        "selected": "... ...",
                        "status": "UNRESOLVED",
                        "confidence": 0.0,
                        "reasons": ["parse"],
                        "source_page": 1,
                        "panel_id": "mededu_anchor",
                        "bbox": [1, 1, 10, 10],
                        "crop_sha256": crop_hash,
                        "candidates": [],
                    },
                ],
            }
        },
    }
    ledger_path = tmp_path / "automatic.yaml"
    ledger_path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")
    result = CSVPostprocessor(
        project_config.with_overrides(output_dir=tmp_path)
    ).run_automatic(
        source_run=source_root,
        ledger_path=ledger_path,
        output_id="automatic",
    )
    corrected = pd.read_csv(result.csv_files[0], dtype=str, keep_default_na=False)
    assert corrected["medical_colleges"].tolist() == ["1", "1"]
    assert corrected["parent_row_index"].tolist() == ["0", "0"]
    assert corrected["subrow_index"].tolist() == ["0", "1"]
    assert all(AUTO_UNRESOLVED_FLAG in value for value in corrected["polytechnics_flag"])
    assert corrected["requires_review"].tolist() == ["True", "True"]
    assert result.unresolved_cells == 1
    assert result.unresolved_log is not None and result.unresolved_log.is_file()
