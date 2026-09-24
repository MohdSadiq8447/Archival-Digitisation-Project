import csv, os
from copy import deepcopy

base = r'E:\\Archival-Digitisation-Project\\1971_Trimmed_PDF\\Uttar_Pradesh\\outputs\\postprocessed\\up1971-remaining48-novita-sourcechecked-v1\\csv\\bareilly_mededu_1971.csv'
outdir = r'E:\\Archival-Digitisation-Project\\1971_Trimmed_PDF\\Uttar_Pradesh\\outputs\\postprocessed\\up1971-bareilly-mededu-source-checked-v1'
outcsv = os.path.join(outdir, 'csv', 'bareilly_mededu_1971.csv')
with open(base, newline='', encoding='utf-8-sig') as f:
    old = list(csv.DictReader(f)); fields = list(old[0])
template = deepcopy(old[0])
data_vars = ['hospitals_dispensaries','med_beds','degree_colleges','medical_colleges','engg_colleges','polytechnics','vocational_institutes','higher_secondary_schools','middle_schools','primary_schools','other_edu_institutions','stadia','cinemas','auditoria','libraries']
flag_vars = [v+'_flag' for v in data_vars]

def make_parent(identity, serial, rtype, ref, children, beds, inherited):
    result=[]
    for i, child in enumerate(children):
        r=deepcopy(template)
        r.update({'sl_no':serial,'sl_no_flag':'','town_name':identity,'town_name_flag':'','row_type':rtype,'reference_target':ref,'requires_review':'False','parent_row_index':'','subrow_index':str(i),'subrow_count':str(len(children)),'row_index':'','pdf_id':'bareilly_mededu_1971','district':'Bareilly','state':'Uttar Pradesh','year':'1971','format_id':'format_002','table_id':'bareilly_mededu_001'})
        for v in flag_vars: r[v]=''
        for v in data_vars: r[v]=inherited.get(v,'')
        r['hospitals_dispensaries']=child; r['med_beds']=beds[i]
        result.append(r)
    return result

e='...'; rows=[]
rows += make_parent('Aonla','1','ORDINARY','',['H (2)','O (1)','FC (1)'],['21',e,e],{'degree_colleges':e,'medical_colleges':e,'engg_colleges':e,'polytechnics':e,'vocational_institutes':e,'higher_secondary_schools':'1','middle_schools':'3','primary_schools':'12','other_edu_institutions':e,'stadia':'.','cinemas':e,'auditoria':e,'libraries':e})
rows += make_parent('Baheri','2','ORDINARY','',['H (1)','D (1)','HC (1)','FC (1)'],['24',e,e,e],{'degree_colleges':e,'medical_colleges':e,'engg_colleges':e,'polytechnics':e,'vocational_institutes':e,'higher_secondary_schools':'2','middle_schools':'1','primary_schools':'4','other_edu_institutions':e,'stadia':e,'cinemas':'1','auditoria':e,'libraries':e})
for serial in ('3','4'):
    rows += make_parent('Bareilly Cantt.',serial,'CROSS_REFERENCE','Bareilly City Urban Agglomeration',['See'],[''],{})
