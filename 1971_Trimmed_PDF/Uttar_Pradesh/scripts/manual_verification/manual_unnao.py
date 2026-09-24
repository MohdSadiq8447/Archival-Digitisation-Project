import csv
import os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Unnao"
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
    pdf_id = "unnao_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other"]
    values = ["1", "Unnao", "PR (32.8) KR (5.8)", "S/OSD", "825", "15,329", E, "B", "TW/OHT", "171,000 Galls.", E, "2,534", "133", "370", "702", E]
    row = deepcopy(template)
    row.update(dict(zip(variables, values)))
    row.update({"pucca_road_km": "32.8", "kutcha_road_km": "5.8", "row_type": "ORDINARY", "reference_target": "", "requires_review": "False", "row_index": "0", "pdf_id": pdf_id, "district": DIST})
    clear_flags(row, variables + ["pucca_road_km", "kutcha_road_km"])
    finish(pdf_id, [row], fields, "# Unnao Civic source-checked output\n\nThe Unnao Civic row and Amenities continuation were transcribed from pages 4–5 at 300 DPI. Earlier status, finance, location, and later statement sections were excluded.\n")


def mededu():
    pdf_id = "unnao_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = ["hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]
    children = [("H (4)", "171"), ("D (1)", E), ("FC (1)", E), ("O (1)", E)]
    inherited = {"degree_colleges": "ASC (1)", "medical_colleges": E, "engg_colleges": E, "polytechnics": E, "vocational_institutes": E, "higher_secondary_schools": "7", "middle_schools": "5", "primary_schools": "32", "other_edu_institutions": "2", "stadia": "1", "cinemas": "1", "auditoria": E, "libraries": "RR (2)"}
    rows = []
    for j, (child, bed) in enumerate(children):
        row = deepcopy(template)
        row.update({"sl_no": "1", "town_name": "Unnao", "hospitals_dispensaries": child, "med_beds": bed, "row_type": "ORDINARY", "reference_target": "", "requires_review": "False", "parent_row_index": "0", "subrow_index": str(j), "subrow_count": str(len(children)), "row_index": str(j), "pdf_id": pdf_id, "district": DIST})
        for variable in variables:
            row[variable] = inherited.get(variable, E)
        row["hospitals_dispensaries"] = child
        row["med_beds"] = bed
        clear_flags(row, variables)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Unnao MedEdu source-checked output\n\nThe Unnao parent and four printed medical-facility child rows were transcribed from pages 6–7 at 300 DPI. Columns 3–4 are child-scoped and columns 5–17 are inherited within the parent; Trade, population, and Banking sections were excluded.\n")


def tehsil():
    pdf_id = "unnao_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    comm = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    all_variables = edu + med + water + comm
    names = ["Safipur", "Hasanganj", "Unnao", "Purwa", "District Total"]
    educational = [["201", "209", "36", "38", "5", "5", E, E, E, E], ["208", "218", "35", "35", "3", "3", E, E, E, E], ["170", "182", "34", "37", "6", "6", E, E, E, E], ["265", "290", "45", "48", "9", "10", E, E, E, E], ["844", "899", "150", "158", "23", "24", E, E, E, E]]
    medical = [["4", "4", "4", "5", E, E, E, E, "2", "2", E, E], ["10", "10", "6", "6", E, E, E, E, "2", "2", E, E], ["5", "5", "6", "6", "1", "1", "2", "2", "2", "2", E, E], ["3", "3", "12", "12", "3", "3", "1", "1", "3", "3", E, E], ["22", "22", "28", "29", "4", "4", "3", "3", "9", "9", E, E]]
    water_values = [["20", "382", E, "1", "373", E, "2", E, E, E, E, "3", E, E], ["11", "504", E, "1", "496", "1", "1", E, E, E, E, "1", E, E], ["15", "286", E, "1", "292", "1", E, E, E, E, "-", "1", E, E], ["28", "544", E, "4", "555", E, "1", E, E, E, E, "2", E, E], ["74", "1,716", E, "7", "1,716", "2", "4", E, E, E, E, "7", E, E]]
    communications = [["68", "322", E, E, "31", "31", E, E, "2", "2", "1", "1"], ["128", "224", E, E, "30", "30", E, E, "5", "5", E, E], ["121", "136", E, E, "45", "45", E, E, "1", "1", "2", "2"], ["170", "190", E, E, "52", "52", "1", "1", "1", "1", E, E], ["487", "872", E, E, "158", "158", "1", "1", "9", "9", "3", "3"]]
    rows = []
    for i, name in enumerate(names):
        row = deepcopy(template)
        row.update({"sl_no": str(i + 1) if i < 4 else "", "tahsil_name": name, "row_type": "TOTAL" if i == 4 else "ORDINARY", "reference_target": "", "requires_review": "False", "row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        row.update(dict(zip(edu, educational[i])))
        row.update(dict(zip(med, medical[i])))
        row.update(dict(zip(water, water_values[i])))
        row.update(dict(zip(comm, communications[i])))
        clear_flags(row, ["sl_no", "tahsil_name"] + all_variables)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Unnao Tahsil source-checked output\n\nThe four tahsil rows and District Total were transcribed from the educational and drinking-water panels on page 184 and medical/communications panels on page 185 at 300 DPI. Printed placeholders, the Unnao lake dash, and totals are preserved.\n")


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
