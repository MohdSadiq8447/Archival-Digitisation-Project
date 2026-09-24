import os, json, yaml

with open('Arunachal_Pradesh_Formats/pdf_formats.yaml') as f:
    ap_data = yaml.safe_load(f)

civic_cols = []
med_cols = []
teh_cols = []

for cat in ap_data['categories']:
    if cat['name'] == 'Civic Amenities': civic_cols = cat['columns']
    if cat['name'] == 'Medical and Educational Amenities': med_cols = cat['columns']
    if cat['name'] == 'Tehsil Appendix': teh_cols = cat['columns']

with open('Kerala_Formats/pdf_formats.yaml') as f:
    ke_data = yaml.safe_load(f)

for cat in ke_data['categories']:
    if cat['name'] == 'Civic Amenities': cat['columns'] = civic_cols
    elif cat['name'] == 'Medical and Educational Amenities': cat['columns'] = med_cols
    elif cat['name'] == 'Tehsil Appendix': cat['columns'] = teh_cols

with open('Kerala_Formats/pdf_formats.yaml', 'w') as f:
    yaml.dump(ke_data, f, sort_keys=False)
