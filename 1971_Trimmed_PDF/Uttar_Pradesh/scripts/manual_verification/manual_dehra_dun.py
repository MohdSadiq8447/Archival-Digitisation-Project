import csv
import os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DISTRICT = "Dehra Dun"


def load_template(pdf_id):
    src = os.path.join(ROOT, f"up1971-{pdf_id}-regex-cleaned-v1", "csv", f"{pdf_id}.csv")
    with open(src, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
        return rows, list(rows[0])


def write_folder(pdf_id, rows, fields, report):
    folder_id = pdf_id.removesuffix("_1971").replace("_", "-")
    outdir = os.path.join(ROOT, f"up1971-{folder_id}-source-checked-v1")
    os.makedirs(os.path.join(outdir, "csv"), exist_ok=True)
    outcsv = os.path.join(outdir, "csv", f"{pdf_id}.csv")
    with open(outcsv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    old, _ = load_template(pdf_id)
    log = os.path.join(outdir, "CORRECTION_LOG.csv")
    with open(log, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["row_index", "variable", "original_value", "corrected_value", "reason"])
        for i, row in enumerate(rows):
            before = old[i] if i < len(old) else {}
            for var in fields:
                if var.endswith("_flag") or var in {"row_index", "parent_row_index", "subrow_index", "subrow_count", "requires_review", "extracted_at"}:
                    continue
                if before.get(var, "") != row.get(var, ""):
                    writer.writerow([i, var, before.get(var, ""), row.get(var, ""), "300-DPI source inspection; identity/continuation/OCR cleanup"])
    with open(os.path.join(outdir, "UNRESOLVED_CELLS.csv"), "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(outdir, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write(report)
    print(f"wrote {outcsv} rows={len(rows)}")


def clear_flags(row, vars_):
    for var in vars_:
        if var + "_flag" in row:
            row[var + "_flag"] = ""
    row["requires_review"] = "False"


def civic():
    pdf_id = "dehra_dun_civic_1971"
    old, fields = load_template(pdf_id)
    t = deepcopy(old[0])
    data = [
        ("1", "Chakrata Cantt.", "PR (30) KR (0)", "OSD", "", "537", "...", "B/HL", "F/OHT", "25,000 Galls.", "Yes", "...", "...", "...", "...", "...", "30.0", "0.0", "ORDINARY", ""),
        ("2", "Clement Town Cantt.", "PR (24) KR (0)", "ST", "100", "360", "...", "B/MT", "HP", "...", "...", "160", "3", "15", "75", "...", "24.0", "0.0", "ORDINARY", ""),
        ("3", "Dehra Dun", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Dehra Dun City Urban Agglomeration"),
        ("4", "Dehra Dun Cantt.", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Dehra Dun City Urban Agglomeration"),
        ("5", "Forest Research Institute & College Area", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "CROSS_REFERENCE", "Dehra Dun City Urban Agglomeration"),
        ("", "Dehra Dun City Urban Agglomeration", "PR (200) KR (22)", "S/PT/OSD", "4,351", "16,967", "...", "B/MT/HL", "R/C/TW/OHT", "865,182 Galls.", "Yes", "22,039", "554", "5,930", "3,647", "...", "200.0", "22.0", "AGGREGATE", ""),
        ("(i)", "Dehra Dun", "PR (132) KR (19)", "S/PT/OSD", "3,594", "14,453", "...", "MT", "R/C/TW/OHT", "448,182 Galls.", "Yes", "16,589", "549", "5,898", "2,706", "...", "132.0", "19.0", "COMPONENT", ""),
        ("(ii)", "Dehra Dun Cantt.", "PR (50) KR (3)", "S/PT/OSD", "170", "2,373", "...", "B/MT", "R/TW/OHT", "140,000 Galls.", "...", "5,000", "4", "20", "679", "...", "50.0", "3.0", "COMPONENT", ""),
        ("(iii)", "Forest Research Institute & College Area", "PR (18) KR (0)", "S", "587", "141", "...", "B/HL", "R/TW/OHT", "277,000 Galls.", "Yes", "450", "1", "12", "262", "...", "18.0", "0.0", "COMPONENT", ""),
        ("6", "Landour Cantt.", "PR (3) KR (4)", "PT/OSD", "", "70", "...", "B/HL", "F/OHT", "33,525 Galls.", "...", "175", "3", "5", "117", "...", "3.0", "4.0", "ORDINARY", ""),
        ("7", "Mussoorie", "PR (32) KR (72)", "S", "2,300", "3,425", "...", "MT", "F/OHT", "3,791,375 Galls.", "Yes", "3,180", "19", "666", "1,232", "...", "32.0", "72.0", "ORDINARY", ""),
        ("8", "Raipur", "PR (6) KR (0)", "ST", "404", "40", "...", "MT", "C/OHT", "176,000 Galls.", "Yes", "405", "2", "14", "150", "...", "6.0", "0.0", "ORDINARY", ""),
        ("9", "Rishikesh", "PR (22) KR (21)", "S/OSD", "200", "1,800", "...", "MT", "R/OHT", "100,000 Galls.", "Yes", "1,182", "215", "770", "353", "...", "22.0", "21.0", "ORDINARY", ""),
        ("10", "Vikasnagar", "PR (2) KR (8)", "ST/OSD", "...", "500", "...", "...", "TW/OHT", "100,000 Galls.", "...", "354", "29", "200", "144", "...", "2.0", "8.0", "ORDINARY", ""),
    ]
    rows = []
    for idx, vals in enumerate(data):
        r = deepcopy(t)
        (serial, name, road, sewer, wb, service, other, night, source, capacity, fire, domestic, industrial, commercial, road_light, elec_other, pucca, kutcha, rtype, ref) = vals
        r.update({"sl_no": serial, "town_name": name, "road_length_km": road, "sewerage_drainage_system": sewer, "water_borne_latrines": wb, "service_latrines": service, "other_latrines": other, "night_soil_disposal_method": night, "water_source": source, "water_capacity": capacity, "fire_service": fire, "elec_domestic": domestic, "elec_industrial": industrial, "elec_commercial": commercial, "elec_road_light": road_light, "elec_other": elec_other, "pucca_road_km": pucca, "kutcha_road_km": kutcha, "row_type": rtype, "reference_target": ref, "row_index": str(idx), "pdf_id": pdf_id, "district": DISTRICT})
        clear_flags(r, ["sl_no", "town_name", "road_length_km", "sewerage_drainage_system", "water_borne_latrines", "service_latrines", "other_latrines", "night_soil_disposal_method", "water_source", "water_capacity", "fire_service", "elec_domestic", "elec_industrial", "elec_commercial", "elec_road_light", "elec_other", "pucca_road_km", "kutcha_road_km"])
        rows.append(r)
    write_folder(pdf_id, rows, fields, "# Dehra Dun Civic source-checked output\n\nSource pages 10–11 inspected at 300 DPI. Identity rows, Dehra Dun City Urban Agglomeration components, road/latrine values, continuation alignment, and electrification columns were transcribed from the printed table; cross-references remain metadata.\n")


def mededu():
    pdf_id = "dehra_dun_mededu_1971"
    old, fields = load_template(pdf_id)
    t = deepcopy(old[0])
    vars_ = ["hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]

    def parent(serial, name, rtype, ref, children, beds, inherited):
        out = []
        for sub, (child, bed) in enumerate(zip(children, beds)):
            r = deepcopy(t)
            r.update({"sl_no": serial, "town_name": name, "row_type": rtype, "reference_target": ref, "parent_row_index": "", "subrow_index": str(sub), "subrow_count": str(len(children)), "row_index": "", "pdf_id": pdf_id, "district": DISTRICT})
            clear_flags(r, ["sl_no", "town_name"] + vars_)
            for v in vars_:
                r[v] = inherited.get(v, "")
            r["hospitals_dispensaries"] = child
            r["med_beds"] = bed
            out.append(r)
        return out

    e = "..."
    rows = []
    inherited = {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "1", "middle_schools": e, "primary_schools": "2", "other_edu_institutions": e, "stadia": e, "cinemas": e, "auditoria": e, "libraries": "PL (1)"}
    rows += parent("1", "Chakrata Cantt.", "ORDINARY", "", ["H (1)", "FC (1)"], ["18", e], inherited)
    inherited = {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": e, "middle_schools": e, "primary_schools": "1", "other_edu_institutions": "1", "stadia": e, "cinemas": "1", "auditoria": e, "libraries": e}
    rows += parent("2", "Clement Town Cantt.", "ORDINARY", "", ["H (1)"], ["10"], inherited)
    for serial, name in [("3", "Dehra Dun"), ("4", "Dehra Dun Cantt."), ("5", "Forest Research Institute & College Area")]:
        rows += parent(serial, name, "CROSS_REFERENCE", "Dehra Dun City Urban Agglomeration", [""], [""], {})
    inherited = {"degree_colleges": "ASC (4)", "medical_colleges": e, "engg_colleges": e, "polytechnics": "2", "vocational_institutes": "Sh. Type (2)", "higher_secondary_schools": "19", "middle_schools": "9", "primary_schools": "80", "other_edu_institutions": "17", "stadia": e, "cinemas": "9", "auditoria": "1", "libraries": "PL (2) RR (4)"}
    rows += parent("", "Dehra Dun City Urban Agglomeration", "AGGREGATE", "", ["H (9)", "D (3)", "*O (1)", "TBC (1)", "FC (2)"], ["433", e, "30", e, e], inherited)
    inherited = {"degree_colleges": "ASC (4)", "medical_colleges": e, "engg_colleges": e, "polytechnics": "2", "vocational_institutes": "Sh. Type (2)", "higher_secondary_schools": "15", "middle_schools": "7", "primary_schools": "72", "other_edu_institutions": "15", "stadia": e, "cinemas": "9", "auditoria": "1", "libraries": "PL (1) RR (4)"}
    rows += parent("(i)", "Dehra Dun", "COMPONENT", "", ["H (7)", "D (2)", "*O (1)", "TBC (1)", "FC (2)"], ["415", e, "30", e, e], inherited)
    inherited = {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "3", "middle_schools": "2", "primary_schools": "8", "other_edu_institutions": "2", "stadia": e, "cinemas": e, "auditoria": e, "libraries": "PL (1)"}
    rows += parent("(ii)", "Dehra Dun Cantt.", "COMPONENT", "", ["H (1)", "D (1)"], ["10", e], inherited)
    inherited = {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "1", "middle_schools": e, "primary_schools": e, "other_edu_institutions": "2", "stadia": e, "cinemas": e, "auditoria": e, "libraries": e}
    rows += parent("(iii)", "Forest Research Institute & College Area", "COMPONENT", "", ["H (1)"], ["8"], inherited)
    rows += parent("6", "Landour Cantt.", "ORDINARY", "", [e], [e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "1", "middle_schools": e, "primary_schools": "1", "other_edu_institutions": e, "stadia": e, "cinemas": e, "auditoria": e, "libraries": e})
    rows += parent("7", "Mussoorie", "ORDINARY", "", ["H (5)", "D (1)", "HC (1)", "FC (1)"], ["137", e, e, e], {"degree_colleges": "AS (1)", "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "11", "middle_schools": "2", "primary_schools": "21", "other_edu_institutions": "1", "stadia": e, "cinemas": "6", "auditoria": "1", "libraries": "PL (2) RR (2)"})
    rows += parent("8", "Raipur", "ORDINARY", "", ["H (1)", "D (1)", "FC (1)"], ["30", e, e], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "1", "middle_schools": e, "primary_schools": e, "other_edu_institutions": "1", "stadia": e, "cinemas": e, "auditoria": e, "libraries": "RR (2)"})
    rows += parent("9", "Rishikesh", "ORDINARY", "", ["H (3)", "D (2)", "TBC (1)"], ["48", e, e], {"degree_colleges": e, "medical_colleges": "**", "engg_colleges": e, "polytechnics": e, "vocational_institutes": e, "higher_secondary_schools": "2", "middle_schools": "3", "primary_schools": "12", "other_edu_institutions": "1", "stadia": e, "cinemas": "1", "auditoria": e, "libraries": "PL (2) RR (3)"})
    rows += parent("10", "Vikasnagar", "ORDINARY", "", ["D (2)"], ["4"], {"degree_colleges": e, "medical_colleges": e, "engg_colleges": e, "polytechnics": e, "vocational_institutes": "O (1)", "higher_secondary_schools": "1", "middle_schools": "2", "primary_schools": "4", "other_edu_institutions": "5", "stadia": e, "cinemas": "1", "auditoria": e, "libraries": "PL (1)"})
    parent_idx = -1
    last = None
    for i, r in enumerate(rows):
        key = (r["sl_no"], r["town_name"], r["row_type"])
        if key != last:
            parent_idx += 1
            last = key
        r["parent_row_index"] = str(parent_idx)
        r["row_index"] = str(i)
    write_folder(pdf_id, rows, fields, "# Dehra Dun MedEdu source-checked output\n\nSource pages 12–13 inspected at 300 DPI. Ten printed identities plus the Dehra Dun City Urban Agglomeration and its three components are retained; 31 child rows preserve printed H/D/O/TBC/FC codes, parent-scoped columns 5–17, and footnote markers without spill contamination.\n")


def tehsil():
    pdf_id = "dehra_dun_tehsil_1971"
    old, fields = load_template(pdf_id)
    t = deepcopy(old[0])
    vars_ = [v for v in fields if not v.endswith("_flag") and v not in {"sl_no", "tahsil_name", "row_type", "reference_target", "requires_review", "row_index", "pdf_id", "district", "state", "year", "format_id", "table_id", "source_pdf", "source_pdf_sha256", "source_page_start", "source_page_end", "anchor_printed_page", "continuation_printed_page", "metadata_workbook", "metadata_workbook_sha256", "extracted_at"}]
    edu = ["junior_basic_villages", "junior_basic_schools", "senior_basic_villages", "senior_basic_schools", "higher_secondary_villages", "higher_secondary_schools", "college_villages", "colleges", "other_edu_villages", "other_edu_institutions"]
    med = ["hospital_villages", "hospitals", "dispensary_villages", "dispensaries", "mcw_villages", "mcw_centres", "health_centre_villages", "health_centres", "family_planning_villages", "family_planning_centres", "other_med_villages", "other_med_institutions"]
    power_water = ["power_available_villages", "power_not_available_villages", "tap_water_villages", "hand_pipe_villages", "well_villages", "tank_villages", "river_villages", "fountain_villages", "canal_villages", "water_fall_villages", "lake_villages", "tube_well_villages", "other_water_villages", "no_water_villages"]
    roads = ["pucca_road_villages", "kachcha_road_villages", "pucca_kachcha_road_villages", "other_road_villages", "post_office_villages", "post_offices", "telegraph_office_villages", "telegraph_offices", "post_telegraph_villages", "post_telegraph_offices", "telephone_villages", "telephones"]
    rowspec = [
        ("1", "Chakrata", ["130", "132", "16", "16", "...", "...", "...", "...", "...", "..."], ["6", "6", "9", "12", "8", "8", "2", "2", "2", "2", "2", "2"], ["5", "374", "228", "1", "30", "...", "8", "68", "8", "10", "...", "...", "34", "..."], ["23", "351", "5", "...", "27", "27", "...", "...", "4", "4", "5", "5"]),
        ("2", "Dehra Dun", ["181", "227", "27", "29", "12", "14", "...", "...", "...", "..."], ["6", "6", "11", "11", "5", "5", "2", "2", "5", "5", "...", "..."], ["95", "297", "136", "30", "82", "4", "86", "75", "52", "...", "...", "10", "9", "..."], ["31", "214", "95", "24", "37", "37", "...", "...", "7", "7", "9", "9"]),
        ("", "District Total (Rural)", ["311", "359", "43", "45", "12", "14", "...", "...", "...", "..."], ["12", "12", "20", "23", "13", "13", "4", "4", "7", "7", "2", "2"], ["100", "671", "364", "31", "112", "4", "94", "143", "60", "10", "...", "10", "43", "..."], ["54", "565", "100", "24", "64", "64", "...", "...", "11", "11", "14", "14"]),
    ]
    rows = []
    for idx, (serial, name, ev, mv, wv, rv) in enumerate(rowspec):
        r = deepcopy(t)
        r.update({"sl_no": serial, "tahsil_name": name, "row_type": "TOTAL" if "Total" in name else "ORDINARY", "reference_target": "", "requires_review": "False", "row_index": str(idx), "pdf_id": pdf_id, "district": DISTRICT})
        vals = dict(zip(edu, ev)) | dict(zip(med, mv)) | dict(zip(power_water, wv)) | dict(zip(roads, rv))
        for var in vars_:
            r[var] = vals.get(var, "")
        clear_flags(r, ["sl_no", "tahsil_name"] + vars_)
        rows.append(r)
    write_folder(pdf_id, rows, fields, "# Dehra Dun Tahsil source-checked output\n\nSource pages 96–97 inspected at 300 DPI. Chakrata, Dehra Dun, and District Total (Rural) are retained with educational, medical, water, roads, post/telegraph, and telephone continuation columns aligned to the printed rows.\n")


if __name__ == "__main__":
    civic()
    mededu()
    tehsil()
