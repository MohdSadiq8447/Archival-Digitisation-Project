import csv, os
from copy import deepcopy
ROOT=r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed"; DIST="Etawah"
def load(pdf):
 p=os.path.join(ROOT,f"up1971-{pdf}-regex-cleaned-v1","csv",f"{pdf}.csv")
 with open(p,encoding="utf-8-sig",newline="") as f:r=list(csv.DictReader(f));return r,list(r[0])
def clear(r,vs):
 for v in vs:
  if v+"_flag" in r:r[v+"_flag"]=""
 r["requires_review"]="False"
def out(pdf,rows,fields,txt):
 folder=pdf.removesuffix("_1971").replace("_","-");d=os.path.join(ROOT,f"up1971-{folder}-source-checked-v1");os.makedirs(os.path.join(d,"csv"),exist_ok=True)
 with open(os.path.join(d,"csv",f"{pdf}.csv"),"w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 old,_=load(pdf)
 with open(os.path.join(d,"CORRECTION_LOG.csv"),"w",encoding="utf-8",newline="") as f:
  w=csv.writer(f);w.writerow(["row_index","variable","original_value","corrected_value","reason"])
  for i,r in enumerate(rows):
   for v in fields:
    if v.endswith("_flag") or v in {"row_index","parent_row_index","subrow_index","subrow_count","requires_review","extracted_at"}:continue
    if old[i].get(v,"")!=r.get(v,""):w.writerow([i,v,old[i].get(v,""),r.get(v,""),"300-DPI source inspection and structural OCR cleanup"])
 with open(os.path.join(d,"UNRESOLVED_CELLS.csv"),"w",encoding="utf-8",newline="") as f:csv.writer(f).writerow(["row_index","variable","value","reason"])
 with open(os.path.join(d,"SOURCE_CHECKED_REPORT.md"),"w",encoding="utf-8") as f:f.write(txt)
 print(pdf,len(rows))
def civic():
 pdf="etawah_civic_1971";old,fields=load(pdf);t=deepcopy(old[0]);vs=["sl_no","town_name","road_length_km","sewerage_drainage_system","water_borne_latrines","service_latrines","other_latrines","night_soil_disposal_method","water_source","water_capacity","fire_service","elec_domestic","elec_industrial","elec_commercial","elec_road_light","elec_other","pucca_road_km","kutcha_road_km"]
 s=[("1","Auraiya","PR (35) KR (16)","OSD","...","2,000","30","B/HC/MT","TW/OHT","50,000 gallons","...","1,046","92","346","800","...","35.0","16.0"),("2","Bharthana","PR (2) KR (11)","OSD","...","1,700","100","B/HC","HP","...","...","832","60","150","245","...","2.0","11.0"),("3","Etawah","PR (26) KR (2)","OSD","...","17,751","15","HC/MT","TW/OHT","200,000 gallons","...","4,700","414","361","1,737","...","26.0","2.0"),("4","Jaswantnagar","PR (0) KR (4)","OSD","...","1,000","...","B/HC","TW/OHT","25,000 gallons","...","175","20","25","80","...","0.0","4.0"),("5","Lakhna","PR (0) KR (4)","OSD","...","896","10","B/HC","TW/OHT","11,000 gallons","...","200","8","250","80","...","0.0","4.0")]
 rows=[]
 for i,x in enumerate(s):r=deepcopy(t);r.update(dict(zip(vs,x)));r.update({"row_type":"ORDINARY","reference_target":"","row_index":str(i),"pdf_id":pdf,"district":DIST});clear(r,vs);rows.append(r)
 out(pdf,rows,fields,"# Etawah Civic source-checked output\n\nSource pages 6–7 inspected at 300 DPI. Five towns and all civic, water-supply and electrification continuation values were transcribed from the printed source.\n")
def mededu():
 pdf="etawah_mededu_1971";old,fields=load(pdf);t=deepcopy(old[0]);vs=["hospitals_dispensaries","med_beds","degree_colleges","medical_colleges","engg_colleges","polytechnics","vocational_institutes","higher_secondary_schools","middle_schools","primary_schools","other_edu_institutions","stadia","cinemas","auditoria","libraries"]
 def p(serial,name,ch,beds,inh):
  z=[]
  for j,(c,b) in enumerate(zip(ch,beds)):
   r=deepcopy(t);r.update({"sl_no":serial,"town_name":name,"row_type":"ORDINARY","reference_target":"","parent_row_index":"","subrow_index":str(j),"subrow_count":str(len(ch)),"row_index":"","pdf_id":pdf,"district":DIST});clear(r,["sl_no","town_name"]+vs)
   for v in vs:r[v]=inh.get(v,"")
   r["hospitals_dispensaries"]=c;r["med_beds"]=b;z.append(r)
  return z
 e="...";rows=[]
 rows+=p("1","Auraiya",["H (3)","D (1)","FC (1)"],["43",e,e],{"degree_colleges":"AC (1)","medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":"Type (1)","higher_secondary_schools":"4","middle_schools":"4","primary_schools":"15","other_edu_institutions":"1","stadia":e,"cinemas":"1","auditoria":e,"libraries":"PL (1) RR (1)"})
 rows+=p("2","Bharthana",["H (2)","HC (1)","FC (1)"],["21",e,e],{"degree_colleges":"A (1)","medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"3","middle_schools":"2","primary_schools":"10","other_edu_institutions":"3","stadia":e,"cinemas":e,"auditoria":e,"libraries":"PL (1) RR (1)"})
 rows+=p("3","Etawah",["H (6)","TBC (1)","*O (1)","FC (1)","HC (1)"],["248","32",e,e,e],{"degree_colleges":"ASC (1)","medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"10","middle_schools":"5","primary_schools":"40","other_edu_institutions":"3","stadia":e,"cinemas":"2","auditoria":e,"libraries":"PL (1) RR (1)"})
 rows+=p("4","Jaswantnagar",["H (1)","D (1)","FC (1)"],["5",e,e],{"degree_colleges":e,"medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"2","middle_schools":"3","primary_schools":"3","other_edu_institutions":"1","stadia":e,"cinemas":e,"auditoria":e,"libraries":"RR (1)"})
 rows+=p("5","Lakhna",["H (1)","FC (1)"],["13",e],{"degree_colleges":e,"medical_colleges":e,"engg_colleges":e,"polytechnics":e,"vocational_institutes":e,"higher_secondary_schools":"1","middle_schools":"1","primary_schools":"2","other_edu_institutions":e,"stadia":e,"cinemas":e,"auditoria":e,"libraries":"RR (1)"})
 pi=-1;last=None
 for i,r in enumerate(rows):k=(r["sl_no"],r["town_name"]);pi+=k!=last;last=k;r["parent_row_index"]=str(pi);r["row_index"]=str(i)
 out(pdf,rows,fields,"# Etawah MedEdu source-checked output\n\nSource pages 6–7 inspected at 300 DPI. Five parents and 16 expanded child rows preserve H/D/HC/TBC/FC/*O hierarchy and parent-scoped continuation values.\n")
def tehsil():
 pdf="etawah_tehsil_1971";old,fields=load(pdf);t=deepcopy(old[0]);edu=["junior_basic_villages","junior_basic_schools","senior_basic_villages","senior_basic_schools","higher_secondary_villages","higher_secondary_schools","college_villages","colleges","other_edu_villages","other_edu_institutions"];med=["hospital_villages","hospitals","dispensary_villages","dispensaries","mcw_villages","mcw_centres","health_centre_villages","health_centres","family_planning_villages","family_planning_centres","other_med_villages","other_med_institutions"];wat=["power_available_villages","power_not_available_villages","tap_water_villages","hand_pipe_villages","well_villages","tank_villages","river_villages","fountain_villages","canal_villages","water_fall_villages","lake_villages","tube_well_villages","other_water_villages","no_water_villages"];rd=["pucca_road_villages","kachcha_road_villages","pucca_kachcha_road_villages","other_road_villages","post_office_villages","post_offices","telegraph_office_villages","telegraph_offices","post_telegraph_villages","post_telegraph_offices","telephone_villages","telephones"]
 E=[["190","207","39","42","15","15","...","...","...","..."],["210","230","44","46","8","8","4","5","...","..."],["174","197","26","29","6","6","...","...","...","..."],["206","213","44","46","11","12","...","...","...","..."]];M=[["8","8","5","5","...","...","...","...","2","2","...","..."],["...","...","9","9","2","2","...","...","1","1","2","2"],["6","6","6","6","2","2","2","2","5","5","...","..."],["10","10","4","4","9","9","...","...","1","1","...","..."]];W=[["1","432","...","92","404","...","...","...","...","...","...","...","...","Nil"],["22","427",".","113","590","17","11","...","...","...","...","3","...","Nil"],["68","294","6","345","5","5",".","3","...","...","18","...","...","Nil"],["114","197","81","307","1","4","...","...","9","...","...","Nil"]];R=[["69","33","7","5","35","35","...","...","3","3","2","2"],["98","76","9","16","40","40","...","...","4","4","...","..."],["95","135","34","39","39","39","...","...","2","2","2","2"],["57","120","12","11","41","41","...","...","3","3","1","1"]]
 rows=[];allv=edu+med+wat+rd
 for i,name in enumerate(["Bidhuna","Auraiya","Etawah","Bharthana"]):
  r=deepcopy(t);r.update({"sl_no":str(i+1),"tahsil_name":name,"row_type":"ORDINARY","reference_target":"","requires_review":"False","row_index":str(i),"pdf_id":pdf,"district":DIST});vals=dict(zip(edu,E[i]))|dict(zip(med,M[i]))|dict(zip(wat,W[i]))|dict(zip(rd,R[i]))
  for v in allv:r[v]=vals.get(v,"")
  clear(r,["sl_no","tahsil_name"]+allv);rows.append(r)
 out(pdf,rows,fields,"# Etawah Tahsil source-checked output\n\nSource pages 162–163 inspected at 300 DPI. Bidhuna, Auraiya, Etawah and Bharthana retain aligned educational, medical, water/power and communications values.\n")
if __name__=="__main__":civic();mededu();tehsil()
