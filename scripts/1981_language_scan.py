from pathlib import Path
import fitz
import sys

state = sys.argv[1]
for path in sorted(Path('1981', state).glob('*.pdf')):
    doc = fitz.open(path)
    text = ''.join(doc[i].get_text() for i in range(min(20, len(doc))))
    devanagari = sum(0x0900 <= ord(ch) <= 0x097F for ch in text)
    bengali = sum(0x0980 <= ord(ch) <= 0x09FF for ch in text)
    latin = sum(ch.isascii() and ch.isalpha() for ch in text)
    print(f'{path.name}\tpages={len(doc)}\tdev={devanagari}\tben={bengali}\tlatin={latin}')
