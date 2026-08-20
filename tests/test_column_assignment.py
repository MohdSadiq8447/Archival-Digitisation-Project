from __future__ import annotations

import pytest

from census_extractor.geometry.column_detector import ColumnSpan
from census_extractor.geometry.panel_detector import PanelGeometry
from census_extractor.ocr.client import OCRResult, OCRToken
from census_extractor.ocr.column_assigner import ColumnAssigner
from census_extractor.pipeline.runner import PipelineRunner
from census_extractor.schemas import SchemaRegistry


def spans():
    return [
        ColumnSpan(1, "Serial", "sl_no", 100, 200, 0, 0.2),
        ColumnSpan(2, "Name", "town_name", 200, 600, 0.2, 1),
    ]


def test_scale_1000_and_assignment():
    result = OCRResult(
        0,
        1,
        "",
        tokens=[
            OCRToken("1", [0, 0, 190, 900]),
            OCRToken("Agra", [250, 0, 600, 900]),
            OCRToken("(M.C.)", [610, 0, 900, 900]),
        ],
    )
    values = ColumnAssigner().assign_tokens_to_columns(result, spans(), (100, 10, 600, 50))
    assert values == {"sl_no": "1", "town_name": "Agra (M.C.)"}


def test_invalid_coordinate_system_has_no_sequential_fallback():
    result = OCRResult(0, 1, "", tokens=[OCRToken("invented", None)])
    assert ColumnAssigner().assign_tokens_to_columns(result, spans(), (100, 10, 600, 50)) == {
        "sl_no": "",
        "town_name": "",
    }
    with pytest.raises(ValueError, match="Invalid"):
        ColumnAssigner.scale_bbox_1000([0, 0, 1001, 20], (0, 0, 100, 100))


def test_anchor_identity_refolds_left_aligned_name_and_cross_reference(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    definition = schema.row_anchor_panel
    boundaries = [0, 190, 340, 520, 630, 720, 810, 900, 1000]
    columns = [
        ColumnSpan(
            column.column_no,
            column.column_name,
            column.variable,
            boundaries[index],
            boundaries[index + 1],
            boundaries[index] / 1000,
            boundaries[index + 1] / 1000,
        )
        for index, column in enumerate(schema.columns_for_panel(definition))
    ]
    panel = PanelGeometry(
        definition,
        1,
        (0, 0, 1000, 100),
        (0, 0, 1000, 10),
        (0, 10, 1000, 100),
        columns,
        list(range(1, 9)),
        1.0,
    )
    result = OCRResult(
        0,
        1,
        "",
        tokens=[
            OCRToken("2", [80, 0, 100, 99]),
            OCRToken("Agra", [120, 0, 163, 99]),
            OCRToken("See", [475, 0, 505, 99]),
            OCRToken("Agra", [530, 0, 574, 99]),
            OCRToken("City Urban Agglomeration", [600, 0, 857, 99]),
        ],
    )
    assigned = ColumnAssigner().assign_tokens_to_columns(result, columns, (0, 0, 1000, 100))
    fixed = PipelineRunner._apply_anchor_identity(
        schema, panel, (0, 0, 1000, 100), result, assigned
    )

    assert fixed["sl_no"] == "2"
    assert fixed["town_name"] == "Agra See Agra City Urban Agglomeration"
    assert all(
        not fixed[column.variable]
        for column in schema.columns_for_panel(definition)
        if column.column_no not in definition.identity_columns
    )


def test_cell_prompt_leakage_is_rejected():
    result = OCRResult(0, 1, "<table>CategoryValue11002100</table>")
    assert PipelineRunner._cell_text(result) == ""
    assert "prompt leakage" in result.parse_issues[-1]


def test_night_soil_code_validation_accepts_complete_sequences():
    assert PipelineRunner._valid_night_soil_code("HC/MT/B")
    assert PipelineRunner._valid_night_soil_code("MT/HL/B/HC")
    assert PipelineRunner._valid_night_soil_code("Nil")
    assert not PipelineRunner._valid_night_soil_code("HC/")
    assert not PipelineRunner._valid_night_soil_code("HC/MI/B")
    assert not PipelineRunner._valid_night_soil_code("B/H/L")
