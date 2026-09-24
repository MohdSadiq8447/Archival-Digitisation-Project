import csv
import os
from copy import deepcopy

ROOT = r"E:\\Archival-Digitisation-Project\\1971_Trimmed_PDF\\Uttar_Pradesh\\outputs\\postprocessed"
DIST = "Gonda"


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
    pdf_id = "gonda_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    vars_ = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other", "pucca_road_km", "kutcha_road_km"]
    values = [
        ("1", "Balrampur", "PR (29) KR (3)", "OSD", "...", "4,287", "...", "B/C", "TW/OHT", "75,000 Galls.", "...", "1,624", "146", "789", "384", "...", "29.0", "3.0"),
        ("2", "Colonelganj", "PR (2) KR (1)", "PT/OSD", "5", "709", "...", "B", "W/HP", "...", "...", "407", "38", "33", "102", "...", "2.0", "1.0"),
        ("3", "Gonda", "PR (28) KR (6)", "PT/OSD", "313", "6,533", "...", "B/HC", "TW/OHT", "75,000 Galls.", "...", "8,059", "535", "2,413", "818", "...", "28.0", "6.0"),
        ("4", "Nawabganj", "PR (6) KR (2)", "PT/OSD", "18", "1,217", "...", "B", "TW/OHT", "15,000 Galls.", "...", "409", "23", "48", "96", "...", "6.0", "2.0"),
        ("5", "Tulsipur", "PR (4) KR (5)", "OSD", "...", "562", "...", "B", "W/HP", "...", "...", "421", "21", "31", "83", "...", "4.0", "5.0"),
        ("6", "Utraula", "PR (2) KR (7)", "OSD", "...", "2,177", "...", "B/HC", "W/HP", "...", "...", "436", "25", "60", "103", "...", "2.0", "7.0"),
    ]
    rows = []
    for idx, data in enumerate(values):
        row = deepcopy(template)
        row.update(dict(zip(vars_, data)))
        row.update({"row_type": "ORDINARY", "reference_target": "", "row_index": str(idx), "pdf_id": pdf_id, "district": DIST})
        clear_flags(row)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Gonda Civic source-checked output\n\nThe Civic panel was separated from the embedded MedEdu and Trade tables. Six town rows and the page-7 amenities continuation were transcribed from the source at 300 DPI.\n")


def mededu():
    pdf_id = "gonda_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    vars_ = ["hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]
    e = "..."

    def parent(serial, town, children, beds, inherited, parent_idx):
        out = []
        for sub_idx, (child, bed) in enumerate(zip(children, beds)):
            row = deepcopy(template)
            row.update({"sl_no": serial, "town_name": town, "row_type": "ORDINARY", "reference_target": "", "parent_row_index": str(parent_idx), "subrow_index": str(sub_idx), "subrow_count": str(len(children)), "row_index": "", "pdf_id": pdf_id, "district": DIST})
            for var in vars_:
                row[var] = inherited.get(var, "")
            row["hospitals_dispensaries"] = child
            row["med_beds"] = bed
            clear_flags(row)
            out.append(row)
        return out

    rows = []
    rows += parent("1", "Balrampur", ["H (2)", "TBC (1)", "FC (1)"], ["72", "8", e], {"degree_colleges": "AS (1)", "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": "Sh. Type (1) O (1)", "higher_secondary_schools": "4", "middle_schools": "6", "primary_schools": "27", "other_edu_institutions": "8", "stadia": e, "cinemas": "1", "auditoria": e, "libraries": e}, 0)
    rows += parent("2", "Colonelganj", ["H (1)", "FC (1)", "O* (1)"], ["6", e, e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "2", "middle_schools": "3", "primary_schools": "8", "other_edu_institutions": "2", "stadia": e, "cinemas": e, "auditoria": e, "libraries": "PL (1)"}, 1)
    rows += parent("3", "Gonda", ["H (7)", "TBC (1)", "FC (2)", "O* (2)"], ["326", "3", e, e], {"degree_colleges": "A (1)", "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": "Sh. Type (1) O (1)", "higher_secondary_schools": "3", "middle_schools": "4", "primary_schools": "29", "other_edu_institutions": "5", "stadia": e, "cinemas": "2", "auditoria": e, "libraries": e}, 2)
    rows += parent("4", "Nawabganj", ["H (1)", "O* (1)"], ["14", e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "3", "middle_schools": e, "primary_schools": "6", "other_edu_institutions": "3", "stadia": e, "cinemas": e, "auditoria": e, "libraries": e}, 3)
    rows += parent("5", "Tulsipur", ["H (2)", "FC (1)", "O* (1)"], ["15", e, e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "2", "middle_schools": "2", "primary_schools": "3", "other_edu_institutions": "5", "stadia": e, "cinemas": e, "auditoria": e, "libraries": "RR (1)"}, 4)
    rows += parent("6", "Utraula", ["H (1)", "FC (1)", "O* (2)"], ["12", e, e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "1", "middle_schools": "3", "primary_schools": "1", "other_edu_institutions": "5", "stadia": e, "cinemas": e, "auditoria": e, "libraries": e}, 5)
    for idx, row in enumerate(rows):
        row["row_index"] = str(idx)
    finish(pdf_id, rows, fields, "# Gonda MedEdu source-checked output\n\nSix parent towns and eighteen child rows preserve the printed H/TBC/FC/O hierarchy from page 6. Columns 5–17 are inherited per parent from the continuation panel on page 7.\n")


