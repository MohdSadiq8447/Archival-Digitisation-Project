import csv
import os
from copy import deepcopy

ROOT = r"E:\\Archival-Digitisation-Project\\1971_Trimmed_PDF\\Uttar_Pradesh\\outputs\\postprocessed"
DIST = "Garhwal"


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
                    writer.writerow([idx, var, before.get(var, ""), row.get(var, ""), "300-DPI source inspection and continuation alignment"])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "garhwal_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    vars_ = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other", "pucca_road_km", "kutcha_road_km"]
    values = [
        ("1", "Bah Bazar", "PR (1) KR (1)", "OSD", "...", "152", "...", "HL", "F", "...", "...", "250", "1", "25", "90", "...", "1.0", "1.0"),
        ("2", "Dogadda", "PR (2) KR (0)", "OSD", "...", "100", "...", "HL", "W/F", "...", "...", "...", "...", "...", "...", "...", "2.0", "0.0"),
        ("3", "Kotdwara", "PR (13) KR (2)", "S/OSD", "130", "1,200", "...", "HL/B", "R", "...", "...", "1,000", "57", "21", "235", "...", "13.0", "2.0"),
        ("4", "Lansdowne Cantt.", "PR (4) KR (1)", "PT/OSD", "167", "548", "...", "HL", "R/OHT", "2,000 Galls.", "...", "90", "...", "3", "135", "...", "4.0", "1.0"),
        ("5", "Pauri", "PR (4) KR (25)", "PT/OSD", "20", "200", "...", "HL", "F", "...", "...", "332", "4", "...", "320", "...", "4.0", "25.0"),
        ("6", "Srinagar", "PR (3) KR (7)", "PT/OSD", "120", "46", "...", "HL", "F/R", "-", "...", "248", "3", "...", "80", "...", "3.0", "7.0"),
    ]
    rows = []
    for idx, data in enumerate(values):
        row = deepcopy(template)
        row.update(dict(zip(vars_, data)))
        row.update({"row_type": "ORDINARY", "reference_target": "", "row_index": str(idx), "pdf_id": pdf_id, "district": DIST})
        clear_flags(row)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Garhwal Civic source-checked output\n\nThe Civic panel was isolated from the preceding Municipal Finance table. Six town rows and their amenities continuation values were transcribed from pages 6–7 at 300 DPI.\n")


def mededu():
    pdf_id = "garhwal_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    vars_ = ["hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]
    e = "..."

    def parent(serial, town, children, beds, inherited, parent_idx):
        result = []
        for sub_idx, (child, bed) in enumerate(zip(children, beds)):
            row = deepcopy(template)
            row.update({"sl_no": serial, "town_name": town, "row_type": "ORDINARY", "reference_target": "", "parent_row_index": str(parent_idx), "subrow_index": str(sub_idx), "subrow_count": str(len(children)), "row_index": "", "pdf_id": pdf_id, "district": DIST})
            for var in vars_:
                row[var] = inherited.get(var, "")
            row["hospitals_dispensaries"] = child
            row["med_beds"] = bed
            clear_flags(row)
            result.append(row)
        return result

    rows = []
    rows += parent("1", "Bah Bazar", [e], [e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "1", "middle_schools": e, "primary_schools": "1", "other_edu_institutions": e, "stadia": e, "cinemas": e, "auditoria": e, "libraries": e}, 0)
    rows += parent("2", "Dogadda", ["H (2)"], ["18"], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "1", "middle_schools": "1", "primary_schools": "2", "other_edu_institutions": e, "stadia": e, "cinemas": e, "auditoria": e, "libraries": e}, 1)
    rows += parent("3", "Kotdwara", ["H (2)", "D (1)"], ["46", "4"], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "2", "middle_schools": "2", "primary_schools": "10", "other_edu_institutions": "1", "stadia": e, "cinemas": "1", "auditoria": e, "libraries": "PL (1)"}, 2)
    rows += parent("4", "Lansdowne Cantt.", ["H (1)"], ["33"], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "3", "middle_schools": e, "primary_schools": "1", "other_edu_institutions": e, "stadia": e, "cinemas": "1", "auditoria": e, "libraries": "PL (1)"}, 3)
    rows += parent("5", "Pauri", ["H (3)", "TBC (1)", "D (1)", "O (1)"], ["71", e, e, e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "3", "middle_schools": "3", "primary_schools": "10", "other_edu_institutions": "1", "stadia": e, "cinemas": e, "auditoria": e, "libraries": "PL (1) RR (1)"}, 4)
    rows += parent("6", "Srinagar", ["H (3)", "* O (1)"], ["37", e], {"degree_colleges": "S (1)", "medical_colleges": e, "engg_colleges": e, "polytechnics": "1", "vocational_institutes": "Sh. type (1)", "higher_secondary_schools": "2", "middle_schools": e, "primary_schools": "1", "other_edu_institutions": "1", "stadia": e, "cinemas": "1", "auditoria": e, "libraries": "PL (1) RR (1)"}, 5)
    for idx, row in enumerate(rows):
        row["row_index"] = str(idx)
    finish(pdf_id, rows, fields, "# Garhwal MedEdu source-checked output\n\nSix town parents and eleven child rows retain the printed hierarchy from page 8. Columns 3–4 are child-scoped and continuation columns 10–17 are aligned at parent level from page 9.\n")


def tehsil():
    pdf_id = "garhwal_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    wat = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    roads = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    rowspec = [
        ("1", "Pauri", ["355", "357", "39", "39", "13", "13", "...", "...", "7", "7"], ["15", "15", "...", "...", "4", "4", "...", "...", "...", "...", "...", "..."], ["1", "1,392", "353", "...", "...", "...", "35", "724", "...", "175", "...", "...", "109", "..."], ["193", "1,217", "21", "...", "79", "79", "...", "...", "1", "1", "...", "..."]),
        ("2", "Lansdowne", ["496", "497", "49", "49", "13", "13", "...", "...", "5", "5"], ["21", "21", "...", "...", "12", "12", "...", "...", "4", "4", "...", "..."], ["2", "2,173", "425", "...", "...", "...", "124", "1,065", "...", "445", "...", "...", "103", "..."], ["183", "1,992", "12", "...", "121", "121", "...", "...", "10", "10", "...", "..."]),
        ("", "District Total (Rural)", ["851", "854", "88", "88", "26", "26", "...", "...", "12", "12"], ["36", "36", "...", "...", "16", "16", "...", "...", "4", "4", "...", "..."], ["3", "3,565", "778", "...", "...", "...", "159", "1,789", "...", "620", "...", "...", "212", "..."], ["316", "3,219", "33", "...", "200", "200", "...", "...", "11", "11", "...", "..."]),
    ]
    rows = []
    all_vars = edu + med + wat + roads
    for idx, (serial, name, e, m, w, rd) in enumerate(rowspec):
        row = deepcopy(template)
        row.update({"sl_no": serial, "tahsil_name": name, "row_type": "TOTAL" if idx == 2 else "ORDINARY", "reference_target": "", "row_index": str(idx), "pdf_id": pdf_id, "district": DIST})
        for var, value in zip(edu, e): row[var] = value
        for var, value in zip(med, m): row[var] = value
        for var, value in zip(wat, w): row[var] = value
        for var, value in zip(roads, rd): row[var] = value
        clear_flags(row)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Garhwal Tahsil source-checked output\n\nPauri, Lansdowne, and District Total (Rural) were transcribed from pages 336–337 at 300 DPI. Educational, medical, water, and communications continuation bands remain aligned.\n")


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
