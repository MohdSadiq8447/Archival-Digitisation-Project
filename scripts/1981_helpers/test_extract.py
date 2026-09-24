import os, subprocess, re

path = 'Bihar/tehsil appendix/1981_Aurangabad_tehsil_appendix.pdf'
subprocess.run(['pdftotext', '-layout', path, 'temp.txt'])
text = open('temp.txt', errors='ignore').read()
pages = text.split('\x0c')

for i, page in enumerate(pages):
    if not page.strip(): continue
    print(f"Page {i+1}:")
    lines = page.split('\n')
    ranges = []
    for line in lines:
        # Check if line is mostly numbers and parentheses
        cleaned = re.sub(r'[\d\(\)\s\.,]', '', line)
        if len(cleaned) > 5:
            continue
        
        # Extract numbers
        tokens = re.findall(r'\b\d+\b|\(\d+\)', line)
        if len(tokens) < 3:
            continue
        nums = [int(re.sub(r'\D', '', t)) for t in tokens]
        
        # Check if sequence
        seq_count = sum(1 for j in range(1, len(nums)) if 0 < nums[j] - nums[j-1] <= 3)
        if seq_count >= len(nums) // 2:
            ranges.append([nums[0], nums[-1]])
            print(f"  Found line: {line.strip()}")
            print(f"  Extracted range: {nums[0]} to {nums[-1]}")
    
    # Merge overlapping or contiguous ranges if needed, but for now just print
