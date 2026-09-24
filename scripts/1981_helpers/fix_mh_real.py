import os, json, yaml

data = {'categories': []}

# CIVIC
civic_pdfs = []
for fn in os.listdir('Maharashtra/civic amenities'):
    if not fn.endswith('.pdf'): continue
    pag = {'page_1_columns': [1, 19]}
    civic_pdfs.append({'filename': fn, 'pagination': pag})

data['categories'].append({'name': 'Civic Amenities', 'pdfs': civic_pdfs})

# MEDEDU
med_pdfs = []
for fn in os.listdir('Maharashtra/mededu'):
    if not fn.endswith('.pdf'): continue
    pag = {'page_1_columns': [1, 10], 'page_2_columns': [11, 20]}
    med_pdfs.append({'filename': fn, 'pagination': pag})

data['categories'].append({'name': 'Medical and Educational Amenities', 'pdfs': med_pdfs})

# TEHSIL
teh_pdfs = []
for fn in os.listdir('Maharashtra/tehsil appendix'):
    if not fn.endswith('.pdf'): continue
    pag = {
        'page_1_columns': [[1, 17], [18, 31]],
        'page_2_columns': [[32, 43], [44, 56]]
    }
    teh_pdfs.append({'filename': fn, 'pagination': pag})

data['categories'].append({'name': 'Tehsil Appendix', 'pdfs': teh_pdfs})

# Group pdfs function
def group_pdfs(pdfs):
    groups = {}
    for pdf in pdfs:
        k = json.dumps(pdf['pagination'], sort_keys=True)
        if k not in groups: groups[k] = {'pagination': pdf['pagination'], 'filenames': []}
        groups[k]['filenames'].append(pdf['filename'])
    grouped = []
    for grp in groups.values():
        if len(grp['filenames']) == 1: grouped.append({'filename': grp['filenames'][0], 'pagination': grp['pagination']})
        else: grouped.append({'filenames': sorted(grp['filenames']), 'pagination': grp['pagination']})
    grouped.sort(key=lambda x: (-len(x.get('filenames', [x.get('filename')])), x.get('filenames', [x.get('filename')])[0]))
    return grouped

for cat in data['categories']:
    cat['pdfs'] = group_pdfs(cat['pdfs'])

# Copy standard columns for Civic and MedEdu
with open('Arunachal_Pradesh_Formats/pdf_formats.yaml') as f:
    ap_data = yaml.safe_load(f)

for cat in ap_data['categories']:
    if cat['name'] == 'Civic Amenities': civic_cols = cat['columns']
    if cat['name'] == 'Medical and Educational Amenities': med_cols = cat['columns']

for cat in data['categories']:
    if cat['name'] == 'Civic Amenities': cat['columns'] = civic_cols
    elif cat['name'] == 'Medical and Educational Amenities': cat['columns'] = med_cols

