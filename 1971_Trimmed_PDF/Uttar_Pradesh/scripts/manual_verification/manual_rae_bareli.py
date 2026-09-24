import csv
import os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Rae Bareli"
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
    pdf_id = "rae_bareli_civic_1971"
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
        ("1", "Jais", "PR (5.0) KR (3.0)", "PT/OSD", "14", "1,200", "3", "B/HC", "TW/OHT", "30,000 Gallons", E, "250", "30", "50", "57", E, "5.0", "3.0", "ORDINARY", ""),
        ("2", "Rae Bareli", "PR (59.5) KR (1.1)", "PT/OSD", "187", "3,648", E, "B/HC/MT", "TW/OHT", "62,500 Gallons", E, "1,219", "132", "547", "442", E, "59.5", "1.1", "ORDINARY", ""),
    ]
    rows = []
    for i, spec in enumerate(specs):
        row = deepcopy(template)
        row.update(dict(zip(variables + ["row_type", "reference_target"], spec)))
        row.update({"row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        clear_flags(row, variables)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Rae Bareli Civic source-checked output\n\nThe two Civic rows and their Amenities continuation were transcribed from pages 1–2 at 300 DPI. Trade, Commerce, Industry, and Banking sections were excluded.\n")


def mededu():
    pdf_id = "rae_bareli_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = [
        "sl_no", "town_name", "hospitals_dispensaries", "med_beds", "degree_colleges",
        "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes",
        "higher_secondary_schools", "middle_schools", "primary_schools",
        "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries",
    ]
    rows = []
    parents = [
        ("1", "Jais", [("H (1)", "9"), ("D (1)", E), ("FC (1)", E)], [E, E, E, E, E, "2", "2", "2", "3", E, E, E, "PL (1)"]),
        ("2", "Rae Bareli", [("H (4)", "132"), ("D (5)", E), ("FC (1)", E), ("HC (1)", E), ("*O (1)", E), ("TBC (1)", "36")], ["AS (1)", E, E, "1", E, "8", "5", "17", "3", "2", "2", E, "PL (3) RR (2)"]),
    ]
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
    finish(pdf_id, rows, fields, "# Rae Bareli MedEdu source-checked output\n\nThe two parents and nine printed medical-facility child rows were transcribed from pages 1–2 at 300 DPI. Columns 3–4 are child-scoped and columns 5–17 are inherited within each parent; the lower non-table material was excluded.\n")


def tehsil():
    pdf_id = "rae_bareli_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    comm = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    all_variables = edu + med + water + comm
    names = ["Maharajganj", "Rae Bareli", "Dalmau", "Salon", "DISTT. TOTAL"]
    educational = [["179", "196", "29", "32", "3", "3", E, E, E, E], ["126", "130", "17", "18", "4", "4", E, E, E, E], ["207", "218", "41", "41", "6", "6", "1", "1", E, E], ["155", "155", "20", "20", "1", "1", E, E, E, E], ["667", "699", "107", "111", "14", "14", "1", "1", E, E]]
    medical = [["7", "7", "11", "20", "3", "3", E, E, "2", "2", "1", "1"], ["5", "5", "14", "14", "2", "2", E, E, "4", "4", E, E], ["19", "19", "5", "5", "1", "1", "1", "1", "1", "1", E, E], ["18", "18", E, E, "5", "5", "1", "1", "1", "1", E, E], ["49", "49", "30", "39", "11", "11", "2", "2", "8", "8", "1", "1"]]
    water_values = [["64", "302", E, E, "366", E, E, E, E, E, E, E, E, E], ["70", "289", E, "4", "354", E, E, E, E, E, E, E, E, E], ["63", "530", E, "11", "585", E, E, E, E, E, E, E, E, E], ["77", "391", E, "1", "458", E, E, E, E, E, "5", E, E, E], ["274", "1,512", E, "16", "1,763", E, E, E, E, E, "5", E, E, E]]
    communications = [["50", "60", "2", "14", "67", "67", E, E, "3", "3", "1", "1"], ["88", "51", "4", "25", "40", "40", E, E, "4", "4", "1", "1"], ["102", "143", "15", "63", "56", "56", E, E, "6", "6", "1", "1"], ["146", "123", E, "106", "50", "50", E, E, "2", "2", E, E], ["386", "377", "21", "208", "213", "213", E, E, "15", "15", "3", "3"]]
    rows = []
    for i, name in enumerate(names):
        row = deepcopy(template)
        row.update({"sl_no": str(i + 1) if i < 4 else "", "tahsil_name": name, "row_type": "TOTAL" if i == 4 else "ORDINARY", "reference_target": "", "row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        row.update(dict(zip(edu, educational[i])))
        row.update(dict(zip(med, medical[i])))
        row.update(dict(zip(water, water_values[i])))
        row.update(dict(zip(comm, communications[i])))
        clear_flags(row, ["sl_no", "tahsil_name"] + all_variables)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Rae Bareli Tahsil source-checked output\n\nThe four tahsil rows and printed DISTT. TOTAL were transcribed from the educational, medical, drinking-water, and communications panels on pages 1–2 at 300 DPI. Printed placeholders and totals are preserved.\n")


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
