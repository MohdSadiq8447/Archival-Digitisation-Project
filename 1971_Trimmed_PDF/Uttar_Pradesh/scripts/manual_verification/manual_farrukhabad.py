import csv,os
from copy import deepcopy
ROOT=r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed";DIST="Farrukhabad"
def load(p):
 q=os.path.join(ROOT,f"up1971-{p}-regex-cleaned-v1","csv",f"{p}.csv")
 with open(q,encoding="utf-8-sig",newline="") as f:r=list(csv.DictReader(f));return r,list(r[0])
def clear(r,vs):
 for v in vs:
  if v+"_flag" in r:r[v+"_flag"]=""
 r["requires_review"]="False"
def finish(p,rows,fields,report):
 f=p.removesuffix("_1971").replace("_","-");d=os.path.join(ROOT,f"up1971-{f}-source-checked-v1");os.makedirs(os.path.join(d,"csv"),exist_ok=True)
 with open(os.path.join(d,"csv",f"{p}.csv"),"w",encoding="utf-8",newline="") as z:w=csv.DictWriter(z,fieldnames=fields);w.writeheader();w.writerows(rows)
 old,_=load(p)
 with open(os.path.join(d,"CORRECTION_LOG.csv"),"w",encoding="utf-8",newline="") as z:
  w=csv.writer(z);w.writerow(["row_index","variable","original_value","corrected_value","reason"])
  for i,r in enumerate(rows):
   before=old[i] if i<len(old) else {}
   for v in fields:
    if v.endswith("_flag") or v in {"row_index","parent_row_index","subrow_index","subrow_count","requires_review","extracted_at"}:continue
    if before.get(v,"")!=r.get(v,""):w.writerow([i,v,before.get(v,""),r.get(v,""),"300-DPI source inspection; hierarchy and continuation cleanup"])
 with open(os.path.join(d,"UNRESOLVED_CELLS.csv"),"w",encoding="utf-8",newline="") as z:csv.writer(z).writerow(["row_index","variable","value","reason"])
 with open(os.path.join(d,"SOURCE_CHECKED_REPORT.md"),"w",encoding="utf-8") as z:z.write(report)
 print(p,len(rows))
def civic():
 p="farrukhabad_civic_1971";old,fields=load(p);t=deepcopy(old[0]);vs=["sl_no","town_name","road_length_km","sewerage_drainage_system","water_borne_latrines","service_latrines","other_latrines","night_soil_disposal_method","water_source","water_capacity","fire_service","elec_domestic","elec_industrial","elec_commercial","elec_road_light","elec_other","pucca_road_km","kutcha_road_km"]
 s=[("1","Chhibramau","PR (10) KR (4)","OSD","...","2,047","...","B/HC","TW/OHT","40,000 Galls.","...","386","55","310","400","...","10.0","4.0","ORDINARY",""),("2","Farrukhabad-cum-Fatehgarh","","","","","","","","","","","","","","","","CROSS_REFERENCE","Farrukhabad-cum-Fatehgarh City Urban Agglomeration"),("","Farrukhabad-cum-Fatehgarh City Urban Agglomeration","PR (45) KR (20)","PT/OSD","275","17,771","...","B/HC/MT/HL","TW/OHT","360,000 Galls.","...","4,123","418","2,956","1,572","...","45.0","20.0","AGGREGATE",""),("(i)","Farrukhabad-cum-Fatehgarh","PR (41.4) KR (20)","PT/OSD","109","17,000","...","B/HC","TW/OHT","300,000 Galls.","...","4,011","414","2,929","1,458","...","41.4","20.0","COMPONENT",""),("(ii)","Fatehgarh Cantt.","PR (3.6) KR (0)","PT/OSD","166","771",".","HL/MT","TW/OHT","60,000 Galls.",".","112","4","27","114","...","3.6","0.0","COMPONENT",""),("3","Fatehgarh Cantt.","","","","","","","","","","","","","CROSS_REFERENCE","Farrukhabad-cum-Fatehgarh City Urban Agglomeration"),("4","Kaimganj","PR (7) KR (3)","OSD","...","1,934","...","B/HC","TW/OHT","50,000 Galls.","...","470","70","975","227","...","7.0","3.0","ORDINARY",""),("5","Kannauj","PR (10) KR (38)","OSD","...","4,360","1","HL/B","TW/OHT","150,000 Galls.","...","840","70","265","266","...","10.0","38.0","ORDINARY","")]
 rows=[]
 for i,x in enumerate(s):r=deepcopy(t);r.update(dict(zip(vs,x)));r.update({"row_type":x[-2],"reference_target":x[-1],"row_index":str(i),"pdf_id":p,"district":DIST});clear(r,vs);rows.append(r)
 finish(p,rows,fields,"# Farrukhabad Civic source-checked output\n\nSource pages 6–7 inspected at 300 DPI. Eight logical rows retain the Farrukhabad-cum-Fatehgarh aggregate/components, cross-references, civic fields and continuation values.\n")
