import csv, os
from copy import deepcopy

ROOT = r"E:\\Archival-Digitisation-Project\\1971_Trimmed_PDF\\Uttar_Pradesh\\outputs\\postprocessed"
DIST = "Jaunpur"

def load(pdf):
    p = os.path.join(ROOT, f"up1971-{pdf}-regex-cleaned-v1", "csv", f"{pdf}.csv")
    with open(p, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f); return list(r), list(r.fieldnames or [])

def clear(r):
    for k in r:
        if k.endswith("_flag"): r[k] = ""
    r["requires_review"] = "False"

def finish(pdf, rows, fields, report):
    slug = pdf.removesuffix("_1971").replace("_", "-")
    out = os.path.join(ROOT, f"up1971-{slug}-source-checked-v1"); os.makedirs(os.path.join(out, "csv"), exist_ok=True)
    with open(os.path.join(out, "csv", f"{pdf}.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    old, _ = load(pdf)
    with open(os.path.join(out, "CORRECTION_LOG.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["row_index", "variable", "original_value", "corrected_value", "reason"])
        for i, row in enumerate(rows):
            before = old[i] if i < len(old) else {}
            for var in fields:
                if var.endswith("_flag") or var in {"row_index", "parent_row_index", "subrow_index", "subrow_count", "requires_review", "extracted_at"}: continue
                if before.get(var, "") != row.get(var, ""):
                    w.writerow([i, var, before.get(var, ""), row.get(var, ""), "300-DPI source inspection and hierarchy/continuation cleanup"])
    with open(os.path.join(out, "UNRESOLVED_CELLS.csv"), "w", encoding="utf-8", newline="") as f: csv.writer(f).writerow(["row_index", "variable", "value", "reason"])
    with open(os.path.join(out, "SOURCE_CHECKED_REPORT.md"), "w", encoding="utf-8") as f: f.write(report)
    print(pdf, len(rows))

def civic():
    pdf="jaunpur_civic_1971"; old, fields=load(pdf); t=deepcopy(old[0])
    vs=["sl_no","town_name","road_length_km","sewerage_drainage_system","water_borne_latrines","service_latrines","other_latrines","night_soil_disposal_method","water_source","water_capacity","fire_service","elec_domestic","elec_industrial","elec_commercial","elec_road_light","elec_other","pucca_road_km","kutcha_road_km"]
    vals=[
        ("1","Jaunpur","PR (35) KR (59)","PT/OSD","60","2,125","...","HC","TW/OHT","540,000 Galls.","Yes","3,219","238","1,745","1,018","...","35.0","59.0"),
        ("2","Kerakat","PR (4) KR (0)","OSD","...","120","...","B","TW/OHT","20,000 Galls.","...","300","17","20","32","...","4.0","0.0"),
        ("3","Machhli shahr","PR (2) KR (0)","OSD","-","935","...","B","HP","...","...","242","19","...","20","...","2.0","0.0"),
        ("4","Mariahu","PR (2) KR (2)","OSD","...","141","...","B","TW/OHT","5,000 Galls.","...","295","21","...","15","...","2.0","2.0"),
        ("5","Mongra Badshahpur","PR (8) KR (10)","PT/OSD","250","250","...","B","TW/OHT","20,000 Galls.","...","335","31","26","112","...","8.0","10.0"),
        ("6","Shahganj","PR (6) KR (1)","PT/OSD","9","551","...","B","HP","...","...","838","57","...","156","...","6.0","1.0"),
    ]
    rows=[]
    for i,v in enumerate(vals):
        r=deepcopy(t); r.update(dict(zip(vs,v))); r.update({"row_type":"ORDINARY","reference_target":"","row_index":str(i),"pdf_id":pdf,"district":DIST}); clear(r); rows.append(r)
    finish(pdf,rows,fields,"# Jaunpur Civic source-checked output\n\nSix Civic town rows were transcribed from printed pages 6–7. The unrelated municipal-finance/ expenditure panels were excluded and civic continuation values aligned by town.\n")

def mededu():
    pdf="jaunpur_mededu_1971"; old, fields=load(pdf); t=deepcopy(old[0]); e="..."
    vs=["hospitals_dispensaries","med_beds","degree_colleges","medical_colleges","engg_colleges","polytechnics","vocational_institutes","higher_secondary_schools","middle_schools","primary_schools","other_edu_institutions","stadia","cinemas","auditoria","libraries"]
    def parent(serial,town,children,beds,inh,pidx):
        out=[]
        for s,(child,bed) in enumerate(zip(children,beds)):
            r=deepcopy(t); r.update({"sl_no":serial,"town_name":town,"row_type":"ORDINARY","reference_target":"","parent_row_index":str(pidx),"subrow_index":str(s),"subrow_count":str(len(children)),"row_index":"","pdf_id":pdf,"district":DIST})
            for v in vs: r[v]=inh.get(v,"")
            r["hospitals_dispensaries"]=child; r["med_beds"]=bed; clear(r); out.append(r)
        return out
    blank={v:"" for v in vs[7:]}
    rows=[]
    rows+=parent("1","Jaunpur",["H (6)","D (1)","FC (1)","TBC (1)"],["223",e,e,e],dict(blank,degree_colleges="AC (1) AS (1)",medical_colleges=e,engg_colleges=e,polytechnics=e,vocational_institutes="Sh. Type (2)"),0)
    rows+=parent("2","Kerakat",[e],[e],dict(blank,degree_colleges=e,medical_colleges=e,engg_colleges=e,polytechnics=e,vocational_institutes=e),1)
    rows+=parent("3","Machhli shahr",["HC (1)","FC (1)"],["12",e],dict(blank,degree_colleges=e,medical_colleges=e,engg_colleges=e,polytechnics=e,vocational_institutes=e),2)
    rows+=parent("4","Mariahu",["H (1)","FC (1)"],["10",e],dict(blank,degree_colleges="A (1)",medical_colleges=e,engg_colleges=e,polytechnics=e,vocational_institutes=e),3)
    rows+=parent("5","Mongra Badshahpur",["HC (1)","FC (1)"],["6",e],dict(blank,degree_colleges=e,medical_colleges=e,engg_colleges=e,polytechnics=e,vocational_institutes=e),4)
    rows+=parent("6","Shahganj",["H (2)","FC (1)"],["22",e],dict(blank,degree_colleges=e,medical_colleges=e,engg_colleges=e,polytechnics=e,vocational_institutes=e),5)
    for i,r in enumerate(rows): r["row_index"]=str(i)
    finish(pdf,rows,fields,"# Jaunpur MedEdu source-checked output\n\nSix parent towns and twelve expanded child rows preserve the medical hierarchy from printed page 8. Columns 5–9 are parent-scoped; the source has no continuation values for columns 10–17, so those fields remain blank rather than inheriting contamination from the following Trade, Commerce, Industry statement.\n")

def tehsil():
    pdf="jaunpur_tehsil_1971"; old, fields=load(pdf); t=deepcopy(old[0])
    edu=["junior_basic_villages","junior_basic_schools","senior_basic_villages","senior_basic_schools","higher_secondary_villages","higher_secondary_schools","college_villages","colleges","other_edu_villages","other_edu_institutions"]
    med=["hospital_villages","hospitals","dispensary_villages","dispensaries","mcw_villages","mcw_centres","health_centre_villages","health_centres","family_planning_villages","family_planning_centres","other_med_villages","other_med_institutions"]
    wat=["power_available_villages","power_not_available_villages","tap_water_villages","hand_pipe_villages","well_villages","tank_villages","river_villages","fountain_villages","canal_villages","water_fall_villages","lake_villages","tube_well_villages","other_water_villages","no_water_villages"]
    roads=["pucca_road_villages","kachcha_road_villages","pucca_kachcha_road_villages","other_road_villages","post_office_villages","post_offices","telegraph_office_villages","telegraph_offices","post_telegraph_villages","post_telegraph_offices","telephone_villages","telephones"]
    specs=[
      ("1","Shahganj",["178","191","38","39","11","11","2","2","2","2"],["10","10","2","2","5","5","3","3","3","3","...","..."],["148","592","...","302","686","...","3","...","13","...","...","4","...","..."],["208","225","8","100","46","46","...","...","5","5","2","2"]),
      ("2","Machhli shahr",["171","173","28","28","7","8","...","...","5","5"],["3","3","8","8","...","...","...","...","4","4","...","..."],["41","612","...","...","638","...","...","...","...","...","...","...","...","..."],["116","145","6","32","27","27","...","...","4","4","...","..."]),
      ("3","Jaunpur",["170","172","33","33","7","7","...","...","3","3"],["7","7","...","...","...","...","...","...","...","...","...","..."],["168","637","...","...","751","...","...","...","...","...","...","...","...","..."],["199","529","...","87","48","48","...","...","...","...","...","..."]),
      ("4","Mariahu",["179","187","29","30","16","16","...","...","...","..."],["5","5","6","6","...","...","...","...","2","2","...","..."],["114","610","...","257","688","...","2","...","...","...","...","...","...","..."],["98","519","5","107","42","42","...","...","...","...","...","..."]),
      ("5","Kerakat",["175","175","41","41","7","7","...","...","...","..."],["3","3","9","9","1","1","1","1","1","1","...","..."],["203","277","...","32","471","...","19","...","3","...","...","...","...","..."],["49","132","7","130","49","49","...","...","2","2","...","..."]),
      ("","District Total (Rural)",["873","898","169","171","48","49","2","2","10","10"],["28","28","25","25","6","6","4","4","6","6","...","..."],["674","2,728","...","591","3,234","...","24","...","16","...","...","4","...","..."],["670","1,550","26","456","212","212","...","...","11","11","2","2"]),
    ]
    rows=[]
    for i,(serial,name,e,m,w,rd) in enumerate(specs):
        r=deepcopy(t); r.update({"sl_no":serial,"tahsil_name":name,"row_type":"TOTAL" if i==5 else "ORDINARY","reference_target":"","row_index":str(i),"pdf_id":pdf,"district":DIST})
        for v,x in zip(edu,e): r[v]=x
        for v,x in zip(med,m): r[v]=x
        for v,x in zip(wat,w): r[v]=x
        for v,x in zip(roads,rd): r[v]=x
        clear(r); rows.append(r)
    finish(pdf,rows,fields,"# Jaunpur Tahsil source-checked output\n\nFive Tahsil rows and District Total (Rural) were transcribed from printed pages 334–335. Education, water, medical, and communications bands were aligned by the printed identity order.\n")

if __name__ == "__main__": civic(); mededu(); tehsil()
