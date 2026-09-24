import csv
import os
from copy import deepcopy


ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Muzaffarnagar"
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
    pdf_id = "muzaffarnagar_civic_1971"
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
        ("1", "Jansath", "PR (4) KR (0)", "OSD", E, "2,000", E, "HL", "HP", E, E, "1,000", E, "50", "40", E, "4.0", "0.0", "ORDINARY", ""),
        ("2", "Kairana", "PR (7) KR (10)", "PT/OSD", "50", "9,006", E, "HC", "HP", E, E, "745", "32", "223", "500", E, "7.0", "10.0", "ORDINARY", ""),
        ("3", "Kandhla", "PR (6) KR (14)", "S/OSD", "N.A.", "2,000", E, "HL/HC", "TW/OHT", "50,000 Galls.", E, "1,200", "11", "18", "196", E, "6.0", "14.0", "ORDINARY", ""),
        ("4", "Khatauli", "PR (22) KR (7)", "S/PT/OSD", "116", "2,015", E, "HL/HC", "TW/OHT", "50,000 Galls.", E, "2,010", "35", "80", "400", E, "22.0", "7.0", "ORDINARY", ""),
        ("5", "Miranpur", "PR (6) KR (0)", "PT/OSD", "10", "2,500", E, "HL", "HP", E, E, "2,000", "20", "150", "70", E, "6.0", "0.0", "ORDINARY", ""),
        ("6", "Muzaffarnagar", "PR (16) KR (0)", "PT/OSD", "2,000", "8,012", E, "HC/HL/MT", "TW/OHT", "94,800 Galls.", "Yes", "9,217", "460", "750", "1,650", E, "16.0", "0.0", "ORDINARY", ""),
        ("7", "Shamli", "PR (46) KR (0)", "PT/OSD", "116", "1,600", E, "MT/HC", "TW/OHT", "1,00,000 Galls.", E, "2,218", "5", "180", "530", E, "46.0", "0.0", "ORDINARY", ""),
    ]
    rows = []
    for i, spec in enumerate(data):
        row = deepcopy(template)
        row.update(dict(zip(variables + ["row_type", "reference_target"], spec)))
        row.update({"row_index": str(i), "pdf_id": pdf_id, "district": DIST})
        clear_flags(row, variables)
        rows.append(row)
    finish(
        pdf_id,
        rows,
        fields,
        "# Muzaffarnagar Civic source-checked output\n\n"
        "The seven printed Civic rows and Amenities continuation panel were transcribed from pages 6–7 at 300 DPI. "
        "The preceding Municipal Finance table was explicitly excluded from the Civic records.\n",
    )


def mededu():
    pdf_id = "muzaffarnagar_mededu_1971"
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
    rows += parent("1", "Jansath", ["H (2)", "FC (1)"], ["14", E], {
        "higher_secondary_schools": "2", "middle_schools": "1", "primary_schools": "3",
    }, 0)
    rows += parent("2", "Kairana", ["H (2)", "HC (1)", "FC (1)", "O (1)"], ["10", "4", "1", "1"], {
        "higher_secondary_schools": "3", "middle_schools": E, "primary_schools": "10",
        "other_edu_institutions": E, "stadia": E, "cinemas": "1", "auditoria": E,
        "libraries": "PL (2)",
    }, 1)
    rows += parent("3", "Kandhla", ["H (1)", "HC (1)"], ["10", "8"], {
        "higher_secondary_schools": "3", "middle_schools": E, "primary_schools": "2",
        "other_edu_institutions": "3", "stadia": E, "cinemas": "1", "auditoria": E,
    }, 2)
    rows += parent("4", "Khatauli", ["H (2)", "NH (1)"], ["12", E], {
        "degree_colleges": "AS (1)", "higher_secondary_schools": "4", "middle_schools": "3",
        "primary_schools": "15", "cinemas": "2",
    }, 3)
    rows += parent("5", "Miranpur", [E], [E], {
        "higher_secondary_schools": "2", "middle_schools": "1", "primary_schools": "3",
        "other_edu_institutions": "6",
    }, 4)
    rows += parent("6", "Muzaffarnagar", ["H (5)", "TBC (1)", "NH (2)", "FC (1)"], ["246", "14", "34", "6"], {
        "degree_colleges": "AS (1) ASC (1) S (2)", "polytechnics": "1", "vocational_institutes": "Sh. Type (3)",
        "higher_secondary_schools": "13", "middle_schools": "1", "primary_schools": "35",
        "other_edu_institutions": "5", "stadia": "1", "cinemas": "5", "auditoria": "2",
        "libraries": "PL (2)",
    }, 5)
    rows += parent("7", "Shamli", ["H (2)", "FC (1)"], ["34", E], {
        "degree_colleges": "AS (1) S (1)", "higher_secondary_schools": "5", "middle_schools": "3",
        "primary_schools": "26", "other_edu_institutions": "5", "cinemas": "2", "libraries": "PL (2)",
    }, 6)
    for i, row in enumerate(rows):
        row["row_index"] = str(i)
    finish(
        pdf_id,
        rows,
        fields,
        "# Muzaffarnagar MedEdu source-checked output\n\n"
        "The seven printed town parents and Cultural Facilities continuation panel were transcribed from pages 8–9 at 300 DPI. "
        "They expand to 17 child rows; columns 3–4 remain child-scoped and columns 5–17 are inherited only within each parent. "
        "The following Trade, Commerce, Industry, and Banking panels were excluded.\n",
    )


