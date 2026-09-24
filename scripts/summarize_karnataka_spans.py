from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Karnataka"
CACHE_DIR = Path(
    r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\karnataka-locate"
)


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def text_for(source: Path) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = CACHE_DIR / (re.sub(r"[^A-Za-z0-9]+", "_", source.stem) + ".txt")
    if cached.is_file():
        return cached.read_text(encoding="utf-8", errors="replace")
    with tempfile.TemporaryDirectory(prefix="karnataka-summary-") as temp_dir:
        temp_path = Path(temp_dir) / "source.txt"
        subprocess.run(
            ["pdftotext", "-layout", str(source), str(temp_path)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        text = temp_path.read_text(encoding="utf-8", errors="replace")
    cached.write_text(text, encoding="utf-8")
    return text


def main() -> None:
    for source in sorted(SOURCE_DIR.glob("1971 *.pdf"), key=lambda p: p.name.lower()):
        pages = [compact(page) for page in text_for(source).split("\f")]
        civic = []
        v = []
        trade = []
        appendix = []
        appendix3 = []
        for i, text in enumerate(pages, start=1):
            low = text.lower()
            if "civic" in low and "amenit" in low and i > 15:
                civic.append(i)
            if i > 20 and (("medical facilities" in low and "educational" in low) or ("medical, educational" in low)):
                v.append(i)
            if "trade" in low and "commerce" in low and i > 20:
                trade.append(i)
            if "appendix" in low and ("talukwise" in low or "medical and other amenities" in low or "medical, communication" in low):
                appendix.append(i)
            if "appendix iii" in low or "appendix-iii" in low:
                appendix3.append(i)
        print(
            f"{source.name}\tpages={len(pages)-1}\t"
            f"civic={civic[:12]}\tv={v[:12]}\ttrade={trade[:12]}\t"
            f"amenity_appendix={appendix[:12]}\tappendix3={appendix3[:12]}"
        )
        for page_number in sorted(set(civic[:4] + v[:4] + appendix[:5] + appendix3[:2])):
            print(f"  p{page_number}: {pages[page_number-1][:220]}")


if __name__ == "__main__":
    main()
