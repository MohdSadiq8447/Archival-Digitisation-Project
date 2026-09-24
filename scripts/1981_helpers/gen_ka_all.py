import os, yaml, json, copy

out_dir = 'Karnataka_Formats'
os.makedirs(out_dir, exist_ok=True)

with open('Karnataka/1981_Karnataka_manifest.json') as f:
    manifest = json.load(f)
    
page_counts = {}
for item in manifest:
    if item['verification']:
        page_counts[(item['table'], item['district'])] = item['verification']['output_pages']

data = {'categories': []}

# CIVIC AMENITIES
civic_pdfs = []
folder = 'Karnataka/civic amenities'
if os.path.exists(folder):
    for fn in os.listdir(folder):
        if not fn.endswith('.pdf'): continue
        d = fn.replace('1981_', '').replace('_civic_amenities.pdf', '')
        p = page_counts.get(('civic_amenities', d), 2)
        pag = {}
        if p == 1: pag['page_1_columns'] = [1, 18]
        else:
            for i in range(1, p+1):
                if i % 2 != 0: pag[f'page_{i}_columns'] = [[1, 10]]
                else: pag[f'page_{i}_columns'] = [[11, 18]]
        civic_pdfs.append({'filename': fn, 'pagination': pag})

civic_cols = [
    {'number': 1, 'name': 'Sl. No.', 'variable_name': 'sl_no'},
    {'number': 2, 'name': 'Class and Name of town', 'variable_name': 'town_class_name'},
    {'number': 3, 'name': 'Civic administration Status (In 1980)', 'variable_name': 'civic_admin_status'},
    {'number': 4, 'name': 'Population', 'variable_name': 'population'},
    {'number': 5, 'name': 'Road length (in Kms.)', 'variable_name': 'road_length'},
    {'number': 6, 'name': 'System of Sewerage', 'variable_name': 'sewerage_system'},
    {'number': 7, 'name': 'Number of Latrines - Water borne', 'variable_name': 'latrines_water_borne'},
    {'number': 8, 'name': 'Number of Latrines - Service', 'variable_name': 'latrines_service'},
    {'number': 9, 'name': 'Number of Latrines - Others', 'variable_name': 'latrines_others'},
    {'number': 10, 'name': 'Method of disposal of night soil', 'variable_name': 'night_soil_disposal'},
    {'number': 11, 'name': 'Protected water supply - Source of supply', 'variable_name': 'water_supply_source'},
    {'number': 12, 'name': 'Protected water supply - System of storage with Capacity (in 1,000 Litres)', 'variable_name': 'water_supply_storage_capacity'},
    {'number': 13, 'name': 'Fire fighting service', 'variable_name': 'fire_fighting_service'},
    {'number': 14, 'name': 'Electrification (Number of Connections) - Domestic', 'variable_name': 'electrification_domestic'},
    {'number': 15, 'name': 'Electrification (Number of Connections) - Industrial', 'variable_name': 'electrification_industrial'},
    {'number': 16, 'name': 'Electrification (Number of Connections) - Commercial', 'variable_name': 'electrification_commercial'},
    {'number': 17, 'name': 'Electrification (Number of Connections) - Road Lighting (Points)', 'variable_name': 'electrification_road_lighting'},
    {'number': 18, 'name': 'Electrification (Number of Connections) - Others', 'variable_name': 'electrification_others'}
]
data['categories'].append({'name': 'Civic Amenities', 'pdfs': civic_pdfs, 'columns': civic_cols})

# MEDEDU
med_pdfs = []
folder = 'Karnataka/mededu'
if os.path.exists(folder):
    for fn in os.listdir(folder):
        if not fn.endswith('.pdf'): continue
        d = fn.replace('1981_', '').replace('_medical_educational_amenities.pdf', '')
        p = page_counts.get(('medical_educational_amenities', d), 2)
        pag = {}
        if p == 1: pag['page_1_columns'] = [1, 11]
        else:
            for i in range(1, p+1):
                if i % 2 != 0: pag[f'page_{i}_columns'] = [[1, 7]]
                else: pag[f'page_{i}_columns'] = [[8, 11]]
        med_pdfs.append({'filename': fn, 'pagination': pag})

