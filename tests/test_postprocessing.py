from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from census_extractor.postprocessing import CorrectionLedger, CSVPostprocessor
from census_extractor.schemas import SchemaRegistry


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
