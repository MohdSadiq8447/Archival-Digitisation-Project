import csv, os, re
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DIST = "Meerut"; e = "..."

def load(pid):
    with open(os.path.join(ROOT, f"up1971-{pid}-regex-cleaned-v1", "csv", f"{pid}.csv"), encoding="utf-8-sig", newline="") as f: rows=list(csv.DictReader(f))
    return rows, list(rows[0])
def clear(r, vs):
    for v in vs:
        if f"{v}_flag" in r: r[f"{v}_flag"]=""
    r["requires_review"]="False"
def finish(pid, rows, fields, report):
    folder=pid.removesuffix("_1971").replace("_","-"); out=os.path.join(ROOT,f"up1971-{folder}-source-checked-v1"); os.makedirs(os.path.join(out,"csv"),exist_ok=True)
    with open(os.path.join(out,"csv",f"{pid}.csv"),"w",encoding="utf-8",newline="") as f: w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    old,_=load(pid)
    with open(os.path.join(out,"CORRECTION_LOG.csv"),"w",encoding="utf-8",newline="") as f:
        w=csv.writer(f);w.writerow(["row_index","variable","original_value","corrected_value","reason"])
        for i,r in enumerate(rows):
            b=old[i] if i<len(old) else {}
            for v in fields:
                if v.endswith("_flag") or v in {"row_index","parent_row_index","subrow_index","subrow_count","requires_review","extracted_at"}: continue
                if b.get(v,"")!=r.get(v,""): w.writerow([i,v,b.get(v,""),r.get(v,""),"300-DPI source inspection; structural/OCR cleanup"])
    with open(os.path.join(out,"UNRESOLVED_CELLS.csv"),"w",encoding="utf-8",newline="") as f: csv.writer(f).writerow(["row_index","variable","value","reason"])
    with open(os.path.join(out,"SOURCE_CHECKED_REPORT.md"),"w",encoding="utf-8") as f:f.write(report)
    print(pid,len(rows))

