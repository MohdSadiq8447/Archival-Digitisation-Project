"""
UP 1971 District Census Handbook — Town & Tahsil page trimmer (reproducible).

Trims the Town Statement IV (civic amenities), Town Statement V (medical/
education), and the Tahsil appendix out of each district PDF *by detecting the
section headers inside the PDF itself*. No external spreadsheet is used.

The embedded OCR text layer is noisy and the "APPENDIX" heading is often
garbled (APPEN / APPE / DIX / NDIX), so section boundaries are located by
stable keywords rather than by fuzzy continuation matching:

  * civic  -> "TOWN STATEMENT ... CIVIC AND OTHER" (Statement IV)
              continued by "DIRECTORY IV ... AMENITIES"
  * mededu -> "TOWN STATEMENT ... MEDICAL" (Statement V)
              continued by "CULTURAL FACILITIES IN TOWNS"
  * appendix -> "TAHSIL-WISE ABSTRACT OF EDUCATIONAL ..." / "APPENDIX ..."
                (always the final 2 pages of a complete volume)

Usage:
  python up1971_pdf_trimmer.py                 # all English districts in pdf-root
  python up1971_pdf_trimmer.py --district Agra # one district
  python up1971_pdf_trimmer.py --output .\out  # custom output dir
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter

import pdf_inspector

PROJECT_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = (
    PROJECT_ROOT
    if (PROJECT_ROOT / "1971-20260725T134344Z-1-001").exists()
    else PROJECT_ROOT.parent
)
DEFAULT_PDF_ROOT = WORKSPACE_ROOT / "1971-20260725T134344Z-1-001" / "1971" / "Uttar Pradesh"
DEFAULT_OUTPUT = WORKSPACE_ROOT / "output-final"

# Hindi Part X-B volumes (Devanagari text layer) — skipped, per the plan.
EXCLUDE_FILES = {
    "1971 Aajmgrah.pdf",        # Hindi Azamgarh
    "1971 Badha.pdf",           # Hindi Budaun
    "1971 Bhrich.pdf",          # Hindi Bahraich
    "1971 Mirzapur (Hindi).pdf",
}

# Districts whose town-statement pages are OCR'd too heavily for reliable
# auto-detection. These are manual reads of the actual scan (1-indexed pages);
# the appendix range is still auto-detected.
VERIFIED_OVERRIDES: dict[str, dict] = {
    "jhansi":      {"civic": (35, 36), "mededu": (37, 38)},
    "uttar kashi": {"civic": (25, 26), "mededu": (25, 26)},
    "mirzapur":    {"civic": (27, 28), "mededu": (29, 30)},
}

FRONT_PAGES = 45   # town statements live in the first pages
TAIL_PAGES = 12    # the appendix is the final 2 pages

CATEGORY_DIRS = {
    "civic": "Civic Amenities",
    "mededu": "Medical_Education",
    "tehsil": "Tehsil_Appendix",
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def slugify(value: str) -> str:
    text = value.strip().lower().replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def district_from_pdf_name(pdf_path: Path) -> str:
    """Human-readable district name from a source filename ('1971 Baliya.pdf' -> 'Baliya')."""
    name = re.sub(r"\.pdf$", "", pdf_path.name, flags=re.IGNORECASE)
    name = re.sub(r"^\s*1971\s+", "", name, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", name).strip()


def discover_districts(pdf_root: Path) -> dict[str, str]:
    """Map normalized district name -> source filename for every English PDF."""
    result: dict[str, str] = {}
    for pdf_path in sorted(pdf_root.glob("*.pdf")):
        if pdf_path.name in EXCLUDE_FILES:
            continue
        district = district_from_pdf_name(pdf_path)
        result[normalize(district)] = pdf_path.name
    return result


def leading_page_number(text: str) -> int | None:
    """Return the printed page number that heads the page, if present.

    The printed number may be at the very start, wrapped in parentheses
    (e.g. "( 315 )"), or pushed a few words in by OCR noise.
    """
    if not text:
        return None
    snippet = re.sub(r"\s+", " ", text[:200]).strip()
    match = re.match(r"^\(?\s*(\d{1,4})\s*\)?", snippet)
    if match:
        return int(match.group(1))
    match = re.search(r"\(\s*(\d{1,4})\s*\)", snippet)
    if match:
        return int(match.group(1))
    return None


# --- section header matchers (operate on normalized text) ------------------ #

def _squash(text: str) -> str:
    """Lowercase and collapse every non-alphanumeric run to a single space."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def is_civic_title(text: str) -> bool:
    # Statement IV "CIVIC AND OTHER" table. The title word itself is OCR-noisy
    # (CIVIC/CIVICS/OIVIC/CIVIO), so key off the distinctive table columns. The
    # scan is anchored after Statement III ("municipal"), so a single reliable
    # column hit is enough — the civic table is the only one that carries these.
    t = _squash(text)
    signals = (
        bool(re.search(r"\b(la[tr]e?r)", t)),      # Number of Latrines
        bool(re.search(r"sewer|sewel", t)),        # System of Sewerage
        bool(re.search(r"\bnight\b|dight", t)),    # disposal of night-soil
        bool(re.search(r"road len", t)),           # Road length
        bool(re.search(r"borne", t)),              # Water Borne
    )
    return sum(signals) >= 1


