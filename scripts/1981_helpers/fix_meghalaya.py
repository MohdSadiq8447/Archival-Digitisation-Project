import yaml
import os

with open('Madhya_Pradesh_Formats/pdf_formats.yaml') as f:
    mp_data = yaml.safe_load(f)

civic_cols = next(c['columns'] for c in mp_data['categories'] if 'civic' in c['name'].lower())
mededu_cols = next(c['columns'] for c in mp_data['categories'] if 'medical' in c['name'].lower())
tehsil_cols = next(c['columns'] for c in mp_data['categories'] if 'tehsil' in c['name'].lower())

# Fix Meghalaya
with open('Meghalaya_Formats/pdf_formats.yaml') as f:
    megh = yaml.safe_load(f)

for cat in megh['categories']:
    if 'civic' in cat['name'].lower():
        cat['columns'] = civic_cols
    elif 'medical' in cat['name'].lower():
        cat['columns'] = mededu_cols
    elif 'tehsil' in cat['name'].lower():
        cat['columns'] = tehsil_cols

with open('Meghalaya_Formats/pdf_formats.yaml', 'w') as f:
    yaml.dump(megh, f, sort_keys=False)
print("Meghalaya Fixed!")