def civic():
    pid="meerut_civic_1971"; old,fields=load(pid); t=deepcopy(old[0])
    vs=["sl_no","town_name","road_length_km","sewerage_drainage_system","water_borne_latrines","service_latrines","other_latrines","night_soil_disposal_method","water_source","water_capacity","fire_service","elec_domestic","elec_industrial","elec_commercial","elec_road_light","elec_other","pucca_road_km","kutcha_road_km"]
    # Printed Civic rows (page 10) and aligned continuation values (page 11).
    def x(*vals):
        # A few blank cross-reference rows were entered with one extra empty cell.
        if len(vals) == 21:
            vals = vals[:18] + vals[-2:]
        return vals
    d=[
      x("1","Aminagar Sarai","PR (8) KR (6)","PT/OSD","15","699",e,"HL","TW/OHT","20,000 Galls.",e,"405","15","182","150",e,"8.0","6.0"),
      x("2","Baghpat","PR (17) KR (1)","OSD",e,"1,550",e,"B/H","TW/OHT","25,000 Galls.","Yes","1,050","82","250","250",e,"17.0","1.0"),
      x("3","Baraut","PR (26) KR (4)","S/OSD","50","5,000",e,"B/H","TW/OHT","50,000 Galls.","Yes","2,500","125","280","260",e,"26.0","4.0"),
      x("4","Faridnagar","PR (5) KR (2)","PT/OSD","28","21",e,"B/HL","HP",e,e,"150","1","37","21",e,"5.0","2.0"),
      x("5","Garh Mukteshwar","PR (23) KR (16)","OSD",e,"4,000",e,"B","HP",e,e,"402","1","266","268",e,"23.0","16.0"),
      x("6","Ghaziabad","","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Ghaziabad City Urban Agglomeration"),
      x("7","Ghaziabad Rly. Colony","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Ghaziabad City Urban Agglomeration"),
      x("","Ghaziabad City Urban Agglomeration","PR (46) KR (0)","S/PT/OSD","2,250","5,012",e,"MT/HC","TW/OHT","484,055 Galls.","Yes","6,000","660","1,162","2,714",e,"46.0","0.0","AGGREGATE",""),
      x("(i)","Ghaziabad","PR (38) KR (0)","S/PT","2,000","5,000",e,"MT/HC","TW/OHT","300,000 Galls.","Yes","4,000","650","1,062","2,229",e,"38.0","0.0","COMPONENT",""),
      x("(ii)","Ghaziabad Rly. Colony","PR (8) KR (0)","S/PT/OSD","250","12",e,"MT/HC","TW/OHT","184,055 Galls.","Yes","2,000","10","103","485",e,"8.0","0.0","COMPONENT",""),
      x("8","Hapur","PR (59) KR (2)","OSD",e,"4,943",e,"HL/B","TW/OHT","114,000 Galls.","Yes","3,500","221","435","836",e,"59.0","2.0"),
      x("9","Hastinapur","PR (15) KR (5)","PT/OSD","130","500",e,"HC/B","TW/OHT","40,000 Galls.","Yes","2,750","10","100","485",e,"15.0","5.0"),
      x("10","Kaila","PR (0) KR (2)","OSD",e,"500",e,"B/HL","HP",e,e,"250","3","52","21",e,"0.0","2.0"),
      x("11","Kanker Khera","PR (3) KR (2)","PT/OSD","50","1,500",e,"B/HL","HP",e,e,"500","5","75","170",e,"3.0","2.0"),
      x("12","Malyana","","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Meerut City Urban Agglomeration"),
      x("13","Mawana","PR (19) KR (0)","PT/OSD","40","3,819",e,"HC","HP",e,e,"900","15","100","248",e,"19.0","0.0"),
      x("14","Meerut","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Meerut City Urban Agglomeration"),
      x("15","Meerut Cantt.","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Meerut City Urban Agglomeration"),
      x("","Meerut City Urban Agglomeration","PR (223) KR (19)","PT/OSD","2,075","5,350",e,"HL/HC/B/MT","HT/TW","570,000 Galls.","Yes","15,531","1,539","5,745","5,825",e,"223.0","19.0","AGGREGATE",""),
      x("(i)","Malyana","PR (5) KR (0)","OSD",e,"1,350",e,"HL/B","HP",e,e,"401","25","75","52",e,"5.0","0.0","COMPONENT",""),
      x("(ii)","Meerut","PR (195) KR (16)","PT/OSD","1,510","33,313",e,"HC/MT","TW/OHT","300,000 Galls.","Yes","13,630","1,610","5,574","4,073",e,"195.0","16.0","COMPONENT",""),
      x("(iii)","Meerut Cantt.","PR (32) KR (3)","PT/OSD","547","4,000",e,"HC/MT","TW/OHT","450,000 Galls.","Yes","1,500","4","96","1,700",e,"32.0","3.0","COMPONENT",""),
      x("16","Modinagar","PR (32) KR (14)","PT/OSD","2,511","7,340",e,"HC/MT","TW/OHT","40,000 Galls.","Yes","3,184","219","2,268","3,403",e,"32.0","14.0"),
      x("17","Muradnagar","PR (8) KR (2)","OSD",e,"2,100",e,"HC/MT","TW/OHT","35,000 Galls.",e,"424","7","100","94",e,"8.0","2.0"),
      x("18","Ordnance Factory Muradnagar","","","","","","","","","","","","","","","","","ORDINARY",""),
      x("19","Pilkhuwa","PR (16) KR (6)","OSD",e,"2,300",e,"HL/B","TW/OHT","225,000 Galls.",e,"800","100","600","3,501",e,"16.0","6.0"),
      x("20","Rasulpur","PR (5) KR (3)","PT/OSD","25","600",e,"HC","HP",e,e,"200","3","50","105",e,"5.0","3.0"),
      x("21","Sardhana","PR (8) KR (6)","PT/OSD","30","500",e,"HC","TW/OHT","16,000 Galls.",e,"700","5","60","112",e,"8.0","6.0"),
      x("22","Shahjahanpur","PR (2) KR (2)","PT/OSD","350","750",e,"B","HP",e,e,"","","","",e,"2.0","2.0"),
    ]
    rows=[]
    for i,spec in enumerate(d):
        r=deepcopy(t);r.update(dict(zip(vs+["row_type","reference_target"],spec)));r.update({"row_index":str(i),"pdf_id":pid,"district":DIST});clear(r,vs);rows.append(r)
    finish(pid,rows,fields,"# Meerut Civic source-checked output\n\nSource pages 10–11 were inspected at 300 DPI. All printed Civic identities, cross-references, aggregate/component rows, and continuation values were isolated from adjacent sections.\n")

