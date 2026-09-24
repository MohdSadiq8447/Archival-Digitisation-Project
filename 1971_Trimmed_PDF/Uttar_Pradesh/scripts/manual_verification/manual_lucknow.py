import csv, os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Lucknow"


def load(pdf_id):
    src = os.path.join(ROOT, f"up1971-{pdf_id}-regex-cleaned-v1", "csv", f"{pdf_id}.csv")
    with open(src, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows, list(rows[0])


def clear(row, variables):
    for variable in variables:
        flag = f"{variable}_flag"
        if flag in row:
            row[flag] = ""
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
                if variable.endswith("_flag") or variable in {
                    "row_index", "parent_row_index", "subrow_index", "subrow_count",
                    "requires_review", "extracted_at",
                }:
                    continue
                if before.get(variable, "") != row.get(variable, ""):
                    writer.writerow([i, variable, before.get(variable, ""), row.get(variable, ""),
                                     "300-DPI source inspection; structural/OCR cleanup"])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "lucknow_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = [
        "sl_no", "town_name", "road_length_km", "sewerage_drainage_system",
        "water_borne_latrines", "service_latrines", "other_latrines",
        "night_soil_disposal_method", "water_source", "water_capacity", "fire_service",
        "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other",
        "pucca_road_km", "kutcha_road_km",
    ]
    rowspec = [
        ("1", "Charbagh-Alambagh", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Lucknow City Urban Agglomeration"),
        ("2", "Lucknow", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Lucknow City Urban Agglomeration"),
        ("3", "Lucknow Cantt.", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Lucknow City Urban Agglomeration"),
        ("", "Lucknow City Urban Agglomeration", "PR (366) KR (20)", "S/ST/OSD/BSD", "20,301", "49,910", "57", "MT/B", "TW/OHT", "43,444,000 Galls.", "Yes", "34,339", "2,124", "15,447", "15,800", "...", "366.0", "20.0", "AGGREGATE", ""),
        ("(i)", "Charbagh-Alambagh", "PR (51) KR (0)", "OSD/ST", "296", "303", "...", "MT/B", "TW/OHT", "244,000 Galls.", "Yes", "N.A.", "N.A.", "N.A.", "N.A.", "...", "51.0", "0.0", "COMPONENT", ""),
        ("(ii)", "Lucknow", "PR (26) KR (20)", "S/OSD/BSD", "20,000", "60,000", "97", "MT/B", "TW/OHT", "43,000,000 Galls.", "Yes", "34,339*", "2,124*", "15,447*", "15,800*", "...", "26.0", "20.0", "COMPONENT", ""),
        ("(iii)", "Lucknow Cantt.", "PR (51) KR (0)", "OSD", "5", "607", "...", "MT/B", "TW/OHT", "200,000 Gall.", "...", "N.A.", "N.A.", "N.A.", "N.A.", "...", "51.0", "0.0", "COMPONENT", ""),
        ("4", "Malihabad", "PR (3) KR (0)", "OSD", "...", "1,217", "...", "B", "HP", "...", "...", "50", "14", "35", "40", "...", "3.0", "0.0", "ORDINARY", ""),
    ]
    rows = []
    for i, spec in enumerate(rowspec):
        row = deepcopy(template)
        values = dict(zip(variables + ["row_type", "reference_target"], spec))
        row.update(values)
        row.update({"row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        clear(row, variables)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Lucknow Civic source-checked output\n\nSource pages 6–7 were inspected at 300 DPI. The Civic table is isolated from the Municipal Finance table; the three printed cross-references, aggregate, components, and Malihabad row retain their source values and continuation alignment.\n")


def mededu():
    pdf_id = "lucknow_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = [
        "sl_no", "town_name", "hospitals_dispensaries", "med_beds", "degree_colleges",
        "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes",
        "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions",
        "stadia", "cinemas", "auditoria", "libraries",
    ]
    e = "..."

    def parent(serial, town, row_type, reference, children, beds, inherited, parent_index):
        result = []
        for sub_index, (child, bed) in enumerate(zip(children, beds)):
            row = deepcopy(template)
            row.update({
                "sl_no": serial, "town_name": town, "row_type": row_type,
                "reference_target": reference, "parent_row_index": str(parent_index),
                "subrow_index": str(sub_index), "subrow_count": str(len(children)),
                "row_index": "", "pdf_id": pdf_id, "district": DIST,
            })
            clear(row, variables)
            for variable in variables:
                row[variable] = inherited.get(variable, "")
            row["sl_no"] = serial
            row["town_name"] = town
            row["hospitals_dispensaries"] = child
            row["med_beds"] = bed
            result.append(row)
        return result

    rows = []
    rows += parent("1", "Charbagh-Alambagh", "CROSS_REFERENCE", "Lucknow City Urban Agglomeration", [""], [""], {}, 0)
    rows += parent("2", "Lucknow", "CROSS_REFERENCE", "Lucknow City Urban Agglomeration", [""], [""], {}, 1)
    rows += parent("3", "Lucknow Cantt.", "CROSS_REFERENCE", "Lucknow City Urban Agglomeration", [""], [""], {}, 2)
    aggregate = {
        "degree_colleges": "A (7) AS (6) ASC (2)", "medical_colleges": "5**", "engg_colleges": e,
        "polytechnics": "4", "vocational_institutes": "Sh. Type (14) O (11)",
        "higher_secondary_schools": "123", "middle_schools": "57", "primary_schools": "471",
        "other_edu_institutions": "24", "stadia": "2", "cinemas": "18", "auditoria": "7",
        "libraries": "PL (10) RR (23)",
    }
    rows += parent("", "Lucknow City Urban Agglomeration", "AGGREGATE", "", ["H (18)", "D (21)", "TBC (1)", "FC (16)", "*O (1)"], ["2,272", "38", "9", e, "35"], aggregate, 3)
    component_i = {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": "1", "vocational_institutes": e, "higher_secondary_schools": e, "middle_schools": "2", "primary_schools": "3", "other_edu_institutions": e, "stadia": "1", "cinemas": e, "auditoria": "1", "libraries": "PL (1) RR (3)"}
    rows += parent("(i)", "Charbagh-Alambagh", "COMPONENT", "", ["H (1)", "D (4)", "FC (1)"], ["72", "9", e], component_i, 4)
    component_ii = {"degree_colleges": "A (7) AS (6) ASC (2)", "medical_colleges": "5**", "engg_colleges": e, "polytechnics": "3", "vocational_institutes": "Sh. Type (14) O (11)", "higher_secondary_schools": "121", "middle_schools": "55", "primary_schools": "460", "other_edu_institutions": "24", "stadia": "1", "cinemas": "18", "auditoria": "6", "libraries": "PL (7) RR (20)"}
    rows += parent("(ii)", "Lucknow", "COMPONENT", "", ["H (15)", "D (16)", "TBC (1)", "FC (15)", "*O (1)"], ["2,156", "29", "9", e, "35"], component_ii, 5)
    component_iii = {v: e for v in ["degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria"]}
    component_iii.update({"primary_schools": "8", "libraries": "PL (2)"})
    rows += parent("(iii)", "Lucknow Cantt.", "COMPONENT", "", ["H (2)", "D (1)"], ["44", e], component_iii, 6)
    malihabad = {v: e for v in ["degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria"]}
    malihabad.update({"middle_schools": "2", "primary_schools": "7", "libraries": "PL (2)"})
    rows += parent("4", "Malihabad", "ORDINARY", "", ["D (2)", "HC (1)", "FC (1)", "*O (1)"], ["8", e, e, e], malihabad, 7)
    for i, row in enumerate(rows):
        row["row_index"] = str(i)
    finish(pdf_id, rows, fields, "# Lucknow MedEdu source-checked output\n\nSource pages 8–9 were inspected at 300 DPI. Eight logical parents (three cross-references, aggregate, three components, and Malihabad) expand to 22 child rows. Columns 3–4 remain child-scoped; columns 5–17 are inherited at parent scope and propagated only within each parent.\n")


def tehsil():
    pdf_id = "lucknow_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    comm = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    all_variables = edu + med + water + comm
    E = [
        ["191", "201", "10", "11", "8", "10", e, e, e, e],
        ["175", "183", "19", "20", "7", "7", e, e, "2", "2"],
        ["135", "153", "12", "13", "4", "4", e, e, e, e],
        ["501", "537", "41", "44", "19", "21", e, e, "2", "2"],
    ]
    M = [
        ["11", "12", "2", "2", "2", "2", "2", "2", "2", "2", e, e],
        ["6", "6", "6", "6", "4", "4", "4", "4", "4", "4", e, e],
        ["10", "10", "4", "4", "7", "7", "4", "4", "5", "5", e, e],
        ["27", "28", "12", "12", "13", "13", "10", "10", "11", "11", e, e],
    ]
    W = [
        ["85", "296", e, "8", "376", "6", "3", e, e, e, e, "3", e, e],
        ["108", "200", e, "2", "302", "22", "4", e, "14", e, e, "1", e, e],
        ["41", "190", e, "3", "227", "7", e, e, e, e, e, e, e, e],
        ["234", "686", e, "13", "905", "35", "7", e, "14", e, e, "4", e, e],
    ]
    R = [
        ["115", "73", e, e, "24", "24", e, e, "5", e, e, e],
        ["110", "107", e, e, "31", "31", "1", "1", "3", "3", e, e],
        ["76", "73", e, e, "23", "23", e, e, "4", e, e, e],
        ["301", "253", e, e, "78", "78", "1", "1", e, e, "1", e],
    ]
    names = ["Malihabad", "Lucknow", "Mohanlalganj", "District Total"]
    rows = []
    for i, name in enumerate(names):
        row = deepcopy(template)
        row.update({"sl_no": str(i + 1) if i < 3 else "", "tahsil_name": name, "row_type": "TOTAL" if i == 3 else "ORDINARY", "reference_target": "", "row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        values = dict(zip(edu, E[i])) | dict(zip(med, M[i])) | dict(zip(water, W[i])) | dict(zip(comm, R[i]))
        row.update(values)
        clear(row, ["sl_no", "tahsil_name"] + all_variables)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Lucknow Tahsil source-checked output\n\nSource pages 106–107 were inspected at 300 DPI. Malihabad, Lucknow, Mohanlalganj, and the printed District Total retain aligned educational, medical, water/power, road, and communications values.\n")


if __name__ == "__main__":
    e = "..."
    civic()
    mededu()
    tehsil()