def is_mededu_title(text: str) -> bool:
    # Statement V medical/education table. "medical" + the statement subtitle
    # ("Educational", "hospital", "dispensary", …). "educational" is the most
    # OCR-stable of the secondary terms (the others are frequently garbled).
    t = _squash(text)
    if "medical" not in t:
        return False
    return any(k in t for k in ("hospit", "dispensar", "nurs", "recrea", "educational"))


def is_directory_v(text: str) -> bool:
    return "cultural facilities" in _squash(text)


def is_municipal_anchor(text: str) -> bool:
    return "municipal" in _squash(text)


def is_appendix(text: str) -> bool:
    # The "APPENDIX" word is often OCR-garbled (APPEN/APPE/DIX/NDIX), so rely on
    # the always-present "Junior/Senior Basic School" summary columns plus the
    # "Tahsil-wise Abstract ..." subtitle and "DISTRICT TOTAL" row. Applied only
    # to the last pages, where these phrases are appendix-only.
    t = _squash(text)
    return any(k in t for k in (
        "junior basic", "senior basic", "abstract", "appendix", "district total", "name of tahsil",
    ))


# --- text extraction -------------------------------------------------------- #

def build_page_texts(pdf_path: Path, pages: list[int]) -> dict[int, str]:
    """Return {1-indexed page: normalized text} for the given pages."""
    reader = PdfReader(str(pdf_path))
    result: dict[int, str] = {}
    for page in pages:
        if page < 1 or page > len(reader.pages):
            continue
        try:
            text = normalize(reader.pages[page - 1].extract_text() or "")
        except Exception:
            text = ""
        result[page] = text
    return result


def first_page(page_texts: dict[int, str], pages: list[int], matcher) -> int | None:
    for page in pages:
        if page in page_texts and matcher(page_texts[page]):
            return page
    return None


# --- range derivation ------------------------------------------------------- #

@dataclass
class SectionRanges:
    civic: list[tuple[int, int]] = None  # type: ignore
    mededu: list[tuple[int, int]] = None  # type: ignore
    appendix: list[tuple[int, int]] = None  # type: ignore
    warnings: list = None  # type: ignore

    def __post_init__(self):
        self.warnings = self.warnings or []


def detect_ranges(page_texts: dict[int, str], page_count: int) -> SectionRanges:
    front = sorted(p for p in page_texts if p <= FRONT_PAGES)
    tail = sorted(p for p in page_texts if p >= max(1, page_count - TAIL_PAGES + 1))

    ranges = SectionRanges()

    # Statement III (municipal finance) is the last statement before civic, and
    # "municipal" survives OCR reliably. Anchor after page 15 to skip the intro.
    municipal = first_page(page_texts, [p for p in front if p >= 15], is_municipal_anchor)

    # civic title is the first civic-table page at/after the municipal anchor.
    civic_start = first_page(page_texts, [p for p in front if p >= (municipal or 0)], is_civic_title)
    if civic_start is None:
        ranges.warnings.append("civic title not found")
        return ranges

    # civic: Statement IV is always two printed pages — the "CIVIC AND OTHER"
    # title table and the following "DIRECTORY IV AMENITIES, 1969" table.
    civic_end = min(civic_start + 1, page_count)
    ranges.civic = [(civic_start, civic_end)]

    # mededu (Statement V medical table + Directory V cultural facilities).
    # Search from the civic page onward: compressed handbooks put the medical
    # title on the same page as the civic title.
    from_civic = [p for p in front if p >= civic_start]
    mededu_title = first_page(page_texts, from_civic, is_mededu_title)
    cultural_page = first_page(page_texts, from_civic, is_directory_v)

    if mededu_title is not None:
        end = cultural_page if (cultural_page is not None and cultural_page >= mededu_title) else mededu_title + 1
        ranges.mededu = [(mededu_title, min(end, page_count))]
    elif cultural_page is not None:
        # No separate medical table (small compressed handbooks): the cultural
        # facilities page alone carries the mededu content.
        ranges.mededu = [(cultural_page, cultural_page)]
    else:
        ranges.warnings.append("mededu title not found")

    # appendix: the final summary table (2 pages at the end of a complete volume).
    appendix_start = first_page(page_texts, tail, is_appendix)
    if appendix_start is not None:
        appendix_end = min(page_count, appendix_start + 1)
        ranges.appendix = [(appendix_start, appendix_end)]
    else:
        ranges.warnings.append("appendix not found (volume may be truncated)")

    return ranges


