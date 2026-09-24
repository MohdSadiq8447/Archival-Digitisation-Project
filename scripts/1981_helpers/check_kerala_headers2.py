import os, subprocess, re

def print_headers(path):
    subprocess.run(['pdftotext', '-layout', path, 'temp.txt'])
    text = open('temp.txt', errors='ignore').read()
    pages = text.split('\x0c')
    for i, p in enumerate(pages[:2]):
        seqs = []
        for line in p.split('\n'):
            tokens = re.findall(r'\b\d+\b|\(\d+\)', line)
            nums = [int(re.sub(r'\D', '', t)) for t in tokens if int(re.sub(r'\D', '', t)) <= 60]
            if len(nums) < 3: continue
            curr = [nums[0]]
            for j in range(1, len(nums)):
                if 0 < nums[j] - curr[-1] <= 3: curr.append(nums[j])
                else:
                    if len(curr) >= 3: seqs.append(curr)
                    curr = [nums[j]]
            if len(curr) >= 3: seqs.append(curr)
        print(f"Page {i+1}: {seqs}")

print("Civic Cannanore:")
print_headers('Kerala/civic amenities/1981_Cannanore_civic_amenities.pdf')
print("MedEdu Cannanore:")
print_headers('Kerala/mededu/1981_Cannanore_medical_educational_amenities.pdf')
