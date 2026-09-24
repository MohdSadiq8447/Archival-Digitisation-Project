from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas"
TRIM_ROOT = ROOT / "output" / "pdf" / "1971_trimmed"


def nums(start: int, end: int) -> list[int]:
    return list(range(start, end + 1))


CIVIC_COLUMNS = [
    (1, "Sl. No.", "sl_no"),
    (2, "Name of Town", "town_name"),
    (3, "Road Length (km)", "road_length_km"),
    (4, "System of Sewerage/Drainage", "sewerage_drainage_system"),
    (5, "Water-Borne Latrines", "water_borne_latrines"),
    (6, "Service Latrines", "service_latrines"),
    (7, "Other Latrines", "other_latrines"),
    (8, "Method of Disposal of Night-Soil", "night_soil_disposal_method"),
    (9, "Protected Water Supply - Source", "water_source"),
    (10, "Protected Water Supply - Capacity", "water_capacity"),
    (11, "Fire Fighting Service", "fire_fighting_service"),
    (12, "Electrification - Domestic", "electrification_domestic"),
    (13, "Electrification - Industrial", "electrification_industrial"),
    (14, "Electrification - Commercial", "electrification_commercial"),
    (15, "Electrification - Road Lighting", "electrification_road_lighting"),
    (16, "Electrification - Others", "electrification_others"),
]

MEDEDU_COLUMNS = [
    (1, "Sl. No.", "sl_no"),
    (2, "Name of Town", "town_name"),
    (3, "Hospitals/Dispensaries/T.B. Clinics/Health Centres/Nursing Homes", "medical_facilities"),
    (4, "Beds in Medical Institutions", "medical_beds"),
    (5, "Arts/Science/Commerce Colleges", "degree_colleges"),
    (6, "Medical Colleges", "medical_colleges"),
    (7, "Engineering Colleges", "engineering_colleges"),
    (8, "Polytechnics", "polytechnics"),
    (9, "Shorthand/Typewriting/Vocational Training Institutes", "vocational_training_institutes"),
    (10, "Higher Secondary or Secondary Schools", "higher_secondary_or_secondary_schools"),
    (11, "Junior Secondary/Middle Schools", "junior_secondary_or_middle_schools"),
    (12, "Primary Schools", "primary_schools"),
    (13, "Other Educational Institutions", "other_educational_institutions"),
    (14, "Stadia", "stadia"),
    (15, "Cinemas", "cinemas"),
    (16, "Auditoria/Drama Halls", "auditoria_drama_halls"),
    (17, "Public Libraries and Reading Rooms", "public_libraries_reading_rooms"),
]


def column_rows(rows: list[tuple[int, str, str]]) -> list[dict[str, object]]:
    return [
        {
            "column_no": no,
            "column_name": label,
            "variable": variable,
            "data_type": "integer_or_code_or_string",
        }
        for no, label, variable in rows
    ]


