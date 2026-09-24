import yaml, json

with open('Bihar/1981_Bihar_manifest.json') as f:
    manifest = json.load(f)

# Get page counts
page_counts = {}
for item in manifest:
    if item['verification']:
        page_counts[(item['table'], item['district'])] = item['verification']['output_pages']

with open('Bihar_Formats/pdf_formats.yaml', 'r') as f:
    data = yaml.safe_load(f)

for category in data['categories']:
    cat_name = category['name']
    
    # We will expand all pdfs out, fix them, then regroup
    all_pdfs = []
    for pdf_entry in category['pdfs']:
        filenames = pdf_entry.get('filenames', [pdf_entry.get('filename')])
        for fn in filenames:
            district = fn.replace('1981_', '').replace('_civic_amenities.pdf', '').replace('_medical_educational_amenities.pdf', '').replace('_tehsil_appendix.pdf', '')
            
            # Map table name
            table_id = 'civic_amenities'
            if 'medical' in fn: table_id = 'medical_educational_amenities'
            elif 'tehsil' in fn: table_id = 'tehsil_appendix'
            
            pages = page_counts.get((table_id, district), 2)
            
            new_pag = {}
            if table_id == 'civic_amenities':
                for p in range(1, pages + 1):
                    if p % 2 != 0: new_pag[f'page_{p}_columns'] = [1, 10]
                    else: new_pag[f'page_{p}_columns'] = [11, 19]
            elif table_id == 'medical_educational_amenities':
                for p in range(1, pages + 1):
                    if p % 2 != 0: new_pag[f'page_{p}_columns'] = [1, 10]
                    else: new_pag[f'page_{p}_columns'] = [11, 20]
            elif table_id == 'tehsil_appendix':
                if pages == 2:
                    new_pag['page_1_columns'] = [[1, 14], [30, 41]]
                    new_pag['page_2_columns'] = [[15, 29], [42, 56]]
                else: # 4 pages
                    # Use the old extracted bounds to snap to the correct clean bounds
                    # But since we just want a clean layout, let's use the most common 4-page spread:
                    # Actually let's look at the old pagination from pdf_entry to decide if it's 1-14 or 1-17
                    old_p1 = pdf_entry.get('pagination', {}).get('page_1_columns', [1, 14])
                    # Flatten if it's a list of lists
                    if isinstance(old_p1[0], list): old_p1 = old_p1[0]
                    
                    if old_p1[-1] >= 16: # likely 1-17
                        new_pag['page_1_columns'] = [1, 17]
                        new_pag['page_2_columns'] = [18, 34]
                        new_pag['page_3_columns'] = [35, 44]
                        new_pag['page_4_columns'] = [45, 56]
                    else:
                        new_pag['page_1_columns'] = [1, 14]
                        new_pag['page_2_columns'] = [15, 29]
                        new_pag['page_3_columns'] = [30, 41]
                        new_pag['page_4_columns'] = [42, 56]
            
            all_pdfs.append({'filename': fn, 'pagination': new_pag})
            
    # Group again
    groups = {}
    for pdf in all_pdfs:
        key = json.dumps(pdf['pagination'], sort_keys=True)
        if key not in groups:
            groups[key] = {'pagination': pdf['pagination'], 'filenames': []}
        groups[key]['filenames'].append(pdf['filename'])
        
    new_pdfs_grouped = []
    for grp in groups.values():
        if len(grp['filenames']) == 1:
            new_pdfs_grouped.append({'filename': grp['filenames'][0], 'pagination': grp['pagination']})
        else:
            new_pdfs_grouped.append({'filenames': sorted(grp['filenames']), 'pagination': grp['pagination']})
    
    new_pdfs_grouped.sort(key=lambda x: (-len(x.get('filenames', [x.get('filename')])), x.get('filenames', [x.get('filename')])[0]))
    category['pdfs'] = new_pdfs_grouped

with open('Bihar_Formats/pdf_formats.yaml', 'w') as outf:
    yaml.dump(data, outf, sort_keys=False)
