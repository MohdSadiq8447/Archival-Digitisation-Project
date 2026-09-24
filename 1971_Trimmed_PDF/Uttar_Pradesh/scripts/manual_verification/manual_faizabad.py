import csv,os
from copy import deepcopy
ROOT=r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed";DIST="Faizabad"
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
    if before.get(v,"")!=r.get(v,""):w.writerow([i,v,before.get(v,""),r.get(v,""),"300-DPI source inspection; structural/OCR cleanup"])
 with open(os.path.join(d,"UNRESOLVED_CELLS.csv"),"w",encoding="utf-8",newline="") as z:csv.writer(z).writerow(["row_index","variable","value","reason"])
 with open(os.path.join(d,"SOURCE_CHECKED_REPORT.md"),"w",encoding="utf-8") as z:z.write(report)
 print(p,len(rows))
def civic():
 p="faizabad_civic_1971";old,fields=load(p);t=deepcopy(old[0]);vs=["sl_no","town_name","road_length_km","sewerage_drainage_system","water_borne_latrines","service_latrines","other_latrines","night_soil_disposal_method","water_source","water_capacity","fire_service","elec_domestic","elec_industrial","elec_commercial","elec_road_light","elec_other","pucca_road_km","kutcha_road_km"]
 s=[("1","Akbarpur","PR (4) KR (8)","ST/OSD","16","3,955","...","C","R/W/HP","...","...","1,495","305","280","130","...","4.0","8.0","ORDINARY",""),("2","Faizabad Cantt.","","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Faizabad City Urban Agglomeration"),("3","Faizabad-cum-Ayodhya","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Faizabad City Urban Agglomeration"),("","Faizabad City Urban Agglomeration","PR (118) KR (12)","S/ST/OSD","2,395","14,065","...","B/MT/C","TW/OHT","3,270,454 Galls.","Yes","13,994","318","3,553","1,937","...","118.0","12.0","AGGREGATE",""),("(i)","Faizabad Cantt.","PR (10) KR (0)","ST/OSD","260","200","...","MT/C","TW/OHT","100,000 Galls.","Yes","180","...","70","192","...","10.0","0.0","COMPONENT",""),("(ii)","Faizabad-cum-Ayodhya","PR (108) KR (12)","S/ST/OSD","2,135","13,865","...","B/MT/C","TW/OHT","3,170,454 Galls.","Yes","13,814","318","3,483","1,745","...","108.0","12.0","COMPONENT",""),("4","Gosainganj","PR (3) KR (0)","ST/OSD","10","400","...","C","W/HP","...","...","250","25","110","52","...","3.0","0.0","ORDINARY",""),("5","Jalalpur","PR (3) KR (0)","ST/OSD","16","1,105","...","C","W/HP","...","...","414","109","293","70","...","3.0","0.0","ORDINARY",""),("6","Tanda","PR (66) KR (0)","S/OSD","250","5,625","...","MT/C","TW/OHT","100,000 Galls.","...","756","612","293","260","...","66.0","0.0","ORDINARY","")]
 rows=[]
 for i,x in enumerate(s):r=deepcopy(t);r.update(dict(zip(vs,x)));r.update({"row_type":x[-2],"reference_target":x[-1],"row_index":str(i),"pdf_id":p,"district":DIST});clear(r,vs);rows.append(r)
 finish(p,rows,fields,"# Faizabad Civic source-checked output\n\nSource pages 6–7 inspected at 300 DPI. Civic identities, aggregate/components, references, road/latrine columns and continuation values were transcribed from the printed source.\n")
