from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf" / "1971_trimmed" / "Tamil Nadu"
SCRATCH = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\tamil-nadu-output-renders-final")
POPPLER = Path(r"C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe")


def main() -> None:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for stale in SCRATCH.glob("*"):
        if stale.is_file():
            stale.unlink()
        elif stale.is_dir():
            for child in stale.glob("*"):
                child.unlink()
            stale.rmdir()

    pdfs = sorted(OUTPUT_DIR.glob("1971_*.pdf"), key=lambda p: p.name.lower())
    by_district: dict[str, list[Path]] = {}
    for pdf in pdfs:
        district = pdf.name.removeprefix("1971_").split("_")[0]
        # District names with spaces need matching against the source/output names.
        district = pdf.stem
        for suffix in ("_medical_educational_amenities", "_civic_amenities", "_tehsil_appendix"):
            if district.endswith(suffix):
                district = district[: -len(suffix)]
                break
        by_district.setdefault(district, []).append(pdf)

    for district, district_pdfs in sorted(by_district.items()):
        district_dir = SCRATCH / district.replace(" ", "_")
        district_dir.mkdir(parents=True, exist_ok=True)
        for pdf in district_pdfs:
            subprocess.run(
                [str(POPPLER), "-jpeg", "-r", "70", str(pdf), str(district_dir / pdf.stem)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        images: list[tuple[str, Image.Image]] = []
        for path in sorted(district_dir.glob("*.jpg"), key=lambda p: p.name.lower()):
            image = Image.open(path).convert("RGB")
            image.thumbnail((300, 400))
            images.append((path.name, image.copy()))
        cols = 4
        cell_w, cell_h = 320, 440
        rows = (len(images) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell_w, max(1, rows) * cell_h), "white")
        draw = ImageDraw.Draw(sheet)
        for index, (label, image) in enumerate(images):
            col, row = index % cols, index // cols
            x, y = col * cell_w + 8, row * cell_h + 24
            draw.text((x, row * cell_h + 5), label, fill="black")
            sheet.paste(image, (x, y))
        sheet.save(SCRATCH / f"{district.replace(' ', '_')}_contact.jpg", quality=88)
    print(f"Rendered {len(pdfs)} output PDFs to {SCRATCH}")


if __name__ == "__main__":
    main()
