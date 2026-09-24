import os, subprocess, re, json

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
                ranges_on_page.append([best_seq[0], best_seq[-1]])
        
        if ranges_on_page:
            page_ranges[f"page_{i+1}_columns"] = ranges_on_page
            
    return page_ranges

print(json.dumps(get_ranges('Bihar/tehsil appendix/1981_Aurangabad_tehsil_appendix.pdf'), indent=2))
print(json.dumps(get_ranges('Bihar/tehsil appendix/1981_Bhojpur_tehsil_appendix.pdf'), indent=2))
print(json.dumps(get_ranges('Bihar/civic amenities/1981_Dhanbad_civic_amenities.pdf'), indent=2))
