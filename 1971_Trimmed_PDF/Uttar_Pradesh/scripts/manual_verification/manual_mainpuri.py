import csv, os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Mainpuri"
e = "..."


def load(pdf_id):
    src = os.path.join(ROOT, f"up1971-{pdf_id}-regex-cleaned-v1", "csv", f"{pdf_id}.csv")
    with open(src, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows, list(rows[0])


def clear(row, variables):
    for variable in variables:
        if f"{variable}_flag" in row:
            row[f"{variable}_flag"] = ""
    row["requires_review"] = "False"


def finish(pdf_id, rows, fields, report):
    folder = pdf_id.removesuffix("_1971").replace("_", "-")
    out = os.path.join(ROOT, f"up1971-{folder}-source-checked-v1")
    os.makedirs(os.path.join(out, "csv"), exist_ok=True)
    with open(os.path.join(out, "csv", f"{pdf_id}.csv"), "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    old, _ = load(pdf_id)
    with open(os.path.join(out, "CORRECTION_LOG.csv"), "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f); writer.writerow(["row_index", "variable", "original_value", "corrected_value", "reason"])
        for i, row in enumerate(rows):
            before = old[i] if i < len(old) else {}
            for variable in fields:
                if variable.endswith("_flag") or variable in {"row_index", "parent_row_index", "subrow_index", "subrow_count", "requires_review", "extracted_at"}:
                    continue
                if before.get(variable, "") != row.get(variable, ""):
                    writer.writerow([i, variable, before.get(variable, ""), row.get(variable, ""), "300-DPI source inspection; structural/OCR cleanup"])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "mainpuri_civic_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    variables = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other", "pucca_road_km", "kutcha_road_km"]
    data = [
        ("1", "Bewar", "PR (7) KR (0)", "ST/OSD", "15", "1,026", e, "B/HC", "TW/OHT", "15,000 Gallons", e, "175", "40", "160", "135", e, "7.0", "0.0", "ORDINARY", ""),
        ("2", "Bhongaon", "PR (6) KR (0)", "OSD", e, "1,005", e, "HC", "TW/OHT", "15,000 Gallons", e, "165", "23", "133", "145", e, "6.0", "0.0", "ORDINARY", ""),
        ("3", "Karhal", "PR (2) KR (1)", "PT/OSD", "11", "1,018", e, "B/HC", "HP/W", e, e, "245", "15", "35", "50", e, "2.0", "1.0", "ORDINARY", ""),
        ("4", "Kuraoli", "PR (2) KR (4)", "PT/OSD", "2", "1,106", e, "B/HC", "HP/W", e, e, "131", "26", "148", "68", e, "2.0", "4.0", "ORDINARY", ""),
        ("5", "*Mainpuri", "PR (41.4) KR (0)", "OSD", e, "6,125", e, "B/HC", "TW/OHT", "10,000 Gallons", e, "2,347", "142", "973", "842", e, "41.4", "0.0", "ORDINARY", ""),
        ("6", "Shikohabad", "PR (31.8) KR (13.43)", "ST/OSD", "402", "2,476", e, "B/HC", "TW/OHT", "75,000 Gallons", e, "1,460", "132", "647", "658", e, "31.8", "13.43", "ORDINARY", ""),
        ("7", "Sirsaganj", "PR (7.5) KR (0)", "OSD", e, "1,523", e, "B", "TW/OHT", "30,000 Gallons", e, "306", "50", "300", "174", e, "7.5", "0.0", "ORDINARY", ""),
    ]
    rows = []
    for i, spec in enumerate(data):
        row = deepcopy(template); row.update(dict(zip(variables + ["row_type", "reference_target"], spec)))
        row.update({"row_index": str(i), "pdf_id": pdf_id, "district": DIST}); clear(row, variables); rows.append(row)
    finish(pdf_id, rows, fields, "# Mainpuri Civic source-checked output\n\nSource pages 6–7 were inspected at 300 DPI. Civic rows and their continuation panels were transcribed independently of the Municipal Finance and expenditure tables.\n")


def mededu():
    pdf_id = "mainpuri_mededu_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    variables = ["sl_no", "town_name", "hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]
    def parent(serial, town, children, beds, inherited, pidx):
        out = []
        for j, (child, bed) in enumerate(zip(children, beds)):
            row = deepcopy(template); row.update({"sl_no": serial, "town_name": town, "row_type": "ORDINARY", "reference_target": "", "parent_row_index": str(pidx), "subrow_index": str(j), "subrow_count": str(len(children)), "row_index": "", "pdf_id": pdf_id, "district": DIST}); clear(row, variables)
            for variable in variables: row[variable] = inherited.get(variable, "")
            row["sl_no"], row["town_name"], row["hospitals_dispensaries"], row["med_beds"] = serial, town, child, bed
            out.append(row)
        return out
    rows = []
    def cross(serial, town, pidx):
        out = parent(serial, town, [""], [""], {}, pidx)
        out[0]["row_type"] = "CROSS_REFERENCE"; out[0]["reference_target"] = "Mainpuri"; return out
    rows += cross("1", "Bewar", 0)
    rows += cross("2", "Bhongaon", 1)
    rows += cross("3", "Karhal", 2)
    # Replace the three temporary cross-reference parents with ordinary rows below; the printed table has no reference rows.
    rows = []
    rows += parent("1", "Bewar", ["H (1)", "NH (1)", "FC (1)"], ["6", e, e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "3", "middle_schools": "2", "primary_schools": "3", "other_edu_institutions": e, "stadia": e, "cinemas": e, "auditoria": e, "libraries": e}, 0)
    rows += parent("2", "Bhongaon", ["H (1)", "NH (1)", "FC (1)"], ["8", e, e], {"degree_colleges": "A (1)", "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "3", "middle_schools": "3", "primary_schools": "3", "other_edu_institutions": e, "stadia": e, "cinemas": e, "auditoria": e, "libraries": "PL (2)"}, 1)
    rows += parent("3", "Karhal", ["HC (1)", "FC (1)"], ["4", e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "2", "middle_schools": "2", "primary_schools": "2", "other_edu_institutions": "2", "stadia": e, "cinemas": e, "auditoria": e, "libraries": e}, 2)
    rows += parent("4", "Kuraoli", ["D (1)"], ["3"], {"degree_colleges": "C (1)", "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "2", "middle_schools": "2", "primary_schools": "1", "other_edu_institutions": e, "stadia": e, "cinemas": e, "auditoria": e, "libraries": e}, 3)
    rows += parent("5", "Mainpuri", ["H (4)", "O (1)", "FC (1)", "TBC (1)", "D (1)"], ["60", "16", e, e, e], {"degree_colleges": "A (1)", "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": "Type (2)", "higher_secondary_schools": "4", "middle_schools": "4", "primary_schools": "13", "other_edu_institutions": "22", "stadia": e, "cinemas": "2", "auditoria": e, "libraries": "PL (4) RR (1)"}, 4)
    rows += parent("6", "Shikohabad", ["H (2)", "O (1)", "FC (1)"], ["16", "12", e], {"degree_colleges": "A (2) AS (1)", "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "4", "middle_schools": "4", "primary_schools": "17", "other_edu_institutions": "1", "stadia": e, "cinemas": "1", "auditoria": e, "libraries": "PL (1)"}, 5)
    rows += parent("7", "Sirsaganj", ["H (1)", "FC (1)"], ["4", e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "3", "middle_schools": "1", "primary_schools": "5", "other_edu_institutions": e, "stadia": e, "cinemas": e, "auditoria": e, "libraries": "PL (5)"}, 6)
    for i, row in enumerate(rows): row["row_index"] = str(i)
    finish(pdf_id, rows, fields, "# Mainpuri MedEdu source-checked output\n\nSource pages 8–9 were inspected at 300 DPI. Seven town parents expand to 19 child rows; columns 3–4 are child-scoped and columns 5–17 are propagated within each parent.\n")


def tehsil():
    pdf_id = "mainpuri_tehsil_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    comm = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    allv = edu + med + water + comm
    E = [["157", "187", "32", "38", "2", "2", e, e, e, e], ["115", "133", "17", "20", "1", "2", "1", "1", e, e], ["132", "202", "28", "33", "9", "9", e, e, "1", "1"], ["142", "172", "18", "19", "9", "11", e, e, e, e], ["232", "323", "41", "44", "12", "12", "3", "3", e, e], ["778", "1,017", "136", "154", "33", "36", "4", "4", "1", "1"]]
    M = [["3", "3", "5", "5", e, e, e, e, "1", "1", e, e], ["4", "4", "1", "1", e, e, e, e, "1", "1", e, e], ["4", "4", e, e, "3", "3", e, e, "2", "2", e, e], ["5", "5", e, e, "6", "6", e, e, "3", "3", e, e], ["10", "10", "4", "4", "4", "4", "2", "2", "4", "4", e, e], ["26", "26", "10", "10", "13", "13", "2", "2", "11", "11", e, e]]
    W = [["172", "119", e, "32", "283", "1", "2", e, e, e, e, "1", e, e], ["55", "138", e, "10", "190", "11", "4", e, "1", e, e, "13", e, e], ["87", "168", e, "42", "242", "2", e, e, e, e, e, "5", e, e], ["110", "165", e, "1", "239", e, e, e, e, e, e, e, e, e], ["41", "373", e, "145", "389", e, e, e, e, e, e, e, e, e], ["465", "964", e, "230", "1,343", "14", "6", e, "1", e, e, "19", e, e]]
    R = [["92", "94", e, "1", "26", "28", e, e, "1", "1", e, e], ["55", "86", e, "13", "16", "16", "1", "1", e, e, "1", "1"], ["84", "164", e, "4", "35", "35", "1", "1", "4", "4", e, e], ["58", "53", e, "59", "27", "27", "1", "1", "2", "2", "1", "1"], ["101", "30", "6", "21", "49", "49", "2", "2", e, e, e, e], ["390", "427", "6", "101", "155", "155", "5", "5", "7", "7", "2", "2"]]
    names = ["Shikohabad", "Karhal", "Mainpuri", "Jasrana", "Bhongaon", "District Total"]
    rows = []
    for i, name in enumerate(names):
        row = deepcopy(template); row.update({"sl_no": str(i + 1) if i < 5 else "", "tahsil_name": name, "row_type": "TOTAL" if i == 5 else "ORDINARY", "reference_target": "", "row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        row.update(dict(zip(edu, E[i]))); row.update(dict(zip(med, M[i]))); row.update(dict(zip(water, W[i]))); row.update(dict(zip(comm, R[i])))
        clear(row, ["sl_no", "tahsil_name"] + allv); rows.append(row)
    finish(pdf_id, rows, fields, "# Mainpuri Tahsil source-checked output\n\nSource pages 160–161 were inspected at 300 DPI. Five tahsils and the printed District Total retain aligned educational, medical, water/power, and communications values.\n")


if __name__ == "__main__":
    civic(); mededu(); tehsil()
