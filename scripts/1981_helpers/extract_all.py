import os, subprocess, re, json, yaml

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
            if len(tokens) < 3:
                continue
            nums = [int(re.sub(r'\D', '', t)) for t in tokens if int(re.sub(r'\D', '', t)) <= 60]
            if len(nums) < 3:
                continue
                
            best_seq = []
            curr_seq = [nums[0]]
            for j in range(1, len(nums)):
                diff = nums[j] - curr_seq[-1]
                if 0 < diff <= 4:
                    curr_seq.append(nums[j])
                elif nums[j] < curr_seq[-1] or diff > 4:
                    if len(curr_seq) > len(best_seq):
                        best_seq = curr_seq
                    curr_seq = [nums[j]]
            if len(curr_seq) > len(best_seq):
                best_seq = curr_seq
                
            if len(best_seq) >= 4:
                # small heuristic: if seq starts with 2, it probably missed 1. 
                start = 1 if best_seq[0] == 2 else best_seq[0]
                ranges_on_page.append([start, best_seq[-1]])
        
        if ranges_on_page:
            # remove duplicates or subsets
            final_ranges = []
            for r in ranges_on_page:
                if not any(r != o and r[0] >= o[0] and r[1] <= o[1] for o in ranges_on_page):
                    if r not in final_ranges:
                        final_ranges.append(r)
            
            # format as flat list of lists if multiple, or just single list if 1
            if len(final_ranges) == 1:
                page_ranges[f"page_{i+1}_columns"] = final_ranges[0]
            else:
                page_ranges[f"page_{i+1}_columns"] = final_ranges
            
    return page_ranges

# Base structure
with open('Arunachal_Pradesh_Formats/pdf_formats.yaml') as f:
    data = yaml.safe_load(f)

# Clear existing pdfs
for cat in data['categories']:
    cat['pdfs'] = []
    if 'default_pagination' in cat:
        del cat['default_pagination']

folders = [
    ('Bihar/civic amenities', 0),
    ('Bihar/mededu', 1),
    ('Bihar/tehsil appendix', 2)
]

for folder, cat_idx in folders:
    if not os.path.exists(folder): continue
    for f in os.listdir(folder):
        if not f.endswith('.pdf'): continue
        path = os.path.join(folder, f)
        pagination = get_ranges(path)
        data['categories'][cat_idx]['pdfs'].append({
            'filename': f,
            'pagination': pagination
        })

with open('Bihar_Formats/pdf_formats.yaml', 'w') as outf:
    yaml.dump(data, outf, sort_keys=False)
