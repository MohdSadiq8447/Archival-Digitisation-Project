from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\punjab-ranges")
POPPLER = Path(r"C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe")


def main() -> None:
    district = sys.argv[1]
    first, last = int(sys.argv[2]), int(sys.argv[3])
    source = ROOT / "1971" / "Punjab" / f"1971 {district}.pdf"
    out = SCRATCH / district.lower().replace(" ", "_") / f"{first}-{last}"
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("p-*.jpg"):
        stale.unlink()
    subprocess.run([str(POPPLER), "-f", str(first), "-l", str(last), "-jpeg", "-r", "90", str(source), str(out / "p")], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    images = sorted(out.glob("p-*.jpg"), key=lambda p: int(p.stem.split("-")[-1]))
    thumbs = []
    for image_path in images:
        image = Image.open(image_path).convert("RGB")
        image.thumbnail((320, 440))
        thumbs.append((image_path.name, image.copy()))
    cols, cell_w, cell_h = 5, 340, 480
    sheet = Image.new("RGB", (cols * cell_w, ((len(thumbs) + cols - 1) // cols) * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(thumbs):
        col, row = index % cols, index // cols
        x, y = col * cell_w + 10, row * cell_h + 28
        draw.text((x, row * cell_h + 6), label, fill="black")
        sheet.paste(image, (x, y))
    target = out / f"{district.lower().replace(' ', '_')}-{first}-{last}.jpg"
    sheet.save(target, quality=90)
    print(target)


if __name__ == "__main__":
    main()
