import csv
import os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Sultanpur"
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
    pdf_id = "sultanpur_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other"]
    values = ["1", "Sultanpur", "PR (40) KR (10)", "ST/OSD/BSD", "635", "3,776", E, "HC/HL", "TW/OHT", "50,000 Galls.", E, "1,104", "143", "746", "296", E]
    row = deepcopy(template)
    row.update(dict(zip(variables, values)))
    row.update({"pucca_road_km": "40.0", "kutcha_road_km": "10.0", "row_type": "ORDINARY", "reference_target": "", "requires_review": "False", "row_index": "0", "pdf_id": pdf_id, "district": DIST})
    clear_flags(row, variables + ["pucca_road_km", "kutcha_road_km"])
    finish(pdf_id, [row], fields, "# Sultanpur Civic source-checked output\n\nThe Sultanpur Civic row and its Amenities continuation were transcribed from pages 6–7 at 300 DPI. Trade, Municipal Finance, and Banking sections were excluded.\n")


def mededu():
    pdf_id = "sultanpur_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = ["hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]

    children = [("H (4)", "241"), ("D (1)", E), ("TBC (1)", E), ("FC (1)", E)]
    inherited = {"degree_colleges": "A (1)", "medical_colleges": E, "engg_colleges": E, "polytechnics": E, "vocational_institutes": "Sh. Type (2)", "higher_secondary_schools": "4", "middle_schools": "4", "primary_schools": "14", "other_edu_institutions": "7", "stadia": E, "cinemas": "1", "auditoria": E, "libraries": "PL (1)"}
    rows = []
    for j, (child, bed) in enumerate(children):
        row = deepcopy(template)
        row.update({"sl_no": "1", "town_name": "Sultanpur", "hospitals_dispensaries": child, "med_beds": bed, "row_type": "ORDINARY", "reference_target": "", "requires_review": "False", "parent_row_index": "0", "subrow_index": str(j), "subrow_count": str(len(children)), "row_index": str(j), "pdf_id": pdf_id, "district": DIST})
        for variable in variables:
            row[variable] = inherited.get(variable, E)
        row["hospitals_dispensaries"] = child
        row["med_beds"] = bed
        clear_flags(row, variables)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Sultanpur MedEdu source-checked output\n\nThe Sultanpur parent and four printed medical-facility child rows were transcribed from pages 6–7 at 300 DPI. Columns 3–4 are child-scoped; columns 5–17 are inherited for the parent. Trade and Banking sections were excluded.\n")


def tehsil():
    pdf_id = "sultanpur_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    comm = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    all_variables = edu + med + water + comm
    names = ["Musafir Khana", "Amethi", "Sultanpur", "Kandipur", "District Total (Rural)"]
    educational = [["242", "268", "22", "23", "9", "9", E, E, "1", "1"], ["216", "241", "26", "29", "6", "6", E, E, "1", "1"], ["250", "382", "37", "39", "8", "8", E, E, "1", "1"], ["296", "333", "32", "32", "14", "14", E, E, "1", "1"], ["1,004", "1,224", "117", "123", "37", "37", E, E, "4", "4"]]
    medical = [["6", "6", "4", "4", "2", "2", "6", "6", "17", "18", E, E], ["7", "8", "13", "19", "4", "4", "3", "3", "10", "12", E, E], ["7", "7", "11", "12", "13", "13", "2", "2", "10", "10", E, E], ["10", "10", "9", "9", "10", "10", "10", "10", "18", "20", E, E], ["30", "31", "37", "44", "29", "29", "21", "21", "55", "60", E, E]]
    water_values = [["64", "371", E, "2", "429", "7", "1", E, E, E, E, "3", E, E], ["15", "448", E, "23", "459", "13", E, E, E, E, E, "9", E, E], ["168", "686", E, "13", "834", "5", "8", E, E, "7", E, "6", E, E], ["277", "506", E, "21", "755", "8", "46", E, E, "7", E, "13", E, E], ["524", "2,011", E, "59", "2,477", "33", "55", E, E, "7", E, "31", E, E]]
    communications = [["42", "148", "16", "144", "56", "56", E, E, "3", "3", "1", "1"], ["98", "100", "9", "119", "37", "37", E, E, "9", "9", "1", "1"], ["220", "273", "57", "158", "78", "78", "1", "1", "4", "4", E, E], ["149", "405", "28", "115", "82", "82", E, E, "4", "4", E, E], ["509", "962", "110", "536", "253", "253", "1", "1", "20", "20", "2", "2"]]
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
    finish(pdf_id, rows, fields, "# Sultanpur Tahsil source-checked output\n\nThe four tahsil rows and District Total (Rural) were transcribed from the educational and drinking-water panels on page 250 and medical/communications panels on page 251 at 300 DPI. Printed placeholders and totals are preserved.\n")


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
