from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path(
    r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\maharashtra-ranges"
)
POPPLER = Path(r"C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe")


def main() -> None:
    district = sys.argv[1]
    first, last = int(sys.argv[2]), int(sys.argv[3])
    source = ROOT / "1971" / "Maharashtra" / f"1971 {district}.pdf"
    out = SCRATCH / district.lower()
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(POPPLER), "-f", str(first), "-l", str(last), "-jpeg", "-r", "75", str(source), str(out / "p")], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    images = sorted(out.glob("p-*.jpg"), key=lambda p: int(p.stem.split("-")[-1]))
    thumbs = []
    for image_path in images:
        image = Image.open(image_path).convert("RGB")
        image.thumbnail((280, 380))
        thumbs.append((image_path.name, image.copy()))
    cols, cell_w, cell_h = 5, 300, 420
    sheet = Image.new("RGB", (cols * cell_w, ((len(thumbs) + cols - 1) // cols) * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(thumbs):
        col, row = index % cols, index // cols
        x, y = col * cell_w + 10, row * cell_h + 28
        draw.text((x, row * cell_h + 6), label, fill="black")
        sheet.paste(image, (x, y))
    sheet.save(out / f"{district.lower()}-{first}-{last}.jpg", quality=90)
    print(out / f"{district.lower()}-{first}-{last}.jpg")


if __name__ == "__main__":
    main()
