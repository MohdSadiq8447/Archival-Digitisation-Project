import csv
import os
from copy import deepcopy

ROOT = r"E:\\Archival-Digitisation-Project\\1971_Trimmed_PDF\\Uttar_Pradesh\\outputs\\postprocessed"
DIST = "Gorakhpur"


def load(pdf_id):
    path = os.path.join(ROOT, f"up1971-{pdf_id}-regex-cleaned-v1", "csv", f"{pdf_id}.csv")
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        return rows, list(reader.fieldnames or [])


def clear_flags(row):
    for key in list(row):
        if key.endswith("_flag"):
            row[key] = ""
    row["requires_review"] = "False"


def finish(pdf_id, rows, fields, report):
    slug = pdf_id.removesuffix("_1971").replace("_", "-")
    out = os.path.join(ROOT, f"up1971-{slug}-source-checked-v1")
    os.makedirs(os.path.join(out, "csv"), exist_ok=True)
    with open(os.path.join(out, "csv", f"{pdf_id}.csv"), "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    old, _ = load(pdf_id)
    with open(os.path.join(out, "CORRECTION_LOG.csv"), "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["row_index", "variable", "original_value", "corrected_value", "reason"])
        for idx, row in enumerate(rows):
            before = old[idx] if idx < len(old) else {}
            for var in fields:
                if var.endswith("_flag") or var in {"row_index", "parent_row_index", "subrow_index", "subrow_count", "requires_review", "extracted_at"}:
                    continue
                if before.get(var, "") != row.get(var, ""):
                    writer.writerow([idx, var, before.get(var, ""), row.get(var, ""), "300-DPI source inspection and hierarchy/continuation cleanup"])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "gorakhpur_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    vars_ = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other", "pucca_road_km", "kutcha_road_km"]
    values = [
        ("1", "Barhalganj", "PR (3) KR (2.5)", "ST/OSD", "35", "1,320", "...", "B", "W/HP", "...", "...", "595", "32", "10", "47", "...", "3.0", "2.5"),
        ("2", "Gorakhpur", "PR (60) KR (30)", "S/ST/OSD", "5,700", "20,000", "...", "B/C/MT", "TW/OHT", "1,500,000 Galls.", "Yes", "11,312", "524", "3,357", "6,345", "...", "60.0", "30.0"),
    ]
    rows = []
    for idx, data in enumerate(values):
        row = deepcopy(template)
        row.update(dict(zip(vars_, data)))
        row.update({"row_type": "ORDINARY", "reference_target": "", "row_index": str(idx), "pdf_id": pdf_id, "district": DIST})
        clear_flags(row)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Gorakhpur Civic source-checked output\n\nTwo Civic town rows and the page-7 amenities continuation were transcribed from the source at 300 DPI.\n")


def mededu():
    pdf_id = "gorakhpur_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    vars_ = ["hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]
    e = "..."

    def parent(serial, town, children, beds, child_fields, inherited, parent_idx):
        out = []
        for sub_idx, (child, bed) in enumerate(zip(children, beds)):
            row = deepcopy(template)
            row.update({"sl_no": serial, "town_name": town, "row_type": "ORDINARY", "reference_target": "", "parent_row_index": str(parent_idx), "subrow_index": str(sub_idx), "subrow_count": str(len(children)), "row_index": "", "pdf_id": pdf_id, "district": DIST})
            for var in vars_:
                row[var] = inherited.get(var, "")
            row["hospitals_dispensaries"] = child
            row["med_beds"] = bed
            for var, values in child_fields.items():
                row[var] = values[sub_idx]
            clear_flags(row)
            out.append(row)
        return out

    rows = []
    rows += parent("1", "Barhalganj", ["H (1)", "HC (1)", "FC (1)"], ["13", e, e], {"degree_colleges": ["AS (1)", "", ""], "medical_colleges": [e, "", ""], "engg_colleges": [e, "", ""], "polytechnics": [e, "", ""], "vocational_institutes": ["Sh. Type (1)", "", ""]}, {"higher_secondary_schools": "2", "middle_schools": "2", "primary_schools": "2", "other_edu_institutions": "2", "stadia": e, "cinemas": e, "auditoria": e, "libraries": e}, 0)
    rows += parent("2", "Gorakhpur", ["H (11)", "TBC (1)", "D (13)", "*O (3)", "FC (6)"], ["1,048", e, e, e, e], {"degree_colleges": ["AS (2) A (1) S (1)"] * 5, "medical_colleges": [e] * 5, "engg_colleges": ["1"] * 5, "polytechnics": ["2"] * 5, "vocational_institutes": ["Sh. Type (3) O (9)"] * 5}, {"higher_secondary_schools": "21", "middle_schools": "20", "primary_schools": "72", "other_edu_institutions": "38", "stadia": "2", "cinemas": "10", "auditoria": "3", "libraries": "PL (7)"}, 1)
    for idx, row in enumerate(rows):
        row["row_index"] = str(idx)
    finish(pdf_id, rows, fields, "# Gorakhpur MedEdu source-checked output\n\nTwo parent towns and eight child rows preserve the printed hierarchy from page 6. Child medical rows retain the source codes; parent-level continuation values from page 7 are propagated consistently.\n")