def tehsil():
    pdf_id = "muzaffarnagar_tehsil_1971"
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
    names = ["Kairana", "Muzaffarnagar", "Budhana", "Jansath", "District Total (Rural)"]
    educational = [
        ["173", "227", "36", "39", "4", "5", "1", "1", "1", "1"],
        ["187", "219", "20", "21", "14", "14", E, E, E, E],
        ["130", "178", "25", "29", "8", "9", E, E, E, E],
        ["178", "216", "23", "26", "12", "12", E, E, E, E],
        ["668", "840", "104", "115", "38", "40", "1", "1", "1", "1"],
    ]
    medical = [
        ["8", "8", "2", "2", "6", "6", "2", "2", "3", "3", E, E],
        ["5", "5", "7", "7", "5", "5", E, E, "1", "1", E, E],
        ["8", "9", "6", "6", "5", "5", "3", "3", "1", "1", E, E],
        ["5", "5", "5", "5", "2", "2", E, E, "1", "1", E, E],
        ["26", "27", "20", "20", "18", "18", "5", "5", "6", "6", E, E],
    ]
    water_values = [
        ["96", "178", E, "240", "231", "1", "1", E, E, E, E, E, E, E],
        ["107", "218", E, "275", "223", E, E, E, "2", E, E, E, E, E],
        ["108", "60", E, "144", "142", E, E, E, E, E, E, "2", E, E],
        ["145", "175", E, "238", "230", E, E, "1", E, "1", E, "1", E, E],
        ["456", "631", E, "897", "926", "1", "1", "1", "2", "1", E, "3", E, "1"],
    ]
    communications = [
        ["49", "142", "33", "6", "47", "47", E, E, "4", "4", "2", "2"],
        ["75", "139", "44", "10", "58", "58", "1", "1", "1", "1", "3", "3"],
        ["51", "92", "13", "7", "49", "49", E, E, "2", "2", "5", "5"],
        ["94", "114", "28", "4", "46", "46", E, E, "3", "3", "5", "5"],
        ["269", "487", "118", "27", "200", "200", "1", "1", "10", "10", "15", "15"],
    ]
    rows = []
    for i, name in enumerate(names):
        row = deepcopy(template)
        row.update({
            "sl_no": str(i + 1) if i < 4 else "",
            "tahsil_name": name,
            "row_type": "TOTAL" if i == 4 else "ORDINARY",
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
        "# Muzaffarnagar Tahsil source-checked output\n\n"
        "The four printed tahsil rows and District Total (Rural) were transcribed from pages 122–123 at 300 DPI, "
        "including educational, medical, power/water, and communications panels.\n",
    )


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
