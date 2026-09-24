from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "West Bengal"
SCRATCH = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\wb-candidate-renders")
POPPLER = Path(r"C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe")
RANGES = {
    "Birbhum": (45, 51),
    "Burdwan": (58, 63),
    "Calcutta": (12, 16),
    "Dinajpur": (58, 64),
    "Haora": (39, 49),
    "Hugli": (52, 57),
    "Jalapiguri": (31, 36),
    "Murshidabad": (49, 55),
    "Purullia": (55, 61),
    "Twentyfour Parganas": (106, 123),
}


def source_for(district: str) -> Path:
    return next(SOURCE_DIR.glob(f"1971 {district}*.pdf"))


def main() -> None:
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for district, (start, end) in RANGES.items():
        district_dir = SCRATCH / district.replace(" ", "_")
        district_dir.mkdir(parents=True, exist_ok=True)
        source = source_for(district)
        subprocess.run(
            [str(POPPLER), "-jpeg", "-r", "65", "-f", str(start), "-l", str(end), str(source), str(district_dir / "source")],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        images: list[tuple[str, Image.Image]] = []
        for path in sorted(district_dir.glob("*.jpg"), key=lambda p: p.name.lower()):
            image = Image.open(path).convert("RGB")
            image.thumbnail((265, 355))
            images.append((path.name, image.copy()))
        cols = 4
        cell_w, cell_h = 280, 385
        rows = (len(images) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell_w, max(1, rows) * cell_h), "white")
        draw = ImageDraw.Draw(sheet)
        for index, (label, image) in enumerate(images):
            col, row = index % cols, index // cols
            x, y = col * cell_w + 8, row * cell_h + 22
            draw.text((x, row * cell_h + 5), label, fill="black")
            sheet.paste(image, (x, y))
        sheet.save(SCRATCH / f"{district.replace(' ', '_')}_contact.jpg", quality=88)
    print(f"Rendered West Bengal candidate pages to {SCRATCH}")


if __name__ == "__main__":
    main()
