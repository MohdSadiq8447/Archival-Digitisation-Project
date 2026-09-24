from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "1971" / "Andra Pradesh"
CACHE_DIR = Path(
    r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\ap-locate"
)


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u00ad", " ")).strip()


def page_range_from_line(line: str) -> tuple[int, int] | None:
    cleaned = re.sub(r"(?<=\d)[.,](?=\d)", "", normalized(line))
    match = re.search(r"(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?\s*$", cleaned)
    if not match:
        return None
    start = int(match.group(1))
    end = int(match.group(2) or match.group(1))
    return start, end


def page_range_after_anchor(text: str, anchor: str) -> tuple[int, int] | None:
    cleaned = re.sub(r"(?<=\d)[.,](?=\d)", "", normalized(text))
    match = re.search(
        anchor + r".*?(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?",
        cleaned,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    start = int(match.group(1))
    end = int(match.group(2) or match.group(1))
    return start, end


def extract_text(source_path: Path) -> str:
    cached_path = CACHE_DIR / (re.sub(r"[^A-Za-z0-9]+", "_", source_path.stem) + ".txt")
    if cached_path.is_file():
        return cached_path.read_text(encoding="utf-8", errors="replace")
    with tempfile.TemporaryDirectory(prefix="ap-pdftext-") as temp_dir:
        text_path = Path(temp_dir) / "source.txt"
        subprocess.run(
            ["pdftotext", "-layout", str(source_path), str(text_path)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return text_path.read_text(encoding="utf-8", errors="replace")


def locate(source_path: Path) -> dict[str, object]:
    pages = extract_text(source_path).split("\f")
    toc_lines: list[str] = []
    for page in pages[:15]:
        toc_lines.extend(normalized(line) for line in page.splitlines())

    civic_range = None
    medical_range = None
    appendix_range = None
    for index, line in enumerate(toc_lines):
        window = " ".join(toc_lines[index : index + 3])
        lower = window.lower()
        if re.search(r"\biv\b", lower) and "civic" in lower:
            civic_range = (
                page_range_after_anchor(window, r"\biv\b\s+.*?civic")
                or civic_range
            )
        if re.search(r"\bv\b", lower) and "educational" in lower:
            medical_range = (
                page_range_after_anchor(window, r"\bv\b\s+.*?educational")
                or medical_range
            )
        if "abstract of amenities" in lower:
            appendix_range = page_range_from_line(line) or appendix_range

    candidates: list[int] = []
    for index, page in enumerate(pages[20:], start=20):
        lower = normalized(page).lower()
        medical_heading = (
            "medical and other amenities" in lower
            or "educational, medical and other amenities" in lower
        )
        appendix_heading = (
            ("talukwise" in lower or "tajukwise" in lower)
            and "abstract" in lower
            and "educational" in lower
            and "nature" in lower
        )
        if (medical_heading and "figures indicate" in lower) or appendix_heading:
            candidates.append(index)

    if civic_range is None or medical_range is None or appendix_range is None:
        raise ValueError(
            f"TOC ranges not found for {source_path.name}: "
            f"civic={civic_range}, medical={medical_range}, appendix={appendix_range}"
        )
    if not candidates:
        raise ValueError(f"Appendix page not found for {source_path.name}")

    appendix_source_start = candidates[0]
    offset = appendix_source_start - appendix_range[0]
    return {
        "source": str(source_path.relative_to(ROOT)),
        "toc_civic": civic_range,
        "toc_medical": medical_range,
        "toc_appendix": appendix_range,
        "appendix_source_start": appendix_source_start,
        "offset": offset,
        "civic_source": [
            page + offset for page in range(civic_range[0], civic_range[1] + 1)
        ],
        "medical_source": [
            page + offset for page in range(medical_range[0], medical_range[1] + 1)
        ],
        "appendix_source": [
            appendix_source_start + i
            for i in range(appendix_range[1] - appendix_range[0] + 1)
        ],
    }


def main() -> None:
    for source_path in sorted(SOURCE_DIR.glob("1971 *.pdf")):
        try:
            print(locate(source_path))
        except Exception as exc:
            print(f"ERROR {source_path.name}: {exc}")


if __name__ == "__main__":
    main()
