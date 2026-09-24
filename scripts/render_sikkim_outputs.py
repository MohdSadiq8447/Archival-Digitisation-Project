from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Sikkim"
SCRATCH = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\sikkim-output-renders-final")
POPPLER = Path(r"C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe")


def main() -> None:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(OUTPUT_DIR.glob("1971_*.pdf"), key=lambda p: p.name.lower())
    for stale in SCRATCH.glob("*.jpg"):
        stale.unlink()
    for pdf in pdfs:
        subprocess.run([str(POPPLER), "-jpeg", "-r", "100", str(pdf), str(SCRATCH / pdf.stem)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    images = []
    for path in sorted(SCRATCH.glob("*.jpg"), key=lambda p: p.name.lower()):
        image = Image.open(path).convert("RGB")
        image.thumbnail((520, 680))
        images.append((path.name, image.copy()))
    sheet = Image.new("RGB", (1080, ((len(images) + 1) // 2) * 740), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(images):
        col, row = index % 2, index // 2
        x, y = col * 540 + 10, row * 740 + 28
        draw.text((x, row * 740 + 6), label, fill="black")
        sheet.paste(image, (x, y))
    sheet.save(SCRATCH / "sikkim_contact.jpg", quality=90)
    print(f"Rendered {len(pdfs)} output PDFs to {SCRATCH}")


if __name__ == "__main__":
    main()
