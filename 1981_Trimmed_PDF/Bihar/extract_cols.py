import os, subprocess, re

for f in os.listdir('tehsil appendix'):
    if not f.endswith('.pdf'): continue
    path = os.path.join('tehsil appendix', f)
    subprocess.run(['pdftotext', '-layout', path, 'temp.txt'])
    text = open('temp.txt', errors='ignore').read()
    pages = text.split('\x0c')
    
    print(f"{f}:")
    for i, page in enumerate(pages):
        if not page.strip(): continue
        lines = page.split('\n')
        seq_lines = []
        for line in lines:
            nums = re.findall(r'\b\d+\b', line)
            if len(nums) > 3:
                nums = [int(n) for n in nums]
                # check if mostly sequential
                diffs = [nums[j+1] - nums[j] for j in range(len(nums)-1)]
                if diffs.count(1) > len(nums) / 2: # At least half are sequential
                    seq_lines.append(nums)
        if seq_lines:
            # Join all sequential lines on this page?
            # Actually, in Aurangabad, Page 1 has 1..14 AND 30..41
            # Let's print all valid sequences found on the page
            for seq in seq_lines:
                print(f"  Page {i+1}: {seq[0]} to {seq[-1]}")
        else:
            print(f"  Page {i+1}: ?")
