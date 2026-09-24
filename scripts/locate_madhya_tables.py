from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Madhya Pradesh"
CACHE_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\madhya-locate")


def text_for(source: Path) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = CACHE_DIR / (re.sub(r"[^A-Za-z0-9]+", "_", source.stem) + ".txt")
    if cached.is_file():
        return cached.read_text(encoding="utf-8", errors="replace")
    with tempfile.TemporaryDirectory(prefix="madhya-pdftext-") as temp_dir:
        temp_path = Path(temp_dir) / "source.txt"
        subprocess.run(["pdftotext", "-layout", str(source), str(temp_path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        text = temp_path.read_text(encoding="utf-8", errors="replace")
    cached.write_text(text, encoding="utf-8")
    return text


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u00ad", " ")).strip()


def main() -> None:
    terms = (
        "civic and other", "civic", "statement iv", "statement v", "medical, educational",
        "medical educational", "medical facilities", "educational facilities", "amenities",
        "appendix", "abstract", "tehsil", "tahsil", "taluk", "taluka",
    )
    for source in sorted(SOURCE_DIR.glob("1971 *.pdf"), key=lambda p: p.name.lower()):
        pages = [compact(page) for page in text_for(source).split("\f")]
        print(f"=== {source.name} pages={len(pages)-1} ===")
        for i, text in enumerate(pages, 1):
            low = text.lower()
            if (i <= 60 or any(term in low for term in ("appendix", "amenities", "tehsil", "tahsil", "taluk", "abstract"))) and any(term in low for term in terms):
                print(f"p{i}: {text[:360]}")


if __name__ == "__main__":
    main()
