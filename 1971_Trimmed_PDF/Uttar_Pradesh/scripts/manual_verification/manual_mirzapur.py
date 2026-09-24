import csv
import os
from copy import deepcopy


ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Mirzapur"
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
                        i,
                        variable,
                        before.get(variable, ""),
                        row.get(variable, ""),
                        "300-DPI source inspection; structural/OCR cleanup",
                    ])

    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(pdf_id, len(rows))


def civic():
    pdf_id = "mirzapur_civic_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = [
        "sl_no", "town_name", "road_length_km", "sewerage_drainage_system",
        "water_borne_latrines", "service_latrines", "other_latrines",
        "night_soil_disposal_method", "water_source", "water_capacity", "fire_service",
        "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other",
        "pucca_road_km", "kutcha_road_km",
    ]
    data = [
        ("1", "Ahraura", "PR (3) KR (2)", "OSD", E, "1,000", E, "HL", "TW/OHT", "30,000 Galls.", E, "247", "28", "24", "75", E, "3.0", "2.0"),
        ("2", "Chopan", "PR (14) KR (1)", "ST/OSD", "250", "20", E, "HL", "R/OHT", "99,880 Galls.", E, "305", "20", "45", "300", E, "14.0", "1.0"),
        ("3", "Chunar", "PR (6) KR (6)", "OSD", E, "769", E, "HL", "TW/OHT", "30,000 Galls.", E, "414", "24", "88", "127", E, "6.0", "6.0"),
        ("4", "Churk Ghurma", "PR (3) KR (0)", "ST", "796", E, E, E, "R/OHT", "15,840 Galls.", "Yes", "1,308", "4", "73", "587", E, "3.0", "0.0"),
        ("5", "Dudhi", "PR (3) KR (0)", "PT/OSD", "18", "95", E, "HL", "R/OHT", "14,960 Galls.", E, "110", "6", "24", "130", E, "3.0", "0.0"),
        ("6", "Kachhwa", "PR (2) KR (2)", "PT/OSD", "25", "600", E, "HL", "N.A.", "N.A.", E, "100", "1", "21", "36", E, "2.0", "2.0"),
        ("7", "Markundi", "PR (3) KR (0)", "OSD", E, "70", E, "HL", "W", E, E, E, E, E, E, E, "3.0", "0.0"),
        ("8", "Mirzapur-cum-Vindhyachal", "PR (77) KR (6)", "ST/OSD", "2,000", "14,000", E, "HL/HC", "TW/OHT", "375,000 Galls.", "Yes", "5,148", "598", "2,899", "1,739", E, "77.0", "6.0"),
        ("9", "Obra", "PR (16) KR (0)", "ST/OSD", "1,215", "221", E, "HL/HC", "TW/OHT", "1,997,600 Galls.", "Yes", "4,500", "14", "160", "400", "6", "16.0", "0.0"),
        ("10", "Pipri", "PR (19) KR (0)", "ST/OSD", "684", E, E, E, "R/OHT", "120,000 Galls.", "Yes", "410", "10", "158", "475", "1", "19.0", "0.0"),
        ("11", "Renukoot", "PR (16) KR (0)", "ST/OSD", "2,296", E, E, E, "R/OHT", "3,500,000 Galls.", "Yes", "1,745", "3", "63", "105", "3", "16.0", "0.0"),
        ("12", "Robertsganj", "PR (8) KR (0)", "ST/OSD", "40", "322", E, "HL", "TW/OHT", "122,222,222 Galls.", E, "513", "30", "114", "125", E, "8.0", "0.0"),
    ]
    rows = []
    for i, spec in enumerate(data):
        row = deepcopy(template)
        row.update(dict(zip(variables, spec)))
        row.update({
            "row_type": "ORDINARY", "reference_target": "", "row_index": str(i),
            "pdf_id": pdf_id, "district": DIST,
        })
        clear_flags(row, variables)
        rows.append(row)
    finish(
        pdf_id,
        rows,
        fields,
        "# Mirzapur Civic source-checked output\n\n"
        "The 12 printed town rows and their Amenities continuation values were transcribed from pages 10–11 at 300 DPI.\n",
    )


