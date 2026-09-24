from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from census_extractor.postprocessing import CorrectionLedger, CSVPostprocessor
from census_extractor.schemas import SchemaRegistry
from census_extractor.source_audit import SourceAuditError, SourceAuditRunner


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _source_frame(schema, rows: list[dict[str, str]]) -> pd.DataFrame:
    records: list[dict[str, str]] = []
    for index, values in enumerate(rows):
        record: dict[str, str] = {}
        for variable in schema.get_all_variables():
            record[variable] = values.get(variable, "...")
            record[f"{variable}_flag"] = values.get(f"{variable}_flag", "")
        if schema.format_id == "format_001":
            record.update(pucca_road_km="", kutcha_road_km="")
        record.update(
            row_type=values.get("row_type", "ORDINARY"),
            reference_target=values.get("reference_target", ""),
            requires_review=values.get("requires_review", "False"),
        )
        if schema.hierarchy is not None:
            record.update(
                parent_row_index=values["parent_row_index"],
                subrow_index=values["subrow_index"],
                subrow_count=values["subrow_count"],
            )
        record.update(
            row_index=str(index),
            pdf_id="fixture",
            district="Fixture",
            state="Uttar Pradesh",
            year="1971",
            format_id=schema.format_id,
        )
        records.append(record)
    return pd.DataFrame.from_records(records)


def _write_source_run(
    tmp_path: Path,
    project_config,
    *,
    format_id: str,
    rows: list[dict[str, str]],
) -> tuple[Path, Path, pd.DataFrame]:
    schema = SchemaRegistry(project_config.schemas_dir).require(format_id)
    frame = _source_frame(schema, rows)
    source_run = tmp_path / "runs" / "source"
    source_csv = source_run / "clean" / "fixture" / "table.csv"
    source_csv.parent.mkdir(parents=True)
    frame.to_csv(source_csv, index=False, lineterminator="\n")
    manifest = {
        "results": {
            "fixture": {
                "format_id": format_id,
                "exported_files": {"csv": str(source_csv.resolve())},
            }
        }
    }
    manifest_path = source_run / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return source_run, manifest_path, frame


def _write_ledger(
    tmp_path: Path,
    manifest_path: Path,
    *,
    format_id: str,
    rows: int,
    parents: int,
    reviewed: int,
    corrections: list[dict[str, object]],
    manifest_hash: str | None = None,
) -> Path:
    ledger = {
        "version": 1,
        "source_run_id": "source",
        "source_manifest_sha256": manifest_hash or _hash(manifest_path),
        "expected_table_count": 1,
        "expected_output_rows": rows,
        "expected_unique_source_cells": reviewed,
        "tables": {
            "fixture": {
                "format_id": format_id,
                "expected_rows": rows,
                "expected_parent_rows": parents,
                "reviewed_unique_cells": reviewed,
                "corrections": corrections,
            }
        },
    }
    path = tmp_path / "ledger.yaml"
    path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")
    return path


def _cell(
    variable: str,
    original: str,
    corrected: str,
    *,
    selector: dict[str, int] | None = None,
    scope: str = "row",
    panel: str = "civic_anchor",
    page: int = 1,
) -> dict[str, object]:
    return {
        "selector": selector or {"row_index": 0},
        "scope": scope,
        "variable": variable,
        "expected_original": original,
        "corrected": corrected,
        "source_page": page,
        "panel_id": panel,
        "reason": "source review",
    }


