import csv
import os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Sitapur"
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
                if variable.endswith("_flag") or variable in {"row_index", "parent_row_index", "subrow_index", "subrow_count", "requires_review", "extracted_at"}: continue
                if before.get(variable, "") != row.get(variable, ""):
                    writer.writerow([i, variable, before.get(variable, ""), row.get(variable, ""), "300-DPI source inspection; unrelated statement sections excluded"])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f: csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f: f.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "sitapur_civic_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    variables = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other", "pucca_road_km", "kutcha_road_km"]
    data = [
        ("1", "Biswan", "PR (26) KR (11)", "OSD/ST", "43", "2,398", E, "B", "TW/OHT", "40,000 Galls.", E, "681", "48", "160", "222", E, "26.0", "11.0", "ORDINARY", ""),
        ("2", "Khairabad", "PR (26.1) KR (39.8)", "OSD/ST", "110", "3,000", E, "B", "HP", E, E, "208", "27", "85", "150", E, "26.1", "39.8", "ORDINARY", ""),
        ("3", "Laharpur", "PR (8.7) KR (4.1)", "OSD/ST", "131", "1,440", E, "B", "HP", E, E, "450", "15", "260", "117", E, "8.7", "4.1", "ORDINARY", ""),
        ("4", "Mahmudabad", "PR (2) KR (14)", "OSD/ST", "49", "1,253", E, "B", "HP", E, E, "325", "22", "81", "160", E, "2.0", "14.0", "ORDINARY", ""),
        ("5", "Neemsar Misrikh", "PR (3.6) KR (7.7)", "OSD/ST", "48", "507", E, "B", "HP", E, E, "323", "37", "82", "159", E, "3.6", "7.7", "ORDINARY", ""),
        ("6", "Sitapur", "PR (47) KR (15)", "OSD/ST", "455", "7,129", E, "B/HC", "TW/OHT/HP", "155,000 Galls.", E, "5,981", "279", "230", "850", E, "47.0", "15.0", "ORDINARY", ""),
    ]
    rows = []
    for i, spec in enumerate(data):
        row = deepcopy(template); row.update(dict(zip(variables + ["row_type", "reference_target"], spec))); row.update({"row_index": str(i), "pdf_id": pdf_id, "district": DIST}); clear_flags(row, variables); rows.append(row)
    finish(pdf_id, rows, fields, "# Sita Pur Civic source-checked output\n\nThe six Civic rows and Amenities continuation were transcribed from pages 6–7 at 300 DPI. Municipal Finance and Expenditure sections were excluded.\n")


def mededu():
    pdf_id = "sitapur_mededu_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    variables = ["sl_no", "town_name", "hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]
    def parent(serial, town, children, inherited, pidx):
        out = []
        for j, (child, bed) in enumerate(children):
            row = deepcopy(template); row.update({"sl_no": serial, "town_name": town, "row_type": "ORDINARY", "reference_target": "", "parent_row_index": str(pidx), "subrow_index": str(j), "subrow_count": str(len(children)), "row_index": "", "pdf_id": pdf_id, "district": DIST})
            for variable in variables: row[variable] = inherited.get(variable, E)
            row.update({"sl_no": serial, "town_name": town, "hospitals_dispensaries": child, "med_beds": bed}); clear_flags(row, variables); out.append(row)
        return out
    rows = []
    rows += parent("1", "Biswan", [("H (2)", "24"), ("FC (1)", E)], {"higher_secondary_schools": "4", "middle_schools": "2", "primary_schools": "15", "libraries": "PL (1)"}, 0)
    rows += parent("2", "Khairabad", [("H (2)", "124"), ("FC (1)", E), ("*O (1)", E)], {"higher_secondary_schools": "2", "middle_schools": "3", "primary_schools": "14", "libraries": "PL (1)"}, 1)
    rows += parent("3", "Laharpur", [("H (1)", "16"), ("D (5)", E), ("NH (1)", E), ("FC (1)", E)], {"higher_secondary_schools": "1", "middle_schools": "2", "primary_schools": "7"}, 2)
    rows += parent("4", "Mahmudabad", [("D (1)", "4"), ("H (2)", "24"), ("FC (1)", E)], {"higher_secondary_schools": "2", "middle_schools": "3", "primary_schools": "7"}, 3)
    rows += parent("5", "Neemsar Misrikh", [("D (1)", "4")], {"higher_secondary_schools": "1", "middle_schools": "6", "primary_schools": "6"}, 4)
    rows += parent("6", "Sitapur", [("H (8)", "886"), ("D (2)", E), ("TBC (1)", "6"), ("FC (4)", E)], {"degree_colleges": "A (2)", "vocational_institutes": "Sh. Type (1)", "higher_secondary_schools": "7", "middle_schools": "10", "primary_schools": "46", "cinemas": "2", "auditoria": "1", "libraries": "PL (3) RR (3)"}, 5)
    for i, row in enumerate(rows): row["row_index"] = str(i)
    finish(pdf_id, rows, fields, "# Sita Pur MedEdu source-checked output\n\nThe six printed town parents and 17 medical-facility child rows were transcribed from pages 8–9 at 300 DPI. Columns 3–4 are child-scoped and columns 5–17 are inherited within each parent; the footnote for *O and Trade/Banking panels were excluded.\n")


