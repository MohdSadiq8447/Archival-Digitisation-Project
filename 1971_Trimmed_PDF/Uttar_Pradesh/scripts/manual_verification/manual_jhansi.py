import csv, os
from copy import deepcopy

ROOT=r"E:\\Archival-Digitisation-Project\\1971_Trimmed_PDF\\Uttar_Pradesh\\outputs\\postprocessed"; DIST="Jhansi"
def load(pdf):
 p=os.path.join(ROOT,f"up1971-{pdf}-regex-cleaned-v1","csv",f"{pdf}.csv")
 with open(p,encoding="utf-8-sig",newline="") as f:r=csv.DictReader(f);return list(r),list(r.fieldnames or [])
def clear(r):
 for k in r:
  if k.endswith("_flag"):r[k]=""
 r["requires_review"]="False"
def finish(pdf,rows,fields,report):
 slug=pdf.removesuffix("_1971").replace("_","-");out=os.path.join(ROOT,f"up1971-{slug}-source-checked-v1");os.makedirs(os.path.join(out,"csv"),exist_ok=True)
 with open(os.path.join(out,"csv",f"{pdf}.csv"),"w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)
 old,_=load(pdf)
 with open(os.path.join(out,"CORRECTION_LOG.csv"),"w",encoding="utf-8",newline="") as f:
  w=csv.writer(f);w.writerow(["row_index","variable","original_value","corrected_value","reason"])
  for i,row in enumerate(rows):
   before=old[i] if i<len(old) else {}
   for v in fields:
    if v.endswith("_flag") or v in {"row_index","parent_row_index","subrow_index","subrow_count","requires_review","extracted_at"}:continue
    if before.get(v,"")!=row.get(v,""):w.writerow([i,v,before.get(v,""),row.get(v,""),"300-DPI source inspection and hierarchy/continuation cleanup"])
 with open(os.path.join(out,"UNRESOLVED_CELLS.csv"),"w",encoding="utf-8",newline="") as f:csv.writer(f).writerow(["row_index","variable","value","reason"])
 with open(os.path.join(out,"SOURCE_CHECKED_REPORT.md"),"w",encoding="utf-8") as f:f.write(report)
 print(pdf,len(rows))

def civic():
 pdf="jhansi_civic_1971";old,fields=load(pdf);t=deepcopy(old[0]);vs=["sl_no","town_name","road_length_km","sewerage_drainage_system","water_borne_latrines","service_latrines","other_latrines","night_soil_disposal_method","water_source","water_capacity","fire_service","elec_domestic","elec_industrial","elec_commercial","elec_road_light","elec_other","pucca_road_km","kutcha_road_km"]
 vals=[
 ("1","Babina Cantt.","PR (8) KR (2)","PT/OSD","400","1,395","...","B/HC","W/HP","...","...","256","18","64","32","...","8.0","2.0","ORDINARY",""),
 ("2","Chirgaon","PR (4) KR (2.4)","OSD","...","350","60","B/HC","W/HP","...","...","511","...","27","110","...","4.0","2.4","ORDINARY",""),
 ("3","Gursarai","PR (3.5) KR (4)","PT/OSD","10","225","50","HC","W/HP","...","...","275","...","9","84","...","3.5","4.0","ORDINARY",""),
 ("4","Hansari Gird","PR (4) KR (2)","OSD","...","60","...","B/HC","W/HP","...","...","30","9","8","10","...","4.0","2.0","ORDINARY",""),
 ("5","Jhansi","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Jhansi City Urban Agglomeration"),
 ("6","Jhansi Cantt.","","","","","","","","","","","","","","","","","CROSS_REFERENCE","Jhansi City Urban Agglomeration"),
 ("7","Jhansi Rly. Settlement","","","","","","","","","","","","","","","","CROSS_REFERENCE","Jhansi City Urban Agglomeration"),
 ("","Jhansi City Urban Agglomeration","PR (136.5) KR (52.5)","PT/OSD","2,189","9,053","...","B/HC/HL/MT","W/TW/OHT","5,065,066 Galls.","Yes","10,594","394","344","2,963","...","136.5","52.5","AGGREGATE",""),
 ("(i)","Jhansi","PR (82.0) KR (40.5)","PT/OSD","1,600","5,600","...","B/HC","W/TW/OHT","4,280,000 Galls.","Yes","8,574","371","137","1,800","...","82.0","40.5","COMPONENT",""),
 ("(ii)","Jhansi Cantt.","PR (40) KR (12)","PT/OSD","130","1,820","...","B/HL","W/TW/OHT","48,000 Galls.","...","350","20","200","323","...","40.0","12.0","COMPONENT",""),
 ("(iii)","Jhansi Rly. Settlement","PR (14.5) KR (0)","PT/OSD","459","1,633","...","B/MT","TW/OHT","737,066 Galls.","Yes","1,670","3","7","840","...","14.5","0.0","COMPONENT",""),
 ("8","Lalitpur","PR (13) KR (5.5)","PT/OSD","60","2,000","...","","TW/OHT","350,000 Galls.","...","980","...","34","1,000","...","13.0","5.5","ORDINARY",""),
 ("9","Mauranipur","PR (17) KR (6.5)","PT/OSD","15","3,000","...","B","TW/OHT","200,000 Galls.","...","1,135","11","75","140","...","17.0","6.5","ORDINARY",""),
 ("10","Ranipur","PR (14) KR (6.5)","OSD","...","1,000","...","HC","W/HP","...","...","144","...","13","40","...","14.0","6.5","ORDINARY",""),
 ("11","Samthar","PR (2) KR (1)","OSD","...","235","45","C","TW/OHT","36,000 Galls.","...","650","10","50","100","...","2.0","1.0","ORDINARY",""),
 ("12","Talbehat","PR (1.5) KR (1)","OSD","...","900","...","HC","W/HP","...","...","178","15","20","56","...","1.5","1.0","ORDINARY",""),]
 rows=[]
 for i,v in enumerate(vals):r=deepcopy(t);r.update(dict(zip(vs,v)));r.update({"row_type":v[-2],"reference_target":v[-1],"row_index":str(i),"pdf_id":pdf,"district":DIST});clear(r);rows.append(r)
 finish(pdf,rows,fields,"# Jhansi Civic source-checked output\n\nSixteen identity rows, including the Jhansi City Urban Agglomeration aggregate, three components, and three cross-references, were transcribed from printed pages 10–11.\n")

def mededu():
 pdf="jhansi_mededu_1971";old,fields=load(pdf);t=deepcopy(old[0]);e="...";vs=["hospitals_dispensaries","med_beds","degree_colleges","medical_colleges","engg_colleges","polytechnics","vocational_institutes","higher_secondary_schools","middle_schools","primary_schools","other_edu_institutions","stadia","cinemas","auditoria","libraries"]
 def par(serial,town,typ,ref,ch,beds,inh,pidx):
  out=[]
  for j,(child,bed) in enumerate(zip(ch,beds)):
   r=deepcopy(t);r.update({"sl_no":serial,"town_name":town,"row_type":typ,"reference_target":ref,"parent_row_index":str(pidx),"subrow_index":str(j),"subrow_count":str(len(ch)),"row_index":"","pdf_id":pdf,"district":DIST})
   for v in vs:r[v]=inh.get(v,"")
   r["hospitals_dispensaries"]=child;r["med_beds"]=bed;clear(r);out.append(r)
  return out
 def inh(deg=e,med=e,eng=e,poly=e,voc=e,higher=e,middle=e,primary=e,other=e,stad=e,cin=e,aud=e,lib=e):return {"degree_colleges":deg,"medical_colleges":med,"engg_colleges":eng,"polytechnics":poly,"vocational_institutes":voc,"higher_secondary_schools":higher,"middle_schools":middle,"primary_schools":primary,"other_edu_institutions":other,"stadia":stad,"cinemas":cin,"auditoria":aud,"libraries":lib}
 rows=[]
 rows+=par("1","Babina Cantt.","ORDINARY","",["H (1)","DO (1)"],["10","6"],inh(higher="1",middle="2",primary="5",cin="2"),0)
 rows+=par("2","Chirgaon","ORDINARY","",["H (1)","D (6)","HC (1)","NH (1)","FC (1)"],["8",e,e,e,e],inh(higher="1",middle="1",primary="3",lib="PL (1)"),1)
 rows+=par("3","Gursarai","ORDINARY","",["H (1)","TBC (1)","HC (1)","FC (1)"],["5","1",e,e],inh(higher="1",middle="1",primary="5"),2)
 rows+=par("4","Hansari Gird","ORDINARY","",["D (3)"],[e],inh(middle="2",primary="2"),3)
 rows+=par("5","Jhansi","CROSS_REFERENCE","Jhansi City Urban Agglomeration",["See"],[""],{},4)
 rows+=par("6","Jhansi Cantt.","CROSS_REFERENCE","Jhansi City Urban Agglomeration",["See"],[""],{},5)
 rows+=par("7","Jhansi Rly. Settlement","CROSS_REFERENCE","Jhansi City Urban Agglomeration",["See"],[""],{},6)
 rows+=par("","Jhansi City Urban Agglomeration","AGGREGATE","",["H (13)","D (4)","HC (3)","O (2)","TEC (1)","FC (3)"],["975",e,e,"20","20",e],inh(deg="ASC (2)",higher="31",middle="67",primary="98",other="2",stad="2",cin="7",aud="9",lib="PL (4)"),7)
 rows+=par("(i)","Jhansi","COMPONENT","",["H (7)","O (2)","D (2)","HC (3)","FC (3)","TBC (1)"],["362","20",e,e,e,"20"],inh(deg="ASC (2)",higher="21",middle="43",primary="60",stad="1",cin="6",lib="PL (1)"),8)
 rows+=par("(ii)","Jhansi Cantt.","COMPONENT","",["D (2)","H (2)"],[e,"468"],inh(higher="10",middle="24",primary="34",other="1",cin="1",lib="PL (1)"),9)
 rows+=par("(iii)","Jhansi Rly. Settlement","COMPONENT","",["H (4)","FC (2)"],["145",e],inh(primary="4",other="1",stad="1",aud="3",lib="PL (2)"),10)
 rows+=par("8","Lalitpur","ORDINARY","",["H (3)","FC (2)"],["90",e],inh(higher="4",middle="6",primary="24",other="2",cin="1",lib="PL (1) RR (1)"),11)
 rows+=par("9","Mauranipur","ORDINARY","",["H (2)","FC (1)"],["30",e],inh(higher="3",middle="2",primary="11",other="1",cin="1",lib="PL (1)"),12)
 rows+=par("10","Ranipur","ORDINARY","",[e],[e],inh(middle="1",primary="11"),13)
 rows+=par("11","Samthar","ORDINARY","",["H (2)","D (5)","NH (3)","HC (2)"],["16",e,e,e],inh(higher="1",middle="2",primary="6",other="5",lib="RR (1)"),14)
 rows+=par("12","Talbehat","ORDINARY","",["H (1)"],["6"],inh(higher="2",middle="1",primary="8",other="1",lib="RR (1)"),15)
 for i,r in enumerate(rows):r["row_index"]=str(i)
 finish(pdf,rows,fields,"# Jhansi MedEdu source-checked output\n\nSixteen parent identities and 41 expanded child rows preserve ordinary, cross-reference, aggregate, and component hierarchy from printed page 12. Columns 5–17 are inherited at parent scope from the printed continuation on page 13.\n")

def tehsil():
 pdf="jhansi_tehsil_1971";old,fields=load(pdf);t=deepcopy(old[0]);edu=["junior_basic_villages","junior_basic_schools","senior_basic_villages","senior_basic_schools","higher_secondary_villages","higher_secondary_schools","college_villages","colleges","other_edu_villages","other_edu_institutions"];med=["hospital_villages","hospitals","dispensary_villages","dispensaries","mcw_villages","mcw_centres","health_centre_villages","health_centres","family_planning_villages","family_planning_centres","other_med_villages","other_med_institutions"];wat=["power_available_villages","power_not_available_villages","tap_water_villages","hand_pipe_villages","well_villages","tank_villages","river_villages","fountain_villages","canal_villages","water_fall_villages","lake_villages","tube_well_villages","other_water_villages","no_water_villages"];roads=["pucca_road_villages","kachcha_road_villages","pucca_kachcha_road_villages","other_road_villages","post_office_villages","post_offices","telegraph_office_villages","telegraph_offices","post_telegraph_villages","post_telegraph_offices","telephone_villages","telephones"]
 specs=[
 ("1","Moth",["142","156","25","29","...","...","...","...","...","..."],["6","6","...","...","4","4","...","...","3","3","...","..."],["27","241","...","...","222","...","5","...","1","...","...","...","...","..."],["48","60","...","6","28","28","...","...","2","2","...","..."]),
 ("2","Garautha",["145","154","26","26","4","4","...","...","...","..."],["7","7","1","1","3","3","1","1","...","...","...","..."],["...","233","...","1","207","...","4","...","...","...","...","...","...","..."],["73","116","2","13","29","29","...","...","3","3","3","3"]),
 ("3","Lalitpur",["198","198","22","22","1","1","...","...","...","..."],["4","4","...","...","1","1","1","1","1","1","...","..."],["3","408","...","4","362","...","...","...","...","...","...","...","...","..."],["57","307","...","10","61","61","...","...","1","1","...","..."]),
 ("4","Jhansi",["122","126","14","14","5","5","...","...","...","..."],["13","13","...","...","2","2","1","1","1","1","...","..."],["11","167","...","32","156","...","6","...","1","...","...","...","...","..."],["61","71","4","23","36","36","...","...","1","1","1","1"]),
 ("5","Mauranipur",["125","134","27","27","1","2","...","...","...","..."],["11","11","...","...","4","4","...","...","...","...","...","..."],["3","172","1","...","162","...","...","...","...","...","...","...","...","..."],["42","105","2","6","29","29","...","...","2","2","...","..."]),
 ("7","Mahroni",["175","188","20","21","2","3","...","...","...","..."],["6","6","4","4","8","8","1","1","3","3","...","..."],["...","341","...","4","299","...","2","...","...","...","...","...","...","..."],["3","245","...","...","56","56","...","...","1","1","...","..."]),
 ("","District Total (Rural)",["907","956","134","139","13","15","...","...","...","..."],["47","47","5","5","22","22","4","4","8","8","...","..."],["48","1,562","1","41","1,427","...","17","...","2","...","...","...","...","..."],["334","904","8","58","239","239","...","...","10","10","4","4"])]
 rows=[]
 for i,(s,n,e,m,w,rd) in enumerate(specs):
  r=deepcopy(t);r.update({"sl_no":s,"tahsil_name":n,"row_type":"TOTAL" if i==6 else "ORDINARY","reference_target":"","row_index":str(i),"pdf_id":pdf,"district":DIST})
  for v,x in zip(edu,e):r[v]=x
  for v,x in zip(med,m):r[v]=x
  for v,x in zip(wat,w):r[v]=x
  for v,x in zip(roads,rd):r[v]=x
  clear(r);rows.append(r)
 finish(pdf,rows,fields,"# Jhansi Tahsil source-checked output\n\nSix Tahsil rows and District Total (Rural) were transcribed from printed pages 94–95. The printed serial gap before Mahroni (serial 7) is preserved.\n")

if __name__=="__main__":civic();mededu();tehsil()
