"""Read-only PDF evidence collection for reviewed schemas; never rewrites source files."""
import argparse
import hashlib
import json
import re
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'schemas_reviewed'
TABLES = ['civic_amenities', 'medical_educational_amenities']


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def inventory():
    return [r for r in json.loads((ROOT / 'output/audit/1981_full_manifest.json').read_text(encoding='utf-8'))
            if r['status'] == 'Trimmed' and r['table'] in TABLES]


def preflight():
    path = DEST / '_audit/preflight.json'
    if path.exists():
        raise RuntimeError('Preflight exists: do not replace the before-state snapshot.')
    rows = inventory()
    actual = set()
    for category in ['civic amenities', 'mededu']:
        actual.update(str(p.relative_to(ROOT)).replace('\\', '/') for p in
                      (ROOT / 'output/pdf/1981_trimmed').glob('*/' + category + '/*.pdf'))
    assert actual == {r['output'] for r in rows}
    entries = []
    for r in rows:
        with fitz.open(ROOT / r['output']) as doc:
            count = len(doc)
        entries.append({k: r[k] for k in ['state', 'district', 'table', 'output', 'source', 'source_pages_selected']})
        entries[-1].update(page_count=count, manifest_page_count=r['verification']['output_pages'],
                           manifest_count_matches=count == r['verification']['output_pages'],
                           sha256=digest(ROOT / r['output']))
    protected = {}
    for p in (ROOT / 'schemas').rglob('*'):
        if p.is_file():
            protected[str(p)] = digest(p)
    for p in (ROOT / 'output/pdf/1981_trimmed').rglob('*.pdf'):
        protected[str(p)] = digest(p)
    reference = Path('F:/1971-20260725T134344Z-1-001/schemas')
    for p in reference.rglob('*.yaml'):
        protected[str(p)] = digest(p)
    save(path, {'scope': '1981 trimmed civic and mededu only', 'pdf_count': len(entries),
                'page_count': sum(r['page_count'] for r in entries), 'entries': entries,
                'protected_files_sha256': protected})
    print(json.dumps({'pdfs': len(entries), 'pages': sum(r['page_count'] for r in entries),
                      'protected_files': len(protected)}))


def number_rows(page):
    words = page.get_text('words')
    rows = []
    for w in sorted(words, key=lambda w: ((w[1] + w[3]) / 2, w[0])):
        raw = w[4].strip('()[]{}.,: ')
        if not re.fullmatch(r'[0-9Il]{1,2}', raw):
            continue
        n = int(raw.replace('I', '1').replace('l', '1'))
        if not 0 <= n <= 25:
            continue
        y = (w[1] + w[3]) / 2
        row = next((r for r in rows if abs(r['y'] - y) <= 6), None)
        if row is None:
            row = {'y': y, 'words': []}
            rows.append(row)
        row['words'].append((w[0], n, w[4]))
    candidates = []
    for row in rows:
        ordered = sorted(row['words'])
        ns = [v[1] for v in ordered]
        sequential = sum(b == a + 1 for a, b in zip(ns, ns[1:]))
        if sequential >= 3 and len(set(ns)) >= 4:
            candidates.append({'y': round(row['y'], 1), 'numbers': ns,
                               'raw': [v[2] for v in ordered], 'consecutive_links': sequential})
    return candidates


def prepare(state, category, full=False, bottom=False):
    table = TABLES[int(category) - 1]
    rows = sorted((r for r in inventory() if r['state'] == state and r['table'] == table), key=lambda r:r['district'])
    out = DEST / '_evidence' / state / ('format_00' + category + '.json')
    records = []
    tiles = []
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 19)
    for r in rows:
        record = {k:r[k] for k in ['district', 'output', 'source', 'source_pages_selected', 'printed_page_labels']}
        record['sha256'] = digest(ROOT / r['output'])
        record['pages'] = []
        with fitz.open(ROOT / r['output']) as doc:
            for i, p in enumerate(doc):
                text = p.get_text(sort=True)
                candidates = number_rows(p)
                record['pages'].append({'pdf_page': i+1, 'source_page':r['source_pages_selected'][i],
                                       'size_points':list(p.rect), 'rotation':p.rotation,
                                       'text':text, 'number_row_candidates':candidates})
                # Every page gets a labelled visual strip. Full-page mode is used for stacked/mixed panels.
                clip = p.rect if full else (fitz.Rect(0, p.rect.height*.4, p.rect.width, p.rect.height) if bottom
                                           else fitz.Rect(0, 0, p.rect.width, p.rect.height * .46))
                pix = p.get_pixmap(matrix=fitz.Matrix(1.5,1.5), clip=clip, alpha=False)
                im = Image.frombytes('RGB', (pix.width,pix.height), pix.samples)
                width = 950
                im = im.resize((width, round(im.height*width/im.width)))
                tile = Image.new('RGB', (width, im.height+32), 'white')
                tile.paste(im, (0,32))
                ImageDraw.Draw(tile).text((8,5), f"{r['district']} / PDF {i+1} / source {r['source_pages_selected'][i]}", font=font, fill='black')
                tiles.append(tile)
        records.append(record)
    save(out, records)
    image_dir = ROOT / 'tmp/pdfs/1981_schema_review' / state / (category + ('_bottom' if bottom else ''))
    image_dir.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(tiles), 6):
        batch=tiles[start:start+6]
        height=max(im.height for im in batch)
        sheet=Image.new('RGB',(1900,height*((len(batch)+1)//2)),'#dddddd')
        for i,im in enumerate(batch):
            sheet.paste(im,((i%2)*950,(i//2)*height))
        sheet.save(image_dir/f'sheet_{start//6+1:02d}.jpg',quality=88)
    print(f'{state} {table}: {len(records)} PDFs / {len(tiles)} pages / {(len(tiles)+5)//6} sheets')
    for r in records:
        print(r['district'], '; '.join(f"p{p['pdf_page']}=" + str([x['numbers'] for x in p['number_row_candidates']]) for p in r['pages']))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('command', choices=['preflight','prepare'])
    parser.add_argument('--state')
    parser.add_argument('--category', choices=['1','2'])
    parser.add_argument('--full',action='store_true')
    parser.add_argument('--bottom',action='store_true')
    args=parser.parse_args()
    if args.command=='preflight': preflight()
    else: prepare(args.state,args.category,args.full,args.bottom)
