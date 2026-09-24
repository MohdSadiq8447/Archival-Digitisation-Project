import csv
import os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Pithoragarh"
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
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    old, _ = load(pdf_id)
    with open(os.path.join(out, "CORRECTION_LOG.csv"), "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f); writer.writerow(["row_index", "variable", "original_value", "corrected_value", "reason"])
        for i, row in enumerate(rows):
            before = old[i] if i < len(old) else {}
            for variable in fields:
                if variable.endswith("_flag") or variable in {"row_index", "parent_row_index", "subrow_index", "subrow_count", "requires_review", "extracted_at"}:
                    continue
                if before.get(variable, "") != row.get(variable, ""):
                    writer.writerow([i, variable, before.get(variable, ""), row.get(variable, ""), "300-DPI source inspection; unrelated statement sections excluded"])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f: f.write(report)
    print(pdf_id, len(rows))

def civic():
    pdf_id = "pithoragarh_civic_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    variables = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other", "pucca_road_km", "kutcha_road_km"]
    spec = ("1", "Pithoragarh", "PR (12) KR (20)", "S/OSD", "225", "174", E, "HL", "F/SR", "65,000 Gallon.", "Yes", "679", "8", "216", "350", E, "12.0", "20.0", "ORDINARY", "")
    row = deepcopy(template); row.update(dict(zip(variables + ["row_type", "reference_target"], spec))); row.update({"row_index": "0", "pdf_id": pdf_id, "district": DIST}); clear_flags(row, variables)
    finish(pdf_id, [row], fields, "# Pithoragarh Civic source-checked output\n\nThe sole Civic row and its Amenities continuation were transcribed from pages 6–7 at 300 DPI. Trade, Commerce, Industry, and Banking sections were excluded.\n")

def mededu():
    pdf_id = "pithoragarh_mededu_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    variables = ["sl_no", "town_name", "hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]
    rows = []
    for j, (child, bed) in enumerate([("H(6)", "272"), ("FC(1)", E)]):
        row = deepcopy(template); row.update({"sl_no": "1", "town_name": "Pithoragarh", "row_type": "ORDINARY", "reference_target": "", "parent_row_index": "0", "subrow_index": str(j), "subrow_count": "2", "row_index": str(j), "pdf_id": pdf_id, "district": DIST}); clear_flags(row, variables)
        for variable in variables: row[variable] = E
        row.update({"sl_no": "1", "town_name": "Pithoragarh", "hospitals_dispensaries": child, "med_beds": bed, "degree_colleges": "AS (1)", "higher_secondary_schools": "5", "middle_schools": "1", "primary_schools": "8", "stadia": "1", "cinemas": "1", "libraries": "PL (1) PR (2)"})
        rows.append(row)
    finish(pdf_id, rows, fields, "# Pithoragarh MedEdu source-checked output\n\nThe Pithoragarh parent and its two printed medical-facility child rows were transcribed from pages 6–7 at 300 DPI. Columns 3–4 are child-scoped and columns 5–17 are inherited within the parent.\n")

def tehsil():
    pdf_id = "pithoragarh_tehsil_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    comm = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    all_variables = edu + med + water + comm
    names = ["Munsiari", "Dharchula", "Didihat", "Pithoragarh", "District Total (Rural)"]
    educational = [["85", "86", "5", "5", "3", "3", E, E, "1", "1"], ["60", "77", "8", "8", "1", "1", E, E, "4", "4"], ["160", "164", "19", "19", "7", "7", "39", "39", "424", "424"], ["155", "165", "26", "27", "6", "7", E, E, E, E], ["460", "492", "58", "59", "17", "18", "39", "39", "428", "428"]]
    medical = [["6", "6", "1", "1", "5", "5", "1", "1", "2", "2", "1", "1"], ["5", "5", "3", "3", "5", "5", "1", "1", "2", "3", E, E], ["4", "4", "6", "6", "10", "10", E, E, "6", "6", E, E], ["14", "14", "1", "1", "11", "11", E, E, "5", "5", E, E], ["29", "29", "11", "11", "31", "31", "2", "2", "15", "16", "1", "1"]]
    water_values = [[E, "223", E, E, E, E, "21", "45", E, "152", E, E, E, E], [E, E, "1", E, "9", E, "25", "41", E, "20", E, E, E, E], [E, E, "1", "8", "7", E, "61", "166", "22", E, E, E, "2", E], [E, "661", "50", E, E, "21", "17", "183", "4", "217", E, E, "293", E], [E, "884", "52", "8", "16", "21", "124", "435", "26", "389", E, E, "295", E]]
    communications = [["11", "205", E, E, "25", "25", E, E, E, E, E, E], ["11", "69", E, E, "37", "37", "1", "1", E, E, E, E], ["98", "602", E, E, "56", "56", "3", "3", E, E, E, E], ["57", "466", E, E, "56", "56", E, E, "2", "2", E, E], ["177", "1,342", E, E, "174", "174", "4", "4", "2", E, E, E]]
    rows = []
    for i, name in enumerate(names):
        row = deepcopy(template); row.update({"sl_no": str(i + 1) if i < 4 else "", "tahsil_name": name, "row_type": "TOTAL" if i == 4 else "ORDINARY", "reference_target": "", "row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        row.update(dict(zip(edu, educational[i]))); row.update(dict(zip(med, medical[i]))); row.update(dict(zip(water, water_values[i]))); row.update(dict(zip(comm, communications[i])))
        clear_flags(row, ["sl_no", "tahsil_name"] + all_variables); rows.append(row)
    finish(pdf_id, rows, fields, "# Pithoragarh Tahsil source-checked output\n\nThe four printed tahsil rows and District Total (Rural) were transcribed from the educational, medical, water, and communications panels on pages 166–167 at 300 DPI. Printed totals and placeholders are preserved.\n")

if __name__ == "__main__":
    civic(); mededu(); tehsil()
