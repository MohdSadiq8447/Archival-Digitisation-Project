import csv, os
from copy import deepcopy
ROOT=r"E:\\Archival-Digitisation-Project\\1971_Trimmed_PDF\\Uttar_Pradesh\\outputs\\postprocessed"; DIST="Kheri"
def load(p):
 with open(os.path.join(ROOT,f"up1971-{p}-regex-cleaned-v1","csv",f"{p}.csv"),encoding="utf-8-sig",newline="") as f:r=csv.DictReader(f);return list(r),list(r.fieldnames or [])
def clear(r):
 for k in r:
  if k.endswith("_flag"):r[k]=""
 r["requires_review"]="False"
def finish(p,rows,fields,report):
 slug=p.removesuffix("_1971").replace("_","-");out=os.path.join(ROOT,f"up1971-{slug}-source-checked-v1");os.makedirs(os.path.join(out,"csv"),exist_ok=True)
 with open(os.path.join(out,"csv",f"{p}.csv"),"w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)
 old,_=load(p)
 with open(os.path.join(out,"CORRECTION_LOG.csv"),"w",encoding="utf-8",newline="") as f:
  w=csv.writer(f);w.writerow(["row_index","variable","original_value","corrected_value","reason"])
  for i,r in enumerate(rows):
   b=old[i] if i<len(old) else {}
   for v in fields:
    if v.endswith("_flag") or v in {"row_index","parent_row_index","subrow_index","subrow_count","requires_review","extracted_at"}:continue
    if b.get(v,"")!=r.get(v,""):w.writerow([i,v,b.get(v,""),r.get(v,""),"300-DPI source inspection and hierarchy/continuation cleanup"])
 with open(os.path.join(out,"UNRESOLVED_CELLS.csv"),"w",encoding="utf-8",newline="") as f:csv.writer(f).writerow(["row_index","variable","value","reason"])
 with open(os.path.join(out,"SOURCE_CHECKED_REPORT.md"),"w",encoding="utf-8") as f:f.write(report)
 print(p,len(rows))

def civic():
 p="kheri_civic_1971";old,fields=load(p);t=deepcopy(old[0]);vs=["sl_no","town_name","road_length_km","sewerage_drainage_system","water_borne_latrines","service_latrines","other_latrines","night_soil_disposal_method","water_source","water_capacity","fire_service","elec_domestic","elec_industrial","elec_commercial","elec_road_light","elec_other","pucca_road_km","kutcha_road_km"]
 vals=[("1","Gola Gokaran Nath","PR (46.4) KR (3)","PT/OSD","212","2,356","14","HC","TW/OHT","50,000 Galls.","...","443","62","647","200","...","46.4","3.0"),("2","Kheri","PR (30.4) KR (8.2)","PT/OSD","204","480","20","B","HP","...","...","310","13","110","90","...","30.4","8.2"),("3","Lakhimpur","PR (82.8) KR (6.3)","PT/OSD","910","4,000","50","HC","TW/OHT","100,000 Galls.","...","2,240","172","1,654","530","...","82.8","6.3"),("4","Mohamdi","PR (6) KR (20)","PT/OSD","12","1,528","2","B/HC","HP","...","...","248","18","30","142","...","6.0","20.0")]
 rows=[]
 for i,v in enumerate(vals):r=deepcopy(t);r.update(dict(zip(vs,v)));r.update({"row_type":"ORDINARY","reference_target":"","row_index":str(i),"pdf_id":p,"district":DIST});clear(r);rows.append(r)
 finish(p,rows,fields,"# Kheri Civic source-checked output\n\nFour Civic town rows and the page-7 amenities continuation were transcribed from the source. The following Medical/Educational and Trade panels were excluded from Civic rows.\n")

def mededu():
 p="kheri_mededu_1971";old,fields=load(p);t=deepcopy(old[0]);e="...";vs=["hospitals_dispensaries","med_beds","degree_colleges","medical_colleges","engg_colleges","polytechnics","vocational_institutes","higher_secondary_schools","middle_schools","primary_schools","other_edu_institutions","stadia","cinemas","auditoria","libraries"]
 def par(serial,town,ch,beds,inh,pidx):
  out=[]
  for j,(c,b) in enumerate(zip(ch,beds)):
   r=deepcopy(t);r.update({"sl_no":serial,"town_name":town,"row_type":"ORDINARY","reference_target":"","parent_row_index":str(pidx),"subrow_index":str(j),"subrow_count":str(len(ch)),"row_index":"","pdf_id":p,"district":DIST});r.update(inh);r["hospitals_dispensaries"]=c;r["med_beds"]=b;clear(r);out.append(r)
  return out
 def I(deg=e,med=e,eng=e,poly=e,voc=e,higher=e,middle=e,primary=e,other=e,stad=e,cin=e,aud=e,lib=e):return {"degree_colleges":deg,"medical_colleges":med,"engg_colleges":eng,"polytechnics":poly,"vocational_institutes":voc,"higher_secondary_schools":higher,"middle_schools":middle,"primary_schools":primary,"other_edu_institutions":other,"stadia":stad,"cinemas":cin,"auditoria":aud,"libraries":lib}
 rows=[]
 rows+=par("1","Gola Gokaran Nath",["H (4)","D (7)","FC (1)","O (1)"],["45","58",e,e],I(deg="A (1)",higher="3",middle="3",primary="9",other="1",cin="2",lib="PL (1) RR (1)"),0)
 rows+=par("2","Kheri",["D (1)","H (1)","O (1)","TBC (1)","O (1)"],[e,e,e,e,e],I(higher=e,middle="2",primary="2"),1)
 rows+=par("3","Lakhimpur",["H (8)","FC (1)","TBC (1)"],["198",e,e],I(deg="A (1) ASC (1)",voc="Sh. Type O (2)",higher="7",middle="5",primary="16",other="4",cin="2",lib="PL (4)"),2)
 rows+=par("4","Mohamdi",["H (1)","D (1)"],["18",e],I(higher="2",middle="3",primary="5"),3)
 for i,r in enumerate(rows):r["row_index"]=str(i)
 finish(p,rows,fields,"# Kheri MedEdu source-checked output\n\nFour parent towns and fourteen expanded child rows preserve the printed medical hierarchy from page 6. Columns 5–17 are parent-scoped and aligned to the page-7 cultural-facilities continuation; the footnote is excluded from data rows.\n")

def tehsil():
 p="kheri_tehsil_1971";old,fields=load(p);t=deepcopy(old[0]);edu=["junior_basic_villages","junior_basic_schools","senior_basic_villages","senior_basic_schools","higher_secondary_villages","higher_secondary_schools","college_villages","colleges","other_edu_villages","other_edu_institutions"];med=["hospital_villages","hospitals","dispensary_villages","dispensaries","mcw_villages","mcw_centres","health_centre_villages","health_centres","family_planning_villages","family_planning_centres","other_med_villages","other_med_institutions"];wat=["power_available_villages","power_not_available_villages","tap_water_villages","hand_pipe_villages","well_villages","tank_villages","river_villages","fountain_villages","canal_villages","water_fall_villages","lake_villages","tube_well_villages","other_water_villages","no_water_villages"];rd=["pucca_road_villages","kachcha_road_villages","pucca_kachcha_road_villages","other_road_villages","post_office_villages","post_offices","telegraph_office_villages","telegraph_offices","post_telegraph_villages","post_telegraph_offices","telephone_villages","telephones"]
 sp=[("1","Nighasan",["231","240","8","8","6","6","...","...","...","..."],["10","10","36","36","4","4","3","3","6","6","...","..."],["77","339","...","388","356","...","5","...","...","...","...","...","...","..."],["114","152","1","74","33","33","...","...","3","3","5","5"]),("2","Lakhimpur",["360","377","15","17","14","15","2","2","...","..."],["12","16","8","8","7","7","5","6","5","5","...","..."],["126","559","...","605","65","17","1","...","14","...","...","...","...","..."],["195","500","...","...","36","36","...","...","3","3","1","1"]),("3","Mohamdi",["317","324","24","27","4","4","...","...","...","..."],["12","12","39","40","5","5","3","3","3","3","...","..."],["208","452","...","148","604","...","20","...","...","...","...","...","...","..."],["129","464","...","...","...","...","...","...","...","...","...","..."]),("","District Total (Rural)",["908","941","47","52","24","25","2","2","...","..."],["34","38","83","84","16","16","11","12","14","14","...","..."],["411","1,350","...","1,141","1,025","77","26","...","14","...","...","...","...","..."],["438","1,116","...","...","197","197","...","...","6","6","6","6"])]
 rows=[]
 for i,(s,n,e,m,w,x) in enumerate(sp):
  r=deepcopy(t);r.update({"sl_no":s,"tahsil_name":n,"row_type":"TOTAL" if i==3 else "ORDINARY","reference_target":"","row_index":str(i),"pdf_id":p,"district":DIST})
  for v,z in zip(edu,e):r[v]=z
  for v,z in zip(med,m):r[v]=z
  for v,z in zip(wat,w):r[v]=z
  for v,z in zip(rd,x):r[v]=z
  clear(r);rows.append(r)
 finish(p,rows,fields,"# Kheri Tahsil source-checked output\n\nThree Tahsil rows and District Total (Rural) were transcribed from printed pages 176–177, with education, water, medical, and communications continuation bands aligned by identity.\n")
if __name__=="__main__":civic();mededu();tehsil()
