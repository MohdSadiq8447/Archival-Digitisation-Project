"""Generate state-specific civic and mededu schemas from the 1981 manifest."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


CIVIC_COLUMNS = [
    (1, "Sl. No.", "sl_no"),
    (2, "Class and name of town", "town_name"),
    (3, "Civic administration status (in 1980)", "civic_administration_status"),
    (4, "Population (in 1980)", "population"),
    (5, "Scheduled Castes and Scheduled Tribes population", "scheduled_caste_tribe_population"),
    (6, "Road Length (in Kms.)", "road_length_km"),
    (7, "System of sewerage", "sewerage_system"),
    (8, "Water-borne latrines", "water_borne_latrines"),
    (9, "Service latrines", "service_latrines"),
    (10, "Other latrines", "other_latrines"),
    (11, "Method of disposal of night soil", "night_soil_disposal_method"),
    (12, "Protected water supply - source of supply", "water_source"),
    (13, "System of storage with capacity in litres", "water_storage_capacity_litres"),
    (14, "Fire-fighting service", "fire_fighting_service"),
    (15, "Electrification - domestic", "electrification_domestic"),
    (16, "Electrification - industrial", "electrification_industrial"),
    (17, "Electrification - commercial", "electrification_commercial"),
    (18, "Electrification - road lighting (points)", "electrification_road_lighting"),
    (19, "Electrification - others", "electrification_others"),
]

MEDEDU_COLUMNS = [
    (1, "Sl. No.", "sl_no"),
    (2, "Class and name of town", "town_name"),
    (3, "Population", "population"),
    (4, "Hospitals/Dispensaries/T.B. Clinics etc.", "medical_facilities"),
    (5, "Beds in medical institutions noted in column 4", "medical_beds"),
    (6, "Arts/Science/Commerce Colleges", "degree_colleges"),
    (7, "Medical Colleges", "medical_colleges"),
    (8, "Engineering Colleges", "engineering_colleges"),
    (9, "Polytechnics", "polytechnics"),
    (10, "Recognised shorthand, typewriting and vocational training institutions", "vocational_training_institutes"),
    (11, "Higher Secondary/Intermediate/P.U.C./Pre-university/Junior College", "higher_secondary_intermediate_colleges"),
    (12, "Secondary/Matriculation", "secondary_matriculation"),
    (13, "Junior Secondary and Middle Schools", "junior_secondary_middle_schools"),
    (14, "Primary Schools", "primary_schools"),
    (15, "Adult literacy classes/others", "adult_literacy_classes_others"),
    (16, "Working women's hostels with number of seats", "working_womens_hostels_seats"),
    (17, "Stadia", "stadia"),
    (18, "Cinema", "cinemas"),
    (19, "Auditoria/Drama/Community halls", "auditoria_drama_community_halls"),
    (20, "Public libraries including reading rooms", "public_libraries_reading_rooms"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    return parser.parse_args()


def nums(start: int, end: int) -> list[int]:
    return list(range(start, end + 1))


def column_definitions(columns: list[tuple[int, str, str]]) -> list[dict[str, object]]:
    return [
        {
            "column_no": number,
            "column_name": label,
            "variable": variable,
            "data_type": "integer_or_code_or_string",
        }
        for number, label, variable in columns
    ]


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def table_config(table: str) -> dict[str, object]:
    if table == "civic_amenities":
        return {
            "format_id": "format_001",
            "name": "civic_amenities_1981",
            "statement": "Statement IV",
            "title": "Civic and Other Amenities, 1979",
            "columns": CIVIC_COLUMNS,
            "panels": [
                {
                    "panel_id": "civic_anchor",
                    "printed_columns": nums(1, 10),
                    "identity_columns": [1, 2],
                    "row_anchor": True,
                },
                {
                    "panel_id": "civic_continuation",
                    "printed_columns": nums(11, 19),
                    "identity_columns": [1, 2],
                    "align_to": "civic_anchor",
                },
            ],
            "layout_profiles": [
                {
                    "profile_id": "vertical_two_panel_single_page",
                    "page_layout": "Columns 1-10 followed vertically by columns 11-19 on one page.",
                },
                {
                    "profile_id": "repeated_two_panel_pages",
                    "page_layout": "Columns 1-10 and 11-19 may repeat across successive pages as town rows continue.",
                },
            ],
            "table_description": "Town Directory Statement IV: Civic and Other Amenities, 1979, with population and civic administration fields for 1980.",
            "notes": [
                "The printed table may use Civic administration status, Scheduled Castes and Scheduled Tribes population, and spelling variants such as Kms./Km.",
                "The continuation panel repeats the town identity columns 1 and 2 for row alignment.",
                "Preserve complete source pages, notes, abbreviations, and scan orientation; do not OCR, crop, or reflow.",
            ],
        }
    return {
        "format_id": "format_002",
        "name": "medical_educational_amenities_1981",
        "statement": "Statement V",
        "title": "Medical, Educational, Recreational and Cultural Facilities, 1979",
        "columns": MEDEDU_COLUMNS,
        "panels": [
            {
                "panel_id": "mededu_anchor",
                "printed_columns": nums(1, 11),
                "identity_columns": [1, 2],
                "row_anchor": True,
            },
            {
                "panel_id": "mededu_continuation",
                "printed_columns": nums(12, 20),
                "identity_columns": [1, 2],
                "align_to": "mededu_anchor",
            },
        ],
        "layout_profiles": [
            {
                "profile_id": "vertical_two_panel_single_page",
                "page_layout": "Columns 1-11 followed vertically by columns 12-20 on one page.",
            },
            {
                "profile_id": "repeated_two_panel_pages",
                "page_layout": "Columns 1-11 and 12-20 may repeat across successive pages as town rows continue.",
            },
        ],
        "table_description": "Town Directory Statement V: Medical, Educational, Recreational and Cultural Facilities, 1979.",
        "notes": [
            "The printed table uses medical facilities and educational, recreational, and cultural facility groups; wording and line breaks vary across scans.",
            "The continuation panel repeats the town identity columns 1 and 2 for row alignment.",
            "Preserve complete source pages, notes, abbreviations, and scan orientation; do not OCR, crop, or reflow.",
        ],
    }


def read_manifest(root: Path) -> list[dict[str, object]]:
    path = root / "output" / "audit" / "1981_full_manifest.json"
    if not path.is_file():
        raise RuntimeError(f"Missing manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_schema(root: Path, state: str, table: str, rows: list[dict[str, object]]) -> dict[str, object]:
    config = table_config(table)
    completed = [row for row in rows if row.get("status") == "Trimmed"]
    if not completed:
        raise RuntimeError(f"No completed {table} outputs for {state}")
    completed.sort(key=lambda row: str(row.get("district", "")))
    output_files = [str(row["output"]) for row in completed]
    for output in output_files:
        if not (root / Path(output)).is_file():
            raise RuntimeError(f"Manifest output missing: {root / Path(output)}")
    page_counts = {
        str(row["district"]): int((row.get("verification") or {}).get("output_pages", 0))
        for row in completed
    }
    districts = [str(row["district"]) for row in completed]
    return {
        "format_id": config["format_id"],
        "name": f"{config['name']}_{slug(state)}",
        "state": state,
        "source_year": 1981,
        "table": config["statement"],
        "table_description": config["table_description"],
        "district_format_assignments": {config["format_id"]: districts},
        "availability": {
            "trimmed_pdf_count": len(completed),
            "districts": len(districts),
            "source_files": [str(row["source_filename"]) for row in completed],
            "output_files": output_files,
            "page_count_by_district": page_counts,
            "content_check": f"All {len(completed)} completed PDFs contain {config['statement']} content.",
        },
        "page_layout": {
            "logical_printed_columns": len(config["columns"]),
            "panels": config["panels"],
            "allowed_profiles": config["layout_profiles"],
            "selection_rule": "Retain every trimmed page belonging to the statement, including repeated headers, continuation rows, totals, footnotes, and notes.",
        },
        "column_definitions": column_definitions(config["columns"]),
        "format_notes": config["notes"],
    }


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    manifest = read_manifest(root)
    states = sorted({str(row["state"]) for row in manifest})
    schema_root = root / "schemas"
    written = []
    for state in states:
        state_rows = [row for row in manifest if str(row["state"]) == state]
        for table in ("civic_amenities", "medical_educational_amenities"):
            schema = build_schema(root, state, table, [row for row in state_rows if row.get("table") == table])
            path = schema_root / state / f"{schema['format_id']}.yaml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml.safe_dump(schema, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
            written.append(path)
        print(f"{state}: wrote format_001.yaml and format_002.yaml")
    print(f"Wrote {len(written)} schema files for {len(states)} states/UTs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
