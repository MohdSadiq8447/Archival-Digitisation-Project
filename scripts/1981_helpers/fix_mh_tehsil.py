import os, json, yaml

with open('Maharashtra_Formats/pdf_formats.yaml') as f:
    data = yaml.safe_load(f)

dists_34 = [
    '1981_Bhandara_tehsil_appendix.pdf',
    '1981_Bid_tehsil_appendix.pdf',
    '1981_Dhule_tehsil_appendix.pdf',
    '1981_Parbhani_tehsil_appendix.pdf'
]

teh_pdfs = []
for fn in os.listdir('Maharashtra/tehsil appendix'):
    if not fn.endswith('.pdf'): continue
    if fn in dists_34:
        pag = {
            'page_1_columns': [[1, 17], [18, 34]],
            'page_2_columns': [[35, 44], [45, 56]]
        }
    else:
        pag = {
            'page_1_columns': [[1, 17], [18, 31]],
            'page_2_columns': [[32, 43], [44, 56]]
        }
    teh_pdfs.append({'filename': fn, 'pagination': pag})

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
    if cat['name'] == 'Tehsil Appendix':
        cat['pdfs'] = group_pdfs(teh_pdfs)

with open('Maharashtra_Formats/pdf_formats.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