med_cols = [
    {'number': 1, 'name': 'Sl. No.', 'variable_name': 'sl_no'},
    {'number': 2, 'name': 'Class and Name of town', 'variable_name': 'town_class_name'},
    {'number': 3, 'name': 'Population', 'variable_name': 'population'},
    {'number': 4, 'name': 'Hospitals/ Dispensaries/T.B. clinics etc.', 'variable_name': 'hospitals_dispensaries_clinics'},
    {'number': 5, 'name': 'Beds in Medical Institutions noted in Col. 4', 'variable_name': 'beds_in_medical_institutions'},
    {'number': 6, 'name': 'Arts/Science/ Commerce Colleges (of degree level and above)', 'variable_name': 'arts_science_commerce_colleges'},
    {'number': 7, 'name': 'Medical Colleges', 'variable_name': 'medical_colleges'},
    {'number': 8, 'name': 'Engineering Colleges', 'variable_name': 'engineering_colleges'},
    {'number': 9, 'name': 'Polytechnics', 'variable_name': 'polytechnics'},
    {'number': 10, 'name': 'Recognised Shorthand, Typewriting and Vocational training Institutes', 'variable_name': 'shorthand_typewriting_vocational_institutes'},
    {'number': 11, 'name': 'Higher secondary/ Inter/ Junior College', 'variable_name': 'higher_secondary_inter_junior_college'}
]
data['categories'].append({'name': 'Medical and Educational Amenities', 'pdfs': med_pdfs, 'columns': med_cols})

# TEHSIL APPENDIX
teh_pdfs = []
folder = 'Karnataka/tehsil appendix'
if os.path.exists(folder):
    for fn in os.listdir(folder):
        if not fn.endswith('.pdf'): continue
        d = fn.replace('1981_', '').replace('_tehsil_appendix.pdf', '')
        p = page_counts.get(('tehsil_appendix', d), 4)
        pag = {}
        for i in range(1, p+1):
            cycle = i % 4
            if cycle == 1: pag[f'page_{i}_columns'] = [[1, 10], [18, 25]]
            elif cycle == 2: pag[f'page_{i}_columns'] = [[11, 17], [26, 34]]
            elif cycle == 3: pag[f'page_{i}_columns'] = [[35, 44]]
            elif cycle == 0: pag[f'page_{i}_columns'] = [[45, 56]]
        teh_pdfs.append({'filename': fn, 'pagination': pag})

