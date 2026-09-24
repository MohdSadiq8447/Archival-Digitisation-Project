import os, subprocess, re, json, yaml

def extract_tehsil(path):
    subprocess.run(['pdftotext', '-layout', path, 'temp.txt'])
    text = open('temp.txt', errors='ignore').read()
    pages = text.split('\x0c')
    
    half_pages = [] # stores dicts: {'page': 1 or 2, 'nums': [list of nums]}
    for i, page in enumerate(pages[:2]):
        if not page.strip(): continue
        lines = page.split('\n')
        half = len(lines) // 2
        for part in [lines[:half], lines[half:]]:
            nums = []
            for line in part:
                tokens = re.findall(r'\b\d+\b|\(\d+\)', line)
                for t in tokens:
                    n = int(re.sub(r'\D', '', t))
                    if 0 < n <= 60:
                        nums.append(n)
            half_pages.append({'page': i+1, 'nums': sorted(list(set(nums)))})
            
    # Classify half-pages into B1, B2, B3, B4 based on median
    blocks = {} # block_id (1..4) -> half_page dict
    for hp in half_pages:
        if not hp['nums']: continue
        median = hp['nums'][len(hp['nums'])//2]
        if median <= 16: bid = 1
        elif 17 <= median <= 31: bid = 2
        elif 32 <= median <= 44: bid = 3
        else: bid = 4
        hp['bid'] = bid
        blocks[bid] = hp
        
    # We must have 4 blocks
    if len(blocks) != 4:
        # fallback if ocr is completely broken
        return {'page_1_columns': [[1, 14], [30, 41]], 'page_2_columns': [[15, 29], [42, 56]]}
        
    # Determine boundaries to tile 1..56
    # We want B1=[1, m1], B2=[m1+1, m2], B3=[m2+1, m3], B4=[m3+1, 56]
    
    def get_min_in_expected_range(bid, exp_min, exp_max):
        valid = [x for x in blocks[bid]['nums'] if exp_min <= x <= exp_max]
        return min(valid) if valid else exp_min

    # For B2, expected start is 15..18
    b2_start = get_min_in_expected_range(2, 15, 18)
    # For B3, expected start is 28..34
    b3_start = get_min_in_expected_range(3, 28, 34)
    # For B4, expected start is 43..46
    b4_start = get_min_in_expected_range(4, 43, 46)
    
    bounds = {
        1: [1, b2_start - 1],
        2: [b2_start, b3_start - 1],
        3: [b3_start, b4_start - 1],
        4: [b4_start, 56]
    }
    
    pag = {}
    for hp in half_pages:
        if 'bid' not in hp: continue
        p = hp['page']
        k = f'page_{p}_columns'
        if k not in pag: pag[k] = []
        pag[k].append(bounds[hp['bid']])
        
    return pag

with open('Jammu_&_Kashmir_Formats/pdf_formats.yaml') as f:
    data = yaml.safe_load(f)

for category in data['categories']:
    if category['name'] == 'Tehsil Appendix':
        all_pdfs = []
        folder = 'Jammu & Kashmir/tehsil appendix'
        for fn in os.listdir(folder):
            if not fn.endswith('.pdf'): continue
            path = os.path.join(folder, fn)
            pag = extract_tehsil(path)
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
