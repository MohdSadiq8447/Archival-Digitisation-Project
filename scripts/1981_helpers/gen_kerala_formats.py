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
        pag = {
            'page_1_columns': [1, 5],
            'page_2_columns': [6, 10],
            'page_3_columns': [11, 15],
            'page_4_columns': [16, 20]
        }
    else:
        # 2 pages. Does it have 1-5 and 11-15 on page 1?
        # Trivandrum, Kottayam, Quilon, Idikki, Kasaragod, Malappuram
        # Actually for all 2-page MedEdu in Kerala, let's look at the blocks.
        if d in ['Alleppey', 'Trichur']: # Wait Trichur has 4 pages
            pag = {
                'page_1_columns': [11, 15],
                'page_2_columns': [16, 20]
            }
        else:
            # We assume it's interleaved like Trivandrum
            pag = {
                'page_1_columns': [[1, 5], [11, 15]],
                'page_2_columns': [[6, 10], [16, 20]]
            }
    med_pdfs.append({'filename': fn, 'pagination': pag})
data['categories'].append({'name': 'Medical and Educational Amenities', 'pdfs': med_pdfs})

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

data['categories'][0]['pdfs'] = group_pdfs(data['categories'][0]['pdfs'])
data['categories'][1]['pdfs'] = group_pdfs(data['categories'][1]['pdfs'])

os.makedirs('Kerala_Formats', exist_ok=True)
with open('Kerala_Formats/pdf_formats.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
