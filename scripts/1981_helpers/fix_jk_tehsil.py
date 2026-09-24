import os, subprocess, re, json, yaml

def extract_exact_blocks(path):
    subprocess.run(['pdftotext', '-layout', path, 'temp.txt'])
    text = open('temp.txt', errors='ignore').read()
    pages = text.split('\x0c')
    
    page_ranges = {}
    for i, page in enumerate(pages[:2]):
        if not page.strip(): continue
        
        # Split page into top and bottom halves (roughly)
        lines = page.split('\n')
        half = len(lines) // 2
        
        blocks_on_page = []
        for part in [lines[:half], lines[half:]]:
            # find the line with the longest sequence of numbers
            best_seq = []
            for line in part:
                tokens = re.findall(r'\b\d+\b|\(\d+\)', line)
                nums = [int(re.sub(r'\D', '', t)) for t in tokens if int(re.sub(r'\D', '', t)) <= 60]
                if len(nums) < 3: continue
                curr = [nums[0]]
                for j in range(1, len(nums)):
                    if 0 < nums[j] - curr[-1] <= 3:
                        curr.append(nums[j])
                    else:
                        if len(curr) > len(best_seq): best_seq = curr
                        curr = [nums[j]]
                if len(curr) > len(best_seq): best_seq = curr
            
            if len(best_seq) >= 4:
                # Based on the sequence, guess the true block
                # The blocks are:
                # B1: starts 1, ends 14 or 16
                # B2: starts 15 or 17, ends 27 or 31
                # B3: starts 28 or 32, ends 42 or 44
                # B4: starts 43 or 45, ends 56
                s = best_seq[0]
                if s <= 3: # B1
                    start = 1
                    # check if 15, 16 are in the block
                    end = 16 if 16 in best_seq or 15 in best_seq else 14
                    # if the sequence physically ended at 15 or 16, it's 16.
                    blocks_on_page.append([start, end])
                elif 14 <= s <= 19: # B2
                    start = 17 if 17 in best_seq else 15
                    end = 31 if 31 in best_seq or 30 in best_seq else 27
                    # In Jammu, B2 is 17 to 31. In Anantnag, 15 to 27.
                    blocks_on_page.append([start, end])
                elif 26 <= s <= 34: # B3
                    start = 32 if 32 in best_seq or 33 in best_seq else 28
                    end = 44 if 44 in best_seq or 43 in best_seq else 42
                    blocks_on_page.append([start, end])
                elif 41 <= s <= 47: # B4
                    start = 45 if 45 in best_seq or 46 in best_seq else 43
                    end = 56
                    blocks_on_page.append([start, end])
                    
        page_ranges[f'page_{i+1}_columns'] = blocks_on_page
    return page_ranges

with open('Jammu_&_Kashmir_Formats/pdf_formats.yaml') as f:
    data = yaml.safe_load(f)

for category in data['categories']:
    if category['name'] == 'Tehsil Appendix':
        all_pdfs = []
        folder = 'Jammu & Kashmir/tehsil appendix'
        for fn in os.listdir(folder):
            if not fn.endswith('.pdf'): continue
            path = os.path.join(folder, fn)
            pag = extract_exact_blocks(path)
            all_pdfs.append({'filename': fn, 'pagination': pag})
            
        # Group them
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