def tehsil():
    pdf_id = "sitapur_tehsil_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    comm = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    all_variables = edu + med + water + comm
    names = ["Misrikh", "Sitapur", "Biswan", "Sidhauli", "District Total (Rural)"]
    educational = [["238", "260", "35", "39", "5", "5", E, E, E, E], ["239", "270", "35", "39", "3", "3", E, E, E, E], ["209", "229", "21", "23", E, E, E, E, "2", "2"], ["222", "237", "27", "28", "4", "4", E, E, E, E], ["908", "996", "118", "129", "12", "12", E, E, "2", "2"]]
    medical = [["3", "3", "42", "46", "5", "5", "2", "2", "2", "2", E, E], ["9", "9", "57", "61", "5", "5", "2", "2", "3", "3", E, E], ["9", "10", "33", "38", "4", "4", "1", "1", E, E, E, E], ["7", "7", "14", "14", "2", "2", "3", "3", "1", "1", E, E], ["28", "29", "146", "159", "16", "16", "8", "8", "6", "6", "1", "1"]]
    water_values = [["162", "495", E, E, "563", E, E, E, E, E, E, E, "82", "173"], ["178", "408", E, "218", "577", "6", "1", E, "1", E, E, E, "212", "219"], ["69", "444", "4", "252", "504", E, E, E, E, E, E, "2", "79", "207"], ["71", "534", E, "440", "599", E, E, E, E, E, E, "3", "64", "196"], ["480", "1,881", "4", "910", "2,243", "6", "1", E, "1", E, E, "5", "437", "795"]]
    communications = [["53", "53", "1", "1", "2", "2", E, E, E, E, E, E], ["62", "62", E, E, "4", "4", E, E, E, E, E, E], ["65", "65", E, E, E, E, E, E, E, E, E, E], ["61", "6", E, E, "3", "3", "1", "1", E, E, E, E], ["241", "241", "1", "1", "9", "9", "1", "1", E, E, E, E]]
    rows = []
    for i, name in enumerate(names):
        row = deepcopy(template); row.update({"sl_no": str(i + 1) if i < 4 else "", "tahsil_name": name, "row_type": "TOTAL" if i == 4 else "ORDINARY", "reference_target": "", "row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        row.update(dict(zip(edu, educational[i]))); row.update(dict(zip(med, medical[i]))); row.update(dict(zip(water, water_values[i]))); row.update(dict(zip(comm, communications[i])))
        clear_flags(row, ["sl_no", "tahsil_name"] + all_variables); rows.append(row)
    finish(pdf_id, rows, fields, "# Sita Pur Tahsil source-checked output\n\nThe four tahsil rows and District Total (Rural) were transcribed from the educational, medical, drinking-water, and communications panels on pages 240–241 at 300 DPI. Printed placeholders and totals are preserved.\n")


if __name__ == "__main__":
    civic(); mededu(); tehsil()
