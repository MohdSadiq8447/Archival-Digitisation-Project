import csv
import os
from copy import deepcopy

ROOT = r"E:\\Archival-Digitisation-Project\\1971_Trimmed_PDF\\Uttar_Pradesh\\outputs\\postprocessed"
DIST = "Hardoi"


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
    pdf_id = "hardoi_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    vars_ = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other", "pucca_road_km", "kutcha_road_km"]
    values = [
        ("1", "Bilgram", "PR (13) KR (3.2)", "OSD", "...", "200", "...", "B/HC", "TW/OHT", "25,000 Galls.", "...", "216", "13", "40", "87", "...", "13.0", "3.2"),
        ("2", "Hardoi", "PR (16.7) KR (0)", "BD/ST/OSD", "100", "5,000", "...", "B/HC", "TW/OHT", "1,17,000 Galls.", "...", "2,323", "221", "185", "1,125", "...", "16.7", "0.0"),
        ("3", "Madhoganj", "PR (4.0) KR (0.0)", "ST/OSD", "70", "1,500", "...", "B", "HP/W", "...", "...", "250", "33", "60", "58", "...", "4.0", "0.0"),
        ("4", "Pihani", "PR (16) KR (1.5)", "OSD", "...", "1,500", "...", "B", "HP/W", "...", "...", "250", "9", "50", "42", "...", "16.0", "1.5"),
        ("5", "Sandi", "PR (10.3) KR (3)", "ST/OSD", "15", "800", "...", "B", "HP", "...", "...", "355", "40", "45", "91", "...", "10.3", "3.0"),
        ("6", "Sandila", "PR (30.7) KR (6.2)", "ST/OSD", "20", "1,500", "...", "B/HC/MT", "TW/OHT", "50,000 Galls.", "...", "513", "44", "56", "100", "...", "30.7", "6.2"),
        ("7", "Shahabad", "PR (20.6) KR (7.6)", "ST/OSD", "45", "4,516", "...", "B/HC", "HP/W", "...", "...", "360", "64", "200", "182", "...", "20.6", "7.6"),
    ]
    rows = []
    for idx, data in enumerate(values):
        row = deepcopy(template)
        row.update(dict(zip(vars_, data)))
        row.update({"row_type": "ORDINARY", "reference_target": "", "row_index": str(idx), "pdf_id": pdf_id, "district": DIST})
        clear_flags(row)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Hardoi Civic source-checked output\n\nSeven Civic town rows and the page-7 amenities continuation were transcribed from the source at 300 DPI.\n")


def mededu():
    pdf_id = "hardoi_mededu_1971"
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
    rows += parent("1", "Bilgram", ["H (2)", "D (2)", "FC (1)"], ["20", "6", e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "1", "middle_schools": "3", "primary_schools": "6", "other_edu_institutions": "2", "stadia": e, "cinemas": e, "auditoria": e, "libraries": "PL (1) RR (1)"}, 0)
    rows += parent("2", "Hardoi", ["H (5)", "TBC (1)", "D (1)", "MCW (1)", "FC (1)"], ["170", e, "5", "2", e], {"degree_colleges": "A (1)", "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": "O (1)", "higher_secondary_schools": "7", "middle_schools": "3", "primary_schools": "19", "other_edu_institutions": "5", "stadia": e, "cinemas": "1", "auditoria": e, "libraries": "PL (4) RR (4)"}, 1)
    rows += parent("3", "Madhoganj", ["D (1)", "H (2)", "FC (1)"], ["4", "6", e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "1", "middle_schools": "2", "primary_schools": "2", "other_edu_institutions": "1", "stadia": e, "cinemas": e, "auditoria": e, "libraries": e}, 2)
    rows += parent("4", "Pihani", ["H (2)", "FC (1)"], ["40", e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "1", "middle_schools": "3", "primary_schools": "7", "other_edu_institutions": "3", "stadia": e, "cinemas": e, "auditoria": e, "libraries": e}, 3)
    rows += parent("5", "Sandi", ["D (1)", "FC (1)"], ["6", e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "1", "middle_schools": "4", "primary_schools": "6", "other_edu_institutions": e, "stadia": e, "cinemas": e, "auditoria": e, "libraries": "PL (1) RR (1)"}, 4)
    rows += parent("6", "Sandila", ["H (3)", "FC (1)"], ["20", e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "3", "middle_schools": "2", "primary_schools": "12", "other_edu_institutions": "4", "stadia": e, "cinemas": "1", "auditoria": e, "libraries": "PL (2) RR (2)"}, 5)
    rows += parent("7", "Shahabad", ["H (2)", "HC (1)", "FC (1)"], ["16", e, e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "2", "middle_schools": "3", "primary_schools": "15", "other_edu_institutions": "3", "stadia": e, "cinemas": e, "auditoria": e, "libraries": "PL (2) RR (2)"}, 6)
    for idx, row in enumerate(rows):
        row["row_index"] = str(idx)
    finish(pdf_id, rows, fields, "# Hardoi MedEdu source-checked output\n\nSeven parent towns and twenty child rows preserve the printed H/D/FC/TBC/MCW/HC hierarchy from page 8. Parent-level continuation columns 10–17 are aligned from page 9.\n")


def tehsil():
    pdf_id = "hardoi_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    wat = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    roads = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    rowspec = [
        ("1", "Shahabad", ["219", "223", "15", "15", "3", "3", "2", "2", "...", "..."], ["...", "...", "11", "11", "...", "...", "...", "...", "4", "4", "...", "..."], ["43", "374", "...", "3", "415", "...", "...", "...", "...", "...", "...", "1", "...", "..."], ["60", "351", "...", "...", "55", "55", "...", "...", "1", "1", "...", "..."] ),
        ("2", "Hardoi", ["244", "268", "25", "25", "2", "2", "...", "...", "...", "..."], ["9", "10", "...", "...", "1", "1", "...", "...", "3", "3", "...", "..."], ["68", "424", "...", "33", "471", "4", "...", "...", "1", "...", "...", "1", "...", "..."], ["165", "247", "...", "...", "49", "49", "...", "...", "3", "3", "...", "..."] ),
        ("3", "Bilgram", ["235", "252", "19", "21", "12", "12", "...", "...", "...", "..."], ["8", "8", "1", "1", "3", "3", "...", "...", "5", "5", "...", "..."], ["97", "415", "...", "4", "475", "5", "6", "...", "...", "...", "...", "...", "...", "..."], ["69", "191", "...", "...", "50", "50", "...", "...", "2", "2", "...", "..."] ),
        ("4", "Sandila", ["206", "225", "17", "18", "8", "8", "...", "...", "...", "..."], ["5", "5", "1", "1", "14", "14", "4", "4", "1", "1", "...", "..."], ["60", "502", "...", "88", "510", "...", "...", "...", "...", "...", "...", "...", "...", "..."], ["61", "474", "...", "...", "54", "55", "...", "...", "...", "...", "...", "..."] ),
        ("", "District Total", ["904", "968", "76", "79", "25", "25", "2", "2", "...", "..."], ["22", "23", "13", "13", "18", "18", "4", "4", "15", "13", "...", "..."], ["268", "1,715", "...", "128", "1,871", "9", "6", "...", "1", "...", "...", "2", "...", "..."], ["335", "1,263", "...", "...", "208", "209", "...", "...", "6", "6", "...", "..."] ),
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
    finish(pdf_id, rows, fields, "# Hardoi Tahsil source-checked output\n\nFour Tahsil rows and District Total were transcribed from pages 204–205 at 300 DPI with continuation columns aligned.\n")


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
