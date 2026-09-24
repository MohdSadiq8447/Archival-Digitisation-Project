import csv
import os
from copy import deepcopy

ROOT = r"E:\\Archival-Digitisation-Project\\1971_Trimmed_PDF\\Uttar_Pradesh\\outputs\\postprocessed"
DIST = "Fatehpur"


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
                    writer.writerow([idx, var, before.get(var, ""), row.get(var, ""), "300-DPI source inspection and regex contamination cleanup"])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "fatehpur_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    values = [
        ("1", "Bindki", "PR (9) KR (6)", "ST/OSD", "100", "1,847", "...", "B/HC", "TW/OHT", "54,000 Gal.", "...", "664", "67", "1", "168", "...", "9.0", "6.0"),
        ("2", "Fatehpur", "PR (72) KR (96)", "ST/OSD", "450", "5,018", ".", "B/HC", "TW/OHT", "100,000 Gal.", "...", "1,707", "107", "2", "300", "...", "72.0", "96.0"),
    ]
    vars_ = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other", "pucca_road_km", "kutcha_road_km"]
    rows = []
    for idx, data in enumerate(values):
        row = deepcopy(template)
        row.update(dict(zip(vars_, data)))
        row.update({"row_type": "ORDINARY", "reference_target": "", "row_index": str(idx), "pdf_id": pdf_id, "district": DIST})
        clear_flags(row)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Fatehpur Civic source-checked output\n\nBoth Civic parents and continuation values were transcribed from source pages 6–7 at 300 DPI.\n")


def mededu():
    pdf_id = "fatehpur_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    vars_ = ["hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]
    ellipsis = "..."

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
    rows += parent("1", "Bindki", ["H (2)", "FC (2)"], ["12", ellipsis], {"degree_colleges": ellipsis, "medical_colleges": ellipsis, "engg_colleges": ellipsis, "polytechnics": ellipsis, "vocational_institutes": ellipsis, "higher_secondary_schools": "3", "middle_schools": "3", "primary_schools": "15", "other_edu_institutions": "1", "stadia": ellipsis, "cinemas": "1", "auditoria": ellipsis, "libraries": "PL (1)"}, 0)
    rows += parent("2", "Fatehpur", ["H (5)", "D (1)", "TBC (1)", "FC (2)"], ["148", "2", ellipsis, ellipsis], {"degree_colleges": "A (1)", "medical_colleges": ellipsis, "engg_colleges": ".", "polytechnics": ellipsis, "vocational_institutes": ellipsis, "higher_secondary_schools": "7", "middle_schools": "4", "primary_schools": "12", "other_edu_institutions": "2", "stadia": ellipsis, "cinemas": "2", "auditoria": ellipsis, "libraries": "PL (1)"}, 1)
    for idx, row in enumerate(rows):
        row["row_index"] = str(idx)
    finish(pdf_id, rows, fields, "# Fatehpur MedEdu source-checked output\n\nTwo parents and six child rows were transcribed from source pages 6–7 at 300 DPI. Hospitals/dispensaries and beds remain child-scoped; columns 5–17 are inherited per parent.\n")


def tehsil():
    pdf_id = "fatehpur_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    wat = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    roads = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    rowspec = [
        ("1", "Bindki", ["225", "254", "37", "43", "5", "5", "...", "...", "...", "..."], ["", "3", "15", "15", "...", "...", "...", "...", "1", "1", "...", "..."], ["87", "336", "...", "390", "6", "...", "...", "...", "...", "...", "...", "...", "...", "..."], ["111", "156", "13", "40", "45", "45", "...", "...", "4", "4", "2", "2"]),
        ("2", "Fatehpur", ["215", "234", "34", "39", "11", "11", "...", "...", "...", "..."], ["", "6", "7", "16", "17", "6", "6", "...", "...", "5", "5", "..."], ["52", "486", "...", "1,474", "...", "6", "...", "...", "...", "...", "1", "...", "...", "..."], ["106", "122", "12", "38", "58", "58", "...", "...", "4", "4", "5", "5"]),
        ("3", "Khaga", ["178", "196", "25", "27", "11", "11", "...", "...", "...", "..."], ["", "6", "6", "...", "...", "5", "5", "1", "1", "5", "5", "..."], ["19", "550", "...", "486", "...", "1", "...", "...", "...", "...", "...", "...", "...", "..."], ["50", "181", "15", "30", "46", "46", "...", "...", "3", "3", "...", "..."]),
        ("", "District Fatehpur", ["618", "684", "96", "109", "27", "27", "...", "...", "...", "..."], ["", "15", "16", "31", "32", "11", "11", "1", "1", "11", "11", "..."], ["158", "1,372", "...", "2,350", "...", "13", "...", "1", "...", "...", "...", "...", "...", "..."], ["267", "459", "40", "108", "149", "149", "...", "...", "11", "11", "7", "7"]),
    ]
    rows = []
    for idx, (serial, name, e, m, w, rd) in enumerate(rowspec):
        row = deepcopy(template)
        row.update({"sl_no": serial, "tahsil_name": name, "row_type": "TOTAL" if idx == 3 else "ORDINARY", "reference_target": "", "row_index": str(idx), "pdf_id": pdf_id, "district": DIST})
        for var, value in zip(edu, e): row[var] = value
        for var, value in zip(med, m): row[var] = value
        for var, value in zip(wat, w): row[var] = value
        for var, value in zip(roads, rd): row[var] = value
        clear_flags(row)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Fatehpur Tahsil source-checked output\n\nFour Tahsil rows, including District Fatehpur total, were transcribed from source pages 156–157 at 300 DPI with continuation columns kept aligned.\n")


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
