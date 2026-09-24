import os, json, yaml

with open('Kerala_Formats/pdf_formats.yaml') as f:
    data = yaml.safe_load(f)

# Define standard columns
civic_cols = [
    {'number': 1, 'name': 'Sl. No.', 'variable_name': 'sl_no'},
    {'number': 2, 'name': 'Class and Name of town', 'variable_name': 'town_class_name'},
    {'number': 3, 'name': 'Civic administration Status (In 1980)', 'variable_name': 'civic_admin_status'},
    {'number': 4, 'name': 'Population', 'variable_name': 'population'},
    {'number': 5, 'name': 'Scheduled castes and Scheduled tribes population', 'variable_name': 'sc_st_population'},
    {'number': 6, 'name': 'Road length (in Kms.)', 'variable_name': 'road_length'},
    {'number': 7, 'name': 'System of Sewerage', 'variable_name': 'sewerage_system'},
    {'number': 8, 'name': 'Number of Latrines - Water borne', 'variable_name': 'latrines_water_borne'},
    {'number': 9, 'name': 'Number of Latrines - Service', 'variable_name': 'latrines_service'},
    {'number': 10, 'name': 'Number of Latrines - Others', 'variable_name': 'latrines_others'},
    {'number': 11, 'name': 'Method of disposal of night soil', 'variable_name': 'night_soil_disposal'},
    {'number': 12, 'name': 'Protected water supply - Source of supply', 'variable_name': 'water_supply_source'},
    {'number': 13, 'name': 'Protected water supply - System of storage with Capacity (in 1,000 Litres)', 'variable_name': 'water_supply_storage_capacity'},
    {'number': 14, 'name': 'Fire fighting service', 'variable_name': 'fire_fighting_service'},
    {'number': 15, 'name': 'Electrification (Number of Connections) - Domestic', 'variable_name': 'electrification_domestic'},
    {'number': 16, 'name': 'Electrification (Number of Connections) - Industrial', 'variable_name': 'electrification_industrial'},
    {'number': 17, 'name': 'Electrification (Number of Connections) - Commercial', 'variable_name': 'electrification_commercial'},
    {'number': 18, 'name': 'Electrification (Number of Connections) - Road Lighting (Points)', 'variable_name': 'electrification_road_lighting'},
    {'number': 19, 'name': 'Electrification (Number of Connections) - Others', 'variable_name': 'electrification_others'}
]

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
    {'number': 11, 'name': 'Higher secondary/ Inter/ Junior College', 'variable_name': 'higher_secondary_inter_junior_college'},
    {'number': 12, 'name': 'Secondary/ Matriculation', 'variable_name': 'secondary_matriculation'},
    {'number': 13, 'name': 'Junior secondary and middle schools', 'variable_name': 'junior_secondary_middle_schools'},
    {'number': 14, 'name': 'Primary schools', 'variable_name': 'primary_schools'},
    {'number': 15, 'name': 'Adult literacy classes/Centres, Others (specify)', 'variable_name': 'adult_literacy_classes'},
    {'number': 16, 'name': 'Working womens hostels with number of seats', 'variable_name': 'working_womens_hostels'},
    {'number': 17, 'name': 'Stadia', 'variable_name': 'recreational_stadium'},
    {'number': 18, 'name': 'Cinema', 'variable_name': 'recreational_cinema'},
    {'number': 19, 'name': 'Auditoria/ Drama/ Community halls', 'variable_name': 'recreational_auditoria_drama_hall'},
    {'number': 20, 'name': 'Public libraries including reading rooms', 'variable_name': 'recreational_public_libraries'}
]

