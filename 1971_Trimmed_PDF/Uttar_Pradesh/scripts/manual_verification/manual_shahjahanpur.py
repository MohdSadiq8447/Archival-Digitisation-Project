import csv
import os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Shahjahanpur"
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
                    writer.writerow([i, variable, before.get(variable, ""), row.get(variable, ""), "300-DPI source inspection; Municipal Finance/Expenditure/Trade sections excluded"])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f: f.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "shahjahanpur_civic_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    variables = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other", "pucca_road_km", "kutcha_road_km"]
    data = [
        ("1", "Jalalabad", "PR (2.2) KR (4)", "PT/OSD", "25", "1,860", E, "B", "HP", E, E, "310", "37", "52", "61", E, "2.2", "4.0", "ORDINARY", ""),
        ("2", "Powayan", "PR (3.5) KR (2.7)", "PT/OSD", "18", "1,138", E, "B", "HP", E, E, "398", "22", "47", "55", E, "3.5", "2.7", "ORDINARY", ""),
        ("3", "Rly. Settlement Roza", "PR (3) KR (6)", "PT/OSD", "10", "800", E, "B", "TW/OHT", "288,000 Galls.", E, "740", "3", "15", "270", E, "3.0", "6.0", "ORDINARY", ""),
        ("4", "Shahjahanpur Cantt.", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Shahjahanpur City Urban Agglomeration"),
        ("", "Shahjahanpur City Urban Agglomeration", "PR (146.2) KR (24.0)", "PT/OSD", "630", "19,175", E, "B/HC", "TW/OHT", "280,000 Galls.", "Yes", "5,384", "260", "1,530", "2,018", E, "146.2", "24.0", "AGGREGATE", ""),
        ("(i)", "Shahjahanpur Cantt.", "PR (17.7) KR (0)", "PT/OSD", "40", "1,500", E, "B", "TW/OHT", "80,000 Galls.", "Yes", "74", "9", "23", "151", E, "17.7", "0.0", "COMPONENT", ""),
        ("(ii)", "Shahjahanpur", "PR (128.5) KR (24.0)", "PT/OSD", "590", "17,675", E, "B/HC", "TW/OHT", "200,000 Galls.", "Yes", "5,310", "251", "1,507", "1,867", E, "128.5", "24.0", "COMPONENT", ""),
        ("5", "Shahjahanpur", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Shahjahanpur City Urban Agglomeration"),
        ("6", "Tilhar", "PR (29.6) KR (8.7)", "PT/OSD", "35", "3,843", E, "B", "HP", E, E, "540", "74", "123", "206", E, "29.6", "8.7", "ORDINARY", ""),
    ]
    rows = []
    for i, spec in enumerate(data):
        if len(spec) == 19: spec = spec[:-2] + ("",) + spec[-2:]
        row = deepcopy(template); row.update(dict(zip(variables + ["row_type", "reference_target"], spec))); row.update({"row_index": str(i), "pdf_id": pdf_id, "district": DIST}); clear_flags(row, variables); rows.append(row)
    finish(pdf_id, rows, fields, "# Shahjahanpur Civic source-checked output\n\nThe Civic rows, Shahjahanpur City Urban Agglomeration aggregate/components, cross-reference rows, and Amenities continuation were transcribed from pages 6–7 at 300 DPI. Municipal Finance, Expenditure, and Trade sections were excluded.\n")


def mededu():
    pdf_id = "shahjahanpur_mededu_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    variables = ["sl_no", "town_name", "hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]
    def parent(serial, town, typ, ref, children, inherited, pidx):
        out = []
        for j, (child, bed) in enumerate(children):
            row = deepcopy(template); row.update({"sl_no": serial, "town_name": town, "row_type": typ, "reference_target": ref, "parent_row_index": str(pidx), "subrow_index": str(j), "subrow_count": str(len(children)), "row_index": "", "pdf_id": pdf_id, "district": DIST})
            for variable in variables: row[variable] = inherited.get(variable, "" if typ == "CROSS_REFERENCE" else E)
            row.update({"sl_no": serial, "town_name": town, "hospitals_dispensaries": child, "med_beds": bed}); clear_flags(row, variables); out.append(row)
        return out
    rows = []
    rows += parent("1", "Jalalabad", "ORDINARY", "", [("H (1)", "8"), ("FC (1)", E)], {"higher_secondary_schools": "3", "middle_schools": "2", "primary_schools": "4"}, 0)
    rows += parent("2", "Powayan", "ORDINARY", "", [("H (1)", "8"), ("FC (1)", E)], {"higher_secondary_schools": "3", "middle_schools": "2", "primary_schools": "4", "libraries": "RR (1)"}, 1)
    rows += parent("3", "Rly. Settlement Roza", "ORDINARY", "", [("H (1)", "8"), ("D (1)", E), ("FC (1)", E)], {"higher_secondary_schools": "2", "middle_schools": "2", "primary_schools": "5", "other_edu_institutions": "1", "cinemas": "1", "libraries": "PL (1)"}, 2)
    rows += parent("4", "Shahjahanpur Cantt.", "CROSS_REFERENCE", "Shahjahanpur City Urban Agglomeration", [("See", "")], {}, 3)
    rows += parent("", "Shahjahanpur City Urban Agglomeration", "AGGREGATE", "", [("H (8)", "269"), ("FC (3)", E), ("D (2)", E), ("TBC (1)", "1"), ("O (1)", "1")], {"degree_colleges": "A (1) AS (1)", "vocational_institutes": "Type (3) O (3)", "higher_secondary_schools": "16", "middle_schools": "13", "primary_schools": "60", "other_edu_institutions": "6", "cinemas": "3", "libraries": "PL (1)"}, 4)
    rows += parent("(i)", "Shahjahanpur Cantt.", "COMPONENT", "", [("H (3)", "86"), ("FC (1)", E)], {"higher_secondary_schools": "1", "primary_schools": "1"}, 5)
    rows += parent("(ii)", "Shahjahanpur", "COMPONENT", "", [("H (5)", "173"), ("D (2)", E), ("TBC (1)", E), ("FC (2)", "1"), ("O (1)", E)], {"degree_colleges": "A (1) AS (1)", "vocational_institutes": "Type (3) O (3)", "higher_secondary_schools": "15", "middle_schools": "13", "primary_schools": "59", "other_edu_institutions": "6", "cinemas": "3", "libraries": "PL (1)"}, 6)
    rows += parent("5", "Shahjahanpur", "CROSS_REFERENCE", "Shahjahanpur City Urban Agglomeration", [("See", "")], {}, 7)
    rows += parent("6", "Tilhar", "ORDINARY", "", [("H (2)", "34"), ("FC (1)", E)], {"higher_secondary_schools": "4", "middle_schools": "1", "primary_schools": "16", "other_edu_institutions": "8", "cinemas": "1"}, 8)
    for i, row in enumerate(rows): row["row_index"] = str(i)
    finish(pdf_id, rows, fields, "# Shahjahanpur MedEdu source-checked output\n\nThe eight logical parents, City Urban Agglomeration aggregate/components, cross-reference rows, and 23 printed medical child rows were transcribed from pages 8–9 at 300 DPI. Columns 3–4 are child-scoped and columns 5–17 are inherited within each parent; Trade and Banking sections were excluded.\n")


def tehsil():
    pdf_id = "shahjahanpur_tehsil_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    comm = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    all_variables = edu + med + water + comm
    names = ["Powayan", "Tilhar", "Shahjahanpur", "Jalalabad", "District Total (Rural)"]
    educational = [["219", "221", "19", "21", "2", "2", E, E, E, E], ["210", "225", "21", "28", "7", "12", E, E, E, E], ["194", "193", "14", "15", "1", "1", E, E, E, E], ["170", "184", "17", "18", "1", "2", E, E, E, E], ["793", "823", "71", "82", "11", "17", E, E, E, E]]
    medical = [["10", "10", "4", "4", "10", "10", E, E, "3", "3", E, E], ["3", "3", "1", "1", "1", "1", E, E, "2", "2", E, E], ["2", "2", "2", "2", "6", "7", "1", "1", "2", "2", E, E], ["1", "1", "4", "4", E, E, E, E, "2", "2", E, E], ["16", "16", "11", "11", "17", "18", "1", "1", "9", "9", E, E]]
    water_values = [["245", "565", "1", "582", "599", "8", "1", E, E, E, E, "7", E, E], ["31", "598", E, "291", "558", "13", "2", E, "18", E, E, "8", E, E], ["43", "497", E, "177", "428", "2", "1", E, "14", E, E, "10", E, E], ["38", "409", "3", "159", "348", "9", "2", E, "4", E, E, "10", "4", E], ["357", "2,069", "4", "1,209", "1,933", "32", "6", E, "36", E, E, "35", "4", E]]
    communications = [["115", "200", "4", "136", "26", "26", E, E, "2", "2", "1", "1"], ["23", "1", "15", "228", "34", "34", E, E, "2", "2", "1", "1"], ["86", "214", "19", "107", "29", "29", E, E, "2", "2", E, E], ["44", "207", "15", "24", "30", "30", E, E, E, E, E, E], ["268", "622", "53", "495", "119", "119", E, E, "6", "6", "2", "2"]]
    rows = []
    for i, name in enumerate(names):
        row = deepcopy(template); row.update({"sl_no": str(i + 1) if i < 4 else "", "tahsil_name": name, "row_type": "TOTAL" if i == 4 else "ORDINARY", "reference_target": "", "row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        row.update(dict(zip(edu, educational[i]))); row.update(dict(zip(med, medical[i]))); row.update(dict(zip(water, water_values[i]))); row.update(dict(zip(comm, communications[i])))
        clear_flags(row, ["sl_no", "tahsil_name"] + all_variables); rows.append(row)
    finish(pdf_id, rows, fields, "# Shahjahanpur Tahsil source-checked output\n\nThe four tahsil rows and District Total (Rural) were transcribed from the educational, medical, drinking-water, and communications panels on pages 242–243 at 300 DPI. Printed placeholders and totals are preserved.\n")


if __name__ == "__main__":
    civic(); mededu(); tehsil()
