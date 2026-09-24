from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path("F:/1971-20260725T134344Z-1-001")
OUT = ROOT / "output" / "pdf" / "1971_trimmed" / "Karnataka"
SCRATCH = Path(
    "C:/Users/USER/.codex/visualizations/2026/09/07/01a07b9c-e77d-7511-9f66-aafc92441f90/karnataka-output-renders-final"
)
POPPLER = Path("C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin")
PDFTOPPM = POPPLER / "pdftoppm.exe"
PDFINFO = POPPLER / "pdfinfo.exe"
SCRATCH.mkdir(parents=True, exist_ok=True)
font = ImageFont.load_default()


def pages_for(pdf: Path) -> int:
    result = subprocess.run([str(PDFINFO), str(pdf)], capture_output=True, text=True, check=True)
    return next(int(line.split(":", 1)[1].strip()) for line in result.stdout.splitlines() if line.startswith("Pages:"))


def make_sheet(images: list[Image.Image], path: Path, cols: int, cell_size: tuple[int, int]) -> None:
    cell_w, cell_h = cell_size
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "#dddddd")
    for index, image in enumerate(images):
        sheet.paste(image, ((index % cols) * cell_w, (index // cols) * cell_h))
    sheet.save(path)


def main() -> None:
    by_district: dict[str, list[Path]] = {}
    for pdf in sorted(OUT.glob("*.pdf")):
        district = pdf.stem.removeprefix("1971_")
        for suffix in ("_civic_amenities", "_medical_educational_amenities", "_tehsil_appendix"):
            if district.endswith(suffix):
                district = district.removesuffix(suffix)
        by_district.setdefault(district, []).append(pdf)

    all_images: list[Image.Image] = []
    for district, pdfs in sorted(by_district.items()):
        district_images: list[Image.Image] = []
        for pdf in sorted(pdfs):
            render_dir = SCRATCH / pdf.stem
            render_dir.mkdir(parents=True, exist_ok=True)
            for page in range(1, pages_for(pdf) + 1):
                prefix = render_dir / f"p{page:02d}"
                png = Path(str(prefix) + ".png")
                if not png.exists():
                    subprocess.run(
                        [str(PDFTOPPM), "-f", str(page), "-l", str(page), "-r", "90", "-png", "-singlefile", str(pdf), str(prefix)],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                rendered = Image.open(png).convert("RGB")
                rendered.thumbnail((460, 650))
                card = Image.new("RGB", (480, 690), "white")
                card.paste(rendered, ((480 - rendered.width) // 2, 28))
                ImageDraw.Draw(card).text((8, 8), f"{pdf.name} page {page}", fill="black", font=font)
                district_images.append(card)
                all_images.append(card.copy())
        make_sheet(district_images, SCRATCH / f"{district}_outputs_contact.png", 3, (480, 690))

    make_sheet(all_images, SCRATCH / "Karnataka_all_outputs_contact.png", 6, (480, 690))
    print(f"Rendered {len(all_images)} pages from {sum(len(v) for v in by_district.values())} PDFs into {SCRATCH}")


if __name__ == "__main__":
    main()
