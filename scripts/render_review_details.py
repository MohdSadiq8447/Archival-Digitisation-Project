"""Render upright derived contact sheets, without changing any source PDF."""
import argparse
import json
from pathlib import Path
import fitz
from PIL import Image, ImageDraw, ImageFont
from review_1981_sources import ROOT, DEST

def run(state, category, rotate):
    evidence = json.loads((DEST / '_evidence' / state / f'format_{category:03d}.json').read_text(encoding='utf-8'))
    dest = ROOT / 'tmp/pdfs/1981_schema_review' / state / f'{category}_upright'
    dest.mkdir(parents=True, exist_ok=True)
    tiles = []
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 24)
    for r in evidence:
        with fitz.open(ROOT / r['output']) as doc:
            for i, page in enumerate(doc):
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                im = Image.frombytes('RGB', (pix.width, pix.height), pix.samples).rotate(rotate, expand=True)
                im = im.resize((1900, round(im.height * 1900 / im.width)))
                tile = Image.new('RGB', (1900, im.height + 40), 'white')
                tile.paste(im, (0, 40))
                ImageDraw.Draw(tile).text((8, 5), f"{r['district']} / PDF {i+1} / source {r['source_pages_selected'][i]}", font=font, fill='black')
                tiles.append(tile)
    for start in range(0, len(tiles), 3):
        batch = tiles[start:start+3]
        sheet = Image.new('RGB', (1900, sum(t.height for t in batch)), 'white')
        y = 0
        for tile in batch:
            sheet.paste(tile, (0, y))
            y += tile.height
        sheet.save(dest / f'sheet_{start//3+1:02d}.jpg', quality=94)
    print(f'{len(tiles)} upright pages in {(len(tiles)+2)//3} sheets: {dest}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', required=True)
    parser.add_argument('--category', required=True, type=int)
    parser.add_argument('--rotate', type=int, default=-90)
    args = parser.parse_args()
    run(args.state, args.category, args.rotate)
