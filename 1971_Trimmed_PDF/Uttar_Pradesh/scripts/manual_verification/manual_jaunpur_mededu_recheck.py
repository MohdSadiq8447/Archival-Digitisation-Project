import csv
import os
from copy import deepcopy


ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
PDF_ID = "jaunpur_mededu_1971"
OUT = os.path.join(ROOT, "up1971-jaunpur-mededu-source-checked-v1")
CSV_PATH = os.path.join(OUT, "csv", f"{PDF_ID}.csv")
E = "..."


def main():
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        old = list(csv.DictReader(f))
    fields = list(old[0])
    inherited = [
        {"degree_colleges": "AC (1) AS (1)", "medical_colleges": E, "engg_colleges": E, "polytechnics": E, "vocational_institutes": "Sh. Type (2)", "higher_secondary_schools": "6", "middle_schools": "6", "primary_schools": "36", "other_edu_institutions": E, "stadia": E, "cinemas": "3", "auditoria": "2", "libraries": "PL (2)"},
        {"higher_secondary_schools": "1", "middle_schools": "1", "primary_schools": "1", "other_edu_institutions": E, "stadia": E, "cinemas": E, "auditoria": E, "libraries": E},
        {"higher_secondary_schools": "1", "middle_schools": "1", "primary_schools": "2", "other_edu_institutions": E, "stadia": E, "cinemas": E, "auditoria": E, "libraries": E},
        {"higher_secondary_schools": "3", "middle_schools": "2", "primary_schools": "4", "other_edu_institutions": E, "stadia": E, "cinemas": E, "auditoria": E, "libraries": E},
        {"higher_secondary_schools": "2", "middle_schools": E, "primary_schools": "2", "other_edu_institutions": E, "stadia": E, "cinemas": E, "auditoria": E, "libraries": "PL (2)"},
        {"higher_secondary_schools": "1", "middle_schools": "2", "primary_schools": "3", "other_edu_institutions": "1", "stadia": E, "cinemas": "2", "auditoria": E, "libraries": "PL (1)"},
    ]
    names = ["Jaunpur", "Kerakat", "Machhlishahr", "Mariahu", "Mongra Badshahpur", "Shahganj"]
    variables = ["sl_no", "town_name", "hospitals_dispensaries", "med_beds", "degree_colleges", "medical_colleges", "engg_colleges", "polytechnics", "vocational_institutes", "higher_secondary_schools", "middle_schools", "primary_schools", "other_edu_institutions", "stadia", "cinemas", "auditoria", "libraries"]
    rows = []
    for row in old:
        row = deepcopy(row)
        parent = int(row["parent_row_index"])
        row["town_name"] = names[parent]
        for var in inherited[parent]:
            row[var] = inherited[parent][var]
        for var in variables:
            flag = f"{var}_flag"
            if flag in row:
                row[flag] = ""
        row["requires_review"] = "False"
        rows.append(row)
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with open(os.path.join(OUT, "CORRECTION_LOG.csv"), "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["row_index", "variable", "original_value", "corrected_value", "reason"])
        for before, after in zip(old, rows):
            for var in fields:
                if var.endswith("_flag") or var in {"row_index", "parent_row_index", "subrow_index", "subrow_count", "requires_review", "extracted_at"}:
                    continue
                if before.get(var, "") != after.get(var, ""):
                    writer.writerow([after["row_index"], var, before.get(var, ""), after.get(var, ""), "300-DPI source recheck; page-2 Cultural Facilities continuation aligned one line per printed parent"])
    with open(os.path.join(OUT, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(OUT, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f:
        f.write("# Jaunpur MedEdu source-checked output\n\nRechecked against both printed pages at 300 DPI. The page-2 Cultural Facilities continuation is aligned one line per parent and propagated consistently to each child. The printed identity is `Machhlishahr`; the continuation values, including Jaunpur `6 / 6 / 36`, Mariahu `3 / 2 / 4`, Mongra Badshahpur `PL (2)`, and Shahganj `1 / 2 / 3 / 1 / 2 / PL (1)`, are preserved. No Trade, Commerce, Industry, or Banking content is included.\n")
    print(PDF_ID, len(rows))


if __name__ == "__main__":
    main()
