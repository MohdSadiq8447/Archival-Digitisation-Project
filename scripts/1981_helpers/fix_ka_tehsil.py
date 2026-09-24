import os, yaml, json

out_dir = 'Karnataka_Formats'

with open(os.path.join(out_dir, 'pdf_formats.yaml')) as f:
    data = yaml.safe_load(f)

for cat in data['categories']:
    if cat['name'] == 'Tehsil Appendix':
        teh_pdfs = []
        for fn in os.listdir('Karnataka/tehsil appendix'):
            if not fn.endswith('.pdf'): continue
            d = fn.replace('1981_', '').replace('_tehsil_appendix.pdf', '')
            
            if d == 'Chikmagalur':
                pag = {
                    'page_1_columns': [[1, 12], [13, 21], [22, 31]],
                    'page_2_columns': [[32, 44], [45, 56]]
                }
            elif d == 'Hassan':
                pag = {
                    'page_1_columns': [[1, 10], [18, 25], [35, 44]],
                    'page_2_columns': [[11, 17], [26, 34], [45, 56]]
                }
            elif d in ['Kolar', 'Mandya']:
                pag = {
                    'page_1_columns': [[1, 17], [18, 34]],
                    'page_2_columns': [[35, 56]]
                }
            elif d == 'Kodagu':
                pag = {
                    'page_1_columns': [[1, 17], [18, 34], [35, 56]]
                }
            else:
                pag = {
                    'page_1_columns': [[1, 10], [18, 25]],
                    'page_2_columns': [[11, 17], [26, 34]],
                    'page_3_columns': [[35, 44]],
                    'page_4_columns': [[45, 56]]
                }
                
            teh_pdfs.append({'filename': fn, 'pagination': pag})

        # Group pdfs
        groups = {}
        for pdf in teh_pdfs:
            k = json.dumps(pdf['pagination'], sort_keys=True)
            if k not in groups: groups[k] = {'pagination': pdf['pagination'], 'filenames': []}
            groups[k]['filenames'].append(pdf['filename'])
        grouped = []
        for grp in groups.values():
            if len(grp['filenames']) == 1: grouped.append({'filename': grp['filenames'][0], 'pagination': grp['pagination']})
            else: grouped.append({'filenames': sorted(grp['filenames']), 'pagination': grp['pagination']})
        grouped.sort(key=lambda x: (-len(x.get('filenames', [x.get('filename')])), x.get('filenames', [x.get('filename')])[0]))
        cat['pdfs'] = grouped

with open(os.path.join(out_dir, 'pdf_formats.yaml'), 'w') as outf:
    yaml.dump(data, outf, sort_keys=False)