rows += make_parent('Bareilly','', 'COMPONENT','',['H (9)','D (3)','NH (1)','HC (1)','TBC (1)','F (4)'],['887',e,'10',e,e,e],{'degree_colleges':'ASC (1) A (2)','medical_colleges':'**','engg_colleges':e,'polytechnics':'1','vocational_institutes':'Sh. type (3) O (2)','higher_secondary_schools':'3','middle_schools':'11','primary_schools':'101','other_edu_institutions':e,'stadia':'1','cinemas':'5','auditoria':e,'libraries':'PL (7)'})
rows += make_parent('Bareilly Cantt.','', 'COMPONENT','',['H (1)','O (1)'],['16','2'],{'degree_colleges':e,'medical_colleges':e,'engg_colleges':e,'polytechnics':e,'vocational_institutes':e,'higher_secondary_schools':'4','middle_schools':e,'primary_schools':'3','other_edu_institutions':e,'stadia':e,'cinemas':'1','auditoria':e,'libraries':'RR (3)'})
rows += make_parent('Izatnagar Rly. Settlement','', 'COMPONENT','',['H (1)','D (2)','FC (1)'],['112',e,'2',e],{'degree_colleges':e,'medical_colleges':e,'engg_colleges':e,'polytechnics':e,'vocational_institutes':e,'higher_secondary_schools':e,'middle_schools':'1','primary_schools':'2','other_edu_institutions':'1','stadia':e,'cinemas':e,'auditoria':e,'libraries':e})
rows += make_parent('Northern Rly. Colony','', 'COMPONENT','',['HC (1)','FC (1)'],['2',e],{'degree_colleges':e,'medical_colleges':e,'engg_colleges':e,'polytechnics':e,'vocational_institutes':e,'higher_secondary_schools':'1','middle_schools':e,'primary_schools':'2','other_edu_institutions':e,'stadia':e,'cinemas':e,'auditoria':e,'libraries':e})
rows += make_parent('Faridpur','5','ORDINARY','',['M (1)','FC (1)'],['12',e],{'degree_colleges':e,'medical_colleges':e,'engg_colleges':e,'polytechnics':e,'vocational_institutes':e,'higher_secondary_schools':'1','middle_schools':'2','primary_schools':'3','other_edu_institutions':e,'stadia':e,'cinemas':e,'auditoria':e,'libraries':e})
rows += make_parent('Izatnagar Rly. Settlement','6','CROSS_REFERENCE','Bareilly City Urban Agglomeration',['See'],[''],{})
rows += make_parent('Nawabganj','7','ORDINARY','',['HC (2)','HC (1)'],[e,'14'],{'degree_colleges':e,'medical_colleges':e,'engg_colleges':e,'polytechnics':e,'vocational_institutes':e,'higher_secondary_schools':'1','middle_schools':e,'primary_schools':'2','other_edu_institutions':e,'stadia':e,'cinemas':e,'auditoria':e,'libraries':e})
rows += make_parent('Northern Rly. Colony','8','CROSS_REFERENCE','Bareilly City Urban Agglomeration',['See'],[''],{})

parent=-1; last=None
for i, r in enumerate(rows):
    key=(r['sl_no'], r['town_name'], r['row_type'])
    if key != last: parent += 1; last=key
    r['parent_row_index']=str(parent); r['row_index']=str(i)

os.makedirs(os.path.dirname(outcsv), exist_ok=True)
with open(outcsv,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
os.makedirs(outdir,exist_ok=True)
with open(os.path.join(outdir,'CORRECTION_LOG.csv'),'w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['row_index','variable','original_value','corrected_value','reason'])
    for i,r in enumerate(rows):
        o=old[i] if i<len(old) else {}
        for v in fields:
            if v.endswith('_flag') or v in ('row_index','parent_row_index','subrow_index','subrow_count','requires_review','extracted_at'): continue
            if o.get(v,'') != r.get(v,''):
                w.writerow([i,v,o.get(v,''),r.get(v,''),'300-DPI source pages 8-9; hierarchy and contamination correction'])
with open(os.path.join(outdir,'UNRESOLVED_CELLS.csv'),'w',newline='',encoding='utf-8') as f:
    csv.writer(f).writerow(['row_index','variable','value','reason'])
with open(os.path.join(outdir,'SOURCE_CHECKED_REPORT.md'),'w',encoding='utf-8') as f:
    f.write('# Bareilly MedEdu source-checked output\n\nSource pages 8–9 inspected at 300 DPI. Twelve logical parents and 28 expanded child rows are retained; cross-reference rows point to Bareilly City Urban Agglomeration, Banking content is excluded, and inherited values repeat only within each printed parent.\n')
print('wrote', outcsv, 'rows', len(rows), 'parents', parent+1)
