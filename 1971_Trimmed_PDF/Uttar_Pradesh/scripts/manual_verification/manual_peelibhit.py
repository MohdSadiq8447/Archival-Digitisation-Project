import csv
import os
from copy import deepcopy


ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Peelibhit"
E = "..."


def load(pdf_id):
    src = os.path.join(ROOT, f"up1971-{pdf_id}-regex-cleaned-v1", "csv", f"{pdf_id}.csv")
    with open(src, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows, list(rows[0])


def clear_flags(row, variables):
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
        writer.writeheader()
        writer.writerows(rows)
    old, _ = load(pdf_id)
    with open(os.path.join(out, "CORRECTION_LOG.csv"), "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["row_index", "variable", "original_value", "corrected_value", "reason"])
        for i, row in enumerate(rows):
            before = old[i] if i < len(old) else {}
            for variable in fields:
                if variable.endswith("_flag") or variable in {
                    "row_index", "parent_row_index", "subrow_index", "subrow_count",
                    "requires_review", "extracted_at",
                }:
                    continue
                if before.get(variable, "") != row.get(variable, ""):
                    writer.writerow([i, variable, before.get(variable, ""), row.get(variable, ""),
                                     "300-DPI source inspection; unrelated statement sections excluded"])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "peelibhit_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = [
        "sl_no", "town_name", "road_length_km", "sewerage_drainage_system",
        "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method",
        "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial",
        "elec_commercial", "elec_road_light", "elec_other", "pucca_road_km", "kutcha_road_km",
    ]
    data = [
        ("1", "Bisalpur", "PR (12.7) KR (2.1)", "PT/OSD", "25", "3,408", E, "B", "HP", E, E, "800", "12", "77", "350", E, "12.7", "2.1", "ORDINARY", ""),
        ("2", "Pilibhit", "PR (109.1) KR (5.3)", "S/OSD", "1,073", "12,584", E, "B", "TW/OHT", "100,000 Galls.", "Yes", "4,357", "230", "146", "1,638", E, "109.1", "5.3", "ORDINARY", ""),
        ("3", "Puranpur", "PR (1) KR (1)", "PT/BD/OSD", "276", "1,743", E, "HC", "HP", E, E, "800", "100", "139", "150", E, "1.0", "1.0", "ORDINARY", ""),
    ]
    rows = []
    for i, spec in enumerate(data):
        row = deepcopy(template)
        row.update(dict(zip(variables + ["row_type", "reference_target"], spec)))
        row.update({"row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        clear_flags(row, variables)
        rows.append(row)
    finish(pdf_id, rows, fields,
           "# Peelibhit Civic source-checked output\n\n"
           "The three printed Civic rows and Amenities continuation panel were transcribed from pages 6–7 at 300 DPI. "
           "Trade, Commerce, Industry, and Banking sections were excluded.\n")


def mededu():
    pdf_id = "peelibhit_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = [
        "sl_no", "town_name", "hospitals_dispensaries", "med_beds", "degree_colleges",
        "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes",
        "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions",
        "stadia", "cinemas", "auditoria", "libraries",
    ]

    def parent(serial, town, children, beds, inherited, pidx):
        out = []
        for j, (child, bed) in enumerate(zip(children, beds)):
            row = deepcopy(template)
            row.update({"sl_no": serial, "town_name": town, "row_type": "ORDINARY", "reference_target": "",
                        "parent_row_index": str(pidx), "subrow_index": str(j), "subrow_count": str(len(children)),
                        "row_index": "", "pdf_id": pdf_id, "district": DIST})
            clear_flags(row, variables)
            for variable in variables:
                row[variable] = inherited.get(variable, E)
            row["sl_no"] = serial
            row["town_name"] = town
            row["hospitals_dispensaries"] = child
            row["med_beds"] = bed
            out.append(row)
        return out

    rows = []
    rows += parent("1", "Bisalpur", ["H(2)", "HC(1)", "FC(1)"], ["16", E, E], {
        "higher_secondary_schools": "4", "middle_schools": "4", "primary_schools": "14",
    }, 0)
    rows += parent("2", "Pilibhit", ["H(5)", "D(2)", "FC(1)", "TBC(1)", "O(1)"], ["134", "1", E, E, E], {
        "degree_colleges": "A (1)", "medical_colleges": "1*", "higher_secondary_schools": "5",
        "middle_schools": "6", "primary_schools": "63", "cinemas": "2", "libraries": "PL (2)",
    }, 1)
    rows += parent("3", "Puranpur", ["H(1)", "FC(1)"], ["10", E], {
        "higher_secondary_schools": "1", "middle_schools": "2", "primary_schools": "6",
        "other_edu_institutions": "2", "libraries": "PL (1)",
    }, 2)
    for i, row in enumerate(rows):
        row["row_index"] = str(i)
    finish(pdf_id, rows, fields,
           "# Peelibhit MedEdu source-checked output\n\n"
           "The three printed town parents and Cultural Facilities continuation panel were transcribed from pages 6–7 at 300 DPI. "
           "Columns 3–4 remain child-scoped and columns 5–17 are inherited only within each parent. The Ayurvedic College marker is retained as printed.\n")


def tehsil():
    pdf_id = "peelibhit_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools",
           "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges",
           "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres",
           "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres",
           "other_med_villages", "other_med_institutions"]
    water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages",
             "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages",
             "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    comm = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages",
            "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices",
            "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    all_variables = edu + med + water + comm
    names = ["Pilibhit", "Bisalpur", "Puranpur", "Distt. Total"]
    educational = [["150", "166", "19", "19", "5", "5", E, E, E, E],
                   ["182", "191", "13", "13", "6", "6", E, E, "1", "1"],
                   ["91", "93", "13", "13", "2", "2", E, E, E, E],
                   ["423", "450", "45", "45", "13", "13", E, E, "1", "1"]]
    medical = [["3", "3", "8", "8", "10", "11", "2", "3", "8", "8", E, E],
               ["3", "3", "10", "10", E, E, E, E, E, E, E, E],
               ["4", "4", "4", "4", "2", "2", "1", "1", "2", "2", E, E],
               ["10", "10", "22", "22", "12", "13", "3", "4", "10", "10", E, E]]
    water_values = [["94", "379", E, "404", "336", "4", "3", E, E, E, E, "49", E, "56"],
                    ["47", "424", E, "406", "413", "10", "2", E, E, E, E, "1", E, "52"],
                    ["53", "341", E, "312", "190", "47", "4", E, E, E, E, "47", E, "85"],
                    ["194", "1,144", E, "1,122", "939", "61", "9", E, E, E, E, "97", E, "193"]]
    communications = [["66", "135", "6", "154", "21", "21", E, E, "8", "8", "3", "3"],
                      ["76", "91", "8", "48", "24", "24", E, E, "1", "1", "2", "2"],
                      ["44", "160", "25", "49", "16", "16", E, E, E, E, "3", "3"],
                      ["186", "389", "39", "251", "61", "61", E, E, "9", "9", "8", "8"]]
    rows = []
    for i, name in enumerate(names):
        row = deepcopy(template)
        row.update({"sl_no": str(i + 1) if i < 3 else "", "tahsil_name": name,
                    "row_type": "TOTAL" if i == 3 else "ORDINARY", "reference_target": "",
                    "row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        row.update(dict(zip(edu, educational[i])))
        row.update(dict(zip(med, medical[i])))
        row.update(dict(zip(water, water_values[i])))
        row.update(dict(zip(comm, communications[i])))
        clear_flags(row, ["sl_no", "tahsil_name"] + all_variables)
        rows.append(row)
    finish(pdf_id, rows, fields,
           "# Peelibhit Tahsil source-checked output\n\n"
           "The three printed tahsil rows and Distt. Total were transcribed from the educational, medical, water, and communications panels on pages 136–137 at 300 DPI. Printed placeholders and totals are preserved.\n")


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
