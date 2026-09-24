import json
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
state = sys.argv[1]
inventory = json.loads((ROOT / 'output' / 'audit' / '1981_inventory.json').read_text(encoding='utf-8'))

for item in inventory:
    if item['state'] != state or not item['eligible']:
        continue
    path = ROOT / item['source']
    doc = fitz.open(path)
    hits = {'civic': [], 'medical': [], 'appendix': []}
    for number, page in enumerate(doc, 1):
        text = page.get_text('text')
        upper = re.sub(r'\s+', ' ', text.upper())
        if 'STATEMENT IV' in upper or 'CIVIC AND OTHER' in upper:
            hits['civic'].append((number, upper[:130]))
        if 'STATEMENT V' in upper or ('MEDICAL' in upper and 'EDUCATIONAL' in upper):
            hits['medical'].append((number, upper[:130]))
        if 'APPENDIX' in upper and ('ABSTRACT' in upper or 'AMENITIES' in upper):
            hits['appendix'].append((number, upper[:130]))
    print(json.dumps({'district': item['district'], 'pages': item['source_pages'], 'hits': {key: [page for page, _ in value] for key, value in hits.items()}}, ensure_ascii=False))
    doc.close()
