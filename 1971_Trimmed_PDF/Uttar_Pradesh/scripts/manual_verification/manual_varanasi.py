import csv
import os
from copy import deepcopy


ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Varanasi"
E = "..."


def load(pdf_id):
    src = os.path.join(ROOT, f"up1971-{pdf_id}-regex-cleaned-v1", "csv", f"{pdf_id}.csv")
    with open(src, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows, list(rows[0])


def clear_flags(row, variables):
    for variable in variables:
        key = f"{variable}_flag"
        if key in row:
            row[key] = ""
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
    old_by_lineage = {(r.get("parent_row_index", ""), r.get("subrow_index", ""), r.get("row_index", "")): r for r in old}
    with open(os.path.join(out, "CORRECTION_LOG.csv"), "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["row_index", "variable", "original_value", "corrected_value", "reason"])
        for i, row in enumerate(rows):
            before = old_by_lineage.get((row.get("parent_row_index", ""), row.get("subrow_index", ""), row.get("row_index", "")), old[i] if i < len(old) else {})
            for variable in fields:
                if variable.endswith("_flag") or variable in {"row_index", "parent_row_index", "subrow_index", "subrow_count", "requires_review", "extracted_at"}:
                    continue
                if before.get(variable, "") != row.get(variable, ""):
                    writer.writerow([i, variable, before.get(variable, ""), row.get(variable, ""), "300-DPI source inspection; continuation panel aligned by printed row order"])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "varanasi_civic_1971"
    old, fields = load(pdf_id)
    variables = ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other"]
    data = [
        ("1", "Banaras Hindu University", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Varanasi City Urban Agglomeration", ""),
        ("2", "Bhadohi", "PR (8) KR (12)", "PT/OSD", "60", "134", "20", "B", "TW/OHT", "50,000 Galls.", E, "1,100", "300", "100", "242", E, "ORDINARY", "", "8.0", "12.0"),
        ("3", "Chakia", "PR (3) KR (2)", "PT/OSD", "50", "250", "-", "HL", "TW/OHT", "15,000 Galls.", E, "139", "18", "150", "36", E, "ORDINARY", "", "3.0", "2.0"),
        ("4", "Chandauli", "PR (3) KR (0)", "PT/OSD", "25", "105", E, "HL", "TW/OHT", "N. A.", E, "240", "4", "25", "15", E, "ORDINARY", "", "3.0", "0.0"),
        ("5", "Gopiganj", "PR (3) KR (4)", "PT/OSD", "200", "200", E, "B", "TW/OHT", "27,000 Galls.", E, "320", "17", "500", "150", E, "ORDINARY", "", "3.0", "4.0"),
        ("6", "Gyanpur", "PR (5) KR (15)", "PT/OSD", "80", "20", E, "B", "TW/OHT", "32,000 Galls.", E, "200", "11", "100", "100", E, "ORDINARY", "", "5.0", "15.0"),
        ("7", "Lohta", "PR (4) KR (0)", "PT/OSD", "300", "70", E, "B", "N. A.", "N. A.", E, "300", "1", "20", "6", E, "ORDINARY", "", "4.0", "0.0"),
        ("8", "Maruadih", "PR (25) KR (0)", "PT/BSD", "3,200", E, E, E, "TW/OHT", "2,000,000 Galls.", "Yes", "2,779", "135", "87", "821", E, "ORDINARY", "", "25.0", "0.0"),
        ("9", "Mughal Sarai", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Mughal Sarai Urban Agglomeration", ""),
        ("10", "Northern Rly. Colony Mughal Sarai", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Mughal Sarai Urban Agglomeration", ""),
        ("", "Mughal Sarai Urban Agglomeration", "PR (38) KR (2)", "ST/OSD", "1,381", "1,330", E, "HC", "TW/OHT", "515,825 Galls.", "Yes", "2,790", "15", "800", "572", E, "AGGREGATE", "", "38.0", "2.0"),
        ("(i)", "Mughal Sarai", "PR (5) KR (0)", "ST/OSD", "59", "719", E, "HC", "TW/OHT", "50,000 Galls.", "Yes", "800", "15", "800", "125", E, "COMPONENT", "", "5.0", "0.0"),
        ("(ii)", "Northern Rly. Colony Mughal Sarai", "PR (33) KR (0)", "ST/OSD", "1,322", "611", E, "HC", "TW/OHT", "465,825 Galls.", "Yes", "1,990", E, E, "467", E, "COMPONENT", "", "33.0", "0.0"),
        ("11", "Ramnagar", "PR (15) KR (6)", "PT/OSD", "401", "1,003", "603", "HC", "R/TW/OHT", "50,000 Galls.", E, "774", "26", "130", "286", E, "ORDINARY", "", "15.0", "6.0"),
        ("12", "Varanasi", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Varanasi City Urban Agglomeration", ""),
        ("13", "Varanasi Cantt.", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Varanasi City Urban Agglomeration", ""),
        ("", "Varanasi City Urban Agglomeration", "PR (280) KR (17)", "S/OSD", "N. A.", "N. A.", "N. A.", "MT/B/HC/HL", "TW/OHT", "42,532,666 Galls.", "Yes", "55,387", "1,355", "785", "10,198", "350", "AGGREGATE", "", "280.0", "17.0"),
        ("(i)", "Banaras Hindu University", "PR (35) KR (0)", "S/OSD", "1,250", "60", E, "MT", "TW/OHT", "230,000 Galls.", E, "799", E, "1", "650", E, "COMPONENT", "", "35.0", "0.0"),
        ("(ii)", "Varanasi", "PR (226) KR (16)", "S/OSD", "N. A.", "N. A.", "N. A.", "MT/HC/B/HL", "TW/OHT", "42,000,000 Galls.", "Yes", "53,000", "1,350", "750", "9,120", "350", "COMPONENT", "", "226.0", "16.0"),
        ("(iii)", "Varanasi Cantt.", "PR (12) KR (1)", "S/OSD", "N. A.", "N. A.", "N. A.", "MT/HC", "**", "**", E, "260", "5", "15", "192", E, "COMPONENT", "", "12.0", "1.0"),
        ("(iv)", "Varanasi Rly. Colony", "PR (7) KR (0)", "S/OSD", "120", "195", "298", "HC", "TW/OHT", "302,666 Galls.", E, "1,328", E, E, "236", E, "COMPONENT", "", "7.0", "0.0"),
        ("14", "Varanasi Rly. Colony", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Varanasi City Urban Agglomeration", ""),
    ]
    rows = []
    for i, values in enumerate(data):
        if len(values) < 20:
            values = values + ("",) * (20 - len(values))
        row = deepcopy(old[i])
        row.update(dict(zip(variables, values[:16])))
        row.update({"row_type": values[16], "reference_target": values[17], "pucca_road_km": values[18], "kutcha_road_km": values[19], "requires_review": "False", "row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        clear_flags(row, variables + ["pucca_road_km", "kutcha_road_km"])
        rows.append(row)
    finish(pdf_id, rows, fields, "# Varanasi Civic source-checked output\n\nAll 22 printed logical rows, including cross-references, Mughal Sarai and Varanasi aggregates, and their components, were transcribed from the Civic anchor and Amenities continuation at 300 DPI. The page-2 continuation is aligned ordinally to the page-1 identity rows; the footnote about N. M. P. Varanasi is retained as source context and not emitted as a data row.\n")


def mededu():
    pdf_id = "varanasi_mededu_1971"
    old, fields = load(pdf_id)
    variables = ["hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]
    parents = [
        ("1", "Banaras Hindu University", "CROSS_REFERENCE", "Varanasi City Urban Agglomeration", [("See", "")], {}),
        ("2", "Bhadohi", "ORDINARY", "", [("H (2)", "32"), ("FC (1)", "")], {"higher_secondary_schools": "3", "middle_schools": "1", "primary_schools": "9", "other_edu_institutions": "7", "cinemas": "1", "libraries": "PL (2) RR (2)"}),
        ("3", "Chakia", "ORDINARY", "", [("H (2)", "12"), ("D (1)", "16"), ("HC (1)", "2"), ("FC (1)", "")], {"higher_secondary_schools": "2", "middle_schools": "1", "primary_schools": "2", "libraries": "PL (1)"}),
        ("4", "Chandauli", "ORDINARY", "", [("H (1)", "12"), ("D (1)", ""), ("NH (1)", ""), ("FC (1)", "")], {"polytechnics": "1", "higher_secondary_schools": "4", "middle_schools": "1", "primary_schools": "2", "libraries": "PL (1)"}),
        ("5", "Gopiganj", "ORDINARY", "", [("H (1)", "46"), ("HC (1)", ""), ("D (1)", "4"), ("FC (1)", "")], {"higher_secondary_schools": "3", "middle_schools": "1", "primary_schools": "2", "other_edu_institutions": "2"}),
        ("6", "Gyanpur", "ORDINARY", "", [("H (2)", "52"), ("HC (1)", ""), ("FC (1)", "")], {"degree_colleges": "ASC (1)", "vocational_institutes": "O (1)", "higher_secondary_schools": "3", "middle_schools": "1", "primary_schools": "1", "other_edu_institutions": "2", "libraries": "PL (1) RR (2)"}),
        ("7", "Lohta", "ORDINARY", "", [("", "")], {"middle_schools": "1", "primary_schools": "4", "stadia": "1", "auditoria": "1", "libraries": "PL (1)"}),
        ("8", "Maruadih", "ORDINARY", "", [("H (1)", "28"), ("HC (1)", ""), ("FC (1)", E)], {}),
        ("9", "Mughal Sarai", "CROSS_REFERENCE", "Mughal Sarai Urban Agglomeration", [("See", "")], {}),
        ("10", "Northern Rly. Colony Mughal Sarai", "CROSS_REFERENCE", "Mughal Sarai Urban Agglomeration", [("See", "")], {}),
        ("", "Mughal Sarai Urban Agglomeration", "AGGREGATE", "", [("H (2)", "67"), ("D (2)", E), ("HC (1)", E), ("FC (2)", E), ("TBC (1)", "20"), ("*O (1)", "6")], {"degree_colleges": "A (1)", "higher_secondary_schools": "4", "middle_schools": "3", "primary_schools": "18", "cinemas": "4", "auditoria": "3", "libraries": "PL (5)"}),
        ("(i)", "Mughal Sarai", "COMPONENT", "", [("H (1)", "12"), ("D (2)", E), ("HC (1)", E), ("FC (1)", E)], {"degree_colleges": "A (1)", "higher_secondary_schools": "2", "middle_schools": "3", "primary_schools": "8", "cinemas": "3"}),
        ("(ii)", "Northern Rly. Colony Mughal Sarai", "COMPONENT", "", [("H (1)", "55"), ("TBC (1)", "20"), ("FC (1)", E), ("*O (1)", "6")], {"higher_secondary_schools": "2", "primary_schools": "10", "cinemas": "1", "auditoria": "3", "libraries": "PL (5)"}),
        ("11", "Ramnagar", "ORDINARY", "", [("H (1)", "106"), ("D (1)", "22"), ("FC (1)", E), ("TBC (1)", E)], {"vocational_institutes": "O (1)", "middle_schools": "3", "primary_schools": "9", "other_edu_institutions": "2", "libraries": "PL (1) RR (1)"}),
        ("12", "Varanasi", "CROSS_REFERENCE", "Varanasi City Urban Agglomeration", [("See", "")], {}),
        ("13", "Varanasi Cantt.", "CROSS_REFERENCE", "Varanasi City Urban Agglomeration", [("See", "")], {}),
        ("", "Varanasi City Urban Agglomeration", "AGGREGATE", "", [("H (21)", "2,623"), ("D (8)", "4"), ("FC (17)", E), ("*O (3)", "47"), ("TBC (1)", E)], {"degree_colleges": "A (6) S (1) C (1) ASC (2) AC (1)", "medical_colleges": "1", "engg_colleges": "3", "polytechnics": "1", "vocational_institutes": "Sh. Type (3) O (12)", "higher_secondary_schools": "45", "middle_schools": "32", "primary_schools": "189", "other_edu_institutions": "7", "stadia": "3", "cinemas": "14", "auditoria": "3", "libraries": "PL (28)"}),
        ("(i)", "Banaras Hindu University", "COMPONENT", "", [("H (1)", "641"), ("D (3)", E), ("FC (1)", E)], {"degree_colleges": "A (2) S (1) C (1)", "medical_colleges": "1", "engg_colleges": "3", "higher_secondary_schools": "1", "primary_schools": "2", "libraries": "PL (1)"}),
        ("(ii)", "Varanasi", "COMPONENT", "", [("H (16)", "1,788"), ("D (5)", "4"), ("*O (3)", "47"), ("TBC (1)", E), ("FC (14)", E)], {"degree_colleges": "ASC (2) A (4) AC (1)", "polytechnics": "1", "vocational_institutes": "Sh. Type (3) O (12)", "higher_secondary_schools": "42", "middle_schools": "28", "primary_schools": "179", "other_edu_institutions": "7", "stadia": "1", "cinemas": "14", "auditoria": "2", "libraries": "PL (25)"}),
        ("(iii)", "Varanasi Cantt.", "COMPONENT", "", [("H (2)", "62"), ("FC (1)", E)], {"higher_secondary_schools": "1", "middle_schools": "3", "primary_schools": "5", "libraries": "PL (1)"}),
        ("(iv)", "Northern Rly. Colony", "COMPONENT", "", [("H (2)", "132"), ("FC (1)", E)], {"higher_secondary_schools": "1", "middle_schools": "1", "primary_schools": "3", "stadia": "1", "libraries": "PL (1)"}),
        ("14", "Northern Rly. Colony", "CROSS_REFERENCE", "Varanasi City Urban Agglomeration", [("See", "")], {}),
    ]
    inherited_defaults = {v: E for v in variables[2:]}
    rows = []
    row_index = 0
    for parent_index, (sl_no, town, row_type, reference_target, children, inherited) in enumerate(parents):
        values = dict(inherited_defaults)
        values.update(inherited)
        count = len(children)
        for subrow_index, (child, bed) in enumerate(children):
            row = deepcopy(old[row_index] if row_index < len(old) else old[-1])
            row.update({"sl_no": sl_no, "town_name": town, "hospitals_dispensaries": child, "med_beds": bed, "row_type": row_type, "reference_target": reference_target, "requires_review": "False", "parent_row_index": str(parent_index), "subrow_index": str(subrow_index), "subrow_count": str(count), "row_index": str(row_index), "pdf_id": pdf_id, "district": DIST})
            for variable in variables[2:]:
                row[variable] = values[variable]
            clear_flags(row, ["sl_no", "town_name"] + variables)
            rows.append(row)
            row_index += 1
    if row_index < len(old):
        raise RuntimeError(f"generated fewer MedEdu rows than the extracted baseline: {row_index} < {len(old)}")
    finish(pdf_id, rows, fields, "# Varanasi MedEdu source-checked output\n\nThe 22 printed parents and 62 expanded child rows were transcribed from the Medical/Educational statement and its Cultural Facilities continuation at 300 DPI. The source contains the H (1) / 55 child under Northern Rly. Colony Mughal Sarai; it was restored because the regex baseline omitted that printed child. Columns 3–4 are child-scoped; columns 5–17 are inherited once per parent and then repeated only within that parent. Cross-reference lines are represented as `See` child rows with a reference target, while the printed maternity/child-welfare note is excluded from the data rows.\n")


if __name__ == "__main__":
    civic()
    mededu()
