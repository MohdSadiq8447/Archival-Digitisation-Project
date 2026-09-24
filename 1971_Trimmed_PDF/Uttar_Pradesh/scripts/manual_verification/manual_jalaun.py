import csv
import os
from copy import deepcopy

ROOT = r"E:\\Archival-Digitisation-Project\\1971_Trimmed_PDF\\Uttar_Pradesh\\outputs\\postprocessed"
DIST = "Jalaun"


def load(pdf_id):
    path = os.path.join(ROOT, f"up1971-{pdf_id}-regex-cleaned-v1", "csv", f"{pdf_id}.csv")
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader), list(reader.fieldnames or [])


def clear_flags(row):
    for key in row:
        if key.endswith("_flag"):
            row[key] = ""
    row["requires_review"] = "False"


def finish(pdf_id, rows, fields, report):
    slug = pdf_id.removesuffix("_1971").replace("_", "-")
    out = os.path.join(ROOT, f"up1971-{slug}-source-checked-v1")
    os.makedirs(os.path.join(out, "csv"), exist_ok=True)
    with open(os.path.join(out, "csv", f"{pdf_id}.csv"), "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    old, _ = load(pdf_id)
    with open(os.path.join(out, "CORRECTION_LOG.csv"), "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh); writer.writerow(["row_index", "variable", "original_value", "corrected_value", "reason"])
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
    pdf_id = "jalaun_civic_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    vars_ = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other", "pucca_road_km", "kutcha_road_km"]
    values = [
        ("1", "Jalaun", "KR (12) PR (8)", "PT/OSD", "25", "1,500", "30", "B", "TW/OHT", "50,000 Galls.", "...", "269", "38", "213", "180", "...", "8.0", "12.0"),
        ("2", "Kalpi", "KR (7.5) PR (12.5)", "PT/OSD", "50", "4,000", "...", "B/HL", "TW/OHT", "50,000 Galls.", "...", "896", "18", "40", "254", "...", "12.5", "7.5"),
        ("3", "Konch", "KR (10) PR (8)", "PT/OSD", "45", "3,004", "...", "HL", "TW/OHT", "75,000 Galls.", "...", "1,042", "62", "12", "310", "...", "8.0", "10.0"),
        ("4", "Orai", "KR (15) PR (12)", "S/OSD", "250", "2,500", "-", "B/HL", "TW/OHT", "72,600 Galls.", "...", "2,364", "70", "88", "615", "...", "12.0", "15.0"),
    ]
    rows = []
    for idx, data in enumerate(values):
        row = deepcopy(template); row.update(dict(zip(vars_, data))); row.update({"row_type": "ORDINARY", "reference_target": "", "row_index": str(idx), "pdf_id": pdf_id, "district": DIST}); clear_flags(row); rows.append(row)
    finish(pdf_id, rows, fields, "# Jalaun Civic source-checked output\n\nFour town rows were transcribed from the Civic table on printed pages 6–7. The unrelated Municipal Finance panel was excluded; continuation amenities were aligned by town.\n")


def mededu():
    pdf_id = "jalaun_mededu_1971"; old, fields = load(pdf_id); template = deepcopy(old[0]); e = "..."
    vars_ = ["hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]
    def parent(serial, town, children, beds, inherited, pidx):
        out = []
        for sidx, (child, bed) in enumerate(zip(children, beds)):
            row = deepcopy(template); row.update({"sl_no": serial, "town_name": town, "row_type": "ORDINARY", "reference_target": "", "parent_row_index": str(pidx), "subrow_index": str(sidx), "subrow_count": str(len(children)), "row_index": "", "pdf_id": pdf_id, "district": DIST})
            for var in vars_: row[var] = inherited.get(var, "")
            row["hospitals_dispensaries"] = child; row["med_beds"] = bed; clear_flags(row); out.append(row)
        return out
    rows = []
    rows += parent("1", "Jalaun", ["H (2)", "FC (1)", "*O (1)"], ["30", e, "4"], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "2", "middle_schools": "4", "primary_schools": "13", "other_edu_institutions": e, "stadia": e, "cinemas": e, "auditoria": e, "libraries": e}, 0)
    rows += parent("2", "Kalpi", ["H (2)", "HC (1)", "FC (1)"], ["20", e, e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "4", "middle_schools": "2", "primary_schools": "13", "other_edu_institutions": e, "stadia": e, "cinemas": "1", "auditoria": e, "libraries": "PL (2)"}, 1)
    rows += parent("3", "Konch", ["H (2)", "D (2)", "FC (1)"], ["28", e, e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "4", "middle_schools": "3", "primary_schools": "21", "other_edu_institutions": e, "stadia": e, "cinemas": e, "auditoria": e, "libraries": "PL (3)"}, 2)
    rows += parent("4", "Orai", ["H (4)", "D (1)", "FC (1)", "TBC (1)"], ["101", "19", e, "4"], {"degree_colleges": "A (1) AS (1)", "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": "Sh. Type (2)", "higher_secondary_schools": "7", "middle_schools": "3", "primary_schools": "23", "other_edu_institutions": "1", "stadia": "1", "cinemas": "2", "auditoria": e, "libraries": "PL (1)"}, 3)
    for idx, row in enumerate(rows): row["row_index"] = str(idx)
    finish(pdf_id, rows, fields, "# Jalaun MedEdu source-checked output\n\nFour parent towns and thirteen expanded child rows preserve the printed medical hierarchy from page 8. Columns 5–17 are parent-scoped and propagated from the continuation panel on page 9.\n")


def tehsil():
    pdf_id = "jalaun_tehsil_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    wat = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    roads = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    rowspec = [
        ("1", "Jalaun", ["234", "260", "34", "36", "8", "8", "...", "...", "2", "2"], ["10", "10", "4", "4", "9", "9", "...", "...", "3", "3", "5", "5"], ["35", "407", "...", "3", "371", "4", "3", "...", "...", "...", "...", "...", "...", "61"], ["82", "164", "17", "1", "52", "52", "...", "...", "3", "3", "...", "..."]),
        ("2", "Konch", ["148", "158", "20", "20", "2", "2", "1", "1", "...", "..."], ["8", "8", "...", "...", "3", "3", "1", "1", "2", "2", "...", "..."], ["20", "295", "3", "250", "21", "4", "...", "...", "...", "...", "...", "...", "...", "37"], ["35", "71", "3", "11", "33", "33", "...", "...", "1", "1", "...", "..."]),
        ("3", "Orai", ["95", "110", "9", "9", "9", "9", "...", "...", "1", "1"], ["5", "5", "1", "1", "4", "4", "...", "...", "...", "...", "...", "..."], ["12", "145", "...", "...", "122", "...", "10", "1", "...", "...", "...", "...", "...", "24"], ["32", "80", "10", "3", "21", "21", "...", "...", "3", "3", "1", "1"]),
        ("4", "Kalpi", ["118", "126", "23", "26", "3", "3", "...", "...", "...", "..."], ["9", "9", "3", "3", "4", "4", "...", "...", "2", "2", "...", "..."], ["7", "235", "...", "2", "197", "7", "9", "...", "...", "...", "...", "...", "1", "26"], ["20", "77", "11", "10", "28", "28", "...", "...", "3", "3", "2", "2"]),
        ("", "District Total (Rural)", ["595", "654", "86", "91", "22", "22", "1", "1", "3", "3"], ["32", "32", "8", "8", "20", "20", "1", "1", "7", "7", "5", "5"], ["74", "1,082", "3", "255", "711", "15", "22", "1", "...", "...", "...", "...", "1", "148"], ["169", "392", "41", "25", "134", "134", "...", "...", "10", "10", "3", "3"]),
    ]
    rows = []
    for idx, (serial, name, e, m, w, rd) in enumerate(rowspec):
        row = deepcopy(template); row.update({"sl_no": serial, "tahsil_name": name, "row_type": "TOTAL" if idx == 4 else "ORDINARY", "reference_target": "", "row_index": str(idx), "pdf_id": pdf_id, "district": DIST})
        for var, value in zip(edu, e): row[var] = value
        for var, value in zip(med, m): row[var] = value
        for var, value in zip(wat, w): row[var] = value
        for var, value in zip(roads, rd): row[var] = value
        clear_flags(row); rows.append(row)
    finish(pdf_id, rows, fields, "# Jalaun Tahsil source-checked output\n\nFour Tahsil rows and District Total (Rural) were transcribed from printed pages 130–131. Education, water, medical, and communications continuation bands were aligned by identity.\n")


if __name__ == "__main__":
    civic(); mededu(); tehsil()