def tehsil():
    pdf_id = "gonda_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    wat = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    roads = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    rowspec = [
        ("1", "Balrampur", ["303", "309", "11", "11", "2", "2", "...", "...", "...", "..."], ["6", "6", "2", "2", "2", "2", "1", "1", "7", "7", "...", "..."], ["85", "567", "...", "9", "639", "...", "...", "...", "...", "...", "...", "...", "...", "..."], ["117", "275", "23", "23", "58", "58", "...", "...", "...", "...", "...", "..."]),
        ("2", "Utraula", ["334", "358", "19", "19", "7", "8", "1", "1", "...", "..."], ["14", "14", "7", "7", "7", "7", "1", "1", "12", "12", "1", "1"], ["101", "742", "...", "674", "836", "...", "...", "...", "...", "...", "...", "...", "...", "..."], ["92", "674", "42", "20", "78", "78", "1", "1", "...", "...", "1", "1"]),
        ("3", "Gonda", ["356", "385", "18", "20", "4", "4", "2", "2", "2", "2"], ["", "7", "8", "8", "1", "1", "1", "1", "14", "15", "...", "..."], ["131", "652", "...", "545", "783", "...", "...", "...", "...", "...", "...", "8", "...", "..."], ["108", "153", "2", "144", "76", "76", "1", "1", "4", "4", "...", "..."]),
        ("4", "Tarabganj", ["327", "355", "22", "24", "8", "9", "...", "...", "1", "1"], ["5", "5", "9", "9", "2", "2", "...", "...", "21", "21", "...", "..."], ["81", "479", "...", "293", "553", "...", "17", "...", "...", "...", "...", "33", "...", "..."], ["63", "279", "33", "38", "65", "65", "...", "...", "...", "3", "2", "2"]),
        ("", "District Total (Rural)", ["1,320", "1,407", "70", "74", "21", "23", "3", "3", "3", "3"], ["32", "32", "26", "26", "12", "12", "3", "3", "54", "55", "1", "1"], ["398", "2,440", "...", "1,526", "2,811", "...", "17", "...", "...", "...", "...", "41", "...", "..."], ["380", "1,381", "100", "225", "277", "277", "2", "...", "...", "...", "3", "3"]),
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
    finish(pdf_id, rows, fields, "# Gonda Tahsil source-checked output\n\nFour Tahsil parents and District Total (Rural) were transcribed from pages 276–277 at 300 DPI with medical, water, and communications continuations aligned.\n")


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