# --- trimming --------------------------------------------------------------- #

def category_filename(district: str, category: str) -> str:
    slug = slugify(district)
    return {"civic": f"{slug}_civic_1971.pdf",
            "mededu": f"{slug}_mededu_1971.pdf",
            "tehsil": f"{slug}_tehsil_1971.pdf"}[category]


def write_trimmed_pdf(source_pdf: Path, ranges: list[tuple[int, int]], output_pdf: Path) -> None:
    reader = PdfReader(str(source_pdf))
    writer = PdfWriter()
    for start, end in ranges:
        for page in range(start, end + 1):
            writer.add_page(reader.pages[page - 1])
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as handle:
        writer.write(handle)


def process_district(district: str, filename: str, pdf_root: Path, output_root: Path) -> dict:
    pdf_path = pdf_root / filename
    if not pdf_path.exists():
        return {"district": district, "source_pdf": filename, "error": "pdf missing"}

    classification = pdf_inspector.classify_pdf(str(pdf_path))
    page_count = int(classification.page_count)

    scan_pages = sorted(set(range(1, min(page_count, FRONT_PAGES) + 1))
                        | set(range(max(1, page_count - TAIL_PAGES + 1), page_count + 1)))
    page_texts = build_page_texts(pdf_path, scan_pages)

    ranges = detect_ranges(page_texts, page_count)

    override = VERIFIED_OVERRIDES.get(normalize(district))
    if override:
        if override.get("civic"):
            ranges.civic = [tuple(override["civic"])]
        if override.get("mededu"):
            ranges.mededu = [tuple(override["mededu"])]
        ranges.warnings.append("used verified override for town statements")

    report: dict = {
        "district": district,
        "source_pdf": filename,
        "page_count": page_count,
        "pdf_type": classification.pdf_type,
        "outputs": {},
        "warnings": ranges.warnings,
    }

    for category, rng in (("civic", ranges.civic), ("mededu", ranges.mededu), ("tehsil", ranges.appendix)):
        if not rng:
            report["outputs"][category] = {"status": "skipped", "reason": "not detected"}
            continue
        start, end = rng[0]
        output_path = output_root / CATEGORY_DIRS[category] / category_filename(district, category)
        write_trimmed_pdf(pdf_path, rng, output_path)
        report["outputs"][category] = {
            "status": "written",
            "actual_pages": [start, end],
            "printed_pages": [
                leading_page_number(page_texts.get(start, "")),
                leading_page_number(page_texts.get(end, "")),
            ],
            "page_count": end - start + 1,
            "output_path": str(output_path),
        }

    return report


# --- CLI -------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-root", type=Path, default=DEFAULT_PDF_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--district", type=str, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()

    all_districts = discover_districts(args.pdf_root)
    if not all_districts:
        raise SystemExit("No PDFs found in the pdf-root.")

    if args.district:
        key = normalize(args.district)
        if key not in all_districts:
            raise SystemExit(f"Unknown district: {args.district}")
        districts = {key: all_districts[key]}
    else:
        districts = all_districts

    (args.output / "reports").mkdir(parents=True, exist_ok=True)
    for category in CATEGORY_DIRS.values():
        (args.output / category).mkdir(parents=True, exist_ok=True)

    reports = []
    for district, filename in districts.items():
        print(f"Processing {district} ...")
        reports.append(process_district(district, filename, args.pdf_root, args.output))

    report_path = args.output / "reports" / "trim-report.json"
    report_path.write_text(json.dumps(reports, indent=2), encoding="utf-8")

    print("\n=== SUMMARY ===")
    for report in reports:
        outs = report["outputs"]
        status = {k: (v.get("status") if isinstance(v, dict) else "?") for k, v in outs.items()}
        print(f"{report['district']:<12} civic={status.get('civic')} mededu={status.get('mededu')} tehsil={status.get('tehsil')}  {report['warnings']}")
    print(f"\nReport written to: {report_path}")


if __name__ == "__main__":
    main()
