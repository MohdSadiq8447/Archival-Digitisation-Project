import os, subprocess, re, json, yaml
import sys

state_dir = sys.argv[1]
manifest_file = sys.argv[2]
out_dir = sys.argv[3]

def get_ranges(path):
    subprocess.run(['pdftotext', '-layout', path, 'temp.txt'])
    text = open('temp.txt', errors='ignore').read()
    pages = text.split('\x0c')
    page_ranges = {}
    for i, page in enumerate(pages):
        if not page.strip(): continue
        lines = page.split('\n')
        ranges_on_page = []
        for line in lines:
            tokens = re.findall(r'\b\d+\b|\(\d+\)', line)
            if len(tokens) < 3: continue
            nums = [int(re.sub(r'\D', '', t)) for t in tokens if int(re.sub(r'\D', '', t)) <= 60]
            if len(nums) < 3: continue
            best_seq = []
            curr_seq = [nums[0]]
            for j in range(1, len(nums)):
                diff = nums[j] - curr_seq[-1]
                if 0 < diff <= 4: curr_seq.append(nums[j])
                elif nums[j] < curr_seq[-1] or diff > 4:
                    if len(curr_seq) > len(best_seq): best_seq = curr_seq
                    curr_seq = [nums[j]]
            if len(curr_seq) > len(best_seq): best_seq = curr_seq
            if len(best_seq) >= 4:
                ranges_on_page.append([best_seq[0], best_seq[-1]])
        if ranges_on_page:
            final_ranges = []
            for r in ranges_on_page:
                if not any(r != o and r[0] >= o[0] and r[1] <= o[1] for o in ranges_on_page):
                    if r not in final_ranges: final_ranges.append(r)
            if len(final_ranges) == 1: page_ranges[f"page_{i+1}_columns"] = final_ranges[0]
            else: page_ranges[f"page_{i+1}_columns"] = final_ranges
    return page_ranges

with open(manifest_file) as f:
    manifest = json.load(f)
page_counts = {}
for item in manifest:
    if item['verification']:
        page_counts[(item['table'], item['district'])] = item['verification']['output_pages']

with open('Arunachal_Pradesh_Formats/pdf_formats.yaml') as f:
    data = yaml.safe_load(f)

for category in data['categories']:
    category['pdfs'] = []
    if 'default_pagination' in category: del category['default_pagination']

folders = [(os.path.join(state_dir, 'civic amenities'), 0), 
           (os.path.join(state_dir, 'mededu'), 1), 
           (os.path.join(state_dir, 'tehsil appendix'), 2)]

all_pdfs = [[], [], []]
for folder, cat_idx in folders:
    if not os.path.exists(folder): continue
    for f in os.listdir(folder):
        if not f.endswith('.pdf'): continue
        path = os.path.join(folder, f)
        raw_pag = get_ranges(path)
        
        district = f.replace('1981_', '').replace('_civic_amenities.pdf', '').replace('_medical_educational_amenities.pdf', '').replace('_tehsil_appendix.pdf', '')
        table_id = 'civic_amenities'
        if 'medical' in f: table_id = 'medical_educational_amenities'
        elif 'tehsil' in f: table_id = 'tehsil_appendix'
        
        pages = page_counts.get((table_id, district), 2)
        new_pag = {}
        if table_id == 'civic_amenities':
            if pages == 1: new_pag['page_1_columns'] = [1, 19]
            else:
                for p in range(1, pages + 1):
                    if p % 2 != 0: new_pag[f'page_{p}_columns'] = [1, 10]
                    else: new_pag[f'page_{p}_columns'] = [11, 19]
        elif table_id == 'medical_educational_amenities':
            if state_dir == 'Jammu & Kashmir' and district in ['Jammu', 'Doda']:
                if pages == 1: new_pag['page_1_columns'] = [1, 20]
                else:
                    for p in range(1, pages + 1):
                        if p % 2 != 0: new_pag[f'page_{p}_columns'] = [1, 10]
                        else: new_pag[f'page_{p}_columns'] = [11, 20]
            else:
                if pages == 1: new_pag['page_1_columns'] = [1, 20]
                else:
                    for p in range(1, pages + 1):
                        if p % 2 != 0: new_pag[f'page_{p}_columns'] = [1, 9]
                        else: new_pag[f'page_{p}_columns'] = [10, 20]
        elif table_id == 'tehsil_appendix':
            if pages == 1: new_pag['page_1_columns'] = [1, 56]
            elif pages == 2:
                # Need to tile the 4 blocks
                blocks = []
                for p_num in [1, 2]:
                    r = raw_pag.get(f'page_{p_num}_columns', [])
                    if len(r) > 0 and isinstance(r[0], int): r = [r] # wrap single list
                    for idx, blk in enumerate(r):
                        if len(blk) == 2:
                            blocks.append({'p': p_num, 'idx': idx, 'start': blk[0], 'end': blk[1]})
                
                # If we don't have exactly 4 blocks, fallback to default J&K logic
                if len(blocks) == 4:
                    blocks.sort(key=lambda x: x['start'])
                    blocks[0]['start'] = 1
                    blocks[0]['end'] = blocks[1]['start'] - 1
                    blocks[1]['end'] = blocks[2]['start'] - 1
                    blocks[2]['end'] = blocks[3]['start'] - 1
                    blocks[3]['end'] = 56
                    
                    # Reconstruct new_pag
                    for b in blocks:
                        k = f"page_{b['p']}_columns"
                        if k not in new_pag: new_pag[k] = []
                        new_pag[k].append([b['start'], b['end']])
                        
                    # ensure single list is flattened if only 1 (though there should be 2 per page)
                else:
                    # fallback
                    new_pag['page_1_columns'] = [[1, 14], [30, 41]]
                    new_pag['page_2_columns'] = [[15, 29], [42, 56]]
            else:
                # 4 pages logic
                old_p1 = raw_pag.get('page_1_columns', [1, 14])
                if isinstance(old_p1[0], list): old_p1 = old_p1[0]
                if old_p1[-1] >= 16:
                    new_pag['page_1_columns'] = [1, 17]
                    new_pag['page_2_columns'] = [18, 34]
                    new_pag['page_3_columns'] = [35, 44]
                    new_pag['page_4_columns'] = [45, 56]
                else:
                    new_pag['page_1_columns'] = [1, 14]
                    new_pag['page_2_columns'] = [15, 29]
                    new_pag['page_3_columns'] = [30, 41]
                    new_pag['page_4_columns'] = [42, 56]
        all_pdfs[cat_idx].append({'filename': f, 'pagination': new_pag})

# Grouping
for cat_idx, pdfs in enumerate(all_pdfs):
    groups = {}
    for pdf in pdfs:
        key = json.dumps(pdf['pagination'], sort_keys=True)
        if key not in groups: groups[key] = {'pagination': pdf['pagination'], 'filenames': []}
        groups[key]['filenames'].append(pdf['filename'])
        
    new_pdfs_grouped = []
    for grp in groups.values():
        if len(grp['filenames']) == 1: new_pdfs_grouped.append({'filename': grp['filenames'][0], 'pagination': grp['pagination']})
        else: new_pdfs_grouped.append({'filenames': sorted(grp['filenames']), 'pagination': grp['pagination']})
    new_pdfs_grouped.sort(key=lambda x: (-len(x.get('filenames', [x.get('filename')])), x.get('filenames', [x.get('filename')])[0]))
    data['categories'][cat_idx]['pdfs'] = new_pdfs_grouped

os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, 'pdf_formats.yaml'), 'w') as outf:
    yaml.dump(data, outf, sort_keys=False)
