from __future__ import annotations

from census_extractor.normalization import normalize_null, normalize_rows, parse_road_lengths
from census_extractor.schemas import SchemaRegistry
from census_extractor.validation.validator import TableValidator


def test_null_and_road_normalization():
    for value in ("", "Nil", "—", "...", " … "):
        assert normalize_null(value) is None
    assert parse_road_lengths("PR 14.50 KR 3.20") == {
        "pucca_road_km": 14.5,
        "kutcha_road_km": 3.2,
    }


def test_cross_reference_retains_target_and_clears_data(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    rows = normalize_rows(
        [{"sl_no": "2", "town_name": "See Sl. No. 1 Agra (U.A.)", "water_borne_latrines": "999"}],
        schema,
    )
    assert rows[0].row_type == "CROSS_REFERENCE"
    assert rows[0].reference_target == "Sl. No. 1 Agra (U.A.)"
    assert rows[0].values["water_borne_latrines"] is None


def test_fuzzy_cross_reference_and_spaced_integer_normalization(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    rows = normalize_rows(
        [
            {
                "sl_no": "2",
                "town_name": "Agra Sec Agra City Urban Agglomeration",
                "water_borne_latrines": "7 0 8",
            },
            {
                "sl_no": "3",
                "town_name": "Bah",
                "water_borne_latrines": "7 0 8",
                "service_latrines": "8,100)",
            },
        ],
        schema,
    )
    assert rows[0].row_type == "CROSS_REFERENCE"
    assert rows[0].reference_target == "Agra City Urban Agglomeration"
    assert rows[0].values["water_borne_latrines"] is None
    assert rows[1].values["water_borne_latrines"] == 708
    assert rows[1].values["service_latrines"] == 8100
    cells = {cell.variable: cell for cell in rows[1].cells}
    assert cells["water_borne_latrines"].raw_value == "7 0 8"
    assert cells["water_borne_latrines"].review_flag == "SPACED_DIGITS"
    assert cells["service_latrines"].raw_value == "8,100)"
    assert cells["service_latrines"].review_flag == "TRAILING_MARK_REMOVED"


def test_ambiguous_numeric_ocr_is_preserved_and_flagged(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    row = normalize_rows(
        [{"sl_no": "1", "town_name": "Swamibagh", "elec_domestic": "2-0"}], schema
    )[0]
    cell = next(cell for cell in row.cells if cell.variable == "elec_domestic")
    assert row.values["elec_domestic"] is None
    assert cell.raw_value == "2-0"
    assert cell.review_flag == "AMBIGUOUS_OCR"
    assert cell.parse_error == "elec_domestic: expected integer for '2-0'"


def test_unrecognized_night_soil_code_is_preserved_and_flagged(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    rows = normalize_rows(
        [
            {"sl_no": "1", "town_name": "A", "night_soil_disposal_method": "HC/MT/B"},
            {"sl_no": "2", "town_name": "B", "night_soil_disposal_method": "HC/MI/B"},
        ],
        schema,
    )
    valid = next(cell for cell in rows[0].cells if cell.variable == "night_soil_disposal_method")
    ambiguous = next(
        cell for cell in rows[1].cells if cell.variable == "night_soil_disposal_method"
    )
    assert valid.raw_value == "HC/MT/B"
    assert valid.review_flag is None
    assert ambiguous.raw_value == "HC/MI/B"
    assert ambiguous.review_flag == "AMBIGUOUS_HISTORIC_CODE"


def test_typed_values_and_valid_quality(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    normalized = normalize_rows(
        [
            {
                "sl_no": "1",
                "town_name": "Agra",
                "water_borne_latrines": "12",
                "road_length_km": "PR 2.5",
                "fire_service": "Nil",
                "elec_domestic": "1",
                "elec_industrial": "1",
                "elec_commercial": "1",
                "elec_road_light": "1",
                "elec_other": "1",
                "sewerage_drainage_system": "Nil",
                "service_latrines": "1",
                "other_latrines": "1",
                "night_soil_disposal_method": "Nil",
                "water_source": "Nil",
                "water_capacity": "Nil",
            },
            {
                "sl_no": "2",
                "town_name": "Bah",
                "water_borne_latrines": "0",
                "road_length_km": "Nil",
                "fire_service": "Nil",
                "elec_domestic": "0",
                "elec_industrial": "0",
                "elec_commercial": "0",
                "elec_road_light": "0",
                "elec_other": "0",
                "sewerage_drainage_system": "Nil",
                "service_latrines": "0",
                "other_latrines": "0",
                "night_soil_disposal_method": "Nil",
                "water_source": "Nil",
                "water_capacity": "Nil",
            },
        ],
        schema,
    )
    report = TableValidator().validate(
        "sample",
        schema,
        normalized,
        panels_complete=True,
        aligned_row_counts={"a": 2, "b": 2},
        panel_scores=[1, 1],
        ocr_row_successes=4,
        ocr_row_total=4,
    )
    assert normalized[0].values["sl_no"] == "1"
    assert normalized[0].values["water_borne_latrines"] == 12
    assert normalized[0].values["pucca_road_km"] == 2.5
    assert report.is_valid
    assert report.quality.overall == 1


def test_invalid_integer_and_duplicate_identity_are_errors(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    normalized = normalize_rows(
        [
            {"sl_no": "1", "town_name": "Agra", "water_borne_latrines": "many"},
            {"sl_no": "1", "town_name": "Agra", "water_borne_latrines": "-2"},
        ],
        schema,
    )
    report = TableValidator().validate(
        "invalid",
        schema,
        normalized,
        panels_complete=True,
        aligned_row_counts={"a": 2, "b": 2},
        panel_scores=[1, 1],
        ocr_row_successes=4,
        ocr_row_total=4,
    )
    codes = {finding.code for finding in report.findings}
    assert {"type_parse", "serial_progression", "duplicate_identity", "nonnegative"}.issubset(codes)
    assert not report.is_valid


def test_tahsil_numeric_total_is_checked(project_config):
    schema = SchemaRegistry(project_config.schemas_dir).require("format_003")
    rows = normalize_rows(
        [
            {"sl_no": "1", "tahsil_name": "Agra", "junior_basic_villages": "2"},
            {"sl_no": "2", "tahsil_name": "Bah", "junior_basic_villages": "3"},
            {"tahsil_name": "DISTRICT TOTAL", "junior_basic_villages": "6"},
        ],
        schema,
    )
    report = TableValidator().validate(
        "tahsil",
        schema,
        rows,
        panels_complete=True,
        aligned_row_counts={panel.panel_id: 3 for panel in schema.panels},
        panel_scores=[1] * 4,
        ocr_row_successes=12,
        ocr_row_total=12,
    )
    assert any(finding.code == "tahsil_total_sum" for finding in report.findings)
