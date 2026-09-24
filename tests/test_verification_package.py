from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from census_extractor.autocorrection import sha256_file
from census_extractor.metadata import MetadataRegistry
from census_extractor.schemas import SchemaRegistry
from census_extractor.verification import CodexVerificationPackageBuilder


def test_codex_verification_package_covers_every_cell_and_guards_hashes(
    project_config, tmp_path
):
    config = project_config.with_overrides(output_dir=tmp_path, auto_deskew=False)
    document = MetadataRegistry(config.metadata_path).get("baliya_civic_1971")
    assert document is not None
    schema = SchemaRegistry(config.schemas_dir).require(document.format_id)
    provisional = tmp_path / "postprocessed" / "provisional"
    csv_path = provisional / "csv" / f"{document.pdf_id}.csv"
    csv_path.parent.mkdir(parents=True)
    row: dict[str, str | int | bool] = {
        "row_index": 0,
        "pdf_id": document.pdf_id,
        "district": document.district,
        "format_id": document.format_id,
        "requires_review": True,
    }
    for variable in schema.get_all_variables():
        row[variable] = (
            "1" if variable == "sl_no" else "Baliya" if variable == "town_name" else "..."
        )
        row[f"{variable}_flag"] = "AMBIGUOUS_OCR" if variable == "sl_no" else ""
    pd.DataFrame([row]).to_csv(csv_path, index=False, lineterminator="\n")

    geometry_path = tmp_path / "runs" / "source" / "audit" / "baliya.geometry.json"
    geometry_path.parent.mkdir(parents=True)
    panels = []
    for definition in schema.panels:
        width = 800
        step = width // len(definition.printed_columns)
        panels.append(
            {
                "panel_id": definition.panel_id,
                "page": definition.page,
                "table_bbox": [0, 0, width, 180],
                "body_bbox": [0, 40, width, 180],
                "column_spans": {
                    str(number): {
                        "x_start": index * step,
                        "x_end": (index + 1) * step,
                    }
                    for index, number in enumerate(definition.printed_columns)
                },
                "rows": [{"row_index": 0, "bbox": [0, 60, width, 130]}],
            }
        )
    geometry_path.write_text(
        json.dumps({"panels": panels}), encoding="utf-8", newline="\n"
    )

    manifest_path = tmp_path / "runs" / "source" / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "results": {
                    document.pdf_id: {
                        "format_id": document.format_id,
                        "exported_files": {"geometry": str(geometry_path)},
                    }
                }
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    decisions = []
    for column in schema.get_all_columns():
        definition = next(
            panel for panel in schema.panels if column.column_no in panel.printed_columns
        )
        value = str(row[column.variable])
        decisions.append(
            {
                "selector": {"row_index": 0},
                "scope": "row",
                "variable": column.variable,
                "original": value,
                "selected": value,
                "status": "UNRESOLVED",
                "confidence": 0.0,
                "reasons": ["awaiting Codex source audit"],
                "source_page": definition.page,
                "panel_id": definition.panel_id,
                "bbox": [1, 60, 10, 130],
                "crop_sha256": "A" * 64,
                "candidates": [],
            }
        )
    pdf_path = config.pdfs_dir / document.file_name
    ledger = {
        "version": 2,
        "mode": "automatic",
        "verification_strategy": "full_cell_consensus",
        "source_run_id": "source",
        "source_manifest_sha256": sha256_file(manifest_path),
        "max_cell_retries": 2,
        "uncertain_policy": "keep_value_and_flag",
        "tables": {
            document.pdf_id: {
                "pdf_id": document.pdf_id,
                "format_id": document.format_id,
                "source_csv_sha256": sha256_file(csv_path),
                "geometry_sha256": sha256_file(geometry_path),
                "source_pdf_sha256": sha256_file(pdf_path),
                "expected_rows": 1,
                "expected_parent_rows": 1,
                "suspicious_cells": len(decisions),
                "unique_cells": len(decisions),
                "decisions": decisions,
            }
        },
    }
    ledger_path = tmp_path / "automatic.yaml"
    ledger_path.write_text(
        yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8", newline="\n"
    )

    builder = CodexVerificationPackageBuilder(config)
    result = builder.build(
        source_manifest=manifest_path,
        automatic_ledger=ledger_path,
        provisional_root=provisional,
        documents=[document],
    )
    assert result["unique_source_cells"] == len(schema.get_all_variables())
    assert result["selected_pdfs"] == 1
    package_root = Path(result["root"])
    assert not (package_root / "SOURCE_REVIEW.xlsx").exists()
    records = [
        json.loads(line)
        for line in (package_root / "verification_index.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert {record["variable"] for record in records} == set(
        schema.get_all_variables()
    )
    assert all(record["requires_review"] for record in records)
    assert all((package_root / record["cell_crop"]).is_file() for record in records)

    resumed = builder.build(
        source_manifest=manifest_path,
        automatic_ledger=ledger_path,
        provisional_root=provisional,
        documents=[document],
    )
    assert resumed["index_sha256"] == result["index_sha256"]
    with (package_root / "verification_index.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("{}\n")
    with pytest.raises(ValueError, match="index hash"):
        builder.build(
            source_manifest=manifest_path,
            automatic_ledger=ledger_path,
            provisional_root=provisional,
            documents=[document],
        )
