import csv
import os
from copy import deepcopy


ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Moradabad"
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
                        "300-DPI source inspection; structural/OCR cleanup",
                    ])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "moradabad_civic_1971"
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
        ("1", "Amroha", "PR (29) KR (5)", "OSD", E, "21,012", "36", "B/HC", "TW/OHT", "675,000 Galls.", E, "3,400", "250", "150", "1,200", E, "29.0", "5.0", "ORDINARY", ""),
        ("2", "Bahjoi", "PR (4) KR (1)", "PT/OSD", "11", "1,742", E, "B/HC", "HP/W", E, E, "700", "3", "64", "155", E, "4.0", "1.0", "ORDINARY", ""),
        ("3", "Bilari", "PR (6) KR (3)", "PT/OSD", "95", "780", E, "B/HC", "HP", E, E, "362", "67", "109", "203", E, "6.0", "3.0", "ORDINARY", ""),
        ("4", "Chandausi", "PR (17) KR (7)", "PT/OSD", "400", "4,500", "15", "B/HC/MT", "TW/OHT", "60,000 Galls.", "Yes", "3,161", "301", "118", "745", E, "17.0", "7.0", "ORDINARY", ""),
        ("5", "Dhanaura", "PR (11) KR (0)", "PT/OSD", "29", "529", E, "B", "HP/W", E, E, "507", "7", "38", "162", E, "11.0", "0.0", "ORDINARY", ""),
        ("6", "Hasanpur", "PR (20) KR (13)", "OSD", E, "2,000", E, "B", "HP/W", E, E, "672", "81", "167", "347", E, "20.0", "13.0", "ORDINARY", ""),
        ("7", "Kanth", "PR (2) KR (1)", "OSD", E, "1,600", E, "B", "HP/W", E, E, "354", "28", "94", "275", E, "2.0", "1.0", "ORDINARY", ""),
        ("10", "Rustamnagar Sahaspur", "PR (1) KR (3)", "PT/OSD", "11", "381", "85", "HC", "HP/W", E, E, "170", "1", "11", "24", E, "1.0", "3.0", "ORDINARY", ""),
        ("11", "Sambhal", "PR (35) KR (4)", "OSD", E, "5,109", E, "B/HC", "HP/W", E, E, "3,158", "287", "118", "1,500", E, "35.0", "4.0", "ORDINARY", ""),
        ("12", "Thakurdwara", "PR (10) KR (0)", "OSD", E, "1,425", E, "B/HC", "HP/W", E, E, "168", "22", "125", "136", E, "10.0", "0.0", "ORDINARY", ""),
    ]
    rows = []
    specs = [
        ("8", "Moradabad", "CROSS_REFERENCE", "Moradabad City Urban Agglomeration"),
        ("", "Moradabad City Urban Agglomeration", "AGGREGATE", ""),
        ("(i)", "Moradabad", "COMPONENT", ""),
        ("(ii)", "Moradabad Rly. Settlement", "COMPONENT", ""),
        ("9", "Moradabad Rly. Settlement", "CROSS_REFERENCE", "Moradabad City Urban Agglomeration"),
    ]
    aggregate = ("", "Moradabad City Urban Agglomeration", "PR (166) KR (5)", "PT/OSD", "5,706", "36,983", E, "B/HC/MT", "TW/OHT", "3,313,270 Galls.", "Yes", "29,498", "3,020", "7,480", "3,400", E, "166.0", "5.0", "AGGREGATE", "")
    component_i = ("(i)", "Moradabad", "PR (153) KR (5)", "PT/OSD", "5,600", "35,413", E, "B/HC/MT", "TW/OHT", "110,000 Galls.", "Yes", "27,352", "3,015", "7,460", "2,687", E, "153.0", "5.0", "COMPONENT", "")
    component_ii = ("(ii)", "Moradabad Rly. Settlement", "PR (13) KR (0)", "PT/OSD", "106", "1,570", E, "B/HC", "TW/OHT", "3,203,270 Galls.", "Yes", "2,146", "5", "20", "713", E, "13.0", "0.0", "COMPONENT", "")
    for spec in ordinary[:7]:
        rows.append(spec)
    rows.append(("8", "Moradabad", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Moradabad City Urban Agglomeration"))
    rows.append(aggregate)
    rows.append(component_i)
    rows.append(component_ii)
    rows.append(("9", "Moradabad Rly. Settlement", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Moradabad City Urban Agglomeration"))
    rows.extend(ordinary[7:])
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
        "# Moradabad Civic source-checked output\n\n"
        "The printed Civic rows and Amenities continuation values were transcribed from pages 10–11 at 300 DPI. "
        "The Moradabad City Urban Agglomeration aggregate, its two components, and both cross-reference rows are retained as separate logical rows.\n",
    )


def mededu():
    pdf_id = "moradabad_mededu_1971"
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
                "sl_no": serial,
                "town_name": town,
                "row_type": typ,
                "reference_target": reference,
                "parent_row_index": str(pidx),
                "subrow_index": str(j),
                "subrow_count": str(len(children)),
                "row_index": "",
                "pdf_id": pdf_id,
                "district": DIST,
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
    rows += parent("1", "Amroha", "ORDINARY", "", ["H (2)", "FC (1)"], ["30", E], {
        "degree_colleges": "A (1)", "higher_secondary_schools": "6", "middle_schools": "2",
        "primary_schools": "38", "other_edu_institutions": "7", "stadia": E,
        "cinemas": "3", "auditoria": E, "libraries": "PL (3)",
    }, 0)
    rows += parent("2", "Bahjoi", "ORDINARY", "", ["H (1)", "HC (1)", "FC (1)"], ["6", "4", E], {
        "higher_secondary_schools": "3", "middle_schools": "2", "primary_schools": "3",
    }, 1)
    rows += parent("3", "Bilari", "ORDINARY", "", ["HC (1)"], ["4"], {
        "vocational_institutes": "Sh. Type (1)", "higher_secondary_schools": "1",
        "middle_schools": "2", "primary_schools": "4",
    }, 2)
    rows += parent("4", "Chandausi", "ORDINARY", "", ["H (2)", "D (2)", "TBC (1)", "FC (1)"], ["40", "16", E, E], {
        "degree_colleges": "A (1) ASC (1)", "vocational_institutes": "Sh. Type (1) O (1)",
        "higher_secondary_schools": "6", "middle_schools": "3", "primary_schools": "25",
        "other_edu_institutions": "3", "stadia": E, "cinemas": "1", "auditoria": "1",
        "libraries": "PL (1)",
    }, 3)
    rows += parent("5", "Dhanaura", "ORDINARY", "", ["HC (1)"], ["4"], {
        "higher_secondary_schools": "2", "middle_schools": E, "primary_schools": "3",
        "other_edu_institutions": "3",
    }, 4)
    rows += parent("6", "Hasanpur", "ORDINARY", "", ["D (2)"], ["8"], {
        "higher_secondary_schools": "2", "middle_schools": "3", "primary_schools": "12",
        "cinemas": "1",
    }, 5)
    rows += parent("7", "Kanth", "ORDINARY", "", ["H (2)", "FC (1)"], ["12", E], {
        "degree_colleges": "AS (1)", "vocational_institutes": "Type (2)",
        "higher_secondary_schools": "1", "middle_schools": "2", "primary_schools": "4",
        "other_edu_institutions": "1", "libraries": "PL (1)",
    }, 6)
    rows += parent("8", "Moradabad", "CROSS_REFERENCE", "Moradabad City Urban Agglomeration", [""], [""], {}, 7)
    rows += parent("", "Moradabad City Urban Agglomeration", "AGGREGATE", "", ["H (9)", "TBC (1)", "O (2)", "D (3)", "FC (4)"], ["431", E, "50", E, E], {
        "degree_colleges": "ASC (4)", "polytechnics": "1", "vocational_institutes": "Sh. Type (1) O (1)",
        "higher_secondary_schools": "27", "middle_schools": "21", "primary_schools": "52",
        "other_edu_institutions": E, "stadia": "2", "cinemas": "6", "auditoria": "2",
        "libraries": "RR (2) PL (5)",
    }, 8)
    rows += parent("(i)", "Moradabad", "COMPONENT", "", ["H (8)", "TBC (1)", "O (2)", "D (3)", "FC (3)"], ["326", E, "50", E, E], {
        "degree_colleges": "ASC (4)", "polytechnics": "1", "vocational_institutes": "Sh. Type (1)",
        "higher_secondary_schools": "27", "middle_schools": "21", "primary_schools": "47",
        "stadia": "1", "cinemas": "6", "auditoria": "1", "libraries": "RR (2)",
    }, 9)
    rows += parent("(ii)", "Moradabad Rly. Settlement", "COMPONENT", "", ["H (1)", "FC (1)"], ["105", E], {
        "primary_schools": "5", "stadia": "1", "auditoria": "1", "libraries": "PL (3) PL (2)",
    }, 10)
    rows += parent("9", "Moradabad Rly. Settlement", "CROSS_REFERENCE", "Moradabad City Urban Agglomeration", [""], [""], {}, 11)
    rows += parent("10", "Rustamnagar Sahaspur", "ORDINARY", "", [E], [E], {
        "higher_secondary_schools": E, "middle_schools": "1", "primary_schools": "2",
        "other_edu_institutions": E, "libraries": "PL (2)",
    }, 12)
    rows += parent("11", "Sambhal", "ORDINARY", "", ["H (1)", "HC (1)", "FC (1)"], ["6", "4", E], {
        "degree_colleges": "A (1)", "higher_secondary_schools": "5", "middle_schools": "9",
        "primary_schools": "42", "cinemas": "1", "libraries": "RR (4)",
    }, 13)
    rows += parent("12", "Thakurdwara", "ORDINARY", "", ["HC (1)", "FC (1)"], ["4", E], {
        "higher_secondary_schools": "1", "middle_schools": "2", "primary_schools": "1",
        "other_edu_institutions": "4",
    }, 14)
    for i, row in enumerate(rows):
        row["row_index"] = str(i)
    finish(
        pdf_id,
        rows,
        fields,
        "# Moradabad MedEdu source-checked output\n\n"
        "The printed MedEdu parent bands and continuation panel were transcribed from pages 12–13 at 300 DPI. "
        "Fifteen logical parents expand to 34 child rows; columns 3–4 remain child-scoped and columns 5–17 are inherited only within each parent.\n",
    )


def tehsil():
    pdf_id = "moradabad_tehsil_1971"
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
    names = ["Hasanpur", "Sambhal", "Amroha", "Thakurdwara", "Moradabad", "Bilari", "District Total (Rural)"]
    educational = [
        ["233", "233", "17", "17", "5", "5", E, E, E, E],
        ["246", "249", "17", "17", "6", "6", E, E, E, E],
        ["240", "257", "19", "20", "2", "2", E, E, E, E],
        ["124", "134", "15", "15", "4", "4", E, E, E, E],
        ["158", "160", "11", "11", "3", "3", E, E, "1", "1"],
        ["175", "177", "8", "9", "3", "3", E, E, E, E],
        ["1,176", "1,210", "87", "89", "23", "23", E, E, "1", "1"],
    ]
    medical = [
        ["9", "9", E, E, "3", "3", E, E, E, E, E, E],
        ["11", "11", E, E, E, E, "2", "2", E, E, E, E],
        ["3", "3", "1", "1", E, E, "3", "3", "1", "1", E, E],
        ["3", "3", E, E, "5", "5", "1", "1", "1", "1", E, E],
        ["2", "2", "7", "7", "3", "3", E, E, "3", "3", E, E],
        ["7", "7", "4", "4", "2", "2", E, E, "3", "3", E, E],
        ["35", "35", "12", "12", "13", "13", "6", "6", "8", "8", E, E],
    ]
    water_values = [
        ["141", "550", E, "442", "525", E, E, E, E, E, E, E, E, E],
        ["196", "336", E, "485", "497", E, E, E, E, E, E, E, E, E],
        ["259", "343", E, "490", "506", "2", E, E, E, E, E, "4", E, E],
        ["45", "294", E, "238", "238", E, E, E, E, E, E, E, E, E],
        ["41", "300", E, "242", "278", E, E, E, E, E, E, "1", E, E],
        ["275", "174", E, "390", "390", "1", E, E, E, E, E, E, E, E],
        ["957", "1,997", E, "2,287", "2,434", "3", E, E, E, E, E, "5", E, E],
    ]
    communications = [
        ["91", "427", "19", "23", "24", "24", E, E, "3", "3", E, E],
        ["91", "369", "45", "8", "38", "38", E, E, E, E, E, E],
        ["73", "404", "32", "41", "31", "31", E, E, E, E, E, E],
        ["19", "194", "23", E, "24", "24", E, E, E, E, E, E],
        ["184", "62", "14", "53", "24", "24", E, E, E, E, E, E],
        ["184", "204", "2", "2", "29", "29", E, E, E, "1", E, E],
        ["642", "1,660", "135", "127", "170", "170", E, E, E, "4", E, E],
    ]
    rows = []
    for i, name in enumerate(names):
        row = deepcopy(template)
        row.update({
            "sl_no": str(i + 1) if i < 6 else "",
            "tahsil_name": name,
            "row_type": "TOTAL" if i == 6 else "ORDINARY",
            "reference_target": "",
            "row_index": str(i),
            "pdf_id": pdf_id,
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
        "# Moradabad Tahsil source-checked output\n\n"
        "The six printed tahsil rows and District Total (Rural) were transcribed from pages 304–305 at 300 DPI, "
        "including the educational, medical, power/water, and communications panels.\n",
    )


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
