import csv, os
from copy import deepcopy
ROOT=r"E:\\Archival-Digitisation-Project\\1971_Trimmed_PDF\\Uttar_Pradesh\\outputs\\postprocessed"; DIST="Kanpur"
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
 p="kanpur_civic_1971";old,fields=load(p);t=deepcopy(old[0]);vs=["sl_no","town_name","road_length_km","sewerage_drainage_system","water_borne_latrines","service_latrines","other_latrines","night_soil_disposal_method","water_source","water_capacity","fire_service","elec_domestic","elec_industrial","elec_commercial","elec_road_light","elec_other","pucca_road_km","kutcha_road_km"]
 vals=[
 ("1","Armapur Estate","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Kanpur City Urban Agglomeration"),
 ("2","Central Rly. Colony","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Kanpur City Urban Agglomeration"),
 ("3","Chakeri","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Kanpur City Urban Agglomeration"),
 ("4","I. I. T.","","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Kanpur City Urban Agglomeration"),
 ("5","Kanpur","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Kanpur City Urban Agglomeration"),
 ("6","Kanpur Cantt.","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Kanpur City Urban Agglomeration"),
 ("","Kanpur City Urban Agglomeration","PR (934.4) KR (35)","S/PT/OSD","104,812","48,886","28","B/MT/HC","TW/OHT","1,471,700 Galls.","Yes","72,178","3,986","21,065","23,182","...","934.4","35.0","AGGREGATE",""),
 ("(i)","Armapur Estate","PR (22) KR (0)","PT/OSD","2,626","370","...","MT","TW/OHT","311,400 Galls.","Yes","1,400","3","26","631","...","22.0","0.0","COMPONENT",""),
 ("(ii)","Central Rly. Colony","PR (3) KR (0)","PT/OSD","44","67","28","HC","TW/OHT","52,300 Galls.","...","47","5","...","27","...","3.0","0.0","COMPONENT",""),
 ("(iii)","Chakeri","N. A.","","N. A.","N. A.","","N. A.","","Not Available","","Not Available","...","7","595","...","","","COMPONENT",""),
 ("(iv)","I. I. T.","PR (14.4) KR (0)","S","1,262","...","...","...","","Not Available","","835","...","7","595","...","14.4","0.0","COMPONENT",""),
 ("(v)","Kanpur","PR (850) KR (26)","S/OSD","100,058","42,803","...","B/HC/MT","TW/OHT","800,000 Galls.","Yes","59,916","1,037","20,836","19,837","...","850.0","26.0","COMPONENT",""),
 ("(vi)","Kanpur Cantt.","PR (29) KR (6)","S/OSD","168","1,583","...","MT","TW/OHT","50,000 Galls.","...","2,000","N.A.","110","764","...","29.0","6.0","COMPONENT",""),
 ("(vii)","Northern Rly. Colony","PR (8) KR (3)","S/OSD","500","3,900","...","HC","TW/OHT","100,000 Galls.","...","7,480","2,941","50","1,200","...","8.0","3.0","COMPONENT",""),
 ("(viii)","Rawatpur Station Yard","PR (8) KR (0)","S/OSD","154","86","...","HC","TW/OHT","108,000 Galls.","...","500","...","36","128","...","8.0","0.0","COMPONENT",""),
 ("7","Northern Rly. Colony","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Kanpur City Urban Agglomeration"),
 ("8","Pukhrayan","PR (8) KR (9)","ST/OSD","26","1,185","...","B/HC","TW/OHT","15,000 Galls.","...","410","9","30","83","...","8.0","9.0","ORDINARY",""),
 ("9","Rawatpur Station Yard","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Kanpur City Urban Agglomeration"),]
 rows=[]
 for i,v in enumerate(vals):r=deepcopy(t);r.update(dict(zip(vs,v)));r.update({"row_type":v[-2],"reference_target":v[-1],"row_index":str(i),"pdf_id":p,"district":DIST});clear(r);rows.append(r)
 finish(p,rows,fields,"# Kanpur Civic source-checked output\n\nEighteen identity rows, including Kanpur City Urban Agglomeration, eight components, and cross-references, were transcribed from printed pages 10–11.\n")