# Custom Tehsil Columns for Maharashtra
mh_teh_cols = [
    {'number': 1, 'name': 'Sl. No.', 'variable_name': 'sl_no'},
    {'number': 2, 'name': 'Name of Tehsil', 'variable_name': 'tehsil_name'},
    {'number': 3, 'name': 'EDUCATIONAL - Primary School - Villages', 'variable_name': 'educational_primary_school_villages'},
    {'number': 4, 'name': 'EDUCATIONAL - Primary School - Institutions', 'variable_name': 'educational_primary_school_institutions'},
    {'number': 5, 'name': 'EDUCATIONAL - Middle School - Villages', 'variable_name': 'educational_middle_school_villages'},
    {'number': 6, 'name': 'EDUCATIONAL - Middle School - Institutions', 'variable_name': 'educational_middle_school_institutions'},
    {'number': 7, 'name': 'EDUCATIONAL - Matriculation/Secondary/PUC/Intermediate/Junior College - Villages', 'variable_name': 'educational_matriculation_secondary_villages'},
    {'number': 8, 'name': 'EDUCATIONAL - Matriculation/Secondary/PUC/Intermediate/Junior College - Institutions', 'variable_name': 'educational_matriculation_secondary_institutions'},
    {'number': 9, 'name': 'EDUCATIONAL - College (Graduate and above) - Villages', 'variable_name': 'educational_college_villages'},
    {'number': 10, 'name': 'EDUCATIONAL - College (Graduate and above) - Institutions', 'variable_name': 'educational_college_institutions'},
    {'number': 11, 'name': 'EDUCATIONAL - Adult literacy Class/Centres - Villages', 'variable_name': 'educational_adult_literacy_villages'},
    {'number': 12, 'name': 'EDUCATIONAL - Adult literacy Class/Centres - Institutions', 'variable_name': 'educational_adult_literacy_institutions'},
    {'number': 13, 'name': 'EDUCATIONAL - Others - Villages', 'variable_name': 'educational_others_villages'},
    {'number': 14, 'name': 'EDUCATIONAL - Others - Institutions', 'variable_name': 'educational_others_institutions'},
    {'number': 15, 'name': 'Villages with no Educational facilities', 'variable_name': 'villages_no_educational_facility'},
    {'number': 16, 'name': 'MEDICAL - Dispensary - Villages', 'variable_name': 'medical_dispensary_villages'},
    {'number': 17, 'name': 'MEDICAL - Dispensary - Institutions', 'variable_name': 'medical_dispensary_institutions'},
    {'number': 18, 'name': 'MEDICAL - Hospital - Villages', 'variable_name': 'medical_hospital_villages'},
    {'number': 19, 'name': 'MEDICAL - Hospital - Institutions', 'variable_name': 'medical_hospital_institutions'},
    {'number': 20, 'name': 'MEDICAL - Maternity and Child Welfare Centre/Maternity Home/Child Welfare Centre - Villages', 'variable_name': 'medical_maternity_child_welfare_villages'},
    {'number': 21, 'name': 'MEDICAL - Maternity and Child Welfare Centre/Maternity Home/Child Welfare Centre - Institutions', 'variable_name': 'medical_maternity_child_welfare_institutions'},
    {'number': 22, 'name': 'MEDICAL - Primary Health Centre/Health Centre - Villages', 'variable_name': 'medical_primary_health_centre_villages'},
    {'number': 23, 'name': 'MEDICAL - Primary Health Centre/Health Centre - Institutions', 'variable_name': 'medical_primary_health_centre_institutions'},
    {'number': 24, 'name': 'MEDICAL - Family Planning Centre - Villages', 'variable_name': 'medical_family_planning_villages'},
    {'number': 25, 'name': 'MEDICAL - Family Planning Centre - Institutions', 'variable_name': 'medical_family_planning_institutions'},
    {'number': 26, 'name': 'MEDICAL - Primary Health Sub Centre/PHU - Villages', 'variable_name': 'medical_primary_health_sub_centre_villages'},
    {'number': 27, 'name': 'MEDICAL - Primary Health Sub Centre/PHU - Institutions', 'variable_name': 'medical_primary_health_sub_centre_institutions'},
    {'number': 28, 'name': 'MEDICAL - Community Health worker - Villages', 'variable_name': 'medical_community_health_worker_villages'},
    {'number': 29, 'name': 'MEDICAL - Community Health worker - Institutions', 'variable_name': 'medical_community_health_worker_institutions'},
    {'number': 30, 'name': 'MEDICAL - Registered private practitioner - Villages', 'variable_name': 'medical_registered_private_practitioner_villages'},
    {'number': 31, 'name': 'MEDICAL - Registered private practitioner - Institutions', 'variable_name': 'medical_registered_private_practitioner_institutions'},
    {'number': 32, 'name': 'MEDICAL - Others - Villages', 'variable_name': 'medical_others_villages'},
    {'number': 33, 'name': 'MEDICAL - Others - Institutions', 'variable_name': 'medical_others_institutions'},
    {'number': 34, 'name': 'Villages with no Medical Facility', 'variable_name': 'villages_no_medical_facility'},
    {'number': 35, 'name': 'DRINKING WATER - Tap', 'variable_name': 'drinking_water_tap'},
    {'number': 36, 'name': 'DRINKING WATER - Well', 'variable_name': 'drinking_water_well'},
    {'number': 37, 'name': 'DRINKING WATER - Tank', 'variable_name': 'drinking_water_tank'},
    {'number': 38, 'name': 'DRINKING WATER - Tube-well', 'variable_name': 'drinking_water_tube_well'},
    {'number': 39, 'name': 'DRINKING WATER - River', 'variable_name': 'drinking_water_river'},
    {'number': 40, 'name': 'DRINKING WATER - Fountain', 'variable_name': 'drinking_water_fountain'},
    {'number': 41, 'name': 'DRINKING WATER - Canal', 'variable_name': 'drinking_water_canal'},
    {'number': 42, 'name': 'DRINKING WATER - Others', 'variable_name': 'drinking_water_others'},
    {'number': 43, 'name': 'More than one source of any Type', 'variable_name': 'more_than_one_source_any_type'},
    {'number': 44, 'name': 'Villages with no drinking water facility', 'variable_name': 'villages_no_drinking_water'},
    {'number': 45, 'name': 'POST AND TELEGRAPH - PO', 'variable_name': 'po'},
    {'number': 46, 'name': 'POST AND TELEGRAPH - TO', 'variable_name': 'to'},
    {'number': 47, 'name': 'POST AND TELEGRAPH - PTO', 'variable_name': 'pto'},
    {'number': 48, 'name': 'POST AND TELEGRAPH - PO and Phone', 'variable_name': 'po_and_phone'},
    {'number': 49, 'name': 'POST AND TELEGRAPH - TO and Phone', 'variable_name': 'to_and_phone'},
    {'number': 50, 'name': 'POST AND TELEGRAPH - PTO & Phone', 'variable_name': 'pto_and_phone'},
    {'number': 51, 'name': 'POST AND TELEGRAPH - Phone', 'variable_name': 'phone'},
    {'number': 52, 'name': 'COMMUNICATIONS - Bus Stop', 'variable_name': 'communications_bus_stop'},
    {'number': 53, 'name': 'COMMUNICATIONS - Railway Station', 'variable_name': 'communications_railway_station'},
    {'number': 54, 'name': 'COMMUNICATIONS - Navigable Waterway', 'variable_name': 'communications_navigable_water_way'},
    {'number': 55, 'name': 'POWER SUPPLY - Available', 'variable_name': 'power_supply_available'},
    {'number': 56, 'name': 'POWER SUPPLY - Not Available', 'variable_name': 'power_supply_not_available'}
]

for cat in data['categories']:
    if cat['name'] == 'Tehsil Appendix':
        cat['columns'] = mh_teh_cols

os.makedirs('Maharashtra_Formats', exist_ok=True)
with open('Maharashtra_Formats/pdf_formats.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
