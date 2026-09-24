import csv, os
from copy import deepcopy

ROOT = r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"
DISTRICT = "Deoria"

def load(pdf):
    p=os.path.join(ROOT,f"up1971-{pdf}-regex-cleaned-v1","csv",f"{pdf}.csv")
    with open(p,encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f)); return rows,list(rows[0])

def flags(r,vs):
    for v in vs:
        if v+"_flag" in r:r[v+"_flag"]=""
    r["requires_review"]="False"

def finish(pdf,rows,fields,report):
    folder=pdf.removesuffix("_1971").replace("_","-")
    out=os.path.join(ROOT,f"up1971-{folder}-source-checked-v1"); os.makedirs(os.path.join(out,"csv"),exist_ok=True)
    path=os.path.join(out,"csv",f"{pdf}.csv")
    with open(path,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    old,_=load(pdf)
    with open(os.path.join(out,"CORRECTION_LOG.csv"),"w",encoding="utf-8",newline="") as f:
        w=csv.writer(f);w.writerow(["row_index","variable","original_value","corrected_value","reason"])
        for i,r in enumerate(rows):
            for v in fields:
                if v.endswith("_flag") or v in {"row_index","parent_row_index","subrow_index","subrow_count","requires_review","extracted_at"}:continue
                if old[i].get(v,"")!=r.get(v,""):w.writerow([i,v,old[i].get(v,""),r.get(v,""),"300-DPI source inspection; structural and transcription cleanup"])
    with open(os.path.join(out,"UNRESOLVED_CELLS.csv"),"w",encoding="utf-8",newline="") as f:csv.writer(f).writerow(["row_index","variable","value","reason"])
    with open(os.path.join(out,"SOURCE_CHECKED_REPORT.md"),"w",encoding="utf-8") as f:f.write(report)
    print(path,len(rows))

def civic():
    pdf="deoria_civic_1971"; old,fields=load(pdf); t=deepcopy(old[0])
    # serial, name, road, sewerage, water-borne, service, other, night, source, capacity, fire, domestic, industrial, commercial, road-light, other-electric, pucca, kutcha, type, ref
    specs=[
      ("1","Deoria","PR (35) KR (6)","ST/OSD","360","7,500","...","B/C","TW/OHT","50,000 Gallons","...","2,120","160","635","507","...","35.0","6.0","ORDINARY",""),
      ("2","Gaura Barhaj","PR (2) KR (8)","ST/OSD","50","450","2","B","TW/OHT","40,000 Gallons","...","306","21","47","122","...","2.0","8.0","ORDINARY",""),
      ("3","Padrauna","PR (15) KR (3)","ST/OSD","150","1,850","...","B/HL","TW/OHT","25,000 Gallons","...","718","39","26","224","...","15.0","3.0","ORDINARY",""),
      ("4","Siwarhi","PR (2) KR (8)","ST/OSD","35","750","...","B","W/HP","...","...","515","27","210","63","...","2.0","8.0","ORDINARY",""),]
    vars=["sl_no","town_name","road_length_km","sewerage_drainage_system","water_borne_latrines","service_latrines","other_latrines","night_soil_disposal_method","water_source","water_capacity","fire_service","elec_domestic","elec_industrial","elec_commercial","elec_road_light","elec_other","pucca_road_km","kutcha_road_km"]
    rows=[]
    for i,s in enumerate(specs):
        r=deepcopy(t);r.update(dict(zip(vars,s[:-2])));r.update({"row_type":s[-2],"reference_target":s[-1],"row_index":str(i),"pdf_id":pdf,"district":DISTRICT});flags(r,vars);rows.append(r)
    finish(pdf,rows,fields,"# Deoria Civic source-checked output\n\nSource pages 6–7 inspected at 300 DPI. Four printed towns and all civic/continuation columns were transcribed from the source; placeholders remain distinct and no following section text is included.\n")

def mededu():
    pdf="deoria_mededu_1971";old,fields=load(pdf);t=deepcopy(old[0])
    dvs=["hospitals_dispensaries","med_beds","degree_colleges","medical_colleges","engg_colleges","polytechnics","vocational_institutes","higher_secondary_schools","middle_schools","primary_schools","other_edu_institutions","stadia","cinemas","auditoria","libraries"]
    def parent(serial,name,typ,ref,children,beds,inh):
        out=[]
        for j,(c,b) in enumerate(zip(children,beds)):
            r=deepcopy(t);r.update({"sl_no":serial,"town_name":name,"row_type":typ,"reference_target":ref,"parent_row_index":"","subrow_index":str(j),"subrow_count":str(len(children)),"row_index":"","pdf_id":pdf,"district":DISTRICT})
            flags(r,["sl_no","town_name"]+dvs)
            for v in dvs:r[v]=inh.get(v,"")
            r["hospitals_dispensaries"]=c;r["med_beds"]=b;out.append(r)
        return out
    e="...";rows=[]
    rows+=parent("1","Deoria","ORDINARY","",["H (5)","D (2)","TBC (1)","FC (2)","*O (3)"],["220",e,e,e,e],{"degree_colleges":"ASC (1) A (1)","medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":"Sh. Type (2) O (2)","higher_secondary_schools":"9","middle_schools":"7","primary_schools":"26","other_edu_institutions":"6","stadia":e,"cinemas":"2","auditoria":e,"libraries":"PL (3) PR (1)"})
    rows+=parent("2","Gaura Barhaj","ORDINARY","",["H (1)","D (1)","FC (1)","*O (1)"],["8",e,e,e],{"degree_colleges":e,"medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"3","middle_schools":"4","primary_schools":"12","other_edu_institutions":"4","stadia":".","cinemas":e,"auditoria":e,"libraries":"PL (2)"})
    rows+=parent("3","Padrauna","ORDINARY","",["H (2)","TBC (1)","*O (1)","FC (1)"],["49",e,e,e],{"degree_colleges":"ASC (1)","medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":"Sh. Type (1) O (1)","higher_secondary_schools":"3","middle_schools":"7","primary_schools":"12","other_edu_institutions":"2","stadia":e,"cinemas":"2","auditoria":e,"libraries":"PL (1)"})
    rows+=parent("4","Siwarhi","ORDINARY","",[e],[e],{"degree_colleges":e,"medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"1","middle_schools":e,"primary_schools":"3","other_edu_institutions":e,"stadia":e,"cinemas":e,"auditoria":e,"libraries":"PL (1)"})
    p=-1;last=None
    for i,r in enumerate(rows):
        k=(r["sl_no"],r["town_name"],r["row_type"])
        if k!=last:p+=1;last=k
        r["parent_row_index"]=str(p);r["row_index"]=str(i)
    finish(pdf,rows,fields,"# Deoria MedEdu source-checked output\n\nSource pages 6–7 inspected at 300 DPI. Four parents and 14 expanded child rows preserve H/D/TBC/FC/*O hierarchy, parent-scoped educational/cultural values, printed ellipses, and the maternity-centre marker.\n")

def tehsil():
    pdf="deoria_tehsil_1971";old,fields=load(pdf);t=deepcopy(old[0])
    edu=["junior_basic_villages","junior_basic_schools","senior_basic_villages","senior_basic_schools","higher_secondary_villages","higher_secondary_schools","college_villages","colleges","other_edu_villages","other_edu_institutions"]
    med=["hospital_villages","hospitals","dispensary_villages","dispensaries","mcw_villages","mcw_centres","health_centre_villages","health_centres","family_planning_villages","family_planning_centres","other_med_villages","other_med_institutions"]
    water=["power_available_villages","power_not_available_villages","tap_water_villages","hand_pipe_villages","well_villages","tank_villages","river_villages","fountain_villages","canal_villages","water_fall_villages","lake_villages","tube_well_villages","other_water_villages","no_water_villages"]
    roads=["pucca_road_villages","kachcha_road_villages","pucca_kachcha_road_villages","other_road_villages","post_office_villages","post_offices","telegraph_office_villages","telegraph_offices","post_telegraph_villages","post_telegraph_offices","telephone_villages","telephones"]
    # arrays are educational, medical, water/power, roads; source pages 364–365
    specs=[
      ("1","Hata",["273","277","38","38","10","10","4","4","2", "..."],["4","4","9","9","...","...","3","3","...","...","...","..."],["155","565","...","483","679","1","53","...","...","...","29","...","...","..."],["104","482","36","52","60","60","...","...","5","5","1","1"]),
      ("2","Padrauna",["321","323","40","40","9","9","2","2","...","..."],["6","6","4","4","...","...","3","3","3","3","...","..."],["141","761","...","302","842","...","...","...","...","...","12","...","...","..."],["106","632","6","15","45","45","...","...","1","1","...","..."] ),
      ("3","Deoria",["329","332","51","51","16","16","2","2","...","..."],["8","8","8","8","1","1","...","1","1","...","...","..."],["367","588","...","538","915","...","...","...","...","...","...","...","...","..."],["326","581","4","3","55","55","...","...","1","1","...","..."] ),
      ("4","Salempur",["314","321","59","60","22","22","4","4","1","..."],["4","4","2","2","1","1","1","1","...","...","...","..."],["104","1,126","...","210","1,096","3","...","...","...","...","...","...","...","..."],["184","817","...","30","80","80","...","...","...","...","...","..."] ),
      ("","District Total (Rural)",["1,237","1,253","188","189","57","57","12","12","3","..."],["22","22","23","23","2","2","4","4","7","7","...","..."],["767","3,040","...","1,533","3,532","4","53","...","...","...","41","...","...","..."],["720","2,512","46","100","240","240","...","...","7","7","1","1"]),
    ]
    rows=[]
    for i,(serial,name,ev,mv,wv,rv) in enumerate(specs):
        r=deepcopy(t);r.update({"sl_no":serial,"tahsil_name":name,"row_type":"TOTAL" if "Total" in name else "ORDINARY","reference_target":"","requires_review":"False","row_index":str(i),"pdf_id":pdf,"district":DISTRICT})
        vals=dict(zip(edu,ev))|dict(zip(med,mv))|dict(zip(water,wv))|dict(zip(roads,rv))
        allv=edu+med+water+roads
        for v in allv:r[v]=vals.get(v,"")
        flags(r,["sl_no","tahsil_name"]+allv);rows.append(r)
    finish(pdf,rows,fields,"# Deoria Tahsil source-checked output\n\nSource pages 364–365 inspected at 300 DPI. Hata, Padrauna, Deoria, Salempur, and District Total (Rural) retain the printed educational, medical, power/water, roads, post/telegraph, and telephone values.\n")

if __name__=="__main__":civic();mededu();tehsil()
