import os, json, yaml

# Re-generate the Maharashtra YAML with explicit MedEdu paginations

data = {'categories': []}

# CIVIC (landscape 1-19)
civic_pdfs = []
for fn in os.listdir('Maharashtra/civic amenities'):
    if not fn.endswith('.pdf'): continue
    pag = {'page_1_columns': [1, 19]}
    civic_pdfs.append({'filename': fn, 'pagination': pag})
data['categories'].append({'name': 'Civic Amenities', 'pdfs': civic_pdfs})

# MEDEDU
# Based on the visual and OCR analysis:
# [1, 10], [11, 20]: Akola, Amravati, Buldana, Nagpur (wait, nagpur visually was [1,9][10,20]), Wardha?
# Actually, the safest way is to hardcode based on the task-848 output, but manually corrected based on visual insight.
# If task-848 P2 contained 10, it's [1, 9], [10, 20]. Else [1, 10], [11, 20].

mededu_p2_10 = [
    '1981_Ahmadnagar_medical_educational_amenities.pdf',
    '1981_Bhandara_medical_educational_amenities.pdf',
    '1981_Bid_medical_educational_amenities.pdf',
    '1981_Chandrapur_medical_educational_amenities.pdf',
    '1981_Dhule_medical_educational_amenities.pdf',
    '1981_Greater Maharashtra_medical_educational_amenities.pdf',
    '1981_Jalgaon_medical_educational_amenities.pdf',
    '1981_Kolhapur_medical_educational_amenities.pdf',
    '1981_Nagpur_medical_educational_amenities.pdf',
    '1981_Nasik_medical_educational_amenities.pdf',
    '1981_Osmanabad_medical_educational_amenities.pdf',
    '1981_Parbhani_medical_educational_amenities.pdf',
    '1981_Pune_medical_educational_amenities.pdf',
    '1981_Ratnagiri_medical_educational_amenities.pdf',
    '1981_Sangli_medical_educational_amenities.pdf',
    '1981_Satara_medical_educational_amenities.pdf',
    '1981_Sholapur_medical_educational_amenities.pdf',
    '1981_Thane_medical_educational_amenities.pdf',
    '1981_Yavatmal_medical_educational_amenities.pdf'
]

med_pdfs = []
for fn in os.listdir('Maharashtra/mededu'):
    if not fn.endswith('.pdf'): continue
    if fn in mededu_p2_10:
        pag = {'page_1_columns': [1, 9], 'page_2_columns': [10, 20]}
    else:
        # Akola, Amravati, Buldana, Nanded, Wardha, etc.
        pag = {'page_1_columns': [1, 10], 'page_2_columns': [11, 20]}
    med_pdfs.append({'filename': fn, 'pagination': pag})

data['categories'].append({'name': 'Medical and Educational Amenities', 'pdfs': med_pdfs})

# TEHSIL (landscape, custom)
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

# Read old yaml for columns
with open('Maharashtra_Formats/pdf_formats.yaml') as f:
    old_data = yaml.safe_load(f)

for cat in old_data['categories']:
    if cat['name'] == 'Civic Amenities': civic_cols = cat['columns']
    if cat['name'] == 'Medical and Educational Amenities': med_cols = cat['columns']
    if cat['name'] == 'Tehsil Appendix': teh_cols = cat['columns']

for cat in data['categories']:
    if cat['name'] == 'Civic Amenities': cat['columns'] = civic_cols
    elif cat['name'] == 'Medical and Educational Amenities': cat['columns'] = med_cols
    elif cat['name'] == 'Tehsil Appendix': cat['columns'] = teh_cols

with open('Maharashtra_Formats/pdf_formats.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