def mededu():
 p="farrukhabad_mededu_1971";old,fields=load(p);t=deepcopy(old[0]);vs=["hospitals_dispensaries","med_beds","degree_colleges","medical_colleges","engg_colleges","polytechnics","vocational_institutes","higher_secondary_schools","middle_schools","primary_schools","other_edu_institutions","stadia","cinemas","auditoria","libraries"]
 def par(serial,name,typ,ref,ch,beds,inh):
  z=[]
  for j,(c,b) in enumerate(zip(ch,beds)):
   r=deepcopy(t);r.update({"sl_no":serial,"town_name":name,"row_type":typ,"reference_target":ref,"parent_row_index":"","subrow_index":str(j),"subrow_count":str(len(ch)),"row_index":"","pdf_id":p,"district":DIST});clear(r,["sl_no","town_name"]+vs)
   for v in vs:r[v]=inh.get(v,"")
   r["hospitals_dispensaries"]=c;r["med_beds"]=b;z.append(r)
  return z
 e="...";rows=[]
 rows+=par("1","Chhibramau","ORDINARY","",["H (2)","FC (1)"],["32",e],{"degree_colleges":"S (1)","medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"3","middle_schools":"2","primary_schools":"5","other_edu_institutions":"6","stadia":e,"cinemas":e,"auditoria":".","libraries":"PL (1)"})
 rows+=par("2","Farrukhabad-cum-Fatehgarh","CROSS_REFERENCE","Farrukhabad-cum-Fatehgarh City Urban Agglomeration",[""],[""],{})
 rows+=par("","Farrukhabad-cum-Fatehgarh City Urban Agglomeration","AGGREGATE","",["H (10)","D (3)","FC (2)","*O (1)","TBC (1)"],["610","9",e,e,e],{"degree_colleges":"A (1) AC (1)","medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":"Sh. Type (1)","higher_secondary_schools":"10","middle_schools":"3","primary_schools":"55","other_edu_institutions":"5","stadia":"1","cinemas":"3","auditoria":"1","libraries":"RR (2) PL (4)"})
 rows+=par("(i)","Farrukhabad-cum-Fatehgarh","COMPONENT","",["H (9)","D (1)","FC (1)","*O (1)","TBC (1)"],["545",e,e,e,e],{"degree_colleges":"A (1) AC (1)","medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":"Sh. Type (1)","higher_secondary_schools":"9","middle_schools":"2","primary_schools":"53","other_edu_institutions":"5","stadia":e,"cinemas":"3","auditoria":e,"libraries":"PL (4)"})
 rows+=par("(ii)","Fatehgarh Cantt.","COMPONENT","",["H (1)","D (2)","FC (1)"],["65","9",e],{"degree_colleges":e,"medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"1","middle_schools":"1","primary_schools":"2","other_edu_institutions":e,"stadia":"1","cinemas":e,"auditoria":"1","libraries":"RR (2)"})
 rows+=par("3","Fatehgarh Cantt.","CROSS_REFERENCE","Farrukhabad-cum-Fatehgarh City Urban Agglomeration",[""],[""],{})
 rows+=par("4","Kaimganj","ORDINARY","",["H (2)","FC (1)"],["18",e],{"degree_colleges":e,"medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":e,"middle_schools":"4","primary_schools":"10","other_edu_institutions":e,"stadia":e,"cinemas":e,"auditoria":"2","libraries":"PL (3)"})
 rows+=par("5","Kannauj","ORDINARY","",["H (2)","HC (1)","FC (1)"],["18","4",e],{"degree_colleges":e,"medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"6","middle_schools":"3","primary_schools":"12","other_edu_institutions":"4","stadia":e,"cinemas":e,"auditoria":e,"libraries":"PL (1)"})
 pi=-1;last=None
 for i,r in enumerate(rows):k=(r["sl_no"],r["town_name"],r["row_type"]);pi+=k!=last;last=k;r["parent_row_index"]=str(pi);r["row_index"]=str(i)
 finish(p,rows,fields,"# Farrukhabad MedEdu source-checked output\n\nSource pages 8–9 inspected at 300 DPI. Eight logical parents and 22 expanded child rows preserve aggregate/component hierarchy, cross-references, H/D/FC/*O/TBC codes, and parent-scoped continuation values.\n")
def tehsil():
 p="farrukhabad_tehsil_1971";old,fields=load(p);t=deepcopy(old[0]);edu=["junior_basic_villages","junior_basic_schools","senior_basic_villages","senior_basic_schools","higher_secondary_villages","higher_secondary_schools","college_villages","colleges","other_edu_villages","other_edu_institutions"];med=["hospital_villages","hospitals","dispensary_villages","dispensaries","mcw_villages","mcw_centres","health_centre_villages","health_centres","family_planning_villages","family_planning_centres","other_med_villages","other_med_institutions"];wat=["power_available_villages","power_not_available_villages","tap_water_villages","hand_pipe_villages","well_villages","tank_villages","river_villages","fountain_villages","canal_villages","water_fall_villages","lake_villages","tube_well_villages","other_water_villages","no_water_villages"];rd=["pucca_road_villages","kachcha_road_villages","pucca_kachcha_road_villages","other_road_villages","post_office_villages","post_offices","telegraph_office_villages","telegraph_offices","post_telegraph_villages","post_telegraph_offices","telephone_villages","telephones"]
 E=[["152","162","24","27","5","6","...","...","...","..."],["210","230","43","49","10","11","...","...","...","..."],["179","216","37","39","14","17","2","2","...","..."],["165","194","38","49","7","9","...","...","...","..."],["706","802","142","164","36","43","2","2","...","..."]];M=[["10","11","3","3","1","1","2","2","1","1","...","..."],["8","9","8","8","7","8","1","1","1","1","...","..."],["11","12","2","2","4","4","1","1","3","3","...","..."],["16","17","4","4","5","5","...","...","4","6","...","..."],["45","49","17","17","17","18","2","2","9","11","...","..."]];W=[["49","394","...","10","412","...","...","...","...","...","...","6","...","..."],["229","349","10","11","518","...","1","...","...","...","...","8","...","..."],["89","305","1","93","388","...","...","...","...","...","...","...","...","..."],["111","258","...","1","342","...","7","...","2","...","...","13","...","..."],["478","1,306","11","115","1,660","...","8","...","2","...","...","27","...","..."]];R=[["48","273","22","60","21","21","...","...","2","2","1","1"],["60","349","59","56","55","55","1","1","2","2","4","4"],["68","197","14","13","45","45","2","2","3","3","...","..."],["33","240","18","54","37","37","...","...","7","7","1","1"],["209","1,059","113","183","158","158","3","3","14","14","6","6"]]
 allv=edu+med+wat+rd;rows=[]
 for i,name in enumerate(["Kaimganj","Farrukhabad","Chhibramau","Kannauj","District Total (Rural)"]):
  r=deepcopy(t);r.update({"sl_no":str(i+1) if i<4 else "","tahsil_name":name,"row_type":"TOTAL" if i==4 else "ORDINARY","reference_target":"","requires_review":"False","row_index":str(i),"pdf_id":p,"district":DIST});vals=dict(zip(edu,E[i]))|dict(zip(med,M[i]))|dict(zip(wat,W[i]))|dict(zip(rd,R[i]))
  for v in allv:r[v]=vals.get(v,"")
  clear(r,["sl_no","tahsil_name"]+allv);rows.append(r)
 finish(p,rows,fields,"# Farrukhabad Tahsil source-checked output\n\nSource pages 180–181 inspected at 300 DPI. Kaimganj, Farrukhabad, Chhibramau, Kannauj and District Total (Rural) retain aligned educational, medical, water/power and communications values.\n")
if __name__=="__main__":civic();mededu();tehsil()