teh_cols = [
    {'number': 1, 'name': 'Sl. No.', 'variable_name': 'sl_no'},
    {'number': 2, 'name': 'Name of Taluk', 'variable_name': 'tehsil_name'},
    {'number': 3, 'name': 'EDUCATIONAL - Primary School - Villages', 'variable_name': 'educational_primary_school_villages'},
    {'number': 4, 'name': 'EDUCATIONAL - Primary School - Institutions', 'variable_name': 'educational_primary_school_institutions'},
    {'number': 5, 'name': 'EDUCATIONAL - Middle School - Villages', 'variable_name': 'educational_middle_school_villages'},
    {'number': 6, 'name': 'EDUCATIONAL - Middle School - Institutions', 'variable_name': 'educational_middle_school_institutions'},
    {'number': 7, 'name': 'EDUCATIONAL - Matriculation/Secondary School - Villages', 'variable_name': 'educational_matriculation_secondary_villages'},
    {'number': 8, 'name': 'EDUCATIONAL - Matriculation/Secondary School - Institutions', 'variable_name': 'educational_matriculation_secondary_institutions'},
    {'number': 9, 'name': 'EDUCATIONAL - Higher Secondary/PUC/Intermediate/Junior College - Villages', 'variable_name': 'educational_higher_secondary_puc_villages'},
    {'number': 10, 'name': 'EDUCATIONAL - Higher Secondary/PUC/Intermediate/Junior College - Institutions', 'variable_name': 'educational_higher_secondary_puc_institutions'},
    {'number': 11, 'name': 'EDUCATIONAL - College (Graduate and above) - Villages', 'variable_name': 'educational_college_villages'},
    {'number': 12, 'name': 'EDUCATIONAL - College (Graduate and above) - Institutions', 'variable_name': 'educational_college_institutions'},
    {'number': 13, 'name': 'EDUCATIONAL - Adult literacy Class/Centres - Villages', 'variable_name': 'educational_adult_literacy_villages'},
    {'number': 14, 'name': 'EDUCATIONAL - Adult literacy Class/Centres - Institutions', 'variable_name': 'educational_adult_literacy_institutions'},
    {'number': 15, 'name': 'EDUCATIONAL - Others - Villages', 'variable_name': 'educational_others_villages'},
    {'number': 16, 'name': 'EDUCATIONAL - Others - Institutions', 'variable_name': 'educational_others_institutions'},
    {'number': 17, 'name': 'Villages with no Educational facilities', 'variable_name': 'villages_no_educational_facility'},
    {'number': 18, 'name': 'MEDICAL - Dispensary - Villages', 'variable_name': 'medical_dispensary_villages'},
    {'number': 19, 'name': 'MEDICAL - Dispensary - Institutions', 'variable_name': 'medical_dispensary_institutions'},
    {'number': 20, 'name': 'MEDICAL - Hospital - Villages', 'variable_name': 'medical_hospital_villages'},
    {'number': 21, 'name': 'MEDICAL - Hospital - Institutions', 'variable_name': 'medical_hospital_institutions'},
    {'number': 22, 'name': 'MEDICAL - Maternity and Child Welfare Centre/Maternity Home/Child Welfare Centre - Villages', 'variable_name': 'medical_maternity_child_welfare_villages'},
    {'number': 23, 'name': 'MEDICAL - Maternity and Child Welfare Centre/Maternity Home/Child Welfare Centre - Institutions', 'variable_name': 'medical_maternity_child_welfare_institutions'},
    {'number': 24, 'name': 'MEDICAL - Primary Health Centre/Health Centre - Villages', 'variable_name': 'medical_primary_health_centre_villages'},
    {'number': 25, 'name': 'MEDICAL - Primary Health Centre/Health Centre - Institutions', 'variable_name': 'medical_primary_health_centre_institutions'},
    {'number': 26, 'name': 'MEDICAL - Family Planning Centre - Villages', 'variable_name': 'medical_family_planning_villages'},
    {'number': 27, 'name': 'MEDICAL - Family Planning Centre - Institutions', 'variable_name': 'medical_family_planning_institutions'},
    {'number': 28, 'name': 'MEDICAL - Primary Health Sub Centre/PHU - Villages', 'variable_name': 'medical_primary_health_sub_centre_villages'},
    {'number': 29, 'name': 'MEDICAL - Primary Health Sub Centre/PHU - Institutions', 'variable_name': 'medical_primary_health_sub_centre_institutions'},
    {'number': 30, 'name': 'MEDICAL - Community Health worker - Villages', 'variable_name': 'medical_community_health_worker_villages'},
    {'number': 31, 'name': 'MEDICAL - Community Health worker - Institutions', 'variable_name': 'medical_community_health_worker_institutions'},
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
    {'number': 45, 'name': 'POST AND TELEGRAPH - Post Office', 'variable_name': 'post_office'},
    {'number': 46, 'name': 'POST AND TELEGRAPH - Telegraph Office', 'variable_name': 'telegraph_office'},
    {'number': 47, 'name': 'POST AND TELEGRAPH - Post and Telegraph Office', 'variable_name': 'post_and_telegraph_office'},
    {'number': 48, 'name': 'POST AND TELEGRAPH - Phone/Telephone Connection', 'variable_name': 'telephone_connection'},
    {'number': 49, 'name': 'Villages with no Post, Telegraph or Telephone facility', 'variable_name': 'villages_no_post_telegraph_telephone'},
    {'number': 50, 'name': 'COMMUNICATIONS - Bus Stop', 'variable_name': 'communications_bus_stop'},
    {'number': 51, 'name': 'COMMUNICATIONS - Railway Station', 'variable_name': 'communications_railway_station'},
    {'number': 52, 'name': 'COMMUNICATIONS - Navigable Water Way', 'variable_name': 'communications_navigable_water_way'},
    {'number': 53, 'name': 'Villages with no communication facility', 'variable_name': 'villages_no_communication'},
    {'number': 54, 'name': 'APPROACH - Pucca Road', 'variable_name': 'approach_pucca_road'},
    {'number': 55, 'name': 'APPROACH - Kacha Road', 'variable_name': 'approach_kacha_road'},
    {'number': 56, 'name': 'Villages with no approach road', 'variable_name': 'villages_no_approach_road'}
]
data['categories'].append({'name': 'Tehsil Appendix', 'pdfs': teh_pdfs, 'columns': teh_cols})

# Group pdfs
for cat in data['categories']:
    groups = {}
    for pdf in cat['pdfs']:
        k = json.dumps(pdf['pagination'], sort_keys=True)
        if k not in groups: groups[k] = {'pagination': pdf['pagination'], 'filenames': []}
        groups[k]['filenames'].append(pdf['filename'])
    grouped = []
    for grp in groups.values():
        if len(grp['filenames']) == 1: grouped.append({'filename': grp['filenames'][0], 'pagination': grp['pagination']})
        else: grouped.append({'filenames': sorted(grp['filenames']), 'pagination': grp['pagination']})
    grouped.sort(key=lambda x: (-len(x.get('filenames', [x.get('filename')])), x.get('filenames', [x.get('filename')])[0]))
    cat['pdfs'] = grouped

with open(os.path.join(out_dir, 'pdf_formats.yaml'), 'w') as outf:
    yaml.dump(data, outf, sort_keys=False)
