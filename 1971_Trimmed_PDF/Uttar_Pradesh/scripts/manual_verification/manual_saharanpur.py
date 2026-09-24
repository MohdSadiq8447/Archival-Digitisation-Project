import csv
import os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Saharanpur"
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
                    writer.writerow([i, variable, before.get(variable, ""), row.get(variable, ""), "300-DPI source inspection; identity/continuation cleanup; unrelated sections excluded"])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "saharanpur_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = [
        "sl_no", "town_name", "road_length_km", "sewerage_drainage_system",
        "water_borne_latrines", "service_latrines", "other_latrines",
        "night_soil_disposal_method", "water_source", "water_capacity", "fire_service",
        "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light",
        "elec_other", "pucca_road_km", "kutcha_road_km",
    ]
    data = [
        ("1", "Bharat Heavy Electricals Ltd., Ranipur", "PR (40) KR (0)", "ST", "3,000", E, E, E, "TW/OHT", "120,000 Galls.", "Yes", "3,000", "4", "40", "872", E, "40.0", "0.0", "ORDINARY", ""),
        ("2", "Deoband", "PR (46) KR (26)", "PT/OSD", "10", "5,000", E, "B", "HP/W", E, E, "811", "52", "88", "459", E, "46.0", "26.0", "ORDINARY", ""),
        ("3", "Gangoh", "PR (17) KR (5)", "OSD", E, "935", E, "HL", "HP/W", E, E, "980", "42", "120", "253", E, "17.0", "5.0", "ORDINARY", ""),
        ("4", "Gurukul Kangri", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Hardwar Urban Agglomeration"),
        ("5", "Hardwar", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Hardwar Urban Agglomeration"),
        ("", "Hardwar Urban Agglomeration", "PR (82) KR (0)", "S/ST/OSD", "1,702", "5,588", "10", "HL/HC/MT", "TW/OHT", "5,298,920 Galls.", "Yes", "9,033", "261", "222", "1,919", E, "82.0", "0.0", "AGGREGATE", ""),
        ("(i)", "Gurukul Kangri", "PR (3) KR (0)", "S", "82", "60", "10", "HL", "TW/OHT", "12,000 Galls.", E, "1,815", E, "1", "50", E, "3.0", "0.0", "COMPONENT", ""),
        ("(ii)", "Hardwar", "PR (78) KR (0)", "S/OSD", "1,600", "5,528", E, "HC/MT", "TW/OHT", "5,281,920 Galls.", "Yes", "6,218", "258", "220", "1,849", E, "78.0", "0.0", "COMPONENT", ""),
        ("(iii)", "Jwalapur Mahavidyalaya", "PR (1) KR (0)", "ST", "20", E, E, "HC", "TW/OHT", "5,000 Galls.", E, "1,000", "3", "1", "20", E, "1.0", "0.0", "COMPONENT", ""),
        ("6", "Jwalapur Mahavidyalaya", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Hardwar Urban Agglomeration"),
        ("7", "Manglaur", "PR (21) KR (19)", "PT/OSD", "15", "3,500", E, "HL/HC/MT", "HP/W", E, E, "399", "16", "100", "190", E, "21.0", "19.0", "ORDINARY", ""),
        ("8", "Nakur", "PR (9) KR (4)", "PT/OSD", "17", "1,153", E, "HC", "TW/HP/W", "1,500 Galls.", E, "354", "11", "81", "45", E, "9.0", "4.0", "ORDINARY", ""),
        ("9", "Rampur Maniharan", "PR (8) KR (2)", "PT/OSD", "10", "1,535", E, "B", "HP/W", E, E, "350", "35", "100", "76", E, "8.0", "2.0", "ORDINARY", ""),
        ("10", "Roorkee", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Roorkee Urban Agglomeration"),
        ("11", "Roorkee Cantt.", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Roorkee Urban Agglomeration"),
        ("", "Roorkee Urban Agglomeration", "PR (61) KR (0)", "S/OSD", "300", "7,870", "701", "MT/B/HL", "TW/OHT/HP", "120,000 Galls.", "Yes", "3,072", "230", "1,036", "919", "-", "61.0", "0.0", "AGGREGATE", ""),
        ("(i)", "Roorkee", "PR (55) KR (0)", "S/OSD", "300", "7,812", "701", "B/MT", "TW/OHT", "100,000 Galls.", "Yes", "2,990", "230", "1,032", "787", E, "55.0", "0.0", "COMPONENT", ""),
        ("(ii)", "Roorkee Cantt.", "PR (6) KR (0)", "OSD", E, "58", E, "HL", "TW/OHT/HP", "20,000 Galls.", E, "82", E, "4", "132", E, "6.0", "0.0", "COMPONENT", ""),
        ("12", "Saharanpur", "PR (145) KR (45)", "S/OSD", "3,000", "44,700", E, "HL/HC/MT", "TW/OHT", "300,000 Galls.", "Yes", "17,534", "764", "1,000", "8,381", E, "145.0", "45.0", "ORDINARY", ""),
    ]
    rows = []
    for i, spec in enumerate(data):
        # Cross-reference rows have no printed data in columns 3–18; normalize
        # their compact tuple before assigning the fixed Civic schema.
        if len(spec) == 19:
            spec = spec[:-2] + ("",) + spec[-2:]
        row = deepcopy(template)
        row.update(dict(zip(variables + ["row_type", "reference_target"], spec)))
        row.update({"row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        clear_flags(row, variables)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Saharanpur Civic source-checked output\n\nThe printed Civic identities, Hardwar and Roorkee Urban Agglomeration aggregates/components, cross-reference rows, and Amenities continuation were transcribed from pages 10–11 at 300 DPI. Trade, Commerce, Industry, and Banking sections were excluded.\n")


def mededu():
    pdf_id = "saharanpur_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = [
        "sl_no", "town_name", "hospitals_dispensaries", "med_beds", "degree_colleges",
        "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes",
        "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions",
        "stadia", "cinemas", "auditoria", "libraries",
    ]

    def parent(serial, town, typ, ref, children, inherited, pidx):
        out = []
        for j, (child, bed) in enumerate(children):
            row = deepcopy(template)
            row.update({"sl_no": serial, "town_name": town, "row_type": typ, "reference_target": ref, "parent_row_index": str(pidx), "subrow_index": str(j), "subrow_count": str(len(children)), "row_index": "", "pdf_id": pdf_id, "district": DIST})
            for variable in variables:
                row[variable] = inherited.get(variable, "" if typ == "CROSS_REFERENCE" else E)
            row["sl_no"] = serial
            row["town_name"] = town
            row["hospitals_dispensaries"] = child
            row["med_beds"] = bed
            clear_flags(row, variables)
            out.append(row)
        return out

    rows = []
    rows += parent("1", "Bharat Heavy Electricals Ltd., Ranipur", "ORDINARY", "", [("H (1)", "50"), ("D (3)", "25"), ("TBC (1)", E), ("FC (1)", E)], {}, 0)
    rows += parent("2", "Deoband", "ORDINARY", "", [("H (1)", "4"), ("D (1)", "6")], {}, 1)
    rows += parent("3", "Gangoh", "ORDINARY", "", [("D (1)", "4")], {}, 2)
    rows += parent("4", "Gurukul Kangri", "CROSS_REFERENCE", "Hardwar Urban Agglomeration", [("See", "")], {}, 3)
    rows += parent("5", "Hardwar", "CROSS_REFERENCE", "Hardwar Urban Agglomeration", [("See", "")], {}, 4)
    rows += parent("", "Hardwar Urban Agglomeration", "AGGREGATE", "", [("H (3)", "64"), ("D (3)", "8"), ("FC (2)", E)], {"degree_colleges": "ASC (1) AS (1) A (3) S (1) C (1)", "medical_colleges": "3 **", "engg_colleges": E, "polytechnics": "1", "vocational_institutes": "Sh. Type (1)", "higher_secondary_schools": "9", "middle_schools": "3", "primary_schools": "45", "other_edu_institutions": "8", "stadia": E, "cinemas": "3", "auditoria": "6", "libraries": "PL (13) RR (1)"}, 5)
    rows += parent("(i)", "Gurukul Kangri", "COMPONENT", "", [("D (1)", "8")], {"degree_colleges": "ASC (1) A (1) S (1)", "medical_colleges": "2 **", "higher_secondary_schools": "2", "middle_schools": E, "primary_schools": E, "other_edu_institutions": "1", "libraries": "PL (1)"}, 6)
    rows += parent("(ii)", "Hardwar", "COMPONENT", "", [("H (3)", "64"), ("D (1)", E), ("FC (2)", E)], {"degree_colleges": "A (1) AS (1) C (1)", "medical_colleges": "1 **", "engg_colleges": E, "polytechnics": "1", "vocational_institutes": "Sh. Type (1)", "higher_secondary_schools": "6", "middle_schools": "2", "primary_schools": "41", "other_edu_institutions": "7", "stadia": E, "cinemas": "2", "auditoria": "4", "libraries": "PL (10)"}, 7)
    rows += parent("(iii)", "Jwalapur Mahavidyalaya", "COMPONENT", "", [("D (1)", E)], {"degree_colleges": "A (1)", "higher_secondary_schools": "1", "middle_schools": "1", "primary_schools": "1", "other_edu_institutions": E, "cinemas": "1", "auditoria": "2", "libraries": "PL (2) RR (1)"}, 8)
    rows += parent("6", "Jwalapur Mahavidyalaya", "CROSS_REFERENCE", "Hardwar Urban Agglomeration", [("See", "")], {}, 9)
    rows += parent("7", "Manglaur", "ORDINARY", "", [("H (1)", "12")], {"higher_secondary_schools": "1", "middle_schools": "2", "primary_schools": "13", "other_edu_institutions": "5", "libraries": "PL (1)"}, 10)
    rows += parent("8", "Nakur", "ORDINARY", "", [("D (1)", "4")], {"higher_secondary_schools": "1", "middle_schools": "2", "primary_schools": "2", "other_edu_institutions": "3"}, 11)
    rows += parent("9", "Rampur Maniharan", "ORDINARY", "", [("H (1)", "6")], {"degree_colleges": "S (1)", "higher_secondary_schools": "1", "middle_schools": "4", "primary_schools": "7", "other_edu_institutions": "1", "libraries": "PL (1)"}, 12)
    rows += parent("10", "Roorkee", "CROSS_REFERENCE", "Roorkee Urban Agglomeration", [("See", "")], {}, 13)
    rows += parent("11", "Roorkee Cantt.", "CROSS_REFERENCE", "Roorkee Urban Agglomeration", [("See", "")], {}, 14)
    rows += parent("", "Roorkee Urban Agglomeration", "AGGREGATE", "", [("H (3)", "94"), ("D (3)", E), ("O (1)", "11"), ("FC (1)", E)], {"degree_colleges": "A (2) S (1)", "medical_colleges": "-", "engg_colleges": "1", "polytechnics": "1", "vocational_institutes": "Sh. Type (1)", "higher_secondary_schools": "7", "middle_schools": "10", "primary_schools": "42", "other_edu_institutions": "10", "stadia": "1", "cinemas": "5", "auditoria": "2", "libraries": "PL (2)"}, 15)
    rows += parent("(i)", "Roorkee", "COMPONENT", "", [("H (3)", "94"), ("D (2)", E), ("O (1)", "11"), ("FC (1)", E)], {"degree_colleges": "A (2) S (1)", "engg_colleges": "1", "polytechnics": "1", "vocational_institutes": "Sh. Type (1)", "higher_secondary_schools": "6", "middle_schools": "8", "primary_schools": "22", "other_edu_institutions": "9", "stadia": "1", "cinemas": "4", "auditoria": "2", "libraries": "PL (1)"}, 16)
    rows += parent("(ii)", "Roorkee Cantt.", "COMPONENT", "", [("D (1)", "8")], {"higher_secondary_schools": "1", "middle_schools": "2", "primary_schools": "2", "other_edu_institutions": "1", "cinemas": "1", "libraries": "PL (1)"}, 17)
    rows += parent("12", "Saharanpur", "ORDINARY", "", [("H (9)", "328"), ("D (3)", E), ("TBC (1)", E), ("O (1)", "60"), ("FC (4)", E)], {"degree_colleges": "ASC (1) S (1) A (2)", "vocational_institutes": "Sh. Type (2)", "higher_secondary_schools": "21", "middle_schools": "11", "primary_schools": "191", "other_edu_institutions": "8", "stadia": E, "cinemas": "7", "auditoria": "9", "libraries": "PL (15) RR (20)"}, 18)
    for i, row in enumerate(rows):
        row["row_index"] = str(i)
    finish(pdf_id, rows, fields, "# Saharanpur MedEdu source-checked output\n\nThe printed ordinary identities, Hardwar and Roorkee Urban Agglomeration aggregates/components, cross-reference rows, and all medical child bands were transcribed from pages 12–13 at 300 DPI. Columns 3–4 are child-scoped; columns 5–17 are inherited within each parent. The Ayurvedic footnote and unrelated panels were excluded from data cells.\n")


def tehsil():
    pdf_id = "saharanpur_tehsil_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    comm = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    all_variables = edu + med + water + comm
    names = ["Saharanpur", "Nakur", "Deoband", "Roorkee", "District Total (Rural)"]
    educational = [["230", "251", "28", "32", "9", "10", E, E, "4", "4"], ["166", "166", "29", "27", "2", "3", E, E, E, E], ["191", "241", "28", "33", "10", "10", E, E, "1", "1"], ["223", "230", "36", "35", "4", "4", "1", "1", E, "-"], ["820", "888", "121", "127", "25", "27", "1", "1", "5", "5"]]
    medical = [["15", "15", "4", "4", "2", "2", "2", "2", "3", "3", E, E], [E, E, "8", "8", E, E, E, E, E, E, E, E], ["8", "8", "7", "7", "4", "4", E, E, "1", "1", E, E], ["18", "18", "7", "7", E, E, "1", "1", "1", "1", E, E], ["41", "41", "26", "26", "6", "6", "3", "3", "5", "5", E, E]]
    water_values = [["101", "544", "2", "413", "443", E, "21", E, "10", E, E, "11", E, E], ["49", "498", E, "389", "327", E, E, E, E, E, E, "1", E, E], ["131", "294", E, "289", "282", E, "8", "1", E, E, E, "2", E, E], ["107", "433", E, "400", "378", "10", E, E, E, E, E, "1", E, E], ["388", "1,769", "2", "1,491", "1,430", "18", "22", E, "10", E, E, "15", E, E]]
    communications = [["174", "291", "6", "46", "46", "46", E, E, "3", "3", "4", "4"], ["63", "72", "15", "2", "20", "20", E, E, "3", "3", "1", "1"], ["44", "34", "6", "38", "237", "37", E, E, "2", "2", "4", "4"], ["185", "143", "1", "33", "45", "45", "1", "1", "3", "3", E, E], ["466", "540", "28", "319", "348", "148", "1", "1", "11", "11", "9", "9"]]
    rows = []
    for i, name in enumerate(names):
        row = deepcopy(template)
        row.update({"sl_no": str(i + 1) if i < 4 else "", "tahsil_name": name, "row_type": "TOTAL" if i == 4 else "ORDINARY", "reference_target": "", "row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        row.update(dict(zip(edu, educational[i]))); row.update(dict(zip(med, medical[i]))); row.update(dict(zip(water, water_values[i]))); row.update(dict(zip(comm, communications[i])))
        clear_flags(row, ["sl_no", "tahsil_name"] + all_variables)
        rows.append(row)
    finish(pdf_id, rows, fields, "# Saharanpur Tahsil source-checked output\n\nThe four tahsil rows and District Total (Rural) were transcribed from the educational, medical, drinking-water, and communications panels on pages 224–225 at 300 DPI. Printed placeholders, dashes, and totals are preserved.\n")


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
