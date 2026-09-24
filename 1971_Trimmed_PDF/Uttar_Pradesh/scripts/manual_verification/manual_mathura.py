import csv, os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Mathura"
e = "..."


def load(pdf_id):
    src = os.path.join(ROOT, f"up1971-{pdf_id}-regex-cleaned-v1", "csv", f"{pdf_id}.csv")
    with open(src, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows, list(rows[0])


def clear(row, variables):
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
                    writer.writerow([i, variable, before.get(variable, ""), row.get(variable, ""), "300-DPI source inspection; structural/OCR cleanup"])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f: f.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "mathura_civic_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    variables = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other", "pucca_road_km", "kutcha_road_km"]
    data = [
        ("1", "Baldeo", "PR (3) KR (1)", "PT/OSD", "20", "250", e, "HC", "HP/W", e, e, "175", "6", "125", "65", e, "3.0", "1.0", "ORDINARY", ""),
        ("2", "Govardhan", "PR (4) KR (15)", "PT/OSD", "33", "2,000", e, "HL/HC", "TW/OHT", "100,000 Gallons", e, "703", "33", "293", "96", "13", "4.0", "15.0", "ORDINARY", ""),
        ("3", "Kosi Kalan", "PR (6)", "PT/OSD", "30", "2,000", e, "MT", "TW/OHT", "180,000 Gallons", e, "482", "44", "590", "225", "10", "6.0", "", "ORDINARY", ""),
        ("4", "Mathura", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Mathura City Urban Agglomeration"),
        ("5", "Mathura Cantt.", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Mathura City Urban Agglomeration"),
        ("", "Mathura City Urban Agglomeration", "PR (71.8) KR (17.8)", "S/OSD/BD", "250", "3,500", e, "MT", "TW/OHT", "750,000 Gallons", "Yes", "12,479", "328", "302", "2,361", e, "71.8", "17.8", "AGGREGATE", ""),
        ("(i)", "Mathura", "PR (62.3) KR (6.3)", "S/OSD/BD", "250", "3,000", e, "MT", "TW/OHT", "700,000 Gallons", "Yes", "12,409", "324", "300", "2,016", e, "62.3", "6.3", "COMPONENT", ""),
        ("(ii)", "Mathura Cantt.", "PR (9.5) KR (0)", "OSD", e, "500", e, "MT", "TW/OHT", "50,000 Gallons", e, "70", "4", "2", "345", e, "9.5", "0.0", "COMPONENT", ""),
        ("6", "Sadabad", "PR (2.5) KR (5)", "OSD", e, "150", e, "HC", "TW/OHT", "25,000 Gallons", e, "281", e, "156", "81", e, "2.5", "5.0", "ORDINARY", ""),
        ("7", "Vrindaban", "PR (15)", "S/OSD", "231", "2,154", e, "MT", "TW/OHT", "262,500 Gallons", e, "3,267", "278", "545", "3", e, "15.0", "", "ORDINARY", ""),
    ]
    rows = []
    for i, spec in enumerate(data):
        row = deepcopy(template); row.update(dict(zip(variables + ["row_type", "reference_target"], spec))); row.update({"row_index": str(i), "pdf_id": pdf_id, "district": DIST}); clear(row, variables); rows.append(row)
    finish(pdf_id, rows, fields, "# Mathura Civic source-checked output\n\nSource pages 6–7 were inspected at 300 DPI. The Civic table is separated from Municipal Finance and expenditure sections; cross-references, aggregate/components, and continuation values retain their printed alignment.\n")


def mededu():
    pdf_id = "mathura_mededu_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    variables = ["sl_no", "town_name", "hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]
    def parent(serial, town, typ, ref, children, beds, inherited, pidx):
        out = []
        for j, (child, bed) in enumerate(zip(children, beds)):
            row = deepcopy(template); row.update({"sl_no": serial, "town_name": town, "row_type": typ, "reference_target": ref, "parent_row_index": str(pidx), "subrow_index": str(j), "subrow_count": str(len(children)), "row_index": "", "pdf_id": pdf_id, "district": DIST}); clear(row, variables)
            for variable in variables: row[variable] = inherited.get(variable, "")
            row["sl_no"], row["town_name"], row["hospitals_dispensaries"], row["med_beds"] = serial, town, child, bed; out.append(row)
        return out
    rows = []
    rows += parent("1", "Baldeo", "ORDINARY", "", ["HC (2)", "FC (1)"], ["4", e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "1", "middle_schools": "8", "primary_schools": "2", "other_edu_institutions": e, "stadia": e, "cinemas": e, "auditoria": e, "libraries": e}, 0)
    rows += parent("2", "Govardhan", "ORDINARY", "", ["H (1)", "HC (1)", "FC (1)"], ["12", e, e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "2", "middle_schools": e, "primary_schools": "4", "other_edu_institutions": e, "stadia": e, "cinemas": e, "auditoria": e, "libraries": e}, 1)
    rows += parent("3", "Kosi Kalan", "ORDINARY", "", ["D (2)"], [e], {"degree_colleges": "A (1)", "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "3", "middle_schools": e, "primary_schools": "16", "other_edu_institutions": "1", "stadia": e, "cinemas": "1", "auditoria": e, "libraries": "PL (2)"}, 2)
    rows += parent("4", "Mathura", "CROSS_REFERENCE", "Mathura City Urban Agglomeration", [""], [""], {}, 3)
    rows += parent("5", "Mathura Cantt.", "CROSS_REFERENCE", "Mathura City Urban Agglomeration", [""], [""], {}, 4)
    agg = {"degree_colleges": "A (2) S (1)", "medical_colleges": e, "engg_colleges": e, "polytechnics": "1", "vocational_institutes": e, "higher_secondary_schools": "18", "middle_schools": "4", "primary_schools": "78", "other_edu_institutions": "1", "stadia": e, "cinemas": "4", "auditoria": "1", "libraries": "PL (7)"}
    rows += parent("", "Mathura City Urban Agglomeration", "AGGREGATE", "", ["H (7)", "D (2)", "TBC (1)", "FC (2)", "*O (4)"], ["300", e, "73", e, "89"], agg, 5)
    comp_i = {"degree_colleges": "A (2) S (1)", "medical_colleges": e, "engg_colleges": e, "polytechnics": "1", "vocational_institutes": e, "higher_secondary_schools": "16", "middle_schools": "4", "primary_schools": "76", "other_edu_institutions": e, "stadia": e, "cinemas": "3", "auditoria": "1", "libraries": "PL (7)"}
    rows += parent("(i)", "Mathura", "COMPONENT", "", ["H (6)", "D (1)", "TBC (1)", "FC (2)", "*O (4)"], ["225", e, "73", e, "89"], comp_i, 6)
    comp_ii = {v: e for v in variables[4:]}
    comp_ii.update({"higher_secondary_schools": "2", "primary_schools": "2", "other_edu_institutions": "1", "cinemas": "1"})
    rows += parent("(ii)", "Mathura Cantt.", "COMPONENT", "", ["H (1)", "D (1)"], ["75", e], comp_ii, 7)
    sad = {v: e for v in variables[4:]}; sad.update({"higher_secondary_schools": "1", "middle_schools": "3", "primary_schools": "4", "libraries": "PL (1)"})
    rows += parent("6", "Sadabad", "ORDINARY", "", ["HC (1)", "FC (1)"], ["4", e], sad, 8)
    vr = {v: e for v in variables[4:]}; vr.update({"degree_colleges": "A (1)", "higher_secondary_schools": "5", "middle_schools": "3", "primary_schools": "15", "other_edu_institutions": "4", "libraries": "PL (5)"})
    rows += parent("7", "Vrindaban", "ORDINARY", "", ["H (2)", "FC (1)", "**O (3)"], ["36", e, "661"], vr, 9)
    for i, row in enumerate(rows): row["row_index"] = str(i)
    finish(pdf_id, rows, fields, "# Mathura MedEdu source-checked output\n\nSource pages 8–9 were inspected at 300 DPI. Ten logical parents (including two cross-references, the aggregate, and two components) expand to 25 child rows with child-scoped medical values and parent-scoped continuation values.\n")


def tehsil():
    pdf_id = "mathura_tehsil_1971"; old, fields = load(pdf_id); template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    comm = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    allv = edu + med + water + comm
    E = [["135", "152", "10", "10", "4", "4", e, e, e, e], ["171", "215", "21", "21", "6", "6", "2", "2", e, e], ["170", "204", "24", "24", "10", "10", e, e, e, e], ["164", "180", "20", "20", "2", "2", "2", "2", e, e], ["640", "751", "75", "75", "22", "22", "4", "4", e, e]]
    M = [["6", "6", "5", "5", "9", "9", "1", "1", "5", "5", e, e], ["1", "1", "14", "14", "8", "8", "1", "1", "6", "6", e, e], ["16", "17", e, e, "2", "2", "1", "1", "3", "3", e, e], ["8", "8", "20", "20", e, e, e, e, "3", "3", e, e], ["31", "32", "39", "39", "19", "19", "3", "3", "17", "17", e, e]]
    W = [["5", "201", e, "5", "170", "1", "12", e, e, e, e, e, e, e], ["42", "214", e, e, "212", "3", e, e, e, e, e, "3", e, e], ["46", "278", e, "35", "256", e, "3", e, "7", e, e, "44", e, e], ["97", "125", e, "1", "214", e, e, e, e, e, e, "11", e, e], ["190", "818", e, "41", "852", "4", "15", e, "7", e, e, "59", e, e]]
    R = [["35", "32", "5", "11", "33", "33", e, e, "1", "1", "4", "4"], ["55", "43", "19", "29", "35", "35", "3", "3", "5", "5", "7", "7"], ["44", "29", "7", "71", "47", "47", e, e, "1", "1", "1", "1"], ["56", "46", e, "7", "36", "36", e, e, e, e, e, e], ["190", "150", "31", "118", "151", "151", "3", "3", "7", "7", "12", "12"]]
    names = ["Chhata", "Mathura", "Mat", "Sadabad", "District Total"]; rows = []
    for i, name in enumerate(names):
        row = deepcopy(template); row.update({"sl_no": str(i + 1) if i < 4 else "", "tahsil_name": name, "row_type": "TOTAL" if i == 4 else "ORDINARY", "reference_target": "", "row_index": str(i), "pdf_id": pdf_id, "district": DIST}); row.update(dict(zip(edu, E[i]))); row.update(dict(zip(med, M[i]))); row.update(dict(zip(water, W[i]))); row.update(dict(zip(comm, R[i]))); clear(row, ["sl_no", "tahsil_name"] + allv); rows.append(row)
    finish(pdf_id, rows, fields, "# Mathura Tahsil source-checked output\n\nSource pages 114–115 were inspected at 300 DPI. Chhata, Mathura, Mat, Sadabad, and the printed District Total retain aligned educational, medical, water/power, and communication values.\n")


if __name__ == "__main__":
    civic(); mededu(); tehsil()
