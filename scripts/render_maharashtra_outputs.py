from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Maharashtra"
SCRATCH = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\maharashtra-output-renders-final")
POPPLER = Path(r"C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe")


def main() -> None:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(OUTPUT_DIR.glob("1971_*.pdf"), key=lambda p: p.name.lower())
    cleaned_districts: set[str] = set()
    for pdf in pdfs:
        stem = pdf.stem.removeprefix("1971_")
        for suffix in ("_civic_amenities", "_medical_educational_amenities"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        district = stem
        out = SCRATCH / district.lower()
        out.mkdir(parents=True, exist_ok=True)
        if district not in cleaned_districts:
            for stale in out.glob("*.jpg"):
                stale.unlink()
            cleaned_districts.add(district)
        subprocess.run([str(POPPLER), "-jpeg", "-r", "90", str(pdf), str(out / pdf.stem)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    by_district: dict[str, list[Path]] = {}
    for png in SCRATCH.glob("**/*.jpg"):
        district = png.parent.name
        by_district.setdefault(district, []).append(png)
    for district, images in sorted(by_district.items()):
        images.sort(key=lambda p: p.name.lower())
        thumbs = []
        for image_path in images:
            image = Image.open(image_path).convert("RGB")
            image.thumbnail((360, 500))
            thumbs.append((image_path.name, image.copy()))
        cols, cell_w, cell_h = 3, 380, 540
        sheet = Image.new("RGB", (cols * cell_w, ((len(thumbs) + cols - 1) // cols) * cell_h), "white")
        draw = ImageDraw.Draw(sheet)
        for index, (label, image) in enumerate(thumbs):
            col, row = index % cols, index // cols
            x, y = col * cell_w + 10, row * cell_h + 28
            draw.text((x, row * cell_h + 6), label, fill="black")
            sheet.paste(image, (x, y))
        sheet.save(SCRATCH / f"{district}_contact.jpg", quality=90)
    print(f"Rendered {len(pdfs)} Maharashtra output PDFs to {SCRATCH}")


if __name__ == "__main__":
    main()
