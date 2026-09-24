import os, json, yaml

data = {'categories': []}

def get_pages(path):
    if not os.path.exists(path): return 0
    import PyPDF2
    with open(path, 'rb') as f:
        return len(PyPDF2.PdfReader(f).pages)

# CIVIC
civic_pdfs = []
for fn in os.listdir('Maharashtra/civic amenities'):
    if not fn.endswith('.pdf'): continue
    # Maharashtra Civic is landscape, so all 19 columns are on a single page, and it repeats per page
    pag = {'page_1_columns': [1, 19]}
    civic_pdfs.append({'filename': fn, 'pagination': pag})
data['categories'].append({'name': 'Civic Amenities', 'pdfs': civic_pdfs})

# MEDEDU
med_pdfs = []
for fn in os.listdir('Maharashtra/mededu'):
    if not fn.endswith('.pdf'): continue
    # Maharashtra MedEdu was portrait and standard!
    pag = {'page_1_columns': [1, 10], 'page_2_columns': [11, 20]}
    med_pdfs.append({'filename': fn, 'pagination': pag})
data['categories'].append({'name': 'Medical and Educational Amenities', 'pdfs': med_pdfs})

# TEHSIL
teh_pdfs = []
if os.path.exists('Maharashtra/tehsil appendix'):
    for fn in os.listdir('Maharashtra/tehsil appendix'):
        if not fn.endswith('.pdf'): continue
        # Maharashtra Tehsil is landscape, 2 pages. So 1-28 and 29-56
        pag = {
            'page_1_columns': [1, 28],
            'page_2_columns': [29, 56]
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

# Copy columns from Arunachal Pradesh
with open('Arunachal_Pradesh_Formats/pdf_formats.yaml') as f:
    ap_data = yaml.safe_load(f)

for cat in ap_data['categories']:
    if cat['name'] == 'Civic Amenities': civic_cols = cat['columns']
    if cat['name'] == 'Medical and Educational Amenities': med_cols = cat['columns']
    if cat['name'] == 'Tehsil Appendix': teh_cols = cat['columns']

for cat in data['categories']:
    if cat['name'] == 'Civic Amenities': cat['columns'] = civic_cols
    elif cat['name'] == 'Medical and Educational Amenities': cat['columns'] = med_cols
    elif cat['name'] == 'Tehsil Appendix': cat['columns'] = teh_cols

os.makedirs('Maharashtra_Formats', exist_ok=True)
with open('Maharashtra_Formats/pdf_formats.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
