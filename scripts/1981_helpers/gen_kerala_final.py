import os, json, yaml

data = {'categories': []}

def get_pages(path):
    if not os.path.exists(path): return 0
    import PyPDF2
    with open(path, 'rb') as f:
        return len(PyPDF2.PdfReader(f).pages)

# CIVIC
civic_pdfs = []
for fn in os.listdir('Kerala/civic amenities'):
    if not fn.endswith('.pdf'): continue
    pag = {'page_1_columns': [1, 10], 'page_2_columns': [11, 19]}
    civic_pdfs.append({'filename': fn, 'pagination': pag})
data['categories'].append({'name': 'Civic Amenities', 'pdfs': civic_pdfs})

# MEDEDU
med_pdfs = []
for fn in os.listdir('Kerala/mededu'):
    if not fn.endswith('.pdf'): continue
    d = fn.split('_')[1]
    p = get_pages(f'Kerala/mededu/{fn}')
    if p == 4:
        if d == 'Trichur':
            pag = {'page_1_columns': [1, 6], 'page_2_columns': [7, 10], 'page_3_columns': [11, 15], 'page_4_columns': [16, 20]}
        else:
            pag = {'page_1_columns': [1, 5], 'page_2_columns': [6, 10], 'page_3_columns': [11, 15], 'page_4_columns': [16, 20]}
    else:
        if d == 'Alleppey':
            pag = {'page_1_columns': [11, 15], 'page_2_columns': [16, 20]}
        else:
            pag = {'page_1_columns': [[1, 5], [11, 15]], 'page_2_columns': [[6, 10], [16, 20]]}
    med_pdfs.append({'filename': fn, 'pagination': pag})
data['categories'].append({'name': 'Medical and Educational Amenities', 'pdfs': med_pdfs})

# TEHSIL
teh_pdfs = []
if os.path.exists('Kerala/tehsil appendix'):
    for fn in os.listdir('Kerala/tehsil appendix'):
        if not fn.endswith('.pdf'): continue
        d = fn.split('_')[1]
        
        if d in ['Ernakulam', 'Kottayam']:
            pag = {'page_1_columns': [[1, 16], [30, 43]], 'page_2_columns': [[17, 29], [44, 56]]}
        elif d == 'Trichur':
            pag = {'page_1_columns': [[1, 14], [28, 41]], 'page_2_columns': [[15, 27], [42, 56]]}
        elif d == 'Wayanad':
            pag = {'page_1_columns': [[1, 12], [28, 40]], 'page_2_columns': [[13, 27], [41, 56]]}
        elif d == 'Trivandrum':
            pag = {'page_1_columns': [1, 29], 'page_2_columns': [30, 56]}
        else:
            pag = {'page_1_columns': [1, 27], 'page_2_columns': [28, 56]}
            
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

os.makedirs('Kerala_Formats', exist_ok=True)
with open('Kerala_Formats/pdf_formats.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
