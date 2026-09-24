from pathlib import Path
from PIL import Image, ImageDraw

source = Path("tmp/docx/1981_trim_summary")
paths = sorted(source.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
thumb_w = 420
margin = 18
label_h = 28
columns = 2
rows = (len(paths) + columns - 1) // columns
thumbs = []
for path in paths:
    image = Image.open(path).convert("RGB")
    ratio = thumb_w / image.width
    image = image.resize((thumb_w, int(image.height * ratio)))
    canvas = Image.new("RGB", (thumb_w, image.height + label_h), "white")
    canvas.paste(image, (0, label_h))
    ImageDraw.Draw(canvas).text((6, 6), path.stem, fill="black")
    thumbs.append(canvas)
cell_h = max(image.height for image in thumbs)
sheet = Image.new("RGB", (columns * thumb_w + (columns + 1) * margin, rows * cell_h + (rows + 1) * margin), "#EDEDED")
for index, image in enumerate(thumbs):
    x = margin + (index % columns) * (thumb_w + margin)
    y = margin + (index // columns) * (cell_h + margin)
    sheet.paste(image, (x, y))
out = Path("tmp/docx/1981_trim_summary_contact.png")
sheet.save(out)
print(out)
