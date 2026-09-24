import csv
import os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Rampur"
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
    pdf_id = "rampur_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = [
        "sl_no", "town_name", "road_length_km", "sewerage_drainage_system",
        "water_borne_latrines", "service_latrines", "other_latrines",
        "night_soil_disposal_method", "water_source", "water_capacity", "fire_service",
        "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light",
        "elec_other", "pucca_road_km", "kutcha_road_km",
    ]
    specs = [
        ("1", "Rampur", "PR (130) KR (45)", "PT/OSD", "824", "17,484", "60", "HL/B/HC", "TW/OHT", "100,000 Galls.", "Yes", "11,351", "605", "792", "2,372", E, "130", "45", "ORDINARY", ""),
        ("2", "Tanda", "PR (3) KR (2)", "OSD", E, "1,327", E, "B/HL", "HP/W", E, E, "255", "34", "97", "176", E, "3", "2", "ORDINARY", ""),
    ]
    rows = []
    for i, spec in enumerate(specs):
        row = deepcopy(template)
        row.update(dict(zip(variables + ["row_type", "reference_target"], spec)))
        row.update({"row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        clear_flags(row, variables)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Rampur Civic source-checked output\n\nThe two Civic rows and Amenities continuation were transcribed from pages 6–7 at 300 DPI. Trade, Commerce, Industry, and Banking sections were excluded.\n")


def mededu():
    pdf_id = "rampur_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = [
        "sl_no", "town_name", "hospitals_dispensaries", "med_beds", "degree_colleges",
        "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes",
        "higher_secondary_schools", "middle_schools", "primary_schools",
        "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries",
    ]
    parents = [
        ("1", "Rampur", [("H (6)", "255"), ("D (2)", E), ("HC (3)", "10"), ("TBC (1)", "25"), ("NH (2)", "10"), ("FC (1)", E)], ["ASC (1)", E, E, E, "Sh. Type (2)", "14", "10", "67", E, "1", "4", "1", "PL (2) RR (1)"]),
        ("2", "Tanda", [("H (1)", "7"), ("D (1)", E), ("FC (1)", E)], [E, E, E, E, E, "5", "2", "2", E, E, E, E, "RR (1)"]),
    ]
    rows = []
    row_index = 0
    for parent_index, (sl_no, town, children, inherited) in enumerate(parents):
        for sub_index, (child, bed) in enumerate(children):
            row = deepcopy(template)
            row.update({"sl_no": sl_no, "town_name": town, "row_type": "ORDINARY", "reference_target": "", "parent_row_index": str(parent_index), "subrow_index": str(sub_index), "subrow_count": str(len(children)), "row_index": str(row_index), "pdf_id": pdf_id, "district": DIST})
            for variable in variables:
                row[variable] = E
            row.update({"sl_no": sl_no, "town_name": town, "hospitals_dispensaries": child, "med_beds": bed})
            for variable, value in zip(variables[4:], inherited):
                row[variable] = value
            clear_flags(row, variables)
            rows.append(row)
            row_index += 1
    finish(pdf_id, rows, fields, "# Rampur MedEdu source-checked output\n\nThe two parents and nine printed medical-facility child rows were transcribed from pages 6–7 at 300 DPI. Columns 3–4 are child-scoped and columns 5–17 are inherited within each parent; Trade and other non-MedEdu panels were excluded.\n")


def tehsil():
    pdf_id = "rampur_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    comm = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    all_variables = edu + med + water + comm
    names = ["Suar", "Bilaspur", "Rampur", "Shahabad", "Milak", "District Total (Rural)"]
    educational = [["81", "84", "3", "3", "1", "1", E, E, E, E], ["51", "55", "8", "9", "2", "2", E, E, E, E], ["81", "82", "5", "5", E, E, E, E, E, E], ["57", "63", "8", "9", "2", "2", E, E, E, E], ["78", "85", "8", "9", "2", "2", E, E, E, E], ["348", "359", "32", "35", "7", "7", E, E, E, E]]
    medical = [["4", "4", "4", "4", "2", "2", E, E, "1", "1", E, E], ["3", "3", "3", "3", "1", "1", E, E, "2", "2", E, E], ["2", "2", E, E, E, E, E, E, "1", "1", E, E], ["2", "2", "2", "2", "3", "3", "1", "1", "1", "1", E, E], ["3", "3", E, E, "1", "1", E, E, "1", "1", E, E], ["14", "14", "9", "9", "7", "7", "1", "1", "6", "6", E, E]]
    water_values = [["47", "239", "1", "20", "258", E, E, E, E, E, E, E, E, E], ["94", "121", "1", "197", "127", E, "8", E, "1", E, E, E, E, E], ["38", "109", E, "203", "242", E, E, E, E, E, E, E, E, E], ["89", "114", E, "175", "181", E, "3", E, E, E, E, E, E, E], ["28", "175", E, "196", "196", E, E, E, E, E, E, E, E, E], ["296", "758", "2", "991", "1,004", E, "11", E, "1", E, E, E, E, E]]
    communications = [["53", "160", "26", E, "10", "10", E, E, "1", "1", "1", "1"], ["36", "99", "20", E, "9", "9", E, E, "1", "1", "12", "12"], ["52", "100", "65", "3", "19", "19", E, E, E, E, "2", "2"], ["15", "102", "6", "19", "10", "10", E, E, "2", "2", "1", "1"], ["38", "132", E, "18", "14", "14", E, E, "1", "1", "1", "1"], ["194", "593", "117", "40", "62", "62", E, E, "5", "5", "17", "17"]]
    rows = []
    for i, name in enumerate(names):
        row = deepcopy(template)
        row.update({"sl_no": str(i + 1) if i < 5 else "", "tahsil_name": name, "row_type": "TOTAL" if i == 5 else "ORDINARY", "reference_target": "", "row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        row.update(dict(zip(edu, educational[i])))
        row.update(dict(zip(med, medical[i])))
        row.update(dict(zip(water, water_values[i])))
        row.update(dict(zip(comm, communications[i])))
        clear_flags(row, ["sl_no", "tahsil_name"] + all_variables)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Rampur Tahsil source-checked output\n\nThe five tahsil rows and District Total (Rural) were transcribed from the educational, medical, drinking-water, and communications panels on pages 132–133 at 300 DPI. Printed placeholders and totals are preserved.\n")


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
