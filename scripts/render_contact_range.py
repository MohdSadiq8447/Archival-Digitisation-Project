from __future__ import annotations

import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw


source = Path(sys.argv[1])
output = Path(sys.argv[2])
start = int(sys.argv[3])
end = int(sys.argv[4])
dpi = int(sys.argv[5]) if len(sys.argv) > 5 else 100
scale = dpi / 72
document = fitz.open(source)
images = []
for number in range(start, min(end, len(document)) + 1):
    pixmap = document[number - 1].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    image.thumbnail((700, 950))
    canvas = Image.new("RGB", (720, 990), "white")
    canvas.paste(image, ((720 - image.width) // 2, 28))
    ImageDraw.Draw(canvas).text((12, 8), f"source page {number}", fill="black")
    images.append(canvas)
document.close()
columns = 3
rows = (len(images) + columns - 1) // columns
sheet = Image.new("RGB", (columns * 720, rows * 990), "#dddddd")
for position, image in enumerate(images):
    sheet.paste(image, ((position % columns) * 720, (position // columns) * 990))
output.parent.mkdir(parents=True, exist_ok=True)
sheet.save(output)
print(output)
