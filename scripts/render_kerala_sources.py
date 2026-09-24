from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path("F:/1971-20260725T134344Z-1-001")
SOURCE_DIR = ROOT / "1971" / "Kerala"
SCRATCH = Path("C:/Users/USER/.codex/visualizations/2026/09/07/01a07b9c-e77d-7511-9f66-aafc92441f90/kerala-source-check")
POPPLER = Path("C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin")
PDFTOPPM = POPPLER / "pdftoppm.exe"
SCRATCH.mkdir(parents=True, exist_ok=True)
font = ImageFont.load_default()


spec = importlib.util.spec_from_file_location("extract_kerala_tables", ROOT / "scripts" / "extract_kerala_tables.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def main() -> None:
    for source_name, tables in module.PAGE_MAP.items():
        source = SOURCE_DIR / source_name
        pages = sorted({page for span in tables.values() for page in span})
        cards: list[Image.Image] = []
        for page in pages:
            out_dir = SCRATCH / source.stem / f"p{page:03d}"
            out_dir.mkdir(parents=True, exist_ok=True)
            prefix = out_dir / "page"
            png = Path(str(prefix) + ".png")
            if not png.exists():
                subprocess.run([str(PDFTOPPM), "-f", str(page), "-l", str(page), "-r", "90", "-png", "-singlefile", str(source), str(prefix)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rendered = Image.open(png).convert("RGB")
            rendered.thumbnail((460, 650))
            card = Image.new("RGB", (480, 690), "white")
            card.paste(rendered, ((480 - rendered.width) // 2, 28))
            ImageDraw.Draw(card).text((8, 8), f"{source.name} source page {page}", fill="black", font=font)
            cards.append(card)
        cols = 4
        rows = (len(cards) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 480, rows * 690), "#dddddd")
        for index, card in enumerate(cards):
            sheet.paste(card, ((index % cols) * 480, (index // cols) * 690))
        sheet.save(SCRATCH / f"{source.stem}_source_contact.png")
    print(f"Rendered Kerala source candidate pages into {SCRATCH}")


if __name__ == "__main__":
    main()
