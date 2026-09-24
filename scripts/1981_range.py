from pathlib import Path
import sys
import fitz
import json

ROOT = Path(__file__).resolve().parents[1]
state, district, start, end = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
inventory = json.loads((ROOT / 'output' / 'audit' / '1981_inventory.json').read_text(encoding='utf-8'))
item = next(x for x in inventory if x['state'] == state and x['district'] == district)
doc = fitz.open(ROOT / item['source'])
for n in range(start, min(end, len(doc)) + 1):
    text = ' '.join(doc[n - 1].get_text('text').replace('\x00', ' ').split())
    print(f'{n}: {text[:650]}')
