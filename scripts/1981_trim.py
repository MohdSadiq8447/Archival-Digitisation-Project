from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader, PdfWriter

try:
    import fitz  # type: ignore
except ImportError:  # pragma: no cover - bundled runtime uses the pypdf fallback
    fitz = None


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "1981"
OUTPUT_ROOT = ROOT / "output" / "pdf" / "1981_trimmed"
AUDIT_ROOT = ROOT / "output" / "audit"
TMP_ROOT = ROOT / "tmp" / "pdfs" / "1981"

TABLES = (
    "civic_amenities",
    "medical_educational_amenities",
    "tehsil_appendix",
)

TABLE_LABELS = {
    "civic_amenities": "Civic Amenities",
    "medical_educational_amenities": "Medical and Educational Amenities",
    "tehsil_appendix": "Tehsil Appendix",
}

TABLE_FOLDERS = {
    "civic_amenities": "civic amenities",
    "medical_educational_amenities": "mededu",
    "tehsil_appendix": "tehsil appendix",
}

STATE_ALIASES = {"Darman & Diu": "Daman & Diu"}

BIHAR_DISTRICTS = {
    "1981 Bhagal Pur.pdf": "Bhagalpur",
    "26922_1981_MAD.pdf": "Madhubani",
    "27173_1981_PAS.pdf": "Pashchim Champaran",
    "27176_1981_ROH.pdf": "Rohtas",
    "27179_1981_DCH.pdf": "Purnia",
    "27180_1981_BHO.pdf": "Bhojpur",
    "27843_1981_DAR.pdf": "Darbhanga",
    "27845_1981_MUN.pdf": "Munger",
    "27847_1981_HAZ.pdf": "Hazaribagh",
    "28446_1981_GIR.pdf": "Giridih",
    "28468_1981_DHA.pdf": "Dhanbad",
    "28553_1981_SAM.pdf": "Samastipur",
    "28557_1981_DIS.pdf": "Gaya",
    "41319_1981_SAH.pdf": "Saharsa",
    "41680_1981_GOP.pdf": "Gopalganj",
    "41697_1981_BEG.pdf": "Begusarai",
    "41700_1981_SIW.pdf": "Siwan",
    "42425_1981_AUR.pdf": "Aurangabad",
    "42459_1981_SAN.pdf": "Santhal Pargana",
    "42469_1981_PAL.pdf": "Palamu",
    "42470_1981_SIT.pdf": "Sitamarhi",
    "43198_1981_VAI.pdf": "Vaishali",
    "43804_1981_NAW.pdf": "Nawada",
    "47755_1981_SIN.pdf": "Saran",
}

DISTRICT_ALIASES = {
    ("Andra Pradesh", "1981 West Godavar.pdf"): "West Godavari",
    ("Arunachal Pradesh", "1981 Tirap .pdf"): "Tirap",
    ("Orissa", "1981 Kendujhar,.pdf"): "Kendujhar",
    ("Rajasthan", "1981 Jalsalmer.pdf"): "Jaisalmer",
    ("Uttar Pradesh", "1981 Allgarh.pdf"): "Aligarh",
    ("Uttar Pradesh", "1981 Peelibhit.pdf"): "Pilibhit",
}

SAMPLE_PAGE_MAP = {
    ("Andra Pradesh", "Adilabad"): {
        "civic_amenities": [354, 355],
        "medical_educational_amenities": [358, 359],
        "tehsil_appendix": [260, 261, 262, 263],
    },
    ("Gujarat", "Ahmadabad"): {
        "civic_amenities": [208, 209, 210, 211],
        "medical_educational_amenities": [216, 217, 218, 219, 220, 221],
        "tehsil_appendix": [176, 177, 178, 179],
    },
    ("Uttar Pradesh", "Allahabad"): {
        "civic_amenities": [741, 742, 743, 744],
        "medical_educational_amenities": [747, 748, 749, 750, 751, 752],
        "tehsil_appendix": [577, 578, 579, 580],
    },
}


def compact(value: str) -> str:
    return " ".join(value.replace("\x00", " ").split())


