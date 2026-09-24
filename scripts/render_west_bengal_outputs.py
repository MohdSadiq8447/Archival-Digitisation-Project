from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "West Bengal"
SCRATCH = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\west-bengal-output-renders")
POPPLER = Path(r"C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe")


def district_name(pdf: Path) -> str:
    stem = pdf.stem.removeprefix("1971_")
    for suffix in ("_medical_educational_amenities", "_civic_amenities", "_tehsil_appendix"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    raise ValueError(f"unexpected output filename: {pdf.name}")


def main() -> None:
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(OUTPUT_DIR.glob("1971_*.pdf"), key=lambda p: p.name.lower())
    by_district: dict[str, list[Path]] = {}
    for pdf in pdfs:
        by_district.setdefault(district_name(pdf), []).append(pdf)

    for district, district_pdfs in sorted(by_district.items()):
        district_dir = SCRATCH / district.replace(" ", "_")
        district_dir.mkdir(parents=True, exist_ok=True)
        for pdf in district_pdfs:
            subprocess.run(
                [str(POPPLER), "-jpeg", "-r", "90", str(pdf), str(district_dir / pdf.stem)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        images: list[tuple[str, Image.Image]] = []
        for path in sorted(district_dir.glob("*.jpg"), key=lambda p: p.name.lower()):
            image = Image.open(path).convert("RGB")
            image.thumbnail((260, 350))
            images.append((path.name, image.copy()))
        cols = 4
        cell_w, cell_h = 275, 380
        rows = (len(images) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell_w, max(1, rows) * cell_h), "white")
        draw = ImageDraw.Draw(sheet)
        for index, (label, image) in enumerate(images):
            col, row = index % cols, index // cols
            x, y = col * cell_w + 8, row * cell_h + 23
            draw.text((x, row * cell_h + 5), label, fill="black")
            sheet.paste(image, (x, y))
        sheet.save(SCRATCH / f"{district.replace(' ', '_')}_contact.jpg", quality=88)

    print(f"Rendered {len(pdfs)} West Bengal output PDFs to {SCRATCH}")


if __name__ == "__main__":
    main()