def test_ledger_validates_declared_review_totals(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "source_run_id": "source",
                "source_manifest_sha256": "A" * 64,
                "expected_table_count": 1,
                "expected_output_rows": 1,
                "expected_unique_source_cells": 15,
                "tables": {
                    "fixture": {
                        "format_id": "format_001",
                        "expected_rows": 1,
                        "expected_parent_rows": 1,
                        "reviewed_unique_cells": 16,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unique-cell review total"):
        CorrectionLedger.load(path)


def test_source_audit_queue_and_full_ledger_guard(project_config, tmp_path):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    provisional = tmp_path / "provisional"
    csv_dir = provisional / "csv"
    package = provisional / "codex_verification"
    csv_dir.mkdir(parents=True)
    frame = _source_frame(schema, [{"sl_no": "1", "town_name": "Town"}])
    source_csv = csv_dir / "fixture.csv"
    frame.to_csv(source_csv, index=False, lineterminator="\n")
    crop_path = package / "crops" / "fixture.png"
    package.mkdir(parents=True)
    crop_path.parent.mkdir(parents=True)
    crop_path.write_bytes(b"synthetic crop")
    crop_hash = _hash(crop_path)
    index_records = []
    for number, variable in enumerate(schema.get_all_variables()):
        panel = next(item for item in schema.panels if number + 1 in item.printed_columns)
        index_records.append(
            {
                "pdf_id": "fixture",
                "district": "Fixture",
                "format_id": "format_001",
                "source_pdf_sha256": "B" * 64,
                "source_manifest_sha256": "C" * 64,
                "selector": {"row_index": 0},
                "scope": "row",
                "variable": variable,
                "provisional_value": str(frame.at[0, variable]),
                "source_page": 1,
                "panel_id": panel.panel_id,
                "bbox": [10 + number, 10, 20 + number, 20],
                "cell_crop": "crops/fixture.png",
                "cell_crop_sha256": crop_hash,
            }
        )
    index_path = package / "verification_index.jsonl"
    index_path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in index_records),
        encoding="utf-8",
    )
    manifest = {
        "source_manifest_sha256": "C" * 64,
        "verification_index_sha256": _hash(index_path),
        "unique_source_cells": len(index_records),
    }
    (package / "verification_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    runner = SourceAuditRunner(provisional, project_config.schemas_dir)
    queue = runner.write_queue(tmp_path / "queue.jsonl")
    queued = [json.loads(line) for line in queue.read_text(encoding="utf-8").splitlines()]
    assert len(queued) == 16
    assert all(item["status"] == "PENDING" for item in queued)

    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text(
        "".join(
            json.dumps(
                {
                    **{key: value for key, value in item.items() if key != "status"},
                    "status": "UNRESOLVED" if item["variable"] == "town_name" else "VERIFIED",
                    "reason": "crop was unreadable"
                    if item["variable"] == "town_name"
                    else "source crop agrees",
                },
                sort_keys=True,
            )
            + "\n"
            for item in queued
        ),
        encoding="utf-8",
    )
    ledger = runner.build_ledger(decisions, tmp_path / "ledger.yaml")
    assert ledger.expected_unique_source_cells == 16
    assert ledger.allow_unresolved is True
    assert sum(item.status == "UNRESOLVED" for item in ledger.tables["fixture"].reviews) == 1

    incomplete = tmp_path / "incomplete.jsonl"
    incomplete.write_text("\n".join(decisions.read_text(encoding="utf-8").splitlines()[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(SourceAuditError, match="coverage is incomplete"):
        runner.build_ledger(incomplete, tmp_path / "incomplete-ledger.yaml")


def test_codex_v3_postprocess_retains_unresolved_and_writes_audit_report(
    project_config, tmp_path
):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    provisional = tmp_path / "provisional"
    csv_dir = provisional / "csv"
    package = provisional / "codex_verification"
    csv_dir.mkdir(parents=True)
    package.mkdir(parents=True)
    frame = _source_frame(schema, [{"sl_no": "1", "town_name": "Town"}])
    source_csv = csv_dir / "fixture.csv"
    frame.to_csv(source_csv, index=False, lineterminator="\n")
    crop_path = package / "crops" / "fixture.png"
    crop_path.parent.mkdir(parents=True)
    crop_path.write_bytes(b"synthetic crop")
    crop_hash = _hash(crop_path)
    index_records = []
    for number, variable in enumerate(schema.get_all_variables()):
        panel = next(item for item in schema.panels if number + 1 in item.printed_columns)
        index_records.append(
            {
                "pdf_id": "fixture",
                "district": "Fixture",
                "format_id": "format_001",
                "source_pdf_sha256": "B" * 64,
                "source_manifest_sha256": "C" * 64,
                "selector": {"row_index": 0},
                "scope": "row",
                "variable": variable,
                "provisional_value": str(frame.at[0, variable]),
                "source_page": 1,
                "panel_id": panel.panel_id,
                "bbox": [10 + number, 10, 20 + number, 20],
                "cell_crop": "crops/fixture.png",
                "cell_crop_sha256": crop_hash,
            }
        )
    index_path = package / "verification_index.jsonl"
    index_path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in index_records),
        encoding="utf-8",
    )
    (package / "verification_manifest.json").write_text(
        json.dumps(
            {
                "source_manifest_sha256": "C" * 64,
                "verification_index_sha256": _hash(index_path),
                "unique_source_cells": len(index_records),
            }
        ),
        encoding="utf-8",
    )
    audit = SourceAuditRunner(provisional, project_config.schemas_dir)
    queue = audit.write_queue(tmp_path / "queue.jsonl")
    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text(
        "".join(
            json.dumps(
                {
                    **{key: value for key, value in json.loads(line).items() if key != "status"},
                    "status": "UNRESOLVED" if json.loads(line)["variable"] == "town_name" else "VERIFIED",
                    "reason": "crop unreadable" if json.loads(line)["variable"] == "town_name" else "agrees",
                },
                sort_keys=True,
            )
            + "\n"
            for line in queue.read_text(encoding="utf-8").splitlines()
        ),
        encoding="utf-8",
    )
    ledger_path = tmp_path / "ledger.yaml"
    audit.build_ledger(decisions, ledger_path)
    merged = provisional / "merged"
    merged.mkdir()
    frame.to_csv(merged / "format_001_civic.csv", index=False, lineterminator="\n")
    result = CSVPostprocessor(
        project_config.with_overrides(output_dir=tmp_path / "outputs")
    ).run(source_run=provisional, ledger_path=ledger_path, output_id="codex-final")
    assert result.unresolved_cells == 1
    assert (result.output_root / "SOURCE_AUDIT_REPORT.md").is_file()
    assert "SOURCE_AUDITED_WITH_UNRESOLVED" in result.report.read_text(encoding="utf-8")
    assert result.unresolved_log is not None
    unresolved = pd.read_csv(result.unresolved_log, dtype=str, keep_default_na=False)
    assert unresolved.loc[0, "variable"] == "town_name"
    corrected = pd.read_csv(result.csv_files[0], dtype=str, keep_default_na=False)
    assert corrected.loc[0, "requires_review"] == "True"
    assert corrected.loc[0, "town_name_flag"] == "AUTOCORRECTION_UNRESOLVED"
    assert list(corrected.columns) == list(frame.columns)


def test_five_district_ledger_declares_complete_review_and_stable_counts(project_config):
    ledger = CorrectionLedger.load(
        project_config.data_dir / "postprocessing" / "pilot_5districts_1971.yaml"
    )
    assert len(ledger.tables) == 15
    assert ledger.expected_output_rows == 142
    assert ledger.expected_unique_source_cells == 2_700
    assert sum(
        table.expected_rows
        for table in ledger.tables.values()
        if table.format_id == "format_001"
    ) == 32
    assert sum(
        table.expected_rows
        for table in ledger.tables.values()
        if table.format_id == "format_002"
    ) == 79
    assert sum(
        table.expected_parent_rows
        for table in ledger.tables.values()
        if table.format_id == "format_002"
    ) == 32
    assert sum(
        table.expected_rows
        for table in ledger.tables.values()
        if table.format_id == "format_003"
    ) == 31

    allahabad = ledger.tables["allahabad_mededu_1971"].corrections
    assert any(
        item.variable == "town_name"
        and item.corrected == "ALLAHABAD CITY URBAN AGGLOMERATION"
        for item in allahabad
    )
    assert any(
        item.variable == "degree_colleges" and item.corrected == "A (3) AS (2) S (1)"
        for item in allahabad
    )
    assert any(
        item.variable == "libraries" and item.corrected == "PL (20) RR (1)"
        for item in allahabad
    )


def test_manifest_hash_guard_fails_without_partial_output(project_config, tmp_path):
    source, manifest, _ = _write_source_run(
        tmp_path,
        project_config,
        format_id="format_001",
        rows=[{"sl_no": "1", "town_name": "Town"}],
    )
    ledger = _write_ledger(
        tmp_path,
        manifest,
        format_id="format_001",
        rows=1,
        parents=1,
        reviewed=16,
        corrections=[],
        manifest_hash="0" * 64,
    )
    config = project_config.with_overrides(output_dir=tmp_path)
    with pytest.raises(ValueError, match="manifest SHA-256"):
        CSVPostprocessor(config).run(source_run=source, ledger_path=ledger, output_id="bad")
    assert not (tmp_path / "postprocessed" / "bad").exists()


def test_original_value_and_duplicate_guards_are_atomic(project_config, tmp_path):
    source, manifest, _ = _write_source_run(
        tmp_path,
        project_config,
        format_id="format_001",
        rows=[{"sl_no": "1", "town_name": "Town"}],
    )
    config = project_config.with_overrides(output_dir=tmp_path)
    bad_original = _write_ledger(
        tmp_path,
        manifest,
        format_id="format_001",
        rows=1,
        parents=1,
        reviewed=16,
        corrections=[_cell("town_name", "Wrong", "Correct")],
    )
    with pytest.raises(ValueError, match="original values"):
        CSVPostprocessor(config).run(
            source_run=source, ledger_path=bad_original, output_id="bad-original"
        )
    assert not (tmp_path / "postprocessed" / "bad-original").exists()

    duplicate = _write_ledger(
        tmp_path,
        manifest,
        format_id="format_001",
        rows=1,
        parents=1,
        reviewed=16,
        corrections=[
            _cell("town_name", "Town", "Correct"),
            _cell("town_name", "Town", "Correct"),
        ],
    )
    with pytest.raises(ValueError, match="duplicate correction"):
        CSVPostprocessor(config).run(
            source_run=source, ledger_path=duplicate, output_id="duplicate"
        )
    assert not (tmp_path / "postprocessed" / "duplicate").exists()


def test_civic_recomputes_classification_roads_flags_and_preserves_header(
    project_config, tmp_path
):
    source, manifest, original = _write_source_run(
        tmp_path,
        project_config,
        format_id="format_001",
        rows=[
            {
                "sl_no": "",
                "town_name": "URBAN",
                "town_name_flag": "AMBIGUOUS_OCR",
                "road_length_km": "PR (20) KR (2)",
                "other_latrines": "",
                "requires_review": "True",
            }
        ],
    )
    ledger = _write_ledger(
        tmp_path,
        manifest,
        format_id="format_001",
        rows=1,
        parents=1,
        reviewed=16,
        corrections=[
            _cell("town_name", "URBAN", "Almora Urban Agglomeration"),
            _cell("road_length_km", "PR (20) KR (2)", "PR (26) KR (0.2)"),
            _cell("other_latrines", "", "..."),
        ],
    )
    result = CSVPostprocessor(project_config.with_overrides(output_dir=tmp_path)).run(
        source_run=source, ledger_path=ledger, output_id="corrected"
    )
    corrected = pd.read_csv(result.csv_files[0], dtype=str, keep_default_na=False)
    assert list(corrected.columns) == list(original.columns)
    assert corrected.loc[0, "town_name"] == "Almora Urban Agglomeration"
    assert corrected.loc[0, "row_type"] == "AGGREGATE"
    assert corrected.loc[0, "pucca_road_km"] == "26.0"
    assert corrected.loc[0, "kutcha_road_km"] == "0.2"
    assert corrected.loc[0, "other_latrines"] == "..."
    assert corrected.loc[0, "town_name_flag"] == ""
    assert corrected.loc[0, "requires_review"] == "False"
    assert len(result.csv_files) == 1
    assert result.correction_log.is_file()
    assert result.report.is_file()


def test_mededu_parent_propagation_and_child_only_correction(project_config, tmp_path):
    rows = [
        {
            "sl_no": "1",
            "town_name": "ALLAHABAD",
            "hospitals_dispensaries": "H (2)",
            "med_beds": "20",
            "degree_colleges": "bad degree",
            "parent_row_index": "0",
            "subrow_index": "0",
            "subrow_count": "2",
        },
        {
            "sl_no": "1",
            "town_name": "ALLAHABAD",
            "hospitals_dispensaries": "D (1)",
            "med_beds": "",
            "degree_colleges": "bad degree",
            "parent_row_index": "0",
            "subrow_index": "1",
            "subrow_count": "2",
        },
    ]
    source, manifest, original = _write_source_run(
        tmp_path, project_config, format_id="format_002", rows=rows
    )
    ledger = _write_ledger(
        tmp_path,
        manifest,
        format_id="format_002",
        rows=2,
        parents=1,
        reviewed=19,
        corrections=[
            _cell(
                "town_name",
                "ALLAHABAD",
                "ALLAHABAD CITY URBAN AGGLOMERATION",
                selector={"parent_row_index": 0},
                scope="parent",
                panel="mededu_anchor",
            ),
            _cell(
                "degree_colleges",
                "bad degree",
                "A (3) AS (2) S (1)",
                selector={"parent_row_index": 0},
                scope="parent",
                panel="mededu_anchor",
            ),
            _cell(
                "med_beds",
                "",
                "...",
                selector={"parent_row_index": 0, "subrow_index": 1},
                panel="mededu_anchor",
            ),
        ],
    )
    result = CSVPostprocessor(project_config.with_overrides(output_dir=tmp_path)).run(
        source_run=source, ledger_path=ledger, output_id="mededu"
    )
    corrected = pd.read_csv(result.csv_files[0], dtype=str, keep_default_na=False)
    assert list(corrected.columns) == list(original.columns)
    assert corrected["town_name"].tolist() == [
        "ALLAHABAD CITY URBAN AGGLOMERATION",
        "ALLAHABAD CITY URBAN AGGLOMERATION",
    ]
    assert corrected["degree_colleges"].tolist() == [
        "A (3) AS (2) S (1)",
        "A (3) AS (2) S (1)",
    ]
    assert corrected["med_beds"].tolist() == ["20", "..."]
    assert corrected["row_type"].tolist() == ["AGGREGATE", "AGGREGATE"]
    assert corrected["parent_row_index"].tolist() == ["0", "0"]
    assert corrected["subrow_index"].tolist() == ["0", "1"]


def test_version_two_explicit_reviews_cover_every_cell_and_override_review_flags(
    project_config, tmp_path
):
    rows = [
        {
            "sl_no": "1",
            "town_name": "Town OCR",
            "hospitals_dispensaries": "H(1)",
            "med_beds": "2-0",
            "parent_row_index": "0",
            "subrow_index": "0",
            "subrow_count": "2",
        },
        {
            "sl_no": "1",
            "town_name": "Town OCR",
            "hospitals_dispensaries": "D(1)",
            "med_beds": "...",
            "parent_row_index": "0",
            "subrow_index": "1",
            "subrow_count": "2",
        },
    ]
    source, manifest, original = _write_source_run(
        tmp_path, project_config, format_id="format_002", rows=rows
    )
    schema = SchemaRegistry(project_config.schemas_dir).require("format_002")
    hierarchy = schema.hierarchy
    assert hierarchy is not None
    child_variables = set(hierarchy.child_variables)
    reviews: list[dict[str, object]] = []
    for variable in schema.get_all_variables():
        if variable in child_variables:
            for subrow_index in (0, 1):
                reviews.append(
                    {
                        "selector": {
                            "parent_row_index": 0,
                            "subrow_index": subrow_index,
                        },
                        "scope": "row",
                        "variable": variable,
                        "expected_original": original.loc[subrow_index, variable],
                        "verified_value": original.loc[subrow_index, variable],
                        "status": "VERIFIED",
                        "source_page": 1,
                        "panel_id": "mededu_anchor",
                        "bbox": [1, 1, 10, 10],
                        "crop_sha256": "A" * 64,
                        "reason": "",
                    }
                )
        else:
            expected = original.loc[0, variable]
            corrected = "Town" if variable == "town_name" else expected
            column = schema.get_column_by_var(variable)
            assert column is not None
            reviews.append(
                {
                    "selector": {"parent_row_index": 0},
                    "scope": "parent",
                    "variable": variable,
                    "expected_original": expected,
                    "verified_value": corrected,
                    "status": "CORRECTED" if variable == "town_name" else "VERIFIED",
                    "source_page": 1 if column.column_no <= 9 else 2,
                    "panel_id": (
                        "mededu_anchor"
                        if column.column_no <= 9
                        else "mededu_continuation"
                    ),
                    "bbox": [1, 1, 10, 10],
                    "crop_sha256": "A" * 64,
                    "reason": "source crop" if variable == "town_name" else "",
                }
            )
    ledger_payload = {
        "version": 2,
        "source_run_id": "source",
        "source_manifest_sha256": _hash(manifest),
        "expected_table_count": 1,
        "expected_output_rows": 2,
        "expected_unique_source_cells": 19,
        "tables": {
            "fixture": {
                "format_id": "format_002",
                "expected_rows": 2,
                "expected_parent_rows": 1,
                "reviewed_unique_cells": 19,
                "reviews": reviews,
            }
        },
    }
    ledger = tmp_path / "v2.yaml"
    ledger.write_text(yaml.safe_dump(ledger_payload, sort_keys=False), encoding="utf-8")
    result = CSVPostprocessor(project_config.with_overrides(output_dir=tmp_path)).run(
        source_run=source,
        ledger_path=ledger,
        output_id="verified",
    )
    corrected = pd.read_csv(result.csv_files[0], dtype=str, keep_default_na=False)
    assert corrected["town_name"].tolist() == ["Town", "Town"]
    assert corrected.loc[0, "med_beds"] == "2-0"
    assert corrected.loc[0, "med_beds_flag"] == ""
    assert corrected["requires_review"].tolist() == ["False", "False"]
    correction_log = pd.read_csv(result.correction_log, dtype=str, keep_default_na=False)
    assert correction_log[["variable", "affected_output_rows"]].values.tolist() == [
        ["town_name", "2"]
    ]


def test_version_two_ledger_rejects_incomplete_explicit_coverage(tmp_path):
    path = tmp_path / "incomplete.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "source_run_id": "source",
                "source_manifest_sha256": "A" * 64,
                "expected_table_count": 1,
                "expected_output_rows": 1,
                "expected_unique_source_cells": 2,
                "tables": {
                    "fixture": {
                        "format_id": "format_001",
                        "expected_rows": 1,
                        "expected_parent_rows": 1,
                        "reviewed_unique_cells": 2,
                        "reviews": [],
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="explicit review count"):
        CorrectionLedger.load(path)
