from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Orissa"
SCRATCH = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\orissa-output-renders-final")
POPPLER = Path(r"C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe")


def main() -> None:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(OUTPUT_DIR.glob("1971_*.pdf"), key=lambda p: p.name.lower())
    out = SCRATCH / "puri"
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*.jpg"):
        stale.unlink()
    for pdf in pdfs:
        subprocess.run([str(POPPLER), "-jpeg", "-r", "100", str(pdf), str(out / pdf.stem)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    images = sorted(out.glob("*.jpg"), key=lambda p: p.name.lower())
    thumbs = []
    for image_path in images:
        image = Image.open(image_path).convert("RGB")
        image.thumbnail((420, 560))
        thumbs.append((image_path.name, image.copy()))
    cols, cell_w, cell_h = 3, 440, 600
    sheet = Image.new("RGB", (cols * cell_w, ((len(thumbs) + cols - 1) // cols) * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(thumbs):
        col, row = index % cols, index // cols
        x, y = col * cell_w + 10, row * cell_h + 28
        draw.text((x, row * cell_h + 6), label, fill="black")
        sheet.paste(image, (x, y))
    sheet.save(SCRATCH / "puri_contact.jpg", quality=90)
    print(f"Rendered {len(pdfs)} Orissa output PDFs to {SCRATCH}")


if __name__ == "__main__":
    main()
