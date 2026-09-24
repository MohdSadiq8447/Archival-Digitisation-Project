from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
state = sys.argv[1]
districts = sys.argv[2:]
inventory = __import__('json').loads((ROOT / 'output' / 'audit' / '1981_inventory.json').read_text(encoding='utf-8'))
targets = set(districts)

for item in inventory:
    if item['state'] != state or not item['eligible'] or (targets and item['district'] not in targets):
        continue
    doc = fitz.open(ROOT / item['source'])
    print(f'\n## {item["district"]} ({len(doc)} pages)')
    for n in range(1, len(doc) + 1):
        text = ' '.join(doc[n - 1].get_text('text').replace('\x00', ' ').split())
        if re.search(r'STATEMENT IV|CIVIC AND OTHER|STATEMENT V|MEDICAL.{0,90}EDUCATIONAL|STATEMENT VI|APPENDIX I|APPENDIX II|TAHSILWISE|TEHSILWISE', text, re.I):
            print(f'{n}: {text[:420]}')
    doc.close()