def common_availability(output_folder: str) -> dict[str, object]:
    folder = TRIM_ROOT / output_folder
    pdfs = sorted(p.name for p in folder.glob("*.pdf")) if folder.exists() else []
    table_suffixes = {
        "format_001": "_civic_amenities.pdf",
        "format_002": "_medical_educational_amenities.pdf",
        "format_003": "_tehsil_appendix.pdf",
    }
    counts = {key: sum(name.endswith(suffix) for name in pdfs) for key, suffix in table_suffixes.items()}
    districts: dict[str, list[str]] = {}
    for key, suffix in table_suffixes.items():
        districts[key] = [name[: -len(suffix)].removeprefix("1971_") for name in pdfs if name.endswith(suffix)]
    reviews: list[dict[str, object]] = []
    for review_path in sorted(folder.glob("*_review.json")) if folder.exists() else []:
        try:
            data = json.loads(review_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    reviews.append({
                        "source": item.get("source") or item.get("district"),
                        "table": item.get("table"),
                        "status": item.get("status"),
                        "reason": item.get("reason"),
                    })
    return {
        "trimmed_pdf_counts": counts,
        "trimmed_districts": districts,
        "review_records": reviews,
    }


def common_layouts(columns: int) -> list[dict[str, object]]:
    if columns == 16:
        return [
            {
                "variant_id": "horizontal_8_plus_8",
                "page_1_printed_columns": nums(1, 8),
                "page_2_printed_columns": nums(9, 16),
                "when_to_use": "The page heading or printed column-number row proves a horizontal split.",
            },
            {
                "variant_id": "full_width_row_continuation",
                "page_1_printed_columns": nums(1, 16),
                "later_page_printed_columns": nums(1, 16),
                "when_to_use": "Each page repeats the complete Statement IV header and continues town rows.",
            },
        ]
    return [
        {
            "variant_id": "horizontal_9_plus_8",
            "page_1_printed_columns": nums(1, 9),
            "page_2_printed_columns": nums(10, 17),
            "when_to_use": "The page heading or printed column-number row proves a horizontal split.",
        },
        {
            "variant_id": "full_width_row_continuation",
            "page_1_printed_columns": nums(1, 17),
            "later_page_printed_columns": nums(1, 17),
            "when_to_use": "Each page repeats the complete Statement V header and continues town rows.",
        },
    ]


def make_common_doc(state: dict[str, object], format_id: str, availability: dict[str, object]) -> dict[str, object]:
    is_civic = format_id == "format_001"
    cols = CIVIC_COLUMNS if is_civic else MEDEDU_COLUMNS
    table_name = "civic_amenities" if is_civic else "medical_educational_amenities"
    statement = "Statement IV — Civic and Other Amenities" if is_civic else "Statement V — Medical, Educational, Recreational and Cultural Facilities"
    width = 16 if is_civic else 17
    preferred = state.get("town_layout", "detect_from_headings")
    return {
        "format_id": format_id,
        "name": f"{table_name}_1971_{state['slug']}",
        "source_state": state["source_state"],
        "source_folder": state["source_folder"],
        "table_description": f"{statement} in the 1971 district Town Directory. Preserve complete original source pages; do not OCR, crop, or reflow.",
        "availability": availability,
        "layout_rules": {
            "total_printed_columns": width,
            "preferred_profile": preferred,
            "allowed_profiles": common_layouts(width),
            "page_selection": "Use the first page containing the statement heading and every later page with repeated headers, continuation markers, totals, or table notes.",
            "ambiguity_rule": "If the printed column-number row and table headings do not identify one allowed profile, set status to review_required and do not extract by page position alone.",
        },
        "panels": [
            {
                "panel_id": "statement_anchor",
                "printed_columns": nums(1, width),
                "identity_columns": [1, 2],
                "headings": ["town directory", "statement iv" if is_civic else "statement v"],
                "row_anchor": True,
            },
            {
                "panel_id": "statement_continuation",
                "printed_columns": nums(1, width),
                "identity_columns": [1, 2],
                "headings": ["continuation", "town directory"],
                "align_to": "statement_anchor",
            },
        ],
        "column_definitions": column_rows(cols),
    }


STANDARD50 = [
    (1, "Sl. No.", "sl_no"), (2, "Name of Tahsil/Tehsil", "tahsil_name"),
    (3, "Villages having Junior Basic/Primary Schools", "junior_basic_villages"), (4, "Junior Basic/Primary Schools", "junior_basic_schools"),
    (5, "Villages having Middle/Senior Basic Schools", "middle_villages"), (6, "Middle/Senior Basic Schools", "middle_schools"),
    (7, "Villages having Higher Secondary Schools", "higher_secondary_villages"), (8, "Higher Secondary Schools", "higher_secondary_schools"),
    (9, "Villages having Colleges", "college_villages"), (10, "Colleges", "colleges"),
    (11, "Villages having Other Educational Institutions", "other_education_villages"), (12, "Other Educational Institutions", "other_educational_institutions"),
    (13, "Villages having Hospitals", "hospital_villages"), (14, "Hospitals", "hospitals"),
    (15, "Villages having Dispensaries", "dispensary_villages"), (16, "Dispensaries", "dispensaries"),
    (17, "Villages having M.C.W. Centres", "mcw_villages"), (18, "M.C.W. Centres", "mcw_centres"),
    (19, "Villages having Health Centres", "health_centre_villages"), (20, "Health Centres", "health_centres"),
    (21, "Villages having Family Planning Centres", "family_planning_villages"), (22, "Family Planning Centres", "family_planning_centres"),
    (23, "Villages having Other Medical Institutions", "other_medical_villages"), (24, "Other Medical Institutions", "other_medical_institutions"),
    (25, "Villages with Power Supply Available", "power_available_villages"), (26, "Villages with Power Supply Not Available", "power_not_available_villages"),
    (27, "Villages having Tap Water", "tap_water_villages"), (28, "Villages having Hand Pipe", "hand_pipe_villages"),
    (29, "Villages having Well", "well_villages"), (30, "Villages having Tank", "tank_villages"),
    (31, "Villages having River", "river_villages"), (32, "Villages having Fountain", "fountain_villages"),
    (33, "Villages having Canal", "canal_villages"), (34, "Villages having Water Fall", "water_fall_villages"),
    (35, "Villages having Lake", "lake_villages"), (36, "Villages having Tube-Well", "tube_well_villages"),
    (37, "Villages having Other Water Source", "other_water_villages"), (38, "Villages with No Water Source", "no_water_villages"),
    (39, "Villages having Pucca Road", "pucca_road_villages"), (40, "Villages having Kachcha Road", "kachcha_road_villages"),
    (41, "Villages having Pucca and Kachcha Road", "pucca_kachcha_road_villages"), (42, "Villages having Other Road", "other_road_villages"),
    (43, "Villages having Post Office", "post_office_villages"), (44, "Post Offices", "post_offices"),
    (45, "Villages having Telegraph Office", "telegraph_office_villages"), (46, "Telegraph Offices", "telegraph_offices"),
    (47, "Villages having Post & Telegraph Office", "post_telegraph_villages"), (48, "Post & Telegraph Offices", "post_telegraph_offices"),
    (49, "Villages having Telephone", "telephone_villages"), (50, "Telephones", "telephones"),
]


def rows_with_identity(labels: list[str]) -> list[tuple[int, str, str]]:
    rows = [(1, "Sl. No.", "sl_no"), (2, "Name of District/Tehsil/Taluk/Circle", "area_name")]
    for no, label in enumerate(labels, 3):
        rows.append((no, label, re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")))
    return rows


def profile_standard50() -> dict[str, object]:
    return {
        "profile_id": "standard_50_two_page_packed",
        "status": "ready",
        "total_printed_columns": 50,
        "page_layout": [
            {"page": 1, "printed_columns": nums(1, 12) + nums(25, 38), "panels": ["educational", "power_water"], "identity_columns": [1, 2]},
            {"page": 2, "printed_columns": nums(13, 24) + nums(39, 50), "panels": ["medical", "communications"], "identity_columns": [1, 2]},
        ],
        "column_definitions": column_rows(STANDARD50),
    }


def profile_gujarat44() -> dict[str, object]:
    labels = [
        "Sl. No.", "Name of Taluka/Mahal", "Villages having Primary Schools", "Primary Schools",
        "Villages having Middle Schools", "Middle Schools", "Villages having Higher Secondary Schools", "Higher Secondary Schools",
        "Villages having Colleges", "Colleges", "Villages having Other Educational Institutions", "Other Educational Institutions",
        "Villages having Dispensaries", "Dispensaries", "Villages having Hospitals", "Hospitals",
        "Villages having Maternity & Child Welfare Centres", "Maternity & Child Welfare Centres", "Villages having Health Centres", "Health Centres",
        "Villages having Other Medical Institutions", "Other Medical Institutions", "Villages having Family Planning Centres", "Family Planning Centres",
        "Villages where Power Supply is Available", "Villages where Power Supply is Not Available", "Villages having Tap", "Villages having Well", "Villages having Tank", "Villages having Tube Well", "Villages having River", "Villages having Fountain", "Villages having Canal", "Villages having Other Water Source", "Villages where Water is Not Available",
        "Villages having Pucca Road", "Villages having Kutchha Road", "Villages having Post Office", "Post Offices", "Villages having Telegraph Office", "Telegraph Offices", "Villages having Post & Telegraph Office", "Post & Telegraph Offices", "Villages having Telephone",
    ]
    return {
        "profile_id": "gujarat_44_two_page",
        "status": "ready",
        "total_printed_columns": 44,
        "page_layout": [
            {"page": 1, "printed_columns": nums(1, 22), "panels": ["educational", "medical_through_other_medical"], "identity_columns": [1, 2]},
            {"page": 2, "printed_columns": nums(23, 44), "panels": ["family_planning", "power_water", "communications", "postal_telegraph"], "identity_columns": [1, 2]},
        ],
        "column_definitions": column_rows(list(enumerate(labels, 1)) if False else [(i + 1, label, re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")) for i, label in enumerate(labels)]),
    }


def profile_rajasthan36() -> dict[str, object]:
    labels = [
        "Sl. No.", "District/Tehsil", "Villages having Primary Schools", "Primary Schools", "Villages having Middle Schools", "Middle Schools",
        "Villages having Higher/Higher Secondary Schools", "Higher/Higher Secondary Schools", "Number of Colleges",
        "Villages having Dispensaries", "Dispensaries", "Villages having Hospitals", "Hospitals", "Villages having Health Centres", "Health Centres",
        "Villages having Maternity & Child Welfare Centres", "Maternity & Child Welfare Centres", "Villages having Family Planning Centres", "Family Planning Centres",
        "Villages where Power Supply is Available", "Villages where Power Supply is Not Available", "Villages having Tap", "Villages having Well", "Villages having Tank", "Villages having River", "Villages having Tube Well", "Villages having Other Water Source",
        "Villages having Pucca Road", "Villages having Katcha Road", "Villages having Railway Station", "Villages having Post Office", "Post Offices", "Villages having Telegraph Office", "Telegraph Offices", "Villages having Post & Telegraph Office", "Post & Telegraph Offices",
    ]
    return {
        "profile_id": "rajasthan_36_two_page_packed",
        "status": "ready",
        "total_printed_columns": 36,
        "page_layout": [
            {"page": 1, "printed_columns": nums(1, 9) + nums(20, 30), "panels": ["educational", "power_water", "communications"], "identity_columns": [1, 2]},
            {"page": 2, "printed_columns": nums(10, 19) + nums(31, 36), "panels": ["medical", "postal_telegraph"], "identity_columns": [1, 2]},
        ],
        "column_definitions": column_rows([(i + 1, label, re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")) for i, label in enumerate(labels)]),
    }


def profile_kerala36() -> dict[str, object]:
    labels = [
        "Sl. No.", "District/Taluk", "Villages having Primary Schools", "Primary Schools", "Villages having Middle Schools", "Middle Schools",
        "Villages having Hr. Sec. Schools", "Hr. Sec. Schools", "Villages having Colleges", "Colleges", "Villages having Other Educational Institutions", "Other Educational Institutions",
        "Villages having Dispensaries", "Dispensaries", "Villages having Hospitals", "Hospitals", "Villages having Other Medical Institutions", "Other Medical Institutions",
        "Villages where Power Supply is Available", "Villages where Power Supply is Not Available", "Villages having Tap", "Villages having Well", "Villages having Other Water Source",
        "Villages having Pucca Road", "Villages having Kacha Road", "Villages having Post Office", "Post Offices", "Villages having Telegraph Office", "Telegraph Offices",
        "Villages having Post & Telegraph Office", "Post & Telegraph Offices", "Villages having Public Call Office", "Public Call Offices", "Villages having Telephone", "Telephones", "Other Communication Facility",
    ]
    return {
        "profile_id": "kerala_36_three_page",
        "status": "ready",
        "total_printed_columns": 36,
        "page_layout": [
            {"page": 1, "printed_columns": nums(1, 12), "panels": ["educational"], "identity_columns": [1, 2]},
            {"page": 2, "printed_columns": nums(13, 23), "panels": ["medical", "power_water"], "identity_columns": [1, 2]},
            {"page": 3, "printed_columns": nums(24, 36), "panels": ["roads", "communications", "postal_telegraph"], "identity_columns": [1, 2]},
        ],
        "column_definitions": column_rows([(i + 1, label, re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")) for i, label in enumerate(labels)]),
    }


def profile_punjab33() -> dict[str, object]:
    labels = [
        "Sl. No.", "Name of Tahsil", "Villages having Primary Schools", "Primary Schools", "Villages having Middle Schools", "Middle Schools",
        "Villages having High or Higher Secondary Schools", "High or Higher Secondary Schools", "Villages having Colleges", "Colleges", "Villages having Other Educational Institutions", "Other Educational Institutions",
        "Villages having Dispensaries", "Dispensaries", "Villages having Hospitals", "Hospitals", "Villages having Family Planning Centres", "Family Planning Centres", "Villages having Other Medical Institutions", "Other Medical Institutions",
        "Villages where Power Supply is Available", "Villages where Power Supply is Not Available", "Villages having Tap/Water Supply", "Villages having Well", "Villages having Tube Well", "Villages having Other Water Source",
        "Villages having Pucca Road", "Villages having Kachcha Road", "Villages having Post Office", "Post Offices", "Villages having Telegraph Office", "Telegraph Offices", "Villages having Telephone",
    ]
    return {
        "profile_id": "punjab_33_two_page",
        "status": "ready",
        "total_printed_columns": 33,
        "page_layout": [{"page": 1, "printed_columns": nums(1, 16), "panels": ["educational", "medical_through_hospital"], "identity_columns": [1, 2]}, {"page": 2, "printed_columns": nums(17, 33), "panels": ["medical_other", "power_water", "communications", "postal_telegraph"], "identity_columns": [1, 2]}],
        "column_definitions": column_rows([(i + 1, label, re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")) for i, label in enumerate(labels)]),
    }


def profile_tripura39() -> dict[str, object]:
    labels = [
        "Sl. No.", "Name of Sub-Division", "Villages having Primary Schools", "Primary Schools", "Villages having Middle Schools", "Middle Schools",
        "Villages having Secondary/Higher Secondary Schools", "Secondary/Higher Secondary Schools", "Villages having Colleges", "Colleges", "Villages having Other Educational Institutions", "Other Educational Institutions",
        "Villages having Dispensaries", "Dispensaries", "Villages having Health Centres", "Health Centres", "Villages having Hospitals", "Hospitals",
        "Villages having Family Planning Centres", "Family Planning Centres", "Villages having Maternity & Child Welfare Centres", "Maternity & Child Welfare Centres", "Villages having Veterinary Dispensaries", "Veterinary Dispensaries",
        "Villages where Power Supply is Available", "Villages where Power Supply is Not Available", "Villages having Tap", "Villages having Tube Well", "Villages having Well", "Villages having River", "Villages having Canal", "Villages having Other Water Source",
        "Villages having Pucca Road", "Villages having Katcha Road", "Villages having Railway Station", "Villages having Post Office", "Post Offices", "Villages having Telegraph Office", "Telegraph Offices",
    ]
    return {
        "profile_id": "tripura_39_two_page",
        "status": "ready",
        "total_printed_columns": 39,
        "page_layout": [{"page": 1, "printed_columns": nums(1, 18), "panels": ["educational", "medical"], "identity_columns": [1, 2]}, {"page": 2, "printed_columns": nums(19, 39), "panels": ["medical_other", "power_water", "communications", "postal_telegraph"], "identity_columns": [1, 2]}],
        "column_definitions": column_rows([(i + 1, label, re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")) for i, label in enumerate(labels)]),
    }


def profile_manipur47() -> dict[str, object]:
    labels = [
        "Sl. No.", "Name of Sub-Division", "Villages having Primary Schools", "Primary Schools", "Villages having Middle Schools", "Middle Schools",
        "Villages having Junior High Schools", "Junior High Schools", "Villages having High Schools", "High Schools", "Villages having Higher Secondary Schools", "Higher Secondary Schools",
        "Villages having Up-graded Middle Schools", "Up-graded Middle Schools", "Villages having E.G. Schools", "E.G. Schools", "Villages having Colleges", "Colleges", "Villages having Dispensaries", "Dispensaries", "Villages having Hospitals", "Hospitals", "Other Medical Institutions",
        "Villages having Family Planning Centres", "Family Planning Centres", "Villages having Maternity & Child Welfare Centres", "Maternity & Child Welfare Centres", "Villages having T.B. Hospitals", "T.B. Hospitals", "Villages having Health Centres", "Health Centres", "Villages where Power Supply is Available", "Villages where Power Supply is Not Available",
        "Villages having Tap", "Villages having Well", "Villages having River", "Villages having Other Water Source", "Villages having Pucca Road", "Villages having Katcha Road", "Villages having River/Railway Connection", "Villages having Post Office", "Post Offices", "Villages having Telegraph Office", "Telegraph Offices", "Villages having Post & Telegraph Office", "Post & Telegraph Offices", "Villages having Telephone/Telephone Centre",
    ]
    return {
        "profile_id": "manipur_47_two_page",
        "status": "ready",
        "total_printed_columns": 47,
        "page_layout": [{"page": 1, "printed_columns": nums(1, 23), "panels": ["educational", "medical"], "identity_columns": [1, 2]}, {"page": 2, "printed_columns": nums(24, 47), "panels": ["medical_other", "power_water", "communications", "postal_telegraph"], "identity_columns": [1, 2]}],
        "column_definitions": column_rows([(i + 1, label, re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")) for i, label in enumerate(labels)]),
    }


def profile_nagaland28() -> dict[str, object]:
    return {
        "profile_id": "circle_28_two_page",
        "status": "ready",
        "total_printed_columns": 28,
        "page_layout": [{"page": 1, "printed_columns": nums(1, 12), "panels": ["educational"], "identity_columns": [1, 2]}, {"page": 2, "printed_columns": nums(13, 28), "panels": ["medical", "power_water", "communications", "postal_telegraph"], "identity_columns": [1, 2]}],
        "column_definitions": column_rows([(i, label, variable) for i, label, variable in STANDARD50[:2] + STANDARD50[2:12] + STANDARD50[12:28]]),
    }


def profile_meghalaya39() -> dict[str, object]:
    labels = [
        "Serial No.", "Name of Taluk/Police Station", "Villages having Primary Schools", "Primary Schools", "Villages having Middle Schools", "Middle Schools",
        "Villages having Higher or Secondary Schools", "Higher or Secondary Schools", "Villages having Colleges", "Colleges", "Other Educational Institutions", "Other Educational Institutions Count",
        "Villages having Dispensaries", "Dispensaries", "Villages having Hospitals", "Hospitals", "Villages having Maternity & Child Welfare Centres", "Maternity & Child Welfare Centres", "Villages having Health Centres", "Health Centres", "Villages having Family Planning Centres", "Family Planning Centres",
        "Villages where Power Supply is Available", "Villages where Power Supply is Not Available", "Villages having Tap", "Villages having Well", "Villages having Tube Well", "Villages having River", "Villages having Fountain", "Villages having Canal", "Villages having Other Water Source", "Villages having Pucca Road", "Villages having Kachcha Road", "Villages having Post Office", "Post Offices", "Villages having Telegraph Office", "Telegraph Offices", "Villages having Post & Telegraph Office", "Post & Telegraph Offices",
    ]
    return {
        "profile_id": "meghalaya_police_station_39_two_page",
        "status": "ready",
        "total_printed_columns": 39,
        "page_layout": [{"page": 1, "printed_columns": nums(1, 21), "panels": ["educational", "medical"], "identity_columns": [1, 2]}, {"page": 2, "printed_columns": nums(22, 39), "panels": ["power_water", "communications", "postal_telegraph"], "identity_columns": [1, 2]}],
        "column_definitions": column_rows([(i + 1, label, re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")) for i, label in enumerate(labels)]),
    }


def profile_orissa36() -> dict[str, object]:
    labels = [
        "Sl. No.", "Name of Tahsil", "Villages having Primary Schools", "Primary Schools", "Villages having Middle Schools", "Middle Schools",
        "Villages having High/Higher Secondary Schools", "High/Higher Secondary Schools", "Villages having Colleges", "Colleges", "Villages having Other Educational Institutions", "Other Educational Institutions",
        "Villages having Dispensaries", "Dispensaries", "Villages having Hospitals", "Hospitals", "Villages having Health Centres", "Health Centres", "Villages having Family Planning Centres", "Family Planning Centres",
        "Villages where Power Supply is Available", "Villages where Power Supply is Not Available", "Villages having Tap", "Villages having Well", "Villages having Tank", "Villages having River", "Villages having Tube Well", "Villages having Other Water Source",
        "Villages having Pucca Road", "Villages having Katcha Road", "Villages having Post Office", "Post Offices", "Villages having Telegraph Office", "Telegraph Offices", "Villages having Post & Telegraph Office", "Post & Telegraph Offices",
    ]
    return {
        "profile_id": "orissa_36_two_page",
        "status": "ready",
        "total_printed_columns": 36,
        "page_layout": [{"page": 1, "printed_columns": nums(1, 20), "panels": ["educational", "medical"], "identity_columns": [1, 2]}, {"page": 2, "printed_columns": nums(21, 36), "panels": ["power_water", "communications", "postal_telegraph"], "identity_columns": [1, 2]}],
        "column_definitions": column_rows([(i + 1, label, re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")) for i, label in enumerate(labels)]),
    }


def profile_tamil_vertical() -> dict[str, object]:
    return {
        "profile_id": "tamil_nadu_appendix_ii_vertical_taluk",
        "status": "ready",
        "page_layout": "One complete Appendix II table per source page/taluk; this is a vertical list of facility rows, not a horizontal 36/50-column aggregate.",
        "column_numbering": "The source prints column (1) for the nature of facility and column (2) for the figure/availability value. Do not apply the 50-column Tahsil map.",
        "column_definitions": column_rows([(1, "Nature of facility", "facility_name"), (2, "Figure/availability", "facility_value")]),
        "row_groups": ["Educational", "Medical", "Other amenities", "Power supply", "Drinking water", "Communications", "Post and Telegraph"],
    }


PROFILE_BUILDERS = {
    "standard50": profile_standard50,
    "gujarat44": profile_gujarat44,
    "rajasthan36": profile_rajasthan36,
    "kerala36": profile_kerala36,
    "punjab33": profile_punjab33,
    "tripura39": profile_tripura39,
    "manipur47": profile_manipur47,
    "nagaland28": profile_nagaland28,
    "meghalaya39": profile_meghalaya39,
    "orissa36": profile_orissa36,
    "tamil_vertical": profile_tamil_vertical,
}


STATE_CONFIGS: dict[str, dict[str, object]] = {
    "bihar": {"source_state": "Bihar", "source_folder": "Bihar", "output_folder": "Bihar", "format3": "standard50", "town_layout": "detect_from_headings"},
    "dadra_nagar_haveli": {"source_state": "Dadra & Nagar Haveli", "source_folder": "Dadra & Nagar Haveli", "output_folder": "Dadra & Nagar Haveli", "format3": "review_dnh", "town_layout": "full_width_row_continuation"},
    "daman_diu": {"source_state": "Daman & Diu", "source_folder": "Darman & Diu", "output_folder": "Daman & Diu", "format3": "review_daman", "town_layout": "detect_from_headings"},
    "gujarat": {"source_state": "Gujarat", "source_folder": "Gujarat", "output_folder": "Gujarat", "format3": "gujarat44", "town_layout": "full_width_row_continuation"},
    "haryana": {"source_state": "Haryana", "source_folder": "Haryana", "output_folder": "Haryana", "format3": "unavailable", "town_layout": "unavailable"},
    "jammu_kashmir": {"source_state": "Jammu & Kashmir", "source_folder": "Jammu & Kashmir", "output_folder": "Jammu & Kashmir", "format3": "standard50", "town_layout": "full_width_row_continuation"},
    "karnataka": {"source_state": "Karnataka", "source_folder": "Karnataka", "output_folder": "Karnataka", "format3": "review_karnataka", "town_layout": "full_width_row_continuation"},
    "kerala": {"source_state": "Kerala", "source_folder": "Kerala", "output_folder": "Kerala", "format3": "kerala36", "town_layout": "full_width_row_continuation"},
    "maharashtra": {"source_state": "Maharashtra", "source_folder": "Maharashtra", "output_folder": "Maharashtra", "format3": "unavailable_removed", "town_layout": "full_width_row_continuation"},
    "manipur": {"source_state": "Manipur", "source_folder": "Manipur", "output_folder": "Manipur", "format3": "manipur47", "town_layout": "full_width_row_continuation"},
    "meghalaya": {"source_state": "Meghalaya", "source_folder": "Meghalaya", "output_folder": "Meghalaya", "format3": "meghalaya39", "town_layout": "full_width_row_continuation"},
    "nagaland": {"source_state": "Nagaland", "source_folder": "Nagaland", "output_folder": "Nagaland", "format3": "nagaland28", "town_layout": "full_width_row_continuation"},
    "orissa": {"source_state": "Orissa", "source_folder": "Orissa", "output_folder": "Orissa", "format3": "orissa36", "town_layout": "full_width_row_continuation"},
    "punjab": {"source_state": "Punjab", "source_folder": "Punjab", "output_folder": "Punjab", "format3": "punjab33", "town_layout": "full_width_row_continuation"},
    "rajasthan": {"source_state": "Rajasthan", "source_folder": "Rajasthan", "output_folder": "Rajasthan", "format3": "rajasthan36", "town_layout": "full_width_row_continuation"},
    "sikkim": {"source_state": "Sikkim", "source_folder": "Sikkim", "output_folder": "Sikkim", "format3": "unavailable", "town_layout": "full_width_row_continuation"},
    "tamil_nadu": {"source_state": "Tamil Nadu", "source_folder": "Tamil Nadu", "output_folder": "Tamil Nadu", "format3": "tamil_vertical", "town_layout": "full_width_row_continuation"},
    "tripura": {"source_state": "Tripura", "source_folder": "Tripura", "output_folder": "Tripura", "format3": "tripura39", "town_layout": "full_width_row_continuation"},
    "west_bengal": {"source_state": "West Bengal", "source_folder": "West Bengal", "output_folder": "West Bengal", "format3": "unavailable", "town_layout": "full_width_row_continuation"},
}


def review_reason(config: dict[str, object], format_id: str) -> str | None:
    mode = config["format3"]
    if format_id != "format_003":
        return None
    return {
        "review_dnh": "The supplied appendix is a two-page Taluka abstract with only columns 1–15 legible in the inspected first page; the continuation column boundary must be checked before assigning a complete map.",
        "review_daman": "The combined Goa, Daman and Diu appendix is a two-page Taluka abstract; the full printed column boundary varies across the combined volume and requires page-level confirmation.",
        "review_karnataka": "The Karnataka appendix has a two-page Talukwise layout with regional abbreviations and continuation panels; the inspected page confirms the headings but not a safe complete printed-column map for every district.",
        "unavailable": "No eligible trimmed Tehsil/Taluk/Circle amenities appendix is available in the current inventory; no column map is inferred.",
        "unavailable_removed": "All Maharashtra Tehsil Appendix PDFs were removed after the prior page-span audit; no column map is used until replacement pages are verified.",
    }.get(mode)


def make_format3_doc(state: dict[str, object], availability: dict[str, object]) -> dict[str, object]:
    mode = state["format3"]
    reason = review_reason(state, "format_003")
    base: dict[str, object] = {
        "format_id": "format_003",
        "name": f"tehsil_or_taluk_amenities_1971_{state['slug']}",
        "source_state": state["source_state"],
        "source_folder": state["source_folder"],
        "table_description": "Tehsil/Taluk/Tahsil/Circle/Police-station equivalent amenities abstract. Preserve complete original source pages and source ordering; terminology is state-specific.",
        "availability": availability,
        "selection_rules": [
            "Match the appendix heading and the printed column-number row before selecting a profile.",
            "Use the state-specific profile only when every printed column in the page span is accounted for.",
            "Retain continuation pages, totals, footnotes, and notes; never trim a single page solely because the table appears to start on it.",
            "If the heading, continuation marker, or column numbering is ambiguous, set status to review_required and do not infer.",
        ],
    }
    if mode in PROFILE_BUILDERS:
        base["schema_status"] = "ready"
        base["layout_profiles"] = [PROFILE_BUILDERS[mode]()]
    elif mode == "review_dnh":
        base["schema_status"] = "review_required"
        base["observed_layout"] = {"page_count": 2, "page_1_printed_columns_observed": nums(1, 15), "heading_variants": ["Taluka abstract of Educational, Medical and Other Amenities"]}
        base["review_required"] = reason
    elif mode == "review_daman":
        base["schema_status"] = "review_required"
        base["observed_layout"] = {"page_count": 2, "heading_variants": ["Taluk-wise Abstract of Educational, Medical and Other Amenities"], "combined_volume": True}
        base["review_required"] = reason
    elif mode == "review_karnataka":
        base["schema_status"] = "review_required"
        base["observed_layout"] = {"page_count": "two pages in the inspected Talukwise appendix", "page_1_panels": ["Educational", "Medical", "Power Supply"], "page_2_panels": ["Drinking Water", "Communication", "Postal & Telegraph"], "regional_abbreviations": True}
        base["review_required"] = reason
    else:
        base["schema_status"] = "unavailable"
        base["review_required"] = reason
    return base


def write_yaml(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")


def main() -> None:
    written: list[str] = []
    for slug, config in STATE_CONFIGS.items():
        availability = common_availability(config["output_folder"])
        target = SCHEMA_ROOT / slug
        for format_id in ("format_001", "format_002"):
            write_yaml(target / f"{format_id}.yaml", make_common_doc(config | {"slug": slug}, format_id, availability))
            written.append(str(target / f"{format_id}.yaml"))
        write_yaml(target / "format_003.yaml", make_format3_doc(config | {"slug": slug}, availability))
        written.append(str(target / "format_003.yaml"))
    print(f"Wrote {len(written)} state schema files for {len(STATE_CONFIGS)} states/UTs.")
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
