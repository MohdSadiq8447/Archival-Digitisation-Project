import csv, os
from copy import deepcopy
ROOT=r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"; DIST="Etah"
def load(pdf):
 p=os.path.join(ROOT,f"up1971-{pdf}-regex-cleaned-v1","csv",f"{pdf}.csv")
 with open(p,encoding="utf-8-sig",newline="") as f:r=list(csv.DictReader(f));return r,list(r[0])
def clear(r,vs):
 for v in vs:
  if v+"_flag" in r:r[v+"_flag"]=""
 r["requires_review"]="False"
def write(pdf,rows,fields,report):
 folder=pdf.removesuffix("_1971").replace("_","-"); out=os.path.join(ROOT,f"up1971-{folder}-source-checked-v1");os.makedirs(os.path.join(out,"csv"),exist_ok=True)
 with open(os.path.join(out,"csv",f"{pdf}.csv"),"w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 old,_=load(pdf)
 with open(os.path.join(out,"CORRECTION_LOG.csv"),"w",encoding="utf-8",newline="") as f:
  w=csv.writer(f);w.writerow(["row_index","variable","original_value","corrected_value","reason"])
  for i,r in enumerate(rows):
   for v in fields:
    if v.endswith("_flag") or v in {"row_index","parent_row_index","subrow_index","subrow_count","requires_review","extracted_at"}:continue
    if old[i].get(v,"")!=r.get(v,""):w.writerow([i,v,old[i].get(v,""),r.get(v,""),"300-DPI source inspection and OCR cleanup"])
 with open(os.path.join(out,"UNRESOLVED_CELLS.csv"),"w",encoding="utf-8",newline="") as f:csv.writer(f).writerow(["row_index","variable","value","reason"])
 with open(os.path.join(out,"SOURCE_CHECKED_REPORT.md"),"w",encoding="utf-8") as f:f.write(report)
 print(pdf,len(rows))

def civic():
 pdf="etah_civic_1971";old,fields=load(pdf);t=deepcopy(old[0]); vs=["sl_no","town_name","road_length_km","sewerage_drainage_system","water_borne_latrines","service_latrines","other_latrines","night_soil_disposal_method","water_source","water_capacity","fire_service","elec_domestic","elec_industrial","elec_commercial","elec_road_light","elec_other","pucca_road_km","kutcha_road_km"]
 s=[("1","Aliganj","PR (9) KR (2)","PT/OSD","9","1,942","...","B","HP/W","...","...","324","32","167","220","...","9.0","2.0"),("2","Etah","PR (36.5) KR (3)","PT/OSD","2,205","5,600","...","HC","HP/TW/OHT","100,000 Galls.","...","1,308","100","1,000","605","49","36.5","3.0"),("3","Ganj Dundwara","PR (16.8) KR (3.5)","PT/OSD","104","1,900","...","HC","HP/W","...","...","368","33","137","250","...","16.8","3.5"),("4","Jalesar","PR (16) KR (4)","PT/OSD","8","500","...","HC","HP/TW/OHT","5,640 Galls.",".","360","13","113","206","...","16.0","4.0"),("5","Kasganj","PR (17) KR (5)","PT/OSD","8","9,000","...","HC","HP/W/TW/OHT","100,000 Galls.","...","1,823","125","1,127","824","...","17.0","5.0"),("6","Marehra","PR (13.6) KR (5)","OSD","...","2,113","...","B","HP/W","...","...","165","51","150","135","...","13.6","5.0"),("7","Soron","PR (17.2) KR (6)","OSD","...","2,386","...","HC","HP/W","...","...","559","...","29","218","...","17.2","6.0")]
 rows=[]
 for i,x in enumerate(s):r=deepcopy(t);r.update(dict(zip(vs,x)));r.update({"row_type":"ORDINARY","reference_target":"","row_index":str(i),"pdf_id":pdf,"district":DIST});clear(r,vs);rows.append(r)
 write(pdf,rows,fields,"# Etah Civic source-checked output\n\nSource pages 6–7 inspected at 300 DPI. Seven civic towns, road/latrine values, protected-water and electrification continuation fields were transcribed from the printed source.\n")

def mededu():
 pdf="etah_mededu_1971";old,fields=load(pdf);t=deepcopy(old[0]);vs=["hospitals_dispensaries","med_beds","degree_colleges","medical_colleges","engg_colleges","polytechnics","vocational_institutes","higher_secondary_schools","middle_schools","primary_schools","other_edu_institutions","stadia","cinemas","auditoria","libraries"]
 def p(serial,name,ch,beds,inh):
  out=[]
  for j,(c,b) in enumerate(zip(ch,beds)):
   r=deepcopy(t);r.update({"sl_no":serial,"town_name":name,"row_type":"ORDINARY","reference_target":"","parent_row_index":"","subrow_index":str(j),"subrow_count":str(len(ch)),"row_index":"","pdf_id":pdf,"district":DIST});clear(r,["sl_no","town_name"]+vs)
   for v in vs:r[v]=inh.get(v,"")
   r["hospitals_dispensaries"]=c;r["med_beds"]=b;out.append(r)
  return out
 e="..."; rows=[]
 rows+=p("1","Aliganj",["H (2)","NH (1)","FC (1)"],["22","4",e],{"degree_colleges":e,"medical_colleges":e,"engg_colleges":".","polytechnics":".","vocational_institutes":e,"higher_secondary_schools":"1","middle_schools":"2","primary_schools":"3","other_edu_institutions":"2","stadia":e,"cinemas":e,"auditoria":e,"libraries":e})
 rows+=p("2","Etah",["H (5)","TBC (1)","FC (1)"],["166","10",e],{"degree_colleges":"A (1)","medical_colleges":".","engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"8","middle_schools":"3","primary_schools":"20","other_edu_institutions":"4","stadia":"1","cinemas":"1","auditoria":"1","libraries":"PL (1) RR (1)"})
 rows+=p("3","Ganj Dundwara",["H (1)","NH (1)","FC (1)"],["12","1",e],{"degree_colleges":"AS (1)","medical_colleges":".","engg_colleges":"..","polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"3","middle_schools":"4","primary_schools":"11","other_edu_institutions":e,"stadia":e,"cinemas":e,"auditoria":e,"libraries":"PL (1)"})
 rows+=p("4","Jalesar",["H (2)","FC (1)"],["16",e],{"degree_colleges":e,"medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"1","middle_schools":"2","primary_schools":"9","other_edu_institutions":"1","stadia":e,"cinemas":e,"auditoria":e,"libraries":"PL (2)"})
 rows+=p("5","Kasganj",["H (3)","D (1)","NH (1)","FC (1)","TBC (1)"],["115",e,e,e,"12"],{"degree_colleges":"A (1)","medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"5","middle_schools":"3","primary_schools":"18","other_edu_institutions":"1","stadia":e,"cinemas":"2","auditoria":"2","libraries":"PL (1) RR (1)"})
 rows+=p("6","Marehra",["H (1)","FC (1)"],["6",e],{"degree_colleges":e,"medical_colleges":e,"engg_colleges":"..","polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"2","middle_schools":"1","primary_schools":"5","other_edu_institutions":"2","stadia":e,"cinemas":e,"auditoria":e,"libraries":"PL (1)"})
 rows+=p("7","Soron",["D (1)","FC (1)"],["4",e],{"degree_colleges":e,"medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"1","middle_schools":"1","primary_schools":"11","other_edu_institutions":"3","stadia":e,"cinemas":e,"auditoria":e,"libraries":"RR (1)"})
 last=None;pi=-1
 for i,r in enumerate(rows):k=(r["sl_no"],r["town_name"]); pi+=k!=last;last=k;r["parent_row_index"]=str(pi);r["row_index"]=str(i)
 write(pdf,rows,fields,"# Etah MedEdu source-checked output\n\nSource pages 8–9 inspected at 300 DPI. Seven parents and 20 expanded child rows preserve H/D/NH/FC/TBC hierarchy, parent-scoped cultural values, and the printed facility codes.\n")

def tehsil():
 pdf="etah_tehsil_1971";old,fields=load(pdf);t=deepcopy(old[0]); names=["Kasganj","Jalesar","Etah","Aliganj","District Total"]
 edu=["junior_basic_villages","junior_basic_schools","senior_basic_villages","senior_basic_schools","higher_secondary_villages","higher_secondary_schools","college_villages","colleges","other_edu_villages","other_edu_institutions"]
 med=["hospital_villages","hospitals","dispensary_villages","dispensaries","mcw_villages","mcw_centres","health_centre_villages","health_centres","family_planning_villages","family_planning_centres","other_med_villages","other_med_institutions"]
 wat=["power_available_villages","power_not_available_villages","tap_water_villages","hand_pipe_villages","well_villages","tank_villages","river_villages","fountain_villages","canal_villages","water_fall_villages","lake_villages","tube_well_villages","other_water_villages","no_water_villages"]
 rd=["pucca_road_villages","kachcha_road_villages","pucca_kachcha_road_villages","other_road_villages","post_office_villages","post_offices","telegraph_office_villages","telegraph_offices","post_telegraph_villages","post_telegraph_offices","telephone_villages","telephones"]
 E=[ ["209","228","31","35","8","8",".","...","...","..."],["104","118","27","28","3","3",".",".",".","."],["203","241","37","41","11","12","2","2",".","."],["193","204","32","36","5","8","...","...","1","1"],["709","791","127","140","27","31","2","2","1","1"] ]
 M=[["7","7","7","7","3","3","1","1","4","4","...","..."],["...","...","4","4","1","1","1","1","2","2","...","..."],["11","11","4","4","2","2","...","...","4","4","...","..."],["4","4","7","7","2","2","2","2","2","2","...","..."],["22","22","22","22","8","8","4","4","12","12","...","..."]]
 W=[["123","403","...","313","489","...","...","...","...","...","...","...","...","..."],["34","128","...","16","161","...","...","...","...","...","...","15","...","..."],["86","406","...","120","474","...","...","...","4","...","...","15","...","..."],["56","383","...","278","398","8","2","...","2","...","...","21","...","..."],["299","1,320","...","757","1,522","8","2","...","6","...","...","36","...","..."]]
 R=[["110","151","24","68","46","46","...","...","4","4","5","5"],["15","56","9","75","23","23","...","...","2","2","1","1"],["166","102","14","32","68","68","...","...","1","1","...","..."],["34","163","...","56","48","48","...","...","2","2","1","1"],["325","472","56","231","185","185","...","...","9","9","7","7"]]
 rows=[];allv=edu+med+wat+rd
 for i,name in enumerate(names):
  r=deepcopy(t);r.update({"sl_no":str(i+1) if i<4 else "","tahsil_name":name,"row_type":"TOTAL" if i==4 else "ORDINARY","reference_target":"","requires_review":"False","row_index":str(i),"pdf_id":pdf,"district":DIST})
  vals=dict(zip(edu,E[i]))|dict(zip(med,M[i]))|dict(zip(wat,W[i]))|dict(zip(rd,R[i]))
  for v in allv:r[v]=vals.get(v,"")
  clear(r,["sl_no","tahsil_name"]+allv);rows.append(r)
 write(pdf,rows,fields,"# Etah Tahsil source-checked output\n\nSource pages 170–171 inspected at 300 DPI. Kasganj, Jalesar, Etah, Aliganj and District Total retain the printed educational, medical, water/power and communications values.\n")

if __name__=="__main__":civic();mededu();tehsil()
