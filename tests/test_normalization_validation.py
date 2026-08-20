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
