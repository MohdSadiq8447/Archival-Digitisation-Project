import os, json, yaml

with open('Kerala_Formats/pdf_formats.yaml') as f:
    data = yaml.safe_load(f)

for cat in data['categories']:
    if cat['name'] == 'Medical and Educational Amenities':
        # Flatten the pdfs
        pdfs = []
        for pdf in cat['pdfs']:
            if 'filenames' in pdf:
                for fn in pdf['filenames']:
                    pdfs.append({'filename': fn, 'pagination': pdf['pagination']})
            else:
                pdfs.append({'filename': pdf['filename'], 'pagination': pdf['pagination']})
                
        # Fix Alleppey MedEdu
        for pdf in pdfs:
            if pdf['filename'] == '1981_Alleppey_medical_educational_amenities.pdf':
                pdf['pagination'] = {
                    'page_1_columns': [1, 5],
                    'page_2_columns': [6, 10],
                    'page_3_columns': [11, 15],
                    'page_4_columns': [16, 20]
                }
                
        # Regroup
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
        cat['pdfs'] = grouped

with open('Kerala_Formats/pdf_formats.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
