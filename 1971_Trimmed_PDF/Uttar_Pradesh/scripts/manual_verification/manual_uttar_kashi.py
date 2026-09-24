import csv
import os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Uttar Kashi"
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
    pdf_id = "uttar_kashi_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other"]
    values = ["1", "Uttarkashi", "PR (8) KR (2)", "S/PT/OSD", "200", "400", E, "HL/HC", "R", E, E, "395", "10", "170", "110", E]
    row = deepcopy(template)
    row.update(dict(zip(variables, values)))
    row.update({"pucca_road_km": "8.0", "kutcha_road_km": "2.0", "row_type": "ORDINARY", "reference_target": "", "requires_review": "False", "row_index": "0", "pdf_id": pdf_id, "district": DIST})
    clear_flags(row, variables + ["pucca_road_km", "kutcha_road_km"])
    finish(pdf_id, [row], fields, "# Uttar Kashi Civic source-checked output\n\nThe Uttarkashi Civic row and Amenities continuation were transcribed from pages 6–7 at 300 DPI. Status, Trade, Banking, and other unrelated statements were excluded.\n")


def mededu():
    pdf_id = "uttar_kashi_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = ["hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]
    children = [("H (1)", "36"), ("FC (1)", E)]
    inherited = {"degree_colleges": "S (1)", "medical_colleges": E, "engg_colleges": E, "polytechnics": E, "vocational_institutes": E, "higher_secondary_schools": "2", "middle_schools": E, "primary_schools": "5", "other_edu_institutions": "1", "stadia": E, "cinemas": E, "auditoria": E, "libraries": "PL (1)"}
    rows = []
    for j, (child, bed) in enumerate(children):
        row = deepcopy(template)
        row.update({"sl_no": "1", "town_name": "Uttarkashi", "hospitals_dispensaries": child, "med_beds": bed, "row_type": "ORDINARY", "reference_target": "", "requires_review": "False", "parent_row_index": "0", "subrow_index": str(j), "subrow_count": str(len(children)), "row_index": str(j), "pdf_id": pdf_id, "district": DIST})
        for variable in variables:
            row[variable] = inherited.get(variable, E)
        row["hospitals_dispensaries"] = child
        row["med_beds"] = bed
        clear_flags(row, variables)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Uttar Kashi MedEdu source-checked output\n\nThe Uttarkashi parent and two printed medical-facility child rows were transcribed from pages 6–7 at 300 DPI. Columns 3–4 are child-scoped and columns 5–17 are inherited within the parent; Trade and Banking sections were excluded.\n")


def tehsil():
    pdf_id = "uttar_kashi_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    comm = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    all_variables = edu + med + water + comm
    names = ["Puraula", "Rajgarhi", "Dunda", "Bhatwari", "District Total (Rural)"]
    educational = [["70", "76", "5", "6", "2", "2", E, E, E, E], ["62", "62", "19", "19", "1", "1", E, E, "2", "2"], ["106", "106", "5", "5", E, E, E, E, E, E], ["58", "62", "5", "6", E, E, E, E, E, E], ["296", "306", "34", "36", "3", "3", E, E, "2", "2"]]
    medical = [["3", "3", "6", "6", "5", "5", E, E, E, E, E, E], ["6", "6", "3", "4", "6", "6", E, E, "2", "2", E, E], [E, E, "7", "7", "1", "1", "1", "1", E, "-", E, E], ["6", "6", "2", "3", "8", "8", "5", "5", "2", "2", E, E], ["15", "15", "13", "20", "20", "20", "6", "6", "4", "4", E, E]]
    water_values = [[E, "180", "77", E, "1", E, "6", "85", "4", E, E, E, E, E], ["1", "182", "86", E, "2", E, "10", "73", E, E, E, E, E, E], [E, "223", "39", E, E, E, E, "100", "9", E, E, E, E, E], ["2", "95", "59", E, E, E, "7", "27", "2", "-", E, E, E, E], ["3", "680", "261", E, "3", E, "23", "285", "15", E, E, E, E, E]]
    communications = [["2", "179", E, E, "9", "9", E, E, E, E, E, E], ["21", "179", E, E, "13", "13", E, E, E, E, "2", "2"], ["11", "216", E, E, "13", "13", E, E, E, E, E, E], ["27", "78", E, E, "15", "16", E, E, "1", E, "3", "3"], ["61", "652", E, E, "50", "51", E, E, "1", E, "5", "5"]]
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
    finish(pdf_id, rows, fields, "# Uttar Kashi Tahsil source-checked output\n\nThe four tahsil rows and District Total (Rural) were transcribed from the educational and drinking-water panels on page 84 and medical/communications panels on page 85 at 300 DPI. Printed dashes, ellipses, and totals are preserved.\n")


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
