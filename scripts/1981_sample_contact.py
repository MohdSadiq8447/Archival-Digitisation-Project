from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tmp" / "pdfs" / "1981" / "render_compare"
DEST = ROOT / "tmp" / "pdfs" / "1981" / "contact_sheets"
DEST.mkdir(parents=True, exist_ok=True)

for folder in sorted(SOURCE.iterdir()):
    output_files = sorted(folder.glob("output_*.png"), key=lambda p: int(p.stem.split("_")[1]))
    if not output_files:
        continue
    thumbs = []
    for path in output_files:
        image = Image.open(path).convert("RGB")
        image.thumbnail((360, 460))
        tile = Image.new("RGB", (380, 500), "white")
        tile.paste(image, ((380 - image.width) // 2, 28))
        ImageDraw.Draw(tile).text((12, 8), path.stem, fill="black")
        thumbs.append(tile)
    columns = min(3, len(thumbs))
    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * 380, rows * 500), "#dddddd")
    for index, tile in enumerate(thumbs):
        sheet.paste(tile, ((index % columns) * 380, (index // columns) * 500))
    sheet.save(DEST / f"{folder.name}.png")