def mededu():
 p="faizabad_mededu_1971";old,fields=load(p);t=deepcopy(old[0]);vs=["hospitals_dispensaries","med_beds","degree_colleges","medical_colleges","engg_colleges","polytechnics","vocational_institutes","higher_secondary_schools","middle_schools","primary_schools","other_edu_institutions","stadia","cinemas","auditoria","libraries"]
 def par(serial,name,typ,ref,ch,beds,inh):
  out=[]
  for j,(c,b) in enumerate(zip(ch,beds)):
   r=deepcopy(t);r.update({"sl_no":serial,"town_name":name,"row_type":typ,"reference_target":ref,"parent_row_index":"","subrow_index":str(j),"subrow_count":str(len(ch)),"row_index":"","pdf_id":p,"district":DIST});clear(r,["sl_no","town_name"]+vs)
   for v in vs:r[v]=inh.get(v,"")
   r["hospitals_dispensaries"]=c;r["med_beds"]=b;out.append(r)
  return out
 e="...";rows=[]
 rows+=par("1","Akbarpur","ORDINARY","",["HC (1)","FC (1)","O (1)"],["8",e,e],{"degree_colleges":"A (1)","medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"2","middle_schools":"1","primary_schools":"3","other_edu_institutions":"4","stadia":e,"cinemas":e,"auditoria":e,"libraries":e})
 for n,name in [("2","Faizabad Cantt."),("3","Faizabad-cum-Ayodhya")]:rows+=par(n,name,"CROSS_REFERENCE","Faizabad City Urban Agglomeration",[""],[""],{})
 inh={"degree_colleges":"AS (1)","medical_colleges":e,"engg_colleges":e,"polytechnics":"1","vocational_institutes":e,"higher_secondary_schools":"16","middle_schools":"9","primary_schools":"55","other_edu_institutions":"43","stadia":e,"cinemas":"5","auditoria":e,"libraries":"PL (4) RR (1)"}
 rows+=par("","Faizabad City Urban Agglomeration","AGGREGATE","",["H (8)","TBC (1)","FC (1)","D (1)"],["310",e,e,e],inh)
 rows+=par("(i)","Faizabad Cantt.","COMPONENT","",["D (1)"],[e],{"degree_colleges":e,"medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"2","middle_schools":"1","primary_schools":"4","other_edu_institutions":e,"stadia":e,"cinemas":e,"auditoria":e,"libraries":"RR (1)"})
 rows+=par("(ii)","Faizabad-cum-Ayodhya","COMPONENT","",["H (8)","TBC (1)","FC (1)"],["310",e,e],{"degree_colleges":"AS (1)","medical_colleges":e,"engg_colleges":e,"polytechnics":"1","vocational_institutes":e,"higher_secondary_schools":"14","middle_schools":"8","primary_schools":"51","other_edu_institutions":"43","stadia":e,"cinemas":"5","auditoria":e,"libraries":"PL (4)"})
 rows+=par("4","Gosainganj","ORDINARY","",["D (1)","FC (1)"],["4",e],{"degree_colleges":e,"medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":"O (1)","higher_secondary_schools":"2","middle_schools":"2","primary_schools":"2","other_edu_institutions":"4","stadia":e,"cinemas":e,"auditoria":e,"libraries":e})
 rows+=par("5","Jalalpur","ORDINARY","",["HC (1)","FC (1)"],["8",e],{"degree_colleges":e,"medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"1","middle_schools":"1","primary_schools":"2","other_edu_institutions":"2","stadia":e,"cinemas":"1","auditoria":e,"libraries":"PL (2)"})
 rows+=par("6","Tanda","ORDINARY","",["H (1)","HC (1)"],["20","8"],{"degree_colleges":"A (1)","medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"3","middle_schools":"3","primary_schools":"17","other_edu_institutions":"5","stadia":e,"cinemas":"2","auditoria":e,"libraries":"PL (2)"})
 pi=-1;last=None
 for i,r in enumerate(rows):k=(r["sl_no"],r["town_name"],r["row_type"]);pi+=k!=last;last=k;r["parent_row_index"]=str(pi);r["row_index"]=str(i)
 finish(p,rows,fields,"# Faizabad MedEdu source-checked output\n\nSource pages 8–9 inspected at 300 DPI. Nine logical parents (including aggregate, components, and cross-references) are retained as 19 expanded child rows with child-scoped medical values and parent-scoped continuation values.\n")
def tehsil():
 p="faizabad_tehsil_1971";old,fields=load(p);t=deepcopy(old[0]);edu=["junior_basic_villages","junior_basic_schools","senior_basic_villages","senior_basic_schools","higher_secondary_villages","higher_secondary_schools","college_villages","colleges","other_edu_villages","other_edu_institutions"];med=["hospital_villages","hospitals","dispensary_villages","dispensaries","mcw_villages","mcw_centres","health_centre_villages","health_centres","family_planning_villages","family_planning_centres","other_med_villages","other_med_institutions"];wat=["power_available_villages","power_not_available_villages","tap_water_villages","hand_pipe_villages","well_villages","tank_villages","river_villages","fountain_villages","canal_villages","water_fall_villages","lake_villages","tube_well_villages","other_water_villages","no_water_villages"];rd=["pucca_road_villages","kachcha_road_villages","pucca_kachcha_road_villages","other_road_villages","post_office_villages","post_offices","telegraph_office_villages","telegraph_offices","post_telegraph_villages","post_telegraph_offices","telephone_villages","telephones"]
 E=[["204","219","18","18","2","2","...","...","1","1"],["267","276","15","15","5","5","4","4","...","..."],["313","327","35","36","16","16","...","...","2","2"],["220","235","29","31","5","5","1","1","...","..."],["1,004","1,057","97","100","28","28","5","5","3","3"]];M=[["3","3","6","6","1","1","2","2","4","4","...","..."],["5","5","2","2","1","1","3","3","2","2","...","..."],["7","7","14","14","14","14","4","4","15","15","...","..."],["4","4","1","1","7","7","...","...","3","3","...","..."],["19","19","23","23","23","23","9","9","24","24","...","..."]];W=[["224","184","...","28","377","...","7","...","...","...","...","16","...","..."],["377","254","...","4","628","...","...","...","...","...","...","3","...","..."],["300","605","...","763","901","...","8","...","15","...","...","...","...","."],["147","709","...","64","757","...","2","...","...","...","...","...","...","..."] ,["1,048","1,752","...","859","2,663","...","17","...","15","...","...","19","...","..."]];R=[["119","286","...","...","48","48","...","...","3","3","...","..."],["131","513","...","...","72","72","...","...","1","1","...","..."],["262","417","...","...","81","81","...","...","7","7","...","..."],["132","548","...","...","56","56","...","...","...","...","...","..."],["644","1,764","...","...","257","257","...","...","11","11","...","..."]]
 allv=edu+med+wat+rd;rows=[]
 for i,name in enumerate(["Faizabad","Bikapur","Akbarpur","Tanda","District Total (Rural)"]):
  r=deepcopy(t);r.update({"sl_no":str(i+1) if i<4 else "","tahsil_name":name,"row_type":"TOTAL" if i==4 else "ORDINARY","reference_target":"","requires_review":"False","row_index":str(i),"pdf_id":p,"district":DIST});vals=dict(zip(edu,E[i]))|dict(zip(med,M[i]))|dict(zip(wat,W[i]))|dict(zip(rd,R[i]))
  for v in allv:r[v]=vals.get(v,"")
  clear(r,["sl_no","tahsil_name"]+allv);rows.append(r)
 finish(p,rows,fields,"# Faizabad Tahsil source-checked output\n\nSource pages 276–277 inspected at 300 DPI. Faizabad, Bikapur, Akbarpur, Tanda and District Total (Rural) retain aligned educational, medical, water/power and communications values.\n")
if __name__=="__main__":civic();mededu();tehsil()