def tehsil():
    pdf_id = "gorakhpur_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    wat = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    roads = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    rowspec = [
        ("1", "Pharenda", ["239", "250", "24", "24", "14", "15", "...", "...", "...", "..."], ["11", "11", "9", "9", "6", "6", "...", "...", "10", "10", "1", "1"], ["142", "494", "...", "482", "578", "...", "7", "...", "...", "...", "...", "13", "...", "..."], ["92", "215", "35", "102", "53", "53", "...", "...", "5", "5", "5", "5"]),
        ("2", "Maharajganj", ["295", "312", "31", "35", "12", "13", "2", "2", "5", "5"], ["6", "6", "7", "7", "5", "5", "4", "4", "18", "18", "2", "2"], ["183", "577", "...", "710", "702", "...", "...", "...", "...", "...", "...", "...", "...", "..."], ["99", "445", "132", "19", "73", "73", "...", "...", "3", "3", "3", "3"]),
        ("3", "Gorakhpur", ["371", "385", "54", "58", "19", "19", "7", "7", "8", "14"], ["15", "15", "17", "17", "7", "7", "...", "...", "8", "8", "...", "..."], ["396", "858", "...", "900", "1,097", "5", "12", "...", "...", "...", "...", "27", "...", "..."], ["134", "661", "94", "98", "86", "86", "2", "2", "...", "...", "1", "1"]),
        ("4", "Bansgaon", ["394", "413", "66", "69", "18", "18", "5", "5", "7", "7"], ["21", "21", "15", "15", "4", "4", "2", "2", "8", "8", "2", "2"], ["327", "1,639", "1", "902", "1,641", "4", "39", "...", "...", "...", "...", "71", "...", "..."], ["370", "353", "69", "43", "107", "107", "...", "...", "4", "4", "2", "2"]),
        ("", "District Total (Rural)", ["1,299", "1,360", "175", "186", "63", "65", "14", "14", "20", "26"], ["53", "53", "48", "48", "22", "22", "6", "6", "44", "44", "5", "5"], ["1,048", "3,568", "1", "2,994", "4,018", "9", "58", "...", "...", "...", "...", "111", "...", "..."], ["695", "1,674", "330", "262", "319", "319", "2", "2", "12", "12", "11", "11"]),
    ]
    rows = []
    for idx, (serial, name, e, m, w, rd) in enumerate(rowspec):
        row = deepcopy(template)
        row.update({"sl_no": serial, "tahsil_name": name, "row_type": "TOTAL" if idx == 4 else "ORDINARY", "reference_target": "", "row_index": str(idx), "pdf_id": pdf_id, "district": DIST})
        for var, value in zip(edu, e): row[var] = value
        for var, value in zip(med, m): row[var] = value
        for var, value in zip(wat, w): row[var] = value
        for var, value in zip(roads, rd): row[var] = value
        clear_flags(row)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Gorakhpur Tahsil source-checked output\n\nFour Tahsil rows and District Total (Rural) were transcribed from pages 434–435 at 300 DPI. Medical, water, and communications continuation bands were aligned to the printed rows.\n")


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
