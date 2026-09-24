import os, json, yaml

with open('Jammu_&_Kashmir_Formats/pdf_formats.yaml') as f:
    data = yaml.safe_load(f)

# The exact mapping dictated by manual inspection and user requests
exact_mappings = {
    '1981_Anantnag_tehsil_appendix.pdf': {'page_1_columns': [[1, 14], [28, 42]], 'page_2_columns': [[15, 27], [43, 56]]},
    '1981_Badgam_tehsil_appendix.pdf': {'page_1_columns': [[1, 14], [28, 42]], 'page_2_columns': [[15, 27], [43, 56]]},
    '1981_Baramula_tehsil_appendix.pdf': {'page_1_columns': [[1, 14], [28, 42]], 'page_2_columns': [[15, 27], [43, 56]]},
    '1981_Doda_tehsil_appendix.pdf': {'page_1_columns': [[1, 16], [30, 42]], 'page_2_columns': [[17, 29], [43, 56]]},
    '1981_Jammu_tehsil_appendix.pdf': {'page_1_columns': [[1, 16], [17, 31]], 'page_2_columns': [[32, 44], [45, 56]]},
    '1981_Kargil_tehsil_appendix.pdf': {'page_1_columns': [[1, 14], [28, 42]], 'page_2_columns': [[15, 27], [43, 56]]},
    '1981_Kathua_tehsil_appendix.pdf': {'page_1_columns': [[1, 16], [32, 44]], 'page_2_columns': [[17, 31], [45, 56]]},
    '1981_Kupwara_tehsil_appendix.pdf': {'page_1_columns': [[1, 14], [28, 42]], 'page_2_columns': [[15, 27], [43, 56]]},
    '1981_Ladakh_tehsil_appendix.pdf': {'page_1_columns': [[1, 14], [28, 42]], 'page_2_columns': [[15, 27], [43, 56]]},
    '1981_Pulwama_tehsil_appendix.pdf': {'page_1_columns': [[1, 14], [28, 42]], 'page_2_columns': [[15, 27], [43, 56]]},
    '1981_Punch_tehsil_appendix.pdf': {'page_1_columns': [[1, 14], [31, 42]], 'page_2_columns': [[15, 30], [43, 56]]},
    '1981_Rajauri_tehsil_appendix.pdf': {'page_1_columns': [[1, 15], [28, 42]], 'page_2_columns': [[16, 27], [43, 56]]},
    '1981_Srinagar_tehsil_appendix.pdf': {'page_1_columns': [[1, 14], [28, 42]], 'page_2_columns': [[15, 27], [43, 56]]}
}

for category in data['categories']:
    if category['name'] == 'Tehsil Appendix':
        all_pdfs = []
        for fn, pag in exact_mappings.items():
            all_pdfs.append({'filename': fn, 'pagination': pag})
            
        groups = {}
        for pdf in all_pdfs:
            key = json.dumps(pdf['pagination'], sort_keys=True)
            if key not in groups: groups[key] = {'pagination': pdf['pagination'], 'filenames': []}
            groups[key]['filenames'].append(pdf['filename'])
            
        new_pdfs_grouped = []
        for grp in groups.values():
            if len(grp['filenames']) == 1: new_pdfs_grouped.append({'filename': grp['filenames'][0], 'pagination': grp['pagination']})
            else: new_pdfs_grouped.append({'filenames': sorted(grp['filenames']), 'pagination': grp['pagination']})
        new_pdfs_grouped.sort(key=lambda x: (-len(x.get('filenames', [x.get('filename')])), x.get('filenames', [x.get('filename')])[0]))
        category['pdfs'] = new_pdfs_grouped

with open('Jammu_&_Kashmir_Formats/pdf_formats.yaml', 'w') as outf:
    yaml.dump(data, outf, sort_keys=False)
