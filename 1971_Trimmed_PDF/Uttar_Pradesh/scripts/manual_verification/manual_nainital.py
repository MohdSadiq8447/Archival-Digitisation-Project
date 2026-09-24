import csv
import os
from copy import deepcopy


ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Nainital"
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
                if variable.endswith("_flag") or variable in {
                    "row_index", "parent_row_index", "subrow_index", "subrow_count",
                    "requires_review", "extracted_at",
                }:
                    continue
                if before.get(variable, "") != row.get(variable, ""):
                    writer.writerow([
                        i, variable, before.get(variable, ""), row.get(variable, ""),
                        "300-DPI source inspection; Municipal Finance section excluded",
                    ])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "nainital_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = [
        "sl_no", "town_name", "road_length_km", "sewerage_drainage_system",
        "water_borne_latrines", "service_latrines", "other_latrines",
        "night_soil_disposal_method", "water_source", "water_capacity", "fire_service",
        "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other",
        "pucca_road_km", "kutcha_road_km",
    ]
    ordinary = [
        ("1", "Bhowali", "PR (10) KR (8)", "OSD", E, "423", E, "HC", "F", E, E, "89", "5", "62", "40", E, "10.0", "8.0", "ORDINARY", ""),
        ("2", "Haldwani-cum-Kathgodam", "PR (20.3) KR (1.2)", "OSD", "N.A.", "N.A.", "N.A.", "HC", "TW/OHT", "563,000 Gallons", "Yes", "2,572", "136", "1,378", "1,045", E, "20.3", "1.2", "ORDINARY", ""),
        ("3", "Jaspur", "PR (18) KR (7)", "PT/OSD", "55", "1,625", E, "HC", "HP", E, E, "496", "39", "200", "120", E, "18.0", "7.0", "ORDINARY", ""),
        ("4", "Kashipur", "PR (35.4) KR (3.5)", "OSD", "N.A.", "N.A.", "N.A.", "HC", "TW/OHT", "75,000 Gallons", E, "1,929", "179", "905", "240", E, "35.4", "3.5", "ORDINARY", ""),
        ("7", "Ramnagar", "PR (6.4) KR (5.5)", "PT/OSD", "150", "739", E, "HC", "TW/OHT", "50,000 Gallons", "Yes", "874", "51", "619", "258", E, "6.4", "5.5", "ORDINARY", ""),
        ("8", "Rudrapur", "PR (8) KR (12)", "PT/OSD", "476", "1,035", E, "HC", "TW/OHT", "24,000 Gallons", E, "1,009", "72", "590", "313", E, "8.0", "12.0", "ORDINARY", ""),
        ("9", "Tanakpur", "PR (5.4) KR (1.2)", "PT/OSD", "50", "600", E, "HC", "TW/OHT", "30,000 Gallons", "Yes", "432", "12", "122", "150", E, "5.4", "1.2", "ORDINARY", ""),
    ]
    aggregate = ("", "Naini Tal Urban Agglomeration", "PR (9.2) KR (5.2)", "S/OSD", "N.A.", "N.A.", "N.A.", "HC", "F/L/OHT", "2,636,959 Gallons", "Yes", "4,617", "18", "1,000", "1,209", E, "9.2", "5.2", "AGGREGATE", "")
    component_i = ("(i)", "Naini Tal", "PR (6.7) KR (3.7)", "S/OSD", "12,600", "1,400", E, "HC", "F/L/OHT", "2,611,959 Gallons", "Yes", "4,081", "18", "983", "1,149", E, "6.7", "3.7", "COMPONENT", "")
    component_ii = ("(ii)", "Naini Tal Cantt.", "PR (2.5) KR (1.5)", "OSD", "N.A.", "N.A.", "N.A.", "HC", "F/L/OHT", "25,000 Gallons", E, "536", E, "17", "60", E, "2.5", "1.5", "COMPONENT", "")
    rows = []
    rows.extend(ordinary[:4])
    rows.append(("5", "Naini Tal", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Naini Tal Urban Agglomeration"))
    rows.append(("6", "Naini Tal Cantt.", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Naini Tal Urban Agglomeration"))
    rows.extend([aggregate, component_i, component_ii])
    rows.extend(ordinary[4:])
    output = []
    for i, spec in enumerate(rows):
        row = deepcopy(template)
        row.update(dict(zip(variables + ["row_type", "reference_target"], spec)))
        row.update({"row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        clear_flags(row, variables)
        output.append(row)
    finish(
        pdf_id,
        output,
        fields,
        "# Nainital Civic source-checked output\n\n"
        "The printed Civic rows, Naini Tal Urban Agglomeration aggregate/components, and Amenities continuation panel were transcribed from pages 6–7 at 300 DPI. "
        "Municipal Finance and Expenditure sections were excluded.\n",
    )


def mededu():
    pdf_id = "nainital_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = [
        "sl_no", "town_name", "hospitals_dispensaries", "med_beds", "degree_colleges",
        "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes",
        "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions",
        "stadia", "cinemas", "auditoria", "libraries",
    ]

    def parent(serial, town, typ, reference, children, beds, inherited, pidx):
        out = []
        inherited = inherited or {}
        for j, (child, bed) in enumerate(zip(children, beds)):
            row = deepcopy(template)
            row.update({
                "sl_no": serial, "town_name": town, "row_type": typ,
                "reference_target": reference, "parent_row_index": str(pidx),
                "subrow_index": str(j), "subrow_count": str(len(children)),
                "row_index": "", "pdf_id": pdf_id, "district": DIST,
            })
            clear_flags(row, variables)
            for variable in variables:
                row[variable] = inherited.get(variable, "" if typ == "CROSS_REFERENCE" else E)
            row["sl_no"] = serial
            row["town_name"] = town
            row["hospitals_dispensaries"] = child
            row["med_beds"] = bed
            out.append(row)
        return out

    rows = []
    rows += parent("1", "Bhowali", "ORDINARY", "", ["D(1)", "HC(1)", "O(1)"], ["6", "5", "348"], {
        "higher_secondary_schools": "", "middle_schools": "1", "primary_schools": "3",
    }, 0)
    rows += parent("2", "Haldwani-cum-Kathgodam", "ORDINARY", "", ["H(4)", "D(2)", "TBC(1)", "HC(2)", "*O(1)", "FC(1)"], ["184", "2", E, E, E, E], {
        "degree_colleges": "ASC (1)", "higher_secondary_schools": "5", "middle_schools": "20",
        "primary_schools": "23", "cinemas": "2", "auditoria": "1", "libraries": "PL (3)",
    }, 1)
    rows += parent("3", "Jaspur", "ORDINARY", "", ["H(1)", "D(1)", "*O(1)"], ["4", "4", E], {
        "higher_secondary_schools": "1", "middle_schools": "3", "primary_schools": "4",
        "stadia": E, "cinemas": E, "auditoria": E,
    }, 2)
    rows += parent("4", "Kashipur", "ORDINARY", "", ["H(4)", "D(1)", "*O(2)", "FC(1)"], ["40", E, E, E], {
        "polytechnics": "1", "higher_secondary_schools": "6", "middle_schools": "3",
        "primary_schools": "26", "other_edu_institutions": "2",
    }, 3)
    rows += parent("5", "Naini Tal", "CROSS_REFERENCE", "Naini Tal Urban Agglomeration", [""], [""], {}, 4)
    rows += parent("6", "Naini Tal Cantt.", "CROSS_REFERENCE", "Naini Tal Urban Agglomeration", [""], [""], {}, 5)
    rows += parent("", "Naini Tal Urban Agglomeration", "AGGREGATE", "", ["H(6)", "D(7)", "*O(3)", "FC(1)"], ["216", E, E, E], {
        "degree_colleges": "ASC (1)", "polytechnics": "1", "higher_secondary_schools": "10",
        "middle_schools": "3", "primary_schools": "23", "other_edu_institutions": "4",
        "stadia": "1", "cinemas": "2", "auditoria": "5", "libraries": "PL (3)",
    }, 6)
    rows += parent("(i)", "Naini Tal", "COMPONENT", "", ["H(6)", "D(7)", "*O(3)", "FC(1)"], ["216", E, E, E], {
        "degree_colleges": "ASC (1)", "polytechnics": "1", "higher_secondary_schools": "10",
        "middle_schools": "3", "primary_schools": "22", "other_edu_institutions": "4",
        "stadia": "1", "cinemas": "2", "auditoria": "5", "libraries": "PL (3)",
    }, 7)
    rows += parent("(ii)", "Naini Tal Cantt.", "COMPONENT", "", [E], [E], {
        "higher_secondary_schools": E, "middle_schools": E, "primary_schools": "1",
    }, 8)
    rows += parent("7", "Ramnagar", "ORDINARY", "", ["H(4)"], ["24"], {
        "higher_secondary_schools": "2", "middle_schools": "2", "primary_schools": "6",
        "other_edu_institutions": "13",
    }, 9)
    rows += parent("8", "Rudrapur", "ORDINARY", "", ["H(1)", "HC(2)", "NH(2)", "FC(1)", "O(1)"], ["30", E, E, E, E], {
        "higher_secondary_schools": "7", "middle_schools": "2", "primary_schools": "4",
        "cinemas": "1",
    }, 10)
    rows += parent("9", "Tanakpur", "ORDINARY", "", ["H(2)"], ["16"], {
        "higher_secondary_schools": "1", "primary_schools": "3", "cinemas": "1",
    }, 11)
    for i, row in enumerate(rows):
        row["row_index"] = str(i)
    finish(
        pdf_id,
        rows,
        fields,
        "# Nainital MedEdu source-checked output\n\n"
        "The nine printed town records, two cross-reference rows, Naini Tal Urban Agglomeration aggregate, and its two components were transcribed from the MedEdu table on pages 8–9 at 300 DPI. "
        "The output expands each parent into its printed medical-facility child rows; columns 3–4 are child-scoped and columns 5–17 are inherited only within the correct parent. Footnotes and unrelated sections were excluded.\n",
    )


def tehsil():
    pdf_id = "nainital_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = [
        "junior_basic_villages", "junior_basic_schools", "senior_basic_villages",
        "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools",
        "college_villages", "colleges", "other_edu_villages", "other_edu_institutions",
    ]
    med = [
        "hospital_villages", "hospitals", "dispensary_villages", "dispensaries",
        "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres",
        "family_planning_villages", "family_planning_centres", "other_med_villages",
        "other_med_institutions",
    ]
    water = [
        "power_available_villages", "power_not_available_villages", "tap_water_villages",
        "hand_pipe_villages", "well_villages", "tank_villages", "river_villages",
        "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages",
        "tube_well_villages", "other_water_villages", "no_water_villages",
    ]
    comm = [
        "pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages",
        "other_road_villages", "post_office_villages", "post_offices",
        "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages",
        "post_telegraph_offices", "telephone_villages", "telephones",
    ]
    all_variables = edu + med + water + comm
    names = ["Nainital", "Haldwani", "Kashipur", "Kichha", "Khatima", "District Total"]
    educational = [
        ["273", "288", "29", "28", "14", "15", E, E, E, E],
        ["63", "70", "10", "10", "3", "3", "-", E, E, E],
        ["92", "102", "19", "19", "1", "1", E, E, E, E],
        ["107", "119", "15", "16", "6", "6", "1", "1", E, E],
        ["70", "70", "6", "8", "1", "1", E, E, E, E],
        ["605", "469", "79", "81", "25", "26", "1", "1", E, E],
    ]
    medical = [
        ["6", "6", "13", "13", "10", "10", "1", "1", "5", "5", E, E],
        ["5", "5", "4", "4", "3", "3", E, E, "1", "1", E, E],
        ["4", "4", "1", "1", "2", "2", E, E, E, E, E, E],
        ["10", "10", "4", "4", "9", "9", "3", "3", "5", "5", E, E],
        ["7", "7", E, E, "2", "2", E, E, "2", "2", E, E],
        ["32", "32", "22", "22", "26", "26", "4", "4", "13", "13", E, "-"],
    ]
    water_values = [
        ["70", "558", "257", E, E, "1", "40", "367", "7", E, E, E, E, "-"],
        ["7", "364", E, E, E, E, "198", "2", "189", E, E, "8", E, "-"],
        ["73", "234", "15", "233", "122", "1", "15", E, "96", E, E, "15", E, E],
        ["118", "171", E, "223", "77", E, "11", E, E, E, E, "74", E, E],
        ["35", "209", E, "219", "114", E, "14", E, "1", E, E, E, E, E],
        ["253", "1,535", "272", "675", "313", "2", "278", "369", "293", E, E, "97", E, "-"],
    ]
    communications = [
        ["89", "463", "68", "425", "23", "6", "45", E, "6", "6", "7", "7"],
        ["88", "296", "70", "278", "15", "3", "18", E, "2", "2", "2", "2"],
        ["108", "219", "46", "154", "41", "35", "14", E, "2", "2", "5", "5"],
        ["153", "195", "67", "91", "37", "76", "14", E, "7", "7", "12", "12"],
        ["75", "195", "34", "154", "25", "19", "11", E, "3", "3", "1", "1"],
        ["513", "1,368", "285", "1,102", "141", "139", "102", E, "20", "20", "27", "27"],
    ]
    rows = []
    for i, name in enumerate(names):
        row = deepcopy(template)
        row.update({
            "sl_no": str(i + 1) if i < 5 else "",
            "tahsil_name": name,
            "row_type": "TOTAL" if i == 5 else "ORDINARY",
            "reference_target": "", "row_index": str(i), "pdf_id": pdf_id,
            "district": DIST,
        })
        row.update(dict(zip(edu, educational[i])))
        row.update(dict(zip(med, medical[i])))
        row.update(dict(zip(water, water_values[i])))
        row.update(dict(zip(comm, communications[i])))
        clear_flags(row, ["sl_no", "tahsil_name"] + all_variables)
        rows.append(row)
    finish(
        pdf_id,
        rows,
        fields,
        "# Nainital Tahsil source-checked output\n\n"
        "The five printed tahsil rows and District Total were transcribed from the educational, medical, water, and communications panels on pages 194–195 at 300 DPI. Printed placeholders and the historical total values are preserved.\n",
    )


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
