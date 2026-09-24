from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Kerala"
CACHE_DIR = Path(
    r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\kerala-locate"
)


def text_for(source: Path) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = CACHE_DIR / (re.sub(r"[^A-Za-z0-9]+", "_", source.stem) + ".txt")
    if cached.is_file():
        return cached.read_text(encoding="utf-8", errors="replace")
    with tempfile.TemporaryDirectory(prefix="kerala-pdftext-") as temp_dir:
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


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00ad", " ")).strip()


def main() -> None:
    for source in sorted(SOURCE_DIR.glob("1971 *.pdf"), key=lambda p: p.name.lower()):
        pages = [compact(page) for page in text_for(source).split("\f")]
        print(f"=== {source.name} pages={len(pages)-1} ===")
        for i, text in enumerate(pages, 1):
            low = text.lower()
            if i <= 25 or any(
                term in low
                for term in (
                    "talukwise abstract",
                    "tehsilwise abstract",
                    "appendix",
                    "civic and other",
                    "medical, educational",
                    "medical educational",
                    "medical facilities",
                    "nature of amenities",
                    "amenities abstract",
                )
            ):
                if any(term in low for term in ("civic", "medical", "educational", "amenit", "appendix", "taluk", "tehsil")):
                    print(f"p{i}: {text[:320]}")


if __name__ == "__main__":
    main()
