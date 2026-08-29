from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from census_extractor.geometry.column_detector import ColumnSpan
from census_extractor.geometry.panel_detector import PanelGeometry
from census_extractor.ocr.client import OCRResult, OCRToken
from census_extractor.ocr.column_assigner import ColumnAssigner
from census_extractor.pipeline.runner import PipelineRunner
from census_extractor.preprocessing.pdf_loader import RenderedPage
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


def test_embedded_identity_recovers_component_roman_numeral(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_002")
    definition = next(panel for panel in schema.panels if panel.panel_id == "mededu_anchor")
    columns = [
        ColumnSpan(1, "Serial", "sl_no", 0, 100, 0.0, 0.25),
        ColumnSpan(2, "Town", "town_name", 100, 300, 0.25, 0.75),
        ColumnSpan(3, "Hospitals", "hospitals_dispensaries", 300, 400, 0.75, 1.0),
    ]
    panel = PanelGeometry(
        definition,
        1,
        (0, 0, 400, 80),
        (0, 0, 400, 20),
        (0, 20, 400, 80),
        columns,
        [1, 2, 3],
        1.0,
    )
    image = Image.new("RGB", (400, 100), "white")
    page = RenderedPage(
        page_number=1,
        dpi=300,
        image=image,
        np_image=np.full((100, 400, 3), 255, dtype=np.uint8),
        grayscale=np.full((100, 400), 255, dtype=np.uint8),
        binary=np.zeros((100, 400), dtype=np.uint8),
        pdf_text="i(iii) Subedarganj Rly. Colony",
        pdf_words=[
            {"text": "i(iii)", "bbox": (20, 25, 70, 45)},
            {"text": "Subedarganj", "bbox": (120, 25, 220, 45)},
            {"text": "Rly.", "bbox": (120, 48, 155, 68)},
            {"text": "Colony", "bbox": (165, 48, 230, 68)},
        ],
        width=400,
        height=100,
    )

    fixed = PipelineRunner._apply_embedded_anchor_identity(
        page,
        schema,
        panel,
        (0, 20, 400, 80),
        {"sl_no": "", "town_name": "(i) Subedarganj Rly. Colony"},
    )

    assert fixed["sl_no"] == "(iii)"
    assert fixed["town_name"] == "Subedarganj Rly. Colony"

    page.pdf_words[0] = {"text": "00", "bbox": (20, 25, 70, 45)}
    preserved = PipelineRunner._apply_embedded_anchor_identity(
        page,
        schema,
        panel,
        (0, 20, 400, 80),
        {"sl_no": "6", "town_name": "Sirsa"},
    )
    assert preserved["sl_no"] == "6"


def test_cell_prompt_leakage_is_rejected():
    result = OCRResult(0, 1, "<table>CategoryValue11002100</table>")
    assert PipelineRunner._cell_text(result) == ""
    assert "prompt leakage" in result.parse_issues[-1]


def test_validation_metadata_is_rejected_as_cell_text():
    result = OCRResult(0, 1, "Medical Colleges AMBIGUOUS_OCR expected integer")
    assert PipelineRunner._cell_text(result) == ""
    assert "prompt leakage" in result.parse_issues[-1]


def test_prefixed_ocr_explanation_is_rejected_as_cell_text():
    result = OCRResult(
        0,
        1,
        "tahsil_abstract_1971; panel: tahsil_power_water. "
        "This image does not contain any data, formulas, or tables.",
    )
    assert PipelineRunner._cell_text(result) == ""
    assert "prompt leakage" in result.parse_issues[-1]


def test_expected_value_table_is_rejected_as_cell_text():
    result = OCRResult(0, 1, "Medical Colleges Field | Expected Value 1 | 0 2 | 0")
    assert PipelineRunner._cell_text(result) == ""
    assert "prompt leakage" in result.parse_issues[-1]


@pytest.mark.parametrize(
    "heading",
    ["No. of villages having", "Pucca Road", "Post and Telegraph Office"],
)
def test_table_heading_is_rejected_as_cell_text(heading):
    result = OCRResult(0, 1, heading)
    assert PipelineRunner._cell_text(result) == ""
    assert "prompt leakage" in result.parse_issues[-1]


def test_multi_value_token_crossing_columns_requests_strict_cell_retries(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    definition = next(panel for panel in schema.panels if panel.panel_id == "civic_continuation")
    columns = [
        ColumnSpan(9, "Source", "water_source", 100, 200, 0.0, 0.5),
        ColumnSpan(10, "Capacity", "water_capacity", 200, 300, 0.5, 1.0),
    ]
    panel = PanelGeometry(
        definition,
        2,
        (100, 0, 300, 50),
        (100, 0, 300, 10),
        (100, 10, 300, 50),
        columns,
        [9, 10],
        1.0,
    )
    result = OCRResult(0, 2, "", tokens=[OCRToken("702 1,006", [100, 0, 900, 1000])])

    assert PipelineRunner._cross_boundary_variables(
        schema, panel, result, (100, 10, 300, 50)
    ) == {"water_source", "water_capacity"}


def test_comma_joined_adjacent_integers_request_strict_cell_retries(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_003")
    definition = next(panel for panel in schema.panels if panel.panel_id == "tahsil_power_water")
    columns = [
        ColumnSpan(28, "Hand pump", "hand_pipe_villages", 100, 200, 0.0, 0.5),
        ColumnSpan(29, "Well", "well_villages", 200, 300, 0.5, 1.0),
    ]
    panel = PanelGeometry(
        definition,
        1,
        (100, 0, 300, 50),
        (100, 0, 300, 10),
        (100, 10, 300, 50),
        columns,
        [28, 29],
        1.0,
    )
    result = OCRResult(0, 1, "", tokens=[OCRToken("702,1,006", [100, 0, 900, 1000])])

    assert PipelineRunner._cross_boundary_variables(
        schema, panel, result, (100, 10, 300, 50)
    ) == {"hand_pipe_villages", "well_villages"}
    assert PipelineRunner._recover_joined_numeric_cells(
        schema, panel, result, (100, 10, 300, 50)
    ) == {"hand_pipe_villages": "702", "well_villages": "1,006"}


def test_two_comma_formatted_integers_are_partitioned_uniquely(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_003")
    definition = next(panel for panel in schema.panels if panel.panel_id == "tahsil_power_water")
    columns = [
        ColumnSpan(28, "Hand pump", "hand_pipe_villages", 100, 200, 0.0, 0.5),
        ColumnSpan(29, "Well", "well_villages", 200, 300, 0.5, 1.0),
    ]
    panel = PanelGeometry(
        definition,
        1,
        (100, 0, 300, 50),
        (100, 0, 300, 10),
        (100, 10, 300, 50),
        columns,
        [28, 29],
        1.0,
    )
    result = OCRResult(0, 1, "", tokens=[OCRToken("7,280,5,176", [100, 0, 900, 1000])])

    assert PipelineRunner._recover_joined_numeric_cells(
        schema, panel, result, (100, 10, 300, 50)
    ) == {"hand_pipe_villages": "7,280", "well_villages": "5,176"}


def test_vertically_repeated_grounding_requests_cell_recovery(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_002")
    definition = next(panel for panel in schema.panels if panel.panel_id == "mededu_continuation")
    columns = [
        ColumnSpan(10, "Higher secondary", "higher_secondary_schools", 0, 100, 0.0, 0.5),
        ColumnSpan(11, "Middle", "middle_schools", 100, 200, 0.5, 1.0),
    ]
    panel = PanelGeometry(
        definition,
        2,
        (0, 0, 200, 50),
        (0, 0, 200, 10),
        (0, 10, 200, 50),
        columns,
        [10, 11],
        1.0,
    )
    tokens = [
        OCRToken(value, [x0, y0, x1, y0 + 80])
        for y0 in (10, 300, 600)
        for value, x0, x1 in (("26", 100, 180), ("48", 600, 680))
    ]

    assert PipelineRunner._has_repeated_grounded_row(OCRResult(0, 2, "", tokens=tokens), panel)


def test_strict_cell_boundaries_follow_embedded_inter_cell_gap(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_003")
    definition = next(panel for panel in schema.panels if panel.panel_id == "tahsil_power_water")
    spans = [
        ColumnSpan(28, "Hand pump", "hand_pipe_villages", 100, 200, 0.0, 0.5),
        ColumnSpan(29, "Well", "well_villages", 200, 300, 0.5, 1.0),
    ]
    panel = PanelGeometry(
        definition,
        1,
        (100, 0, 300, 50),
        (100, 0, 300, 10),
        (100, 10, 300, 50),
        spans,
        [28, 29],
        1.0,
    )
    image = Image.new("RGB", (400, 100), "white")
    page = RenderedPage(
        page_number=1,
        dpi=300,
        image=image,
        np_image=np.full((100, 400, 3), 255, dtype=np.uint8),
        grayscale=np.full((100, 400), 255, dtype=np.uint8),
        binary=np.zeros((100, 400), dtype=np.uint8),
        pdf_text="702 1,006",
        pdf_words=[
            {"text": "702", "bbox": (135, 20, 185, 40)},
            {"text": "1,006", "bbox": (190, 20, 260, 40)},
        ],
        width=400,
        height=100,
    )

    bboxes = PipelineRunner._strict_cell_bboxes(page, panel, (100, 10, 300, 50))

    assert bboxes[28] == (100, 10, 187, 50)
    assert bboxes[29] == (187, 10, 300, 50)


def test_night_soil_code_validation_accepts_complete_sequences():
    assert PipelineRunner._valid_night_soil_code("HC/MT/B")
    assert PipelineRunner._valid_night_soil_code("MT/HL/B/HC")
    assert PipelineRunner._valid_night_soil_code("Nil")
    assert not PipelineRunner._valid_night_soil_code("HC/")
    assert not PipelineRunner._valid_night_soil_code("HC/MI/B")
    assert not PipelineRunner._valid_night_soil_code("B/H/L")
