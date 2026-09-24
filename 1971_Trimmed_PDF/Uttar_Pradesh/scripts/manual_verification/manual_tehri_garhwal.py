import csv
import os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Tehri Garhwal"
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
                if variable.endswith("_flag") or variable in {"row_index", "parent_row_index", "subrow_index", "subrow_count", "requires_review", "extracted_at"}:
                    continue
                if before.get(variable, "") != row.get(variable, ""):
                    writer.writerow([i, variable, before.get(variable, ""), row.get(variable, ""), "300-DPI source inspection; unrelated statement sections excluded"])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "tehri_garhwal_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other"]
    data = [
        ("1", "Devaprayag", "PR (10) KR (2)", "PT/OSD", "16", "212", E, "HC/HL", "F", E, E, "78", "1", "40", "193", E, "10.0", "2.0"),
        ("2", "Muni-Ki-Reti", "PR (2) KR (3)", "PT/OSD", "52", "142", E, "HC/HL", "TW/SR", "25,000 Galls.", E, "88", E, "16", "42", E, "2.0", "3.0"),
        ("3", "Narendranagar", "PR (6) KR (4)", "OSD", E, "498", E, "HC/HL", "F/SR", "529,909 Galls.", E, "192", "2", "14", "84", E, "6.0", "4.0"),
        ("4", "Tehri", "PR (6) KR (8)", "PT/OSD", "17", "720", E, "HC/HL", "F/SR", "30,600 Galls.", E, "375", "1", "11", "202", E, "6.0", "8.0"),
    ]
    rows = []
    for i, spec in enumerate(data):
        row = deepcopy(template)
        row.update(dict(zip(variables + ["pucca_road_km", "kutcha_road_km"], spec)))
        row.update({"row_type": "ORDINARY", "reference_target": "", "requires_review": "False", "row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        clear_flags(row, variables + ["pucca_road_km", "kutcha_road_km"])
        rows.append(row)
    finish(pdf_id, rows, fields, "# Tehri Garhwal Civic source-checked output\n\nThe four Civic rows and Amenities continuation were transcribed from pages 10–11 at 300 DPI. Trade, Municipal Finance, and Banking sections were excluded.\n")


def mededu():
    pdf_id = "tehri_garhwal_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = ["hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]

    parents = [
        ("1", "Devaprayag", [("H (1)", "2"), ("*O (1)", E)], {"middle_schools": "1", "primary_schools": "2", "libraries": "RR (1)"}),
        ("2", "Muni-Ki-Reti", [("H (1)", "4"), ("FC (1)", E), ("*O (1)", E)], {"middle_schools": "2", "primary_schools": "2", "other_edu_institutions": "1", "libraries": "PL (1)"}),
        ("3", "Narendranagar", [("H (1)", "36"), ("*O (2)", E), ("FC (1)", E)], {"polytechnics": "-", "middle_schools": "1", "primary_schools": "1", "auditoria": "1", "libraries": "RR (1)"}),
        ("4", "Tehri", [("H (2)", "29"), ("TBC (1)", E), ("FC (1)", E), ("*O (1)", E)], {"degree_colleges": "A (1)", "medical_colleges": E, "engg_colleges": E, "polytechnics": "1", "vocational_institutes": E, "higher_secondary_schools": "4", "middle_schools": "1", "primary_schools": "-", "other_edu_institutions": E, "stadia": E, "cinemas": E, "auditoria": E, "libraries": "RR (1)"}),
    ]
    rows = []
    pidx = 0
    for serial, town, children, inherited in parents:
        for j, (child, bed) in enumerate(children):
            row = deepcopy(template)
            row.update({"sl_no": serial, "town_name": town, "hospitals_dispensaries": child, "med_beds": bed, "row_type": "ORDINARY", "reference_target": "", "requires_review": "False", "parent_row_index": str(pidx), "subrow_index": str(j), "subrow_count": str(len(children)), "row_index": str(len(rows)), "pdf_id": pdf_id, "district": DIST})
            for variable in variables:
                row[variable] = inherited.get(variable, E)
            row["hospitals_dispensaries"] = child
            row["med_beds"] = bed
            clear_flags(row, variables)
            rows.append(row)
        pidx += 1
    finish(pdf_id, rows, fields, "# Tehri Garhwal MedEdu source-checked output\n\nThe four printed town parents and 12 medical-facility child rows were transcribed from pages 12–13 at 300 DPI. Columns 3–4 are child-scoped and columns 5–17 are inherited within each parent; the explanatory *O footnote and later sections were excluded.\n")


def tehsil():
    pdf_id = "tehri_garhwal_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    comm = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    all_variables = edu + med + water + comm
    names = ["Tehri", "Pratapnagar", "Devaprayag", "District Total (Rural)"]
    educational = [["149", "153", "14", "15", "1", "1", E, E, E, E], ["160", "171", "18", "19", "4", "4", E, E, E, E], ["262", "269", "35", "35", "7", "7", E, E, E, E], ["571", "593", "67", "69", "12", "12", E, E, E, E]]
    medical = [["6", "6", "6", "6", "9", "9", E, E, "3", "3", E, E], ["3", "3", "7", "7", "3", "3", "2", "2", "3", "3", E, E], ["10", "10", "12", "12", "5", "5", "2", "2", "4", "4", E, E], ["19", "19", "25", "25", "17", "17", "4", "4", "10", "10", E, E]]
    water_values = [[E, E, "116", E, "10", E, "29", "467", "39", E, E, E, "25", E], ["2", E, "89", E, "4", E, "23", "319", "12", "-", E, E, "63", E], ["2", E, "116", E, "92", "45", "461", "131", "39", E, E, "4", E, E], ["4", E, "321", E, "106", "1", "97", "1,247", "182", "39", E, "4", "88", E]]
    communications = [["74", "497", "4", E, "32", "32", E, E, E, E, E, E], ["4", "401", "2", E, "37", "37", E, E, E, E, E, E], ["60", "745", "44", E, "50", "50", E, E, "2", "2", E, E], ["174", "1,643", "50", E, "119", "129", E, E, "2", "2", E, E]]
    rows = []
    for i, name in enumerate(names):
        row = deepcopy(template)
        row.update({"sl_no": str(i + 1) if i < 3 else "", "tahsil_name": name, "row_type": "TOTAL" if i == 3 else "ORDINARY", "reference_target": "", "requires_review": "False", "row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        row.update(dict(zip(edu, educational[i])))
        row.update(dict(zip(med, medical[i])))
        row.update(dict(zip(water, water_values[i])))
        row.update(dict(zip(comm, communications[i])))
        clear_flags(row, ["sl_no", "tahsil_name"] + all_variables)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Tehri Garhwal Tahsil source-checked output\n\nThe three tahsil rows and District Total (Rural) were transcribed from the educational and drinking-water panels on page 208 and medical/communications panels on page 209 at 300 DPI. Printed dashes, ellipses, and the printed total values are preserved.\n")


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