def mededu():
 p="kanpur_mededu_1971";old,fields=load(p);t=deepcopy(old[0]);e="...";vs=["hospitals_dispensaries","med_beds","degree_colleges","medical_colleges","engg_colleges","polytechnics","vocational_institutes","higher_secondary_schools","middle_schools","primary_schools","other_edu_institutions","stadia","cinemas","auditoria","libraries"]
 def par(serial,town,typ,ref,ch,beds,inh,pidx):
  out=[]
  for j,(c,b) in enumerate(zip(ch,beds)):
   r=deepcopy(t);r.update({"sl_no":serial,"town_name":town,"row_type":typ,"reference_target":ref,"parent_row_index":str(pidx),"subrow_index":str(j),"subrow_count":str(len(ch)),"row_index":"","pdf_id":p,"district":DIST});r.update(inh);r["hospitals_dispensaries"]=c;r["med_beds"]=b;clear(r);out.append(r)
  return out
 def I(deg=e,med=e,eng=e,poly=e,voc=e,higher=e,middle=e,primary=e,other=e,stad=e,cin=e,aud=e,lib=e):return {"degree_colleges":deg,"medical_colleges":med,"engg_colleges":eng,"polytechnics":poly,"vocational_institutes":voc,"higher_secondary_schools":higher,"middle_schools":middle,"primary_schools":primary,"other_edu_institutions":other,"stadia":stad,"cinemas":cin,"auditoria":aud,"libraries":lib}
 rows=[]
 for n,name in [("1","Armapur Estate"),("2","Central Rly. Colony"),("3","Chakeri"),("4","I. I. T."),("5","Kanpur"),("6","Kanpur Cantt.")]:rows+=par(n,name,"CROSS_REFERENCE","Kanpur City Urban Agglomeration",["See"],[""],{},len(rows))
 rows+=par("","Kanpur City Urban Agglomeration","AGGREGATE","",["H (20)","D (72)","HC (3)","TBC (5)","*O (9)","FC (17)"],["2,581",e,"30","118","250",e],I(deg="A (4) ASL (1) AS (5) ASC (3) ASCL (1) L (1)",med="1",eng="4",poly="3",voc="Sh. Type (5)",higher="36",middle="103",primary="495",other="465",stad="1",cin="24",aud="4",lib="PL (20) RR (16)"),6)
 rows+=par("(i)","Armapur Estate","COMPONENT","",["H (1)","D (3)","FC (1)"],["60",e,e],I(higher="1",middle="4",primary="4",cin="1",lib="PL (1)"),7)
 rows+=par("(ii)","Central Rly. Colony","COMPONENT","",["D (2)"],[e],{},8)
 rows+=par("(iii)","Chakeri","COMPONENT","",["Not Available"],[""],{"higher_secondary_schools":"Not Available","cinemas":"Not Available"},9)
 rows+=par("(iv)","I. I. T.","COMPONENT","",["HC (1)"],["30"],I(higher="1",primary="1",other="2"),10)
 rows+=par("(v)","Kanpur","COMPONENT","",["H (17)","D (63)","TBC (5)","*O (9)","FC (14)"],["2,461",e,"118","250",e],I(deg="LA (3) L (1) AS (5) ASC (3) ASCL (1)",med="1",eng="3",poly="3",voc="Sh. Type (5)",higher="77",middle="95",primary="476",other="463",stad="1",cin="20",aud="3",lib="PL (15)"),11)
 rows+=par("(vi)","Kanpur Cantt.","COMPONENT","",["H (1)","D (1)"],["30",e],I(deg="A (1) ASL (1)",higher="7",middle="4",primary="9",cin="3",lib="RR (13)"),12)
 rows+=par("(vii)","Northern Rly. Colony","COMPONENT","",["H (1)","D (3)","HC (1)","FC (1)"],["30",e,e,e],I(primary="5",cin="2",lib="PL (3)"),13)
 rows+=par("(viii)","Rawatpur Station Yard","COMPONENT","",["HC (1)","FC (1)"],[e,e],I(primary="1",lib="RR (3)"),14)
 rows+=par("7","Northern Rly. Colony","CROSS_REFERENCE","Kanpur City Urban Agglomeration",["See"],[""],{},15)
 rows+=par("8","Pukhrayan","ORDINARY","",["D (1)","FC (1)"],["8",e],I(deg="A (1)",higher="5",middle="2",primary="3",lib="PL (4)"),16)
 rows+=par("9","Rawatpur Station Yard","CROSS_REFERENCE","Kanpur City Urban Agglomeration",["See"],[""],{},17)
 for i,r in enumerate(rows):r["row_index"]=str(i)
 finish(p,rows,fields,"# Kanpur MedEdu source-checked output\n\nEighteen parent identities and 35 expanded child rows preserve the aggregate/component hierarchy from printed page 12. Parent continuation values from page 13 are propagated only within each parent; the printed note is excluded from data rows.\n")

