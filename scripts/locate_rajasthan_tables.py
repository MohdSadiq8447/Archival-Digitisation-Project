from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Rajasthan"
CACHE_DIR = Path(
    r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\rajasthan-locate"
)


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u00ad", " ")).strip()


def text_for(source_path: Path) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = CACHE_DIR / (re.sub(r"[^A-Za-z0-9]+", "_", source_path.stem) + ".txt")
    if cached.is_file():
        return cached.read_text(encoding="utf-8", errors="replace")
    with tempfile.TemporaryDirectory(prefix="rajasthan-pdftext-") as temp_dir:
        temp_path = Path(temp_dir) / "source.txt"
        subprocess.run(
            ["pdftotext", "-layout", str(source_path), str(temp_path)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        text = temp_path.read_text(encoding="utf-8", errors="replace")
    cached.write_text(text, encoding="utf-8")
    return text


def main() -> None:
    pattern = re.compile(
        r"statement\s+(?:iv|v)|civic.{0,30}amenit|medical.{0,30}amenit|"
        r"educational.{0,30}amenit|abstract.{0,30}amenit|amenit.{0,30}abstract|"
        r"taluk|taluka|tahsil|tehsil|mahal",
        re.I,
    )
    for source_path in sorted(SOURCE_DIR.glob("1971 *.pdf"), key=lambda p: p.name.lower()):
        pages = text_for(source_path).split("\f")
        print(f"=== {source_path.name} pages={len(pages)-1} ===")
        for page_index, page in enumerate(pages):
            lines = [norm(line) for line in page.splitlines()]
            hits = [line for line in lines if line and pattern.search(line)]
            if hits:
                print(f"p{page_index + 1}: " + " | ".join(hits[:5]))


if __name__ == "__main__":
    main()