def mededu():
    pdf_id = "mirzapur_mededu_1971"
    old, fields = load(pdf_id)
    template = deepcopy(old[0])
    variables = [
        "sl_no", "town_name", "hospitals_dispensaries", "med_beds", "degree_colleges",
        "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes",
        "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions",
        "stadia", "cinemas", "auditoria", "libraries",
    ]

    def parent(serial, town, children, beds, inherited, pidx):
        out = []
        for j, (child, bed) in enumerate(zip(children, beds)):
            row = deepcopy(template)
            row.update({
                "sl_no": serial, "town_name": town, "row_type": "ORDINARY", "reference_target": "",
                "parent_row_index": str(pidx), "subrow_index": str(j),
                "subrow_count": str(len(children)), "row_index": "", "pdf_id": pdf_id,
                "district": DIST,
            })
            clear_flags(row, variables)
            for variable in variables:
                row[variable] = inherited.get(variable, E)
            row["sl_no"] = serial
            row["town_name"] = town
            row["hospitals_dispensaries"] = child
            row["med_beds"] = bed
            out.append(row)
        return out

    rows = []
    rows += parent("1", "Ahraura", ["H (1)", "FC (1)"], ["7", E], {
        "degree_colleges": E, "medical_colleges": E, "engg_colleges": E, "polytechnics": E,
        "vocational_institutes": E, "higher_secondary_schools": "1", "middle_schools": "2",
        "primary_schools": "3", "other_edu_institutions": E, "stadia": E, "cinemas": E,
        "auditoria": E, "libraries": E,
    }, 0)
    rows += parent("2", "Chopan", ["HC (2)", "D (1)", "FC (1)"], ["4", "4", E], {
        "degree_colleges": E, "medical_colleges": E, "engg_colleges": E, "polytechnics": E,
        "vocational_institutes": E, "higher_secondary_schools": "1", "middle_schools": E,
        "primary_schools": "2", "other_edu_institutions": E, "stadia": "1", "cinemas": E,
        "auditoria": "1", "libraries": E,
    }, 1)
    rows += parent("3", "Chunar", ["H (3)", "FC (1)"], ["40", E], {
        "degree_colleges": E, "medical_colleges": E, "engg_colleges": E, "polytechnics": E,
        "vocational_institutes": E, "higher_secondary_schools": "1", "middle_schools": "1",
        "primary_schools": "4", "other_edu_institutions": "1", "stadia": E, "cinemas": "1",
        "auditoria": "1", "libraries": E,
    }, 2)
    rows += parent("4", "Churk Ghurma", ["H (1)", "D (4)"], ["14", "14"], {
        "degree_colleges": E, "medical_colleges": E, "engg_colleges": E, "polytechnics": E,
        "vocational_institutes": E, "higher_secondary_schools": "2", "middle_schools": E,
        "primary_schools": "2", "other_edu_institutions": E, "stadia": E, "cinemas": E,
        "auditoria": E, "libraries": E,
    }, 3)
    rows += parent("5", "Dudhi", ["H (1)", "HC (1)", "FC (1)"], ["12", "8", E], {
        "degree_colleges": E, "medical_colleges": E, "engg_colleges": E, "polytechnics": E,
        "vocational_institutes": E, "higher_secondary_schools": "1", "middle_schools": "2",
        "primary_schools": "3", "other_edu_institutions": E, "stadia": E, "cinemas": E,
        "auditoria": E, "libraries": "PL (1)",
    }, 4)
    rows += parent("6", "Kachhwa", ["H (1)", "D (1)"], ["130", "4"], {
        "degree_colleges": E, "medical_colleges": E, "engg_colleges": E, "polytechnics": E,
        "vocational_institutes": E, "higher_secondary_schools": "1", "middle_schools": "3",
        "primary_schools": "3", "other_edu_institutions": E, "stadia": E, "cinemas": E,
        "auditoria": E, "libraries": E,
    }, 5)
    rows += parent("7", "Markundi", [E], [E], {
        "degree_colleges": E, "medical_colleges": E, "engg_colleges": E, "polytechnics": E,
        "vocational_institutes": E, "higher_secondary_schools": E, "middle_schools": E,
        "primary_schools": "1", "other_edu_institutions": E, "stadia": E, "cinemas": E,
        "auditoria": E, "libraries": E,
    }, 6)
    rows += parent("8", "Mirzapur-cum-Vindhyachal", ["H (7)", "D (4)", "TBC (1)", "FC (1)", "O (3)"], ["214", E, E, E, E], {
        "degree_colleges": "ASC (3)", "medical_colleges": E, "engg_colleges": E, "polytechnics": "1",
        "vocational_institutes": "Sh. Type (3) O (1)", "higher_secondary_schools": "10",
        "middle_schools": "6", "primary_schools": "54", "other_edu_institutions": E,
        "stadia": E, "cinemas": "2", "auditoria": E, "libraries": "PL (3)",
    }, 7)
    rows += parent("9", "Obra", ["H (1)"], ["22"], {
        "degree_colleges": E, "medical_colleges": E, "engg_colleges": E, "polytechnics": E,
        "vocational_institutes": E, "higher_secondary_schools": "1", "middle_schools": E,
        "primary_schools": "1", "other_edu_institutions": "2", "stadia": E, "cinemas": "1",
        "auditoria": E, "libraries": E,
    }, 8)
    rows += parent("10", "Pipri", ["H (1)", "D (1)"], ["12", "4"], {
        "degree_colleges": E, "medical_colleges": E, "engg_colleges": E, "polytechnics": E,
        "vocational_institutes": E, "higher_secondary_schools": "1", "middle_schools": E,
        "primary_schools": "2", "other_edu_institutions": E, "stadia": E, "cinemas": "1",
        "auditoria": E, "libraries": E,
    }, 9)
    rows += parent("11", "Renukoot", ["D (3)"], ["26"], {
        "degree_colleges": E, "medical_colleges": E, "engg_colleges": E, "polytechnics": E,
        "vocational_institutes": E, "higher_secondary_schools": "1", "middle_schools": E,
        "primary_schools": "3", "other_edu_institutions": E, "stadia": E, "cinemas": E,
        "auditoria": "1", "libraries": E,
    }, 10)
    rows += parent("12", "Robertsganj", ["H (1)"], ["8"], {
        "degree_colleges": E, "medical_colleges": E, "engg_colleges": E, "polytechnics": E,
        "vocational_institutes": E, "higher_secondary_schools": "1", "middle_schools": "2",
        "primary_schools": "6", "other_edu_institutions": E, "stadia": E, "cinemas": "1",
        "auditoria": E, "libraries": E,
    }, 11)
    for i, row in enumerate(rows):
        row["row_index"] = str(i)
    finish(
        pdf_id,
        rows,
        fields,
        "# Mirzapur MedEdu source-checked output\n\n"
        "The 12 printed town parents and their continuation panel were transcribed from pages 12–13 at 300 DPI. "
        "They expand to 25 child rows; columns 3–4 are child-scoped and columns 5–17 are inherited only within each parent.\n",
    )


if __name__ == "__main__":
    civic()
    mededu()
