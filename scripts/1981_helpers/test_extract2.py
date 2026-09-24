import os, subprocess, re

path = 'Bihar/tehsil appendix/1981_Aurangabad_tehsil_appendix.pdf'
subprocess.run(['pdftotext', '-layout', path, 'temp.txt'])
text = open('temp.txt', errors='ignore').read()
pages = text.split('\x0c')

for i, page in enumerate(pages):
    if not page.strip(): continue
    print(f"Page {i+1}:")
    lines = page.split('\n')
    for line in lines:
        cleaned = re.sub(r'[\d\(\)\s\.,]', '', line)
        if len(cleaned) > 5:
            continue
        
        tokens = re.findall(r'\b\d+\b|\(\d+\)', line)
        if len(tokens) < 3:
            continue
        nums = [int(re.sub(r'\D', '', t)) for t in tokens if int(re.sub(r'\D', '', t)) <= 60]
        if len(nums) < 3:
            continue
            
        # find longest increasing contiguous-ish sequence
        best_seq = []
        curr_seq = [nums[0]]
        for j in range(1, len(nums)):
            diff = nums[j] - curr_seq[-1]
            if 0 < diff <= 4:
                curr_seq.append(nums[j])
            elif nums[j] < curr_seq[-1]: # reset
                if len(curr_seq) > len(best_seq):
                    best_seq = curr_seq
                curr_seq = [nums[j]]
        if len(curr_seq) > len(best_seq):
            best_seq = curr_seq
            
        if len(best_seq) >= 3:
            print(f"  Found line: {line.strip()}")
            print(f"  Extracted range: {best_seq[0]} to {best_seq[-1]}")
