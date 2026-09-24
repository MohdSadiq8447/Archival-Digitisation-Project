from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path("F:/1971-20260725T134344Z-1-001")
OUT = ROOT / "output" / "pdf" / "1971_trimmed" / "Kerala"
SCRATCH = Path("C:/Users/USER/.codex/visualizations/2026/09/07/01a07b9c-e77d-7511-9f66-aafc92441f90/kerala-output-renders-final")
POPPLER = Path("C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin")
PDFTOPPM = POPPLER / "pdftoppm.exe"
PDFINFO = POPPLER / "pdfinfo.exe"
SCRATCH.mkdir(parents=True, exist_ok=True)
font = ImageFont.load_default()


def page_count(pdf: Path) -> int:
    result = subprocess.run([str(PDFINFO), str(pdf)], capture_output=True, text=True, check=True)
    return next(int(line.split(":", 1)[1].strip()) for line in result.stdout.splitlines() if line.startswith("Pages:"))


def main() -> None:
    for pdf in sorted(OUT.glob("*.pdf")):
        render_dir = SCRATCH / pdf.stem
        render_dir.mkdir(parents=True, exist_ok=True)
        cards: list[Image.Image] = []
        for page in range(1, page_count(pdf) + 1):
            prefix = render_dir / f"p{page:02d}"
            png = Path(str(prefix) + ".png")
            subprocess.run([str(PDFTOPPM), "-f", str(page), "-l", str(page), "-r", "90", "-png", "-singlefile", str(pdf), str(prefix)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rendered = Image.open(png).convert("RGB")
            rendered.thumbnail((460, 650))
            card = Image.new("RGB", (480, 690), "white")
            card.paste(rendered, ((480 - rendered.width) // 2, 28))
            ImageDraw.Draw(card).text((8, 8), f"{pdf.name} page {page}", fill="black", font=font)
            cards.append(card)
        cols = 3
        rows = (len(cards) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 480, rows * 690), "#dddddd")
        for index, card in enumerate(cards):
            sheet.paste(card, ((index % cols) * 480, (index // cols) * 690))
        sheet.save(SCRATCH / f"{pdf.stem}_contact.png")
    print(f"Rendered {len(list(OUT.glob('*.pdf')))} Kerala PDFs into {SCRATCH}")


if __name__ == "__main__":
    main()
