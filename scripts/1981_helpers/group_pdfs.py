import yaml, json

with open('Bihar_Formats/pdf_formats.yaml', 'r') as f:
    data = yaml.safe_load(f)

for category in data['categories']:
    groups = {}
    for pdf in category['pdfs']:
        if 'filename' in pdf and 'pagination' in pdf:
            key = json.dumps(pdf['pagination'], sort_keys=True)
            if key not in groups:
                groups[key] = {'pagination': pdf['pagination'], 'filenames': []}
            groups[key]['filenames'].append(pdf['filename'])
    
    # Reconstruct pdfs list
    new_pdfs = []
    for grp in groups.values():
        if len(grp['filenames']) == 1:
            new_pdfs.append({'filename': grp['filenames'][0], 'pagination': grp['pagination']})
        else:
            # Sort filenames for neatness
            new_pdfs.append({'filenames': sorted(grp['filenames']), 'pagination': grp['pagination']})
    
    # Sort new_pdfs by number of filenames descending, then by filename
    new_pdfs.sort(key=lambda x: (-len(x.get('filenames', [x.get('filename')])), x.get('filenames', [x.get('filename')])[0]))
    
    category['pdfs'] = new_pdfs

with open('Bihar_Formats/pdf_formats.yaml', 'w') as outf:
    yaml.dump(data, outf, sort_keys=False)