teh_cols = [
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
    {'number': 32, 'name': 'MEDICAL - Subsidised medical practitioner - Villages', 'variable_name': 'medical_subsidised_medical_practitioner_villages'},
    {'number': 33, 'name': 'MEDICAL - Subsidised medical practitioner - Institutions', 'variable_name': 'medical_subsidised_medical_practitioner_institutions'},
    {'number': 34, 'name': 'MEDICAL - Others - Villages', 'variable_name': 'medical_others_villages'},
    {'number': 35, 'name': 'MEDICAL - Others - Institutions', 'variable_name': 'medical_others_institutions'},
    {'number': 36, 'name': 'Villages with no Medical Facility', 'variable_name': 'villages_no_medical_facility'},
    {'number': 37, 'name': 'DRINKING WATER - Tap', 'variable_name': 'drinking_water_tap'},
    {'number': 38, 'name': 'DRINKING WATER - Well', 'variable_name': 'drinking_water_well'},
    {'number': 39, 'name': 'DRINKING WATER - Tank', 'variable_name': 'drinking_water_tank'},
    {'number': 40, 'name': 'DRINKING WATER - Tube-well', 'variable_name': 'drinking_water_tube_well'},
    {'number': 41, 'name': 'DRINKING WATER - River', 'variable_name': 'drinking_water_river'},
    {'number': 42, 'name': 'DRINKING WATER - Fountain', 'variable_name': 'drinking_water_fountain'},
    {'number': 43, 'name': 'DRINKING WATER - Canal', 'variable_name': 'drinking_water_canal'},
    {'number': 44, 'name': 'DRINKING WATER - Others', 'variable_name': 'drinking_water_others'},
    {'number': 45, 'name': 'More than one source of any Type', 'variable_name': 'more_than_one_source_any_type'},
    {'number': 46, 'name': 'Villages with no drinking water facility', 'variable_name': 'villages_no_drinking_water'},
    {'number': 47, 'name': 'POST AND TELEGRAPH - Post Office', 'variable_name': 'post_office'},
    {'number': 48, 'name': 'POST AND TELEGRAPH - Telegraph Office', 'variable_name': 'telegraph_office'},
    {'number': 49, 'name': 'POST AND TELEGRAPH - Post and Telegraph Office', 'variable_name': 'post_and_telegraph_office'},
    {'number': 50, 'name': 'POST AND TELEGRAPH - Phone/Telephone Connection', 'variable_name': 'telephone_connection'},
    {'number': 51, 'name': 'Villages with no Post, Telegraph or Telephone facility', 'variable_name': 'villages_no_post_telegraph_telephone'},
    {'number': 52, 'name': 'COMMUNICATIONS - Bus Stop', 'variable_name': 'communications_bus_stop'},
    {'number': 53, 'name': 'COMMUNICATIONS - Railway Station', 'variable_name': 'communications_railway_station'},
    {'number': 54, 'name': 'COMMUNICATIONS - Navigable Water Way', 'variable_name': 'communications_navigable_water_way'},
    {'number': 55, 'name': 'Villages with no communication facility', 'variable_name': 'villages_no_communication'},
    {'number': 56, 'name': 'APPROACH - Pucca Road', 'variable_name': 'approach_pucca_road'},
    {'number': 57, 'name': 'APPROACH - Kacha Road', 'variable_name': 'approach_kacha_road'},
    {'number': 58, 'name': 'Villages with no approach road', 'variable_name': 'villages_no_approach_road'}
]

for cat in data['categories']:
    if cat['name'] == 'Civic Amenities':
        cat['columns'] = civic_cols
        
        # Unpack, fix Trivandrum, repack
        pdfs = []
        for pdf in cat['pdfs']:
            if 'filenames' in pdf:
                for fn in pdf['filenames']:
                    pdfs.append({'filename': fn, 'pagination': pdf['pagination']})
            else:
                pdfs.append({'filename': pdf['filename'], 'pagination': pdf['pagination']})
                
        for pdf in pdfs:
            if pdf['filename'] == '1981_Trivandrum_civic_amenities.pdf':
                pdf['pagination'] = {
                    'page_1_columns': [1, 7],
                    'page_2_columns': [8, 19]
                }
                
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
        cat['pdfs'] = grouped
        
    elif cat['name'] == 'Medical and Educational Amenities':
        cat['columns'] = med_cols
        
        # Unpack, fix Trivandrum, repack
        pdfs = []
        for pdf in cat['pdfs']:
            if 'filenames' in pdf:
                for fn in pdf['filenames']:
                    pdfs.append({'filename': fn, 'pagination': pdf['pagination']})
            else:
                pdfs.append({'filename': pdf['filename'], 'pagination': pdf['pagination']})
                
        for pdf in pdfs:
            if pdf['filename'] == '1981_Trivandrum_medical_educational_amenities.pdf':
                pdf['pagination'] = {
                    'page_1_columns': [[1, 5], [11, 14]],
                    'page_2_columns': [[6, 10], [15, 20]]
                }
                
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
        cat['pdfs'] = grouped
        
    elif cat['name'] == 'Tehsil Appendix':
        cat['columns'] = teh_cols

with open('Kerala_Formats/pdf_formats.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