def upper(value: str) -> str:
    return compact(value).upper()


def normalize_state(source_state: str) -> str:
    return STATE_ALIASES.get(source_state, source_state)


def district_label(state: str, source_name: str) -> str:
    if state == "Bihar" and source_name in BIHAR_DISTRICTS:
        return BIHAR_DISTRICTS[source_name]
    if (state, source_name) in DISTRICT_ALIASES:
        return DISTRICT_ALIASES[(state, source_name)]
    stem = Path(source_name).stem
    stem = re.sub(r"^1981\s*", "", stem).strip(" .,_-")
    return compact(stem)


def safe_filename(value: str) -> str:
    value = re.sub(r"[<>:\"/\\|?*]", " ", value)
    return compact(value).strip(".")


def tool_path(name: str, fallback: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    candidate = Path(fallback)
    return str(candidate) if candidate.exists() else name


PDFTOTEXT = tool_path(
    "pdftotext",
    r"C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftotext.exe",
)
PDFTOPPM = tool_path(
    "pdftoppm",
    r"C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe",
)
PDFINFO = tool_path(
    "pdfinfo",
    r"C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdfinfo.exe",
)


def page_box(page, box_name: str) -> tuple[float, float, float, float]:
    box = getattr(page, box_name)
    return tuple(round(float(value), 4) for value in (box.left, box.bottom, box.right, box.top))


def page_rotation(page) -> int:
    try:
        return int(page.rotation or 0)
    except Exception:
        return int(page.get("/Rotate", 0) or 0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_page_texts(source_path: Path, page_limit: int | None = None) -> list[str]:
    if fitz is not None:
        document = fitz.open(str(source_path))
        try:
            count = len(document) if page_limit is None else min(page_limit, len(document))
            return [document[index].get_text("text") for index in range(count)]
        finally:
            document.close()
    reader = PdfReader(str(source_path), strict=False)
    pages = reader.pages if page_limit is None else reader.pages[:page_limit]
    return [page.extract_text() or "" for page in pages]


def read_page_labels(source_path: Path, page_limit: int | None = None, page_numbers: list[int] | None = None) -> list[str | None]:
    indices = [number - 1 for number in page_numbers] if page_numbers is not None else None
    if fitz is None:
        if indices is None:
            return [printed_page_label(text) for text in read_page_texts(source_path, page_limit=page_limit)]
        reader = PdfReader(str(source_path), strict=False)
        return [printed_page_label(reader.pages[index].extract_text() or "") for index in indices]
    document = fitz.open(str(source_path))
    try:
        if indices is None:
            count = len(document) if page_limit is None else min(page_limit, len(document))
            indices = list(range(count))
        labels = []
        for index in indices:
            candidates = []
            for block in document[index].get_text("dict").get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        value = span.get("text", "").strip()
                        top = float(span.get("bbox", [0, 9999, 0, 0])[1])
                        if top <= 110 and re.fullmatch(r"\d{1,4}", value) and value != "1981" and not value.startswith("0"):
                            candidates.append(value)
            labels.append(candidates[0] if len(candidates) == 1 else None)
        return labels
    finally:
        document.close()


def printed_page_label(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates = list(dict.fromkeys(line for line in lines[:18] + lines[-18:] if re.fullmatch(r"\d{1,4}", line)))
    return candidates[0] if len(candidates) == 1 else None


def classify_language(page_texts: list[str]) -> tuple[str, str]:
    sample = "\n".join(page_texts[:12])
    if not sample.strip():
        return "English scan or image-only text", "Opening pages contain no extractable text; visual table review remains required."
    latin = 0
    nonlatin = 0
    for char in sample:
        if not char.isalpha():
            continue
        name = unicodedata.name(char, "")
        if "LATIN" in name:
            latin += 1
        else:
            nonlatin += 1
    value = upper(sample)
    english_signals = sum(
        term in value
        for term in (
            "DISTRICT CENSUS HANDBOOK",
            "VILLAGE & TOWN DIRECTORY",
            "VILLAGE AND TOWN DIRECTORY",
            "TOWN DIRECTORY",
            "STATEMENT IV",
            "STATEMENT V",
            "CIVIC AND OTHER",
            "MEDICAL, EDUCATIONAL",
            "EDUCATIONAL, MEDICAL",
            "AMENITIES",
        )
    )
    if nonlatin and nonlatin / max(1, latin + nonlatin) > 0.45 and english_signals == 0:
        return "non-English", "Opening pages are predominantly non-Latin and contain no reliable English directory signals; skipped per user instruction."
    return "English or bilingual", "Opening pages contain English directory or publication signals."


def cover_text(page_texts: list[str]) -> str:
    return upper(" ".join(page_texts[: min(8, len(page_texts))]))


def classify_volume(source_path: Path, page_texts: list[str]) -> tuple[str, bool, str]:
    if not page_texts:
        return "classification deferred", False, "Opening-page classification is deferred until the extraction phase."
    first = upper(" ".join(page_texts[:2]))
    cover = upper(page_texts[0]) if page_texts else ""
    first_eight = cover_text(page_texts)
    if "PART X-C" in cover or "PART X C" in cover or "ADMINISTRATION REPORT" in cover:
        return "non-directory administrative volume", False, "Cover identifies Part X-C or an administrative report."
    cover_directory = bool(re.search(r"PARTS?\s+XIII\s*[- ]?A", cover)) or any(
        term in cover for term in ("VILLAGE & TOWN DIRECTORY", "VILLAGE AND TOWN DIRECTORY", "TOWN DIRECTORY")
    )
    if cover_directory:
        return "Village/Town Directory volume", True, "Directory volume contains or may contain the requested table groups."
    if re.search(r"PART\s+XIII(?:\s*[- .]+)?B\b", cover) or (
        "PRIMARY CENSUS ABSTRACT" in cover and "VILLAGE" not in cover
    ):
        return "Part XIII-B primary census abstract", False, "PCA-only volume; the requested town statements and amenities appendix are absent."
    has_directory_part = bool(re.search(r"PARTS?\s+XIII\s*[- ]?A", first_eight)) or any(
        term in first_eight for term in ("VILLAGE & TOWN DIRECTORY", "VILLAGE AND TOWN DIRECTORY", "TOWN DIRECTORY")
    )
    if has_directory_part and "PART X-C" not in first:
        return "Village/Town Directory volume", True, "Directory volume contains or may contain the requested table groups."
    if any(term in first_eight for term in ("STATEMENT IV", "CIVIC AND OTHER", "STATEMENT V", "MEDICAL, EDUCATIONAL")):
        return "directory candidate", True, "Requested directory headings are present in the opening pages."
    return "unclassified 1981 volume", False, "Cover and opening pages do not establish an eligible directory volume."


def source_record(source_path: Path, text_limit: int | None = None) -> dict[str, object]:
    relative = source_path.relative_to(ROOT).as_posix()
    state = source_path.parent.name
    canonical_state = normalize_state(state)
    district = district_label(state, source_path.name)
    if text_limit == 0:
        info = subprocess.run([PDFINFO, str(source_path)], check=True, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
        match = re.search(r"^Pages:\s+(\d+)", info, flags=re.MULTILINE)
        if not match:
            raise ValueError(f"pdfinfo did not report page count for {source_path}")
        page_count = int(match.group(1))
    else:
        page_count = len(PdfReader(str(source_path), strict=False).pages)
    texts = read_page_texts(source_path, page_limit=text_limit)
    volume_type, eligible, reason = classify_volume(source_path, texts)
    return {
        "state": canonical_state,
        "source_state": state,
        "district": district,
        "source": relative,
        "source_path": str(source_path),
        "source_filename": source_path.name,
        "census_year": 1981,
        "volume_type": volume_type,
        "eligible": eligible,
        "eligibility_reason": reason,
        "source_pages": page_count,
        "source_size_bytes": source_path.stat().st_size,
        "source_sha256": sha256(source_path) if text_limit is None else None,
        "page_texts": texts,
        "page_labels": read_page_labels(source_path, page_limit=text_limit) if text_limit not in (0, None) else [],
        "language_status": "deferred" if text_limit == 0 else classify_language(texts)[0],
        "language_reason": "Language classification deferred until the extraction phase." if text_limit == 0 else classify_language(texts)[1],
    }


def inventory_records() -> list[dict[str, object]]:
    records = []
    for state_dir in sorted(SOURCE_ROOT.iterdir(), key=lambda path: path.name.lower()):
        if not state_dir.is_dir():
            continue
        for source_path in sorted(state_dir.glob("*.pdf"), key=lambda path: path.name.lower()):
            records.append(source_record(source_path, text_limit=0))
    return records


def ensure_full_texts(record: dict[str, object]) -> None:
    ensure_opening_metadata(record)
    if len(record["page_texts"]) == int(record["source_pages"]):
        return
    record["page_texts"] = read_page_texts(Path(str(record["source_path"])))
    record["page_labels"] = []
    volume_type, eligible, reason = classify_volume(Path(str(record["source_path"])), record["page_texts"])
    record["volume_type"] = volume_type
    record["eligible"] = eligible
    record["eligibility_reason"] = reason
    language_status, language_reason = classify_language(record["page_texts"])
    record["language_status"] = language_status
    record["language_reason"] = language_reason


def ensure_opening_metadata(record: dict[str, object]) -> None:
    if record.get("opening_checked"):
        return
    opening = read_page_texts(Path(str(record["source_path"])), page_limit=8)
    volume_type, eligible, reason = classify_volume(Path(str(record["source_path"])), opening)
    language_status, language_reason = classify_language(opening)
    record["page_texts"] = opening
    record["volume_type"] = volume_type
    record["eligible"] = eligible
    record["eligibility_reason"] = reason
    record["language_status"] = language_status
    record["language_reason"] = language_reason
    record["opening_checked"] = True


def write_inventory(records: list[dict[str, object]]) -> None:
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    public_records = [{key: value for key, value in record.items() if key not in {"page_texts", "page_labels", "opening_page_texts"}} for record in records]
    (AUDIT_ROOT / "1981_inventory.json").write_text(json.dumps(public_records, indent=2), encoding="utf-8")
    fields = [
        "state", "source_state", "district", "source", "source_path", "source_filename", "census_year",
        "volume_type", "eligible", "eligibility_reason", "language_status", "language_reason", "source_pages", "source_size_bytes", "source_sha256",
    ]
    with (AUDIT_ROOT / "1981_inventory.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(public_records)


def hash_source_inventory(phase: str) -> None:
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    rows = []
    for source_path in sorted(SOURCE_ROOT.glob("*/*.pdf"), key=lambda path: str(path).lower()):
        rows.append({
            "source": str(source_path.relative_to(ROOT)).replace("\\", "/"),
            "size_bytes": source_path.stat().st_size,
            "sha256": sha256(source_path),
        })
    (AUDIT_ROOT / f"1981_source_hashes_{phase}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"hashed_sources={len(rows)} phase={phase}")


def is_town_directory(text: str) -> bool:
    value = upper(text)
    return "TOWN DIRECTORY" in value or "STATEMENT IV" in value or "STATEMENT V" in value


def is_contents_page(text: str) -> bool:
    value = upper(text)
    return "CONTENTS" in value and ("PAGE" in value or "STATEMENT" in value or "APPENDIX" in value)


def has_civic_heading(text: str) -> bool:
    value = upper(text)
    if is_contents_page(text) or re.search(r"STATEMENT\s+IV[- ]A\b", value) or "IV-3T" in value or "NOTIFIED SLUM" in value:
        return False
    civic_position = value.find("CIVIC AND")
    if any(term in value for term in ("AREA OF SLUM", "NAME OF SLUM", "NOTIFIED SLUM")) and not (0 <= civic_position < 600):
        return False
    header = value[:700]
    table_terms = ("NUMBER OF LATRINES", "CLASS AND NAME", "PROTECTED WATER", "ROAD", "SEWER", "SYSTEM", "POPULATION")
    return (
        "CIVIC AND" in header
        and ("TOWN" in header or "STATEMENT" in header)
        and "CLASS AND NAME" in header
        and ("NUMBER OF LATRINES" in header or "PROTECTED WATER" in header)
        and sum(term in header for term in table_terms) >= 4
    )


def has_medical_heading(text: str) -> bool:
    value = upper(text)
    if is_contents_page(text) or "STATEMENT VI" in value or "TRADE, COMMERCE" in value:
        return False
    header = value[:700]
    table_terms = ("MEDICAL FACILIT", "HOSPITAL", "DISPENS", "COLLEGE", "POLYTECH", "RECREATIONAL", "CULTURAL")
    return (
        bool(re.search(r"MEDICAL[,.]?\s+EDUCATIONAL", header))
        and "FACILIT" in header
        and "CLASS AND NAME" in header
        and ("TOWN" in header or "STATEMENT" in header)
        and sum(term in header for term in table_terms) >= 4
    )


def has_tehsil_heading(text: str) -> bool:
    value = upper(text)
    if is_contents_page(text):
        return False
    if "APPENDIX" not in value[:400]:
        return False
    unit = any(term in value for term in ("TAHSIL", "TAHSILWISE", "TAHSIL-WISE", "TABSIL", "TEHSIL", "TEHSILWISE", "TALUK", "TALUKA", "TALUKWISE", "MAHAL", "CIRCLE", "BLOCK"))
    amenities = "EDUCATIONAL" in value and "MEDICAL" in value and ("AMENIT" in value or "OTHER" in value)
    table_columns = (
        "PRIMARY SCHOOL" in value
        and ("DISPENS" in value or "HEALTH CENTRE" in value or "POST AND TELEGRAPH" in value)
        and ("NAME OF" in value or "SL. NO" in value or "SI. NO" in value)
    )
    return unit and amenities and "ABSTRACT" in value and table_columns


def looks_civic_table(text: str) -> bool:
    value = upper(text)
    terms = ("ROAD", "SEWER", "WATER", "LATRINE", "POPULATION", "SCHEDULED")
    return sum(term in value for term in terms) >= 3


def looks_medical_table(text: str) -> bool:
    value = upper(text)
    terms = ("MEDICAL", "DISPENS", "HOSPITAL", "EDUCATIONAL", "SCHOOL", "COLLEGE", "CULTURAL")
    return sum(term in value for term in terms) >= 3


def looks_amenities_appendix(text: str) -> bool:
    value = upper(text)
    terms = ("EDUCATIONAL", "MEDICAL", "AMENIT", "DISPENS", "PRIMARY SCHOOL", "TAHSIL", "TEHSIL", "TALUK", "TALUKA", "TABSIL")
    return sum(term in value for term in terms) >= 3


def nearest_town_directory(page_texts: list[str], index: int) -> int | None:
    candidates = [i for i in range(max(0, index - 250), index + 1) if is_town_directory(page_texts[i])]
    return max(candidates) if candidates else None


def contiguous_span(page_texts: list[str], start: int, stop_predicate) -> tuple[list[int], bool]:
    end = len(page_texts) - 1
    stopped = False
    for index in range(start + 1, len(page_texts)):
        if stop_predicate(page_texts[index]):
            end = index - 1
            stopped = True
            break
    return list(range(start, end + 1)), stopped


def locate_civic(page_texts: list[str]) -> tuple[list[int], list[str]]:
    candidates = [i for i, text in enumerate(page_texts) if i >= 8 and has_civic_heading(text)]
    if not candidates:
        return [], ["No reliable Statement IV heading found in a Town Directory section."]
    start = min(candidates)
    if start > 0 and looks_civic_table(page_texts[start - 1]):
        start -= 1
    pages, stopped = contiguous_span(
        page_texts,
        start,
        lambda text: (
            "NOTIFIED SLUM" in upper(text)
            or "STATEMENT IV-A" in upper(text)
            or "STATEMENT IV A" in upper(text)
            or "AREA OF SLUM" in upper(text)
            or "NAME OF SLUM" in upper(text)
            or "IV-3T" in upper(text)
            or has_medical_heading(text)
        ),
    )
    flags = []
    if not pages or not stopped:
        flags.append("unbounded_span")
    return pages, flags


def locate_medical(page_texts: list[str]) -> tuple[list[int], list[str]]:
    candidates = [i for i, text in enumerate(page_texts) if i >= 8 and has_medical_heading(text)]
    if not candidates:
        return [], ["No reliable Statement V heading found in a Town Directory section."]
    start = min(candidates)
    if start > 0 and looks_medical_table(page_texts[start - 1]):
        start -= 1
    pages, stopped = contiguous_span(
        page_texts,
        start,
        lambda text: (
            "STATEMENT VI" in upper(text)
            or "TRADE, COMMERCE" in upper(text)
            or "COMMODIT" in upper(text)
            or "MANUFACTURED" in upper(text)
            or ("APPENDIX" in upper(text) and "MEDICAL, EDUCATIONAL, RECREATIONAL" not in upper(text))
        ),
    )
    flags = []
    if not pages or not stopped:
        flags.append("unbounded_span")
    return pages, flags


def locate_appendix(page_texts: list[str]) -> tuple[list[int], list[str]]:
    candidates = [i for i, text in enumerate(page_texts) if i >= 8 and has_tehsil_heading(text)]
    if not candidates:
        return [], ["No reliable administrative-unit amenities appendix heading found."]
    start = min(candidates)
    for _ in range(min(3, start)):
        previous = page_texts[start - 1]
        previous_upper = upper(previous)
        previous_abstract = "EDUCATIONAL" in previous_upper and any(term in previous_upper for term in ("TAHSIL", "TEHSIL", "TALUK", "TALUKA", "TABSIL"))
        if looks_amenities_appendix(previous) or previous_abstract or not previous.strip():
            start -= 1
        else:
            break
    pages, stopped = contiguous_span(
        page_texts,
        start,
        lambda text: (
            ("APPENDIX" in upper(text) and "ABSTRACT" in upper(text) and "EDUCATIONAL" in upper(text) and "MEDICAL" in upper(text))
            is False
            and (
                bool(re.search(r"APPENDIX\s*(?:II|III|IV)\b", upper(text)))
                or "LAND UTILISATION" in upper(text)
                or "NO AMENIT" in upper(text)
                or "LIST OF VILLAGES" in upper(text)
                or "PROPORTION OF SCHEDULED" in upper(text)
                or "SECTION II" in upper(text)
            )
        ),
    )
    flags = []
    if not pages or not stopped:
        flags.append("unbounded_span")
    return pages, flags


def auto_span(record: dict[str, object], table: str) -> tuple[list[int], list[str], str]:
    if not record["eligible"]:
        return [], [], str(record["eligibility_reason"])
    page_texts = record["page_texts"]
    if table == "civic_amenities":
        pages, flags = locate_civic(page_texts)
    elif table == "medical_educational_amenities":
        pages, flags = locate_medical(page_texts)
    else:
        pages, flags = locate_appendix(page_texts)
    if not pages:
        return [], flags, "No confident text-based span; visual review required."
    return [page + 1 for page in pages], flags, "Located from directory headings and continuation boundaries."


def output_path(record: dict[str, object], table: str) -> Path:
    state_dir = OUTPUT_ROOT / str(record["state"])
    district = safe_filename(str(record["district"]))
    return state_dir / TABLE_FOLDERS[table] / f"1981_{district}_{table}.pdf"


def extract_pages(source_path: Path, page_numbers: list[int], destination: Path) -> None:
    reader = PdfReader(str(source_path), strict=False)
    if not page_numbers or min(page_numbers) < 1 or max(page_numbers) > len(reader.pages):
        raise ValueError(f"Invalid page selection for {source_path}: {page_numbers}")
    writer = PdfWriter()
    for number in page_numbers:
        writer.add_page(reader.pages[number - 1])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        writer.write(handle)


def verify_output(source_path: Path, destination: Path, page_numbers: list[int], compare_render: bool = False) -> dict[str, object]:
    source_reader = PdfReader(str(source_path), strict=False)
    output_reader = PdfReader(str(destination), strict=False)
    if len(output_reader.pages) != len(page_numbers):
        raise ValueError(f"{destination.name}: expected {len(page_numbers)} pages, found {len(output_reader.pages)}")
    page_checks = []
    for output_page, source_number in zip(output_reader.pages, page_numbers):
        source_page = source_reader.pages[source_number - 1]
        boxes = {}
        for box_name in ("mediabox", "cropbox"):
            source_box = page_box(source_page, box_name)
            output_box = page_box(output_page, box_name)
            if source_box != output_box:
                raise ValueError(f"{destination.name}: {box_name} differs from source page {source_number}")
            boxes[box_name] = source_box
        source_rotation = page_rotation(source_page)
        output_rotation = page_rotation(output_page)
        if source_rotation != output_rotation:
            raise ValueError(f"{destination.name}: rotation differs from source page {source_number}")
        page_checks.append({"source_page": source_number, "boxes": boxes, "rotation": source_rotation})
    result = {"output_pages": len(output_reader.pages), "pages": page_checks}
    if compare_render:
        result["render_checks"] = render_compare(source_path, destination, page_numbers)
    return result


def render_one(pdf_path: Path, page_number: int, output_prefix: Path) -> Path:
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    command = [PDFTOPPM, "-png", "-r", "120", "-f", str(page_number), "-l", str(page_number), "-singlefile", str(pdf_path), str(output_prefix)]
    subprocess.run(command, check=True, capture_output=True)
    image_path = output_prefix.with_suffix(".png")
    if not image_path.exists() or image_path.stat().st_size == 0:
        raise ValueError(f"No rendered image produced for {pdf_path} page {page_number}")
    return image_path


def render_compare(source_path: Path, output_path_value: Path, source_pages: list[int]) -> list[dict[str, object]]:
    compare_dir = TMP_ROOT / "render_compare" / safe_filename(output_path_value.stem)
    checks = []
    for output_number, source_number in enumerate(source_pages, start=1):
        source_png = render_one(source_path, source_number, compare_dir / f"source_{source_number}")
        output_png = render_one(output_path_value, output_number, compare_dir / f"output_{output_number}")
        source_hash = sha256(source_png)
        output_hash = sha256(output_png)
        checks.append({"source_page": source_number, "output_page": output_number, "source_png_sha256": source_hash, "output_png_sha256": output_hash, "match": source_hash == output_hash})
    return checks


def base_record(record: dict[str, object], table: str) -> dict[str, object]:
    return {
        "state": record["state"],
        "source_state": record["source_state"],
        "district": record["district"],
        "table": table,
        "table_label": TABLE_LABELS[table],
        "source": record["source"],
        "source_filename": record["source_filename"],
        "volume_type": record["volume_type"],
        "eligible": record.get("eligible"),
        "eligibility_reason": record.get("eligibility_reason"),
        "language_status": record.get("language_status"),
        "language_reason": record.get("language_reason"),
        "source_page_count": record["source_pages"],
        "output": None,
        "source_pages_selected": [],
        "printed_page_labels": [],
        "status": "Needs review",
        "reason": None,
        "flags": [],
        "verification": None,
    }


def process_record(record: dict[str, object], table: str, manual_pages: list[int] | None = None, compare_render: bool = False) -> dict[str, object]:
    ensure_opening_metadata(record)
    result = base_record(record, table)
    if record.get("language_status") == "non-English":
        result["status"] = "Not trimmed"
        result["flags"] = ["non_english_skipped"]
        result["reason"] = str(record.get("language_reason"))
        return result
    if not record.get("eligible"):
        result["status"] = "Not trimmed"
        result["reason"] = str(record.get("eligibility_reason"))
        return result
    ensure_full_texts(record)
    if manual_pages is not None:
        pages = manual_pages
        flags = []
        reason = "Manually verified source span from printed headings, continuation pages, and table structure."
    else:
        pages, flags, reason = auto_span(record, table)
    result["source_pages_selected"] = pages
    result["flags"] = flags
    result["reason"] = reason
    result["printed_page_labels"] = read_page_labels(Path(str(record["source_path"])), page_numbers=pages)
    if not pages:
        if not record["eligible"]:
            result["status"] = "Not trimmed"
        return result
    if flags and manual_pages is None:
        result["status"] = "Needs review"
        return result
    destination = output_path(record, table)
    extract_pages(Path(str(record["source_path"])), pages, destination)
    verification = verify_output(Path(str(record["source_path"])), destination, pages, compare_render=compare_render)
    result["output"] = str(destination.relative_to(ROOT)).replace("\\", "/")
    result["verification"] = verification
    result["status"] = "Trimmed"
    return result


def write_manifests(records: list[dict[str, object]], stem: str) -> None:
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    (AUDIT_ROOT / f"{stem}.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    fields = ["state", "district", "table", "status", "source", "source_filename", "volume_type", "language_status", "source_pages_selected", "printed_page_labels", "output", "reason", "flags"]
    with (AUDIT_ROOT / f"{stem}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = {key: record.get(key) for key in fields}
            for key in ("source_pages_selected", "printed_page_labels", "flags"):
                row[key] = json.dumps(row[key], ensure_ascii=False)
            writer.writerow(row)


def records_by_state(records: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for record in records:
        grouped.setdefault(str(record["state"]), []).append(record)
    return grouped


def run_inventory() -> list[dict[str, object]]:
    records = inventory_records()
    write_inventory(records)
    print(f"inventory_sources={len(records)}")
    print(f"inventory_states={len({record['state'] for record in records})}")
    print(f"inventory_pages={sum(int(record['source_pages']) for record in records)}")
    print(f"eligible_candidates={sum(bool(record['eligible']) for record in records)}")
    return records


def run_sample(records: list[dict[str, object]]) -> list[dict[str, object]]:
    results = []
    wanted = set(SAMPLE_PAGE_MAP)
    for record in records:
        key = (str(record["source_state"]), str(record["district"]))
        if key not in wanted:
            continue
        source = Path(str(record["source_path"]))
        for table in TABLES:
            result = process_record(record, table, SAMPLE_PAGE_MAP[key][table], compare_render=True)
            results.append(result)
            print(f"{result['state']} | {result['district']} | {table} | {result['status']} | {result['source_pages_selected']}")
    if len(results) != 9:
        raise ValueError(f"Expected 9 sample records, found {len(results)}")
    write_manifests(results, "1981_sample_manifest")
    return results


def run_full(records: list[dict[str, object]]) -> list[dict[str, object]]:
    results = []
    for record in records:
        for table in TABLES:
            key = (str(record["source_state"]), str(record["district"]))
            manual_pages = SAMPLE_PAGE_MAP.get(key, {}).get(table)
            result = process_record(record, table, manual_pages=manual_pages, compare_render=manual_pages is not None)
            results.append(result)
            print(f"{result['state']} | {result['district']} | {table} | {result['status']} | {result['source_pages_selected']}")
    write_inventory(records)
    write_manifests(results, "1981_full_manifest")
    for state, state_records in records_by_state(results).items():
        safe_state = safe_filename(state).replace(" ", "_")
        state_dir = OUTPUT_ROOT / state
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / f"1981_{safe_state}_manifest.json").write_text(json.dumps(state_records, indent=2), encoding="utf-8")
        reviews = [record for record in state_records if record["status"] == "Needs review"]
        (state_dir / f"1981_{safe_state}_review.json").write_text(json.dumps(reviews, indent=2), encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("inventory", "hash-before", "hash-after", "sample", "full"))
    args = parser.parse_args()
    if args.command == "hash-before":
        hash_source_inventory("before")
        return
    if args.command == "hash-after":
        hash_source_inventory("after")
        return
    records = run_inventory()
    if args.command == "sample":
        run_sample(records)
    elif args.command == "full":
        run_full(records)


if __name__ == "__main__":
    main()
