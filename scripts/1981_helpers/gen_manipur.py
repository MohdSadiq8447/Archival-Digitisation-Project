import os, yaml

def get_civic():
    pdfs = []
    for fn in os.listdir('Manipur/civic amenities'):
        if not fn.endswith('.pdf'): continue
        pdfs.append({
            'filename': fn,
            'pagination': {'page_1_columns': [[1, 9]], 'page_2_columns': [[10, 19]]}
        })
    return [{'filenames': [p['filename'] for p in pdfs], 'pagination': pdfs[0]['pagination']}]

def get_mededu():
    central = []
    others = []
    for fn in os.listdir('Manipur/mededu'):
        if not fn.endswith('.pdf'): continue
        if 'Central' in fn:
            central.append(fn)
        else:
            others.append(fn)
            
    pdfs = []
    if central:
        pdfs.append({
            'filename': central[0],
            'pagination': {'page_1_columns': [[1, 8]], 'page_2_columns': [[9, 20]]}
        })
    if others:
        pdfs.append({
            'filenames': sorted(others),
            'pagination': {'page_1_columns': [[1, 10]], 'page_2_columns': [[11, 20]]}
        })
    return pdfs

def get_tehsil():
    pdfs = []
    for fn in os.listdir('Manipur/tehsil appendix'):
        if not fn.endswith('.pdf'): continue
        if 'Central' in fn:
            pag = {
                'page_1_columns': [[1, 12], [28, 39], [52, 56]],
                'page_2_columns': [[13, 27], [40, 51]]
            }
        elif 'North' in fn:
            pag = {
                'page_1_columns': [[1, 8], [18, 23], [34, 42]],
                'page_2_columns': [[9, 17], [24, 33], [43, 56]]
            }
        elif 'Tengnoupal' in fn:
            pag = {
                'page_1_columns': [[1, 8], [18, 25], [35, 47]],
                'page_2_columns': [[9, 17], [26, 34], [48, 56]]
            }
        pdfs.append({'filename': fn, 'pagination': pag})
    return pdfs

data = {
    'state': 'Manipur',
    'categories': [
        {
            'name': 'Civic Amenities',
            'pdfs': get_civic()
        },
        {
            'name': 'Medical and Educational Amenities',
            'pdfs': get_mededu()
        },
        {
            'name': 'Tehsil Appendix',
            'pdfs': get_tehsil()
        }
    ]
}

os.makedirs('Manipur_Formats', exist_ok=True)
with open('Manipur_Formats/pdf_formats.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
