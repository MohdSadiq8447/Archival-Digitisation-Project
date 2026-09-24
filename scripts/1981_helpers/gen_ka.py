import os, yaml, re, json, subprocess

out_dir = 'Karnataka_Formats'
os.makedirs(out_dir, exist_ok=True)

with open('Karnataka/1981_Karnataka_manifest.json') as f:
    manifest = json.load(f)
    
page_counts = {}
for item in manifest:
    if item['verification']:
        page_counts[(item['table'], item['district'])] = item['verification']['output_pages']

data = {'categories': []}

# Civic Amenities
civic_pdfs = []
folder = 'Karnataka/civic amenities'
if os.path.exists(folder):
    for fn in os.listdir(folder):
        if not fn.endswith('.pdf'): continue
        d = fn.replace('1981_', '').replace('_civic_amenities.pdf', '')
        p = page_counts.get(('civic_amenities', d), 2)
        # Based on Belgaum/Bangalore:
        # Page 1: 2 to 10. Page 2: 12 to 18 (and 2, 1). 
        # But for extraction, the bounds are [2, 10] and [11, 18]. Wait, 1 is Sl No.
        # So page 1 is [1, 10], page 2 is [11, 18].
        pag = {}
        if p == 1: pag['page_1_columns'] = [1, 18]
        else:
            for i in range(1, p+1):
                if i % 2 != 0: pag[f'page_{i}_columns'] = [1, 10]
                else: pag[f'page_{i}_columns'] = [11, 18]
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

data['categories'].append({
    'name': 'Civic Amenities',
    'description': 'Format for civic amenities tables.',
    'pdfs': civic_pdfs,
    'columns': civic_cols
})

# MedEdu
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
                if i % 2 != 0: pag[f'page_{i}_columns'] = [1, 7]
                else: pag[f'page_{i}_columns'] = [8, 11]
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

data['categories'].append({
    'name': 'Medical and Educational Amenities',
    'description': 'Format for medical, educational, and recreational facilities tables.',
    'pdfs': med_pdfs,
    'columns': med_cols
})

with open(os.path.join(out_dir, 'pdf_formats.yaml'), 'w') as outf:
    yaml.dump(data, outf, sort_keys=False)