def tehsil():
 p="kanpur_tehsil_1971";old,fields=load(p);t=deepcopy(old[0]);edu=["junior_basic_villages","junior_basic_schools","senior_basic_villages","senior_basic_schools","higher_secondary_villages","higher_secondary_schools","college_villages","colleges","other_edu_villages","other_edu_institutions"];med=["hospital_villages","hospitals","dispensary_villages","dispensaries","mcw_villages","mcw_centres","health_centre_villages","health_centres","family_planning_villages","family_planning_centres","other_med_villages","other_med_institutions"];wat=["power_available_villages","power_not_available_villages","tap_water_villages","hand_pipe_villages","well_villages","tank_villages","river_villages","fountain_villages","canal_villages","water_fall_villages","lake_villages","tube_well_villages","other_water_villages","no_water_villages"];rd=["pucca_road_villages","kachcha_road_villages","pucca_kachcha_road_villages","other_road_villages","post_office_villages","post_offices","telegraph_office_villages","telegraph_offices","post_telegraph_villages","post_telegraph_offices","telephone_villages","telephones"]
 sp=[("1","Bilhaur",["202","221","39","47","6","7","...","...","...","..."],["10","10","4","4","6","6","3","3","5","5","...","..."],["36","433","...","1","413","...","7","...","...","...","...","...","...","..."],["54","152","1","74","33","33","...","...","1","1","1","1"]),("2","Derapur",["187","213","36","43","17","17","...","...","1","1"],["8","8","4","4","3","3","1","1","5","5","...","..."],["8","339","...","59","328","1","...","...","...","...","...","...","...","..."],["14","169","...","41","36","36","...","...","1","1","2","2"]),("3","Bhognipur",["163","178","27","32","11","11","...","...","...","..."],["9","9","10","10","1","1","...","...","2","2","...","..."],["19","322","...","1","307","...","...","...","...","...","...","...","...","..."],["56","232","15","4","22","22","...","...","2","2","...","..."]),("4","Akbarpur",["160","167","27","33","10","11","...","...","...","..."],["5","5","6","6","3","3","...","...","1","1","...","..."],["14","284","...","...","288","...","...","...","...","...","...","...","...","..."],["58","67","4","12","34","34","...","...","1","1","1","1"]),("5","Kanpur",["152","170","22","28","3","3","...","...","1","1"],["7","7","7","7","4","4","...","...","3","3","...","..."],["51","235","...","12","248","...","2","...","...","...","...","...","...","..."],["28","131","23","33","37","37","...","...","...","...","...","..."]),("6","Ghatampur",["184","207","33","35","11","11","...","...","1","1"],["4","4","9","9","4","4","3","3","1","1","...","..."],["27","295","...","3","301","...","...","...","...","...","...","15","...","..."],["56","82","4","89","35","35","...","...","1","1","...","..."]),("","District Total",["1,048","1,156","184","218","58","60","...","...","3","3"],["43","43","40","40","21","21","7","7","17","17","...","..."],["155","1,908","...","76","1,885","1","9","...","...","...","...","15","...","..."],["266","833","47","253","197","197","...","...","6","6","4","4"])]
 rows=[]
 for i,(s,n,e,m,w,x) in enumerate(sp):
  r=deepcopy(t);r.update({"sl_no":s,"tahsil_name":n,"row_type":"TOTAL" if i==6 else "ORDINARY","reference_target":"","row_index":str(i),"pdf_id":p,"district":DIST})
  for v,z in zip(edu,e):r[v]=z
  for v,z in zip(med,m):r[v]=z
  for v,z in zip(wat,w):r[v]=z
  for v,z in zip(rd,x):r[v]=z
  clear(r);rows.append(r)
 finish(p,rows,fields,"# Kanpur Tahsil source-checked output\n\nSix Tahsil rows and District Total were transcribed from printed pages 222–223, including the second-page medical and communication continuation bands.\n")

if __name__=="__main__":civic();mededu();tehsil()