def mededu():
    pid="meerut_mededu_1971"; old,fields=load(pid); template=deepcopy(old[0]); vs=["sl_no","town_name","hospitals_dispensaries","med_beds","degree_colleges","medical_colleges","engg_colleges","polytechnics","vocational_institutes","higher_secondary_schools","middle_schools","primary_schools","other_edu_institutions","stadia","cinemas","auditoria","libraries"]
    groups=[
      ("1","Aminagar Sarai","ORDINARY",["D (2)"],["4"]),("2","Baghpat","ORDINARY",["H (1)","O (1)"],["6","7"]),("3","Baraut","ORDINARY",["H (3)","NH (2)","FC (1)"],["42",e,e]),
      ("4","Faridnagar","ORDINARY",["HC (1)"],["4"]),("5","Garh Mukhteshwar","ORDINARY",["H (1)","FC (1)"],[e,e]),("6","Ghaziabad","CROSS_REFERENCE",[""],[""]),
      ("7","Ghaziabad Rly. Colony","CROSS_REFERENCE",[""],[""]),("","Ghaziabad City Urban Agglomeration","AGGREGATE",["H (4)","D (1)","TBC (1)","FC (2)"],["84",e,"20",e]),
      ("(i)","Ghaziabad","COMPONENT",["H (3)","D (1)","TBC (1)","FC (2)"],["82",e,"20",e]),("(ii)","Ghaziabad Rly. Colony","COMPONENT",["H (1)"],["2"]),
      ("8","Hapur","ORDINARY",["H (3)","D (1)","FC (1)"],["40",e,e]),("9","Hastinapur","ORDINARY",["D (1)","H (1)"],[e,"20"]),("10","Kaila","ORDINARY",[""],[""]),("11","Kanker Khera","ORDINARY",[""],[""]),
      ("12","Malyana","CROSS_REFERENCE",[""],[""]),("13","Mawana","ORDINARY",["H (1)","D (1)"],["6","8"]),("14","Meerut","CROSS_REFERENCE",[""],[""]),("15","Meerut Cantt.","CROSS_REFERENCE",[""],[""]),
      ("","Meerut City Urban Agglomeration","AGGREGATE",["H (8)","D (10)","TBC (2)","O (1)","FC (5)","NH (1)"],["695","14",e,"40",e,e]),
      ("(i)","Malyana","COMPONENT",["D (1)"],[e]),("(ii)","Meerut","COMPONENT",["H (6)","D (8)","TBC (1)","O (1)","FC (4)"],["660","14",e,"40",e]),
      ("(iii)","Meerut Cantt.","COMPONENT",["H (2)","D (1)","TBC (1)","NH (1)","FC (1)"],["35",e,e,e,e]),("16","Modinagar","ORDINARY",["H (2)","D (4)","HC (2)"],["50",e,e]),
      ("17","Muradnagar","ORDINARY",["H (1)","D (1)"],["4",e]),("18","Ordnance Factory Muradnagar","ORDINARY",[""],[""]),("19","Pilkhuwa","ORDINARY",["H (1)","D (1)"],["6",e]),("20","Rasulpur","ORDINARY",[""],[""]),
      ("21","Sardhana","ORDINARY",["H (1)","HC (1)","D (1)","FC (1)"],["10","4",e,e]),("22","Shahjahanpur","ORDINARY",[""],[""])]
    # Inherited columns are taken once from each source parent row; contamination-like prose is discarded.
    rows=[]; pos=0
    for pidx,(serial,name,typ,children,beds) in enumerate(groups):
        inherited={}
        if pos<len(old):
            for v in vs[4:]: inherited[v]=old[pos].get(v,"")
        if typ=="CROSS_REFERENCE": inherited={}
        for v,val in list(inherited.items()):
            if any(z in val for z in ["|","Expected-Value","Information not Available","See "]): inherited[v]=""
        for j,(child,bed) in enumerate(zip(children,beds)):
            r=deepcopy(template);r.update({"sl_no":serial,"town_name":name,"row_type":typ,"reference_target":"Meerut City Urban Agglomeration" if typ=="CROSS_REFERENCE" else "","parent_row_index":str(pidx),"subrow_index":str(j),"subrow_count":str(len(children)),"row_index":"","pdf_id":pid,"district":DIST});clear(r,vs)
            for v in vs: r[v]=inherited.get(v,"")
            r.update({"sl_no":serial,"town_name":name,"hospitals_dispensaries":child,"med_beds":bed});rows.append(r)
        pos+=len(children)
    if pos!=len(old): raise RuntimeError(f"Meerut MedEdu source group count {pos} != input {len(old)}")
    # Source continuation panel values for the Meerut aggregate/components are
    # explicitly set because the automatic row projection interleaves these
    # long multiline groups.
    overrides = {
        18: {"degree_colleges":"A (6) S (3) C (1)","medical_colleges":"1","engg_colleges":e,"polytechnics":"4","vocational_institutes":"Sh. Type (7) O (6)","higher_secondary_schools":"20","middle_schools":"23","primary_schools":"116","other_edu_institutions":"3","stadia":"1","cinemas":"13","auditoria":"1","libraries":"PL (4) RR (1)"},
        19: {"degree_colleges":e,"medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"1","middle_schools":"2","primary_schools":"3","other_edu_institutions":"6","stadia":e,"cinemas":e,"auditoria":e,"libraries":e},
        20: {"degree_colleges":"A (6) S (3) C (1)","medical_colleges":"1","engg_colleges":e,"polytechnics":"1","vocational_institutes":"Sh. Type (4) O (6)","higher_secondary_schools":"12","middle_schools":"20","primary_schools":"109","other_edu_institutions":e,"stadia":"1","cinemas":"7","auditoria":"1","libraries":"PL (2)"},
        21: {"degree_colleges":e,"medical_colleges":e,"engg_colleges":e,"polytechnics":"3","vocational_institutes":"Sh. Type (3)","higher_secondary_schools":"7","middle_schools":"1","primary_schools":"4","other_edu_institutions":"3","stadia":e,"cinemas":"6","auditoria":e,"libraries":"PL (2) RR (1)"},
    }
    for r in rows:
        pidx=int(r["parent_row_index"])
        if pidx in overrides: r.update(overrides[pidx])
    for i,r in enumerate(rows):r["row_index"]=str(i)
    finish(pid,rows,fields,"# Meerut MedEdu source-checked output\n\nSource pages 12–13 were inspected at 300 DPI. All 29 logical parents, including cross-references, aggregates, components, and the information-not-available row, retain contiguous child hierarchy; columns 5–17 are inherited at parent scope.\n")

def tehsil():
    pid="meerut_tehsil_1971"; old,fields=load(pid);t=deepcopy(old[0]); edu=["junior_basic_villages","junior_basic_schools","senior_basic_villages","senior_basic_schools","higher_secondary_villages","higher_secondary_schools","college_villages","colleges","other_edu_villages","other_edu_institutions"];med=["hospital_villages","hospitals","dispensary_villages","dispensaries","mcw_villages","mcw_centres","health_centre_villages","health_centres","family_planning_villages","family_planning_centres","other_med_villages","other_med_institutions"];water=["power_available_villages","power_not_available_villages","tap_water_villages","hand_pipe_villages","well_villages","tank_villages","river_villages","fountain_villages","canal_villages","water_fall_villages","lake_villages","tube_well_villages","other_water_villages","no_water_villages"];comm=["pucca_road_villages","kachcha_road_villages","pucca_kachcha_road_villages","other_road_villages","post_office_villages","post_offices","telegraph_office_villages","telegraph_offices","post_telegraph_villages","post_telegraph_offices","telephone_villages","telephones"]; allv=edu+med+water+comm
    E=[["191","250","23","25","20","20",e,e,e,e],["205","238","16","17","14","14",e,e,e,e],["186","196","18","19","17","19",e,e,e,e],["167","188","10","11","14","14",e,e,e,e],["169","205","24","26","5","5",e,e,e,e],["181","200","21","23","7","7",e,e,e,e],["1,081","1,307","114","120","77","80","2","2",e,e]]
    M=[["5","6","3","3",e,e,"1","1","1","1",e,e],["5","5","4","4","3","3","1","1","1","1",e,e],["7","7","3","3",e,e,e,e,e,e,e,e],["9","9","4","4","1","1","1","1",e,e,e,e],["2","2","2","2",e,e,e,e,"1","1",e,e],["5","5","4","4",e,e,e,e,e,e,e,e],["34","34","22","20","4","4","5","3","3","3",e,e]]
    W=[["123","131",e,"214","215",e,"2",e,e,e,e,e,e,e],["113","219",e,"293","295",e,e,e,e,e,e,"3",e,e],["134","72",e,"194","185",e,e,e,e,e,e,e,e,e],["142","87",e,"41","215",e,e,e,e,e,e,e,e,e],["90","216",e,"252","208",e,e,e,e,e,e,e,e,e],["174","158",e,"292","290",e,"2",e,e,e,e,e,e,e],["776","883",e,"1,460","1,448",e,"5",e,e,e,e,"4",e,e]]
    R=[["54","59","22","36","68","68",e,e,"4","4","3","3"],["89","53","4","22","65","65",e,e,e,e,"2","2"],["73","103","6","10","69","69",e,e,"1","1","1","1"],["116","70","6","20","41","41",e,e,"3","3","2","2"],["111","92","8",e,"36","36",e,e,"1","1","3","3"],["89","166","14","18","62","62",e,e,"1","1","1","1"],["529","543","60","106","332","332",e,e,"10","10","12","12"]]
    names=["Baghpat","Ghaziabad","Sardhana","Meerut","Mawana","Hapur","District Total"];rows=[]
    for i,n in enumerate(names):
        r=deepcopy(t);r.update({"sl_no":str(i+1) if i<6 else "","tahsil_name":n,"row_type":"TOTAL" if i==6 else "ORDINARY","reference_target":"","row_index":str(i),"pdf_id":pid,"district":DIST});r.update(dict(zip(edu,E[i])));r.update(dict(zip(med,M[i])));r.update(dict(zip(water,W[i])));r.update(dict(zip(comm,R[i])));clear(r,["sl_no","tahsil_name"]+allv);rows.append(r)
    finish(pid,rows,fields,"# Meerut Tahsil source-checked output\n\nSource pages 194–195 were inspected at 300 DPI. Six tahsils and the printed District Total retain aligned educational, medical, water/power, and communication values.\n")

if __name__=="__main__": civic(); mededu(); tehsil()
