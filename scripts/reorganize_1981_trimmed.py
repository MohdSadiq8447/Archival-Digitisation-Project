"""Reorganize 1981 trimmed PDFs into state/category folders.

The operation moves PDF files without opening and rewriting their content. It
records SHA-256 hashes and page counts before the move, updates known JSON/CSV
metadata paths, and validates every moved PDF afterwards.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


EXPECTED_COUNTS = {
    "civic_amenities": 279,
    "medical_educational_amenities": 280,
    "tehsil_appendix": 277,
}

TABLES = {
    "_civic_amenities.pdf": ("civic amenities", "civic_amenities"),
    "_medical_educational_amenities.pdf": (
        "mededu",
        "medical_educational_amenities",
    ),
    "_tehsil_appendix.pdf": ("tehsil appendix", "tehsil_appendix"),
}


@dataclass
class Record:
    state: str
    category: str
    table: str
    filename: str
    destination: str
    sha256: str
    page_count: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Move PDFs and update metadata after preflight succeeds.",
    )
    parser.add_argument(
        "--finalize",
        action="store_true",
        help="Finish metadata updates and validation from the saved preflight snapshot.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def page_count(path: Path) -> int:
    return len(PdfReader(str(path), strict=False).pages)


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def table_info(filename: str) -> tuple[str, str] | None:
    lowered = filename.casefold()
    for suffix, value in TABLES.items():
        if lowered.endswith(suffix.casefold()):
            return value
    return None


def write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    fields = [
        "state",
        "category",
        "table",
        "filename",
        "destination",
        "sha256",
        "page_count",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_preflight(root: Path, records: list[Record]) -> None:
    audit = root / "output" / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    payload = [asdict(record) for record in records]
    (audit / "1981_reorganization_preflight.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_csv(audit / "1981_reorganization_preflight.csv", payload)


def collect_flat(root: Path) -> list[tuple[Path, Path, str, str, str]]:
    base = root / "output" / "pdf" / "1981_trimmed"
    if not base.is_dir():
        raise RuntimeError(f"Missing trimmed-PDF directory: {base}")

    state_dirs = sorted(path for path in base.iterdir() if path.is_dir())
    found: list[tuple[Path, Path, str, str, str]] = []
    for state_dir in state_dirs:
        for source in sorted(state_dir.iterdir()):
            if not source.is_file() or source.suffix.casefold() != ".pdf":
                continue
            info = table_info(source.name)
            if info is None:
                raise RuntimeError(f"Unrecognized trimmed PDF: {source}")
            category, table = info
            destination = state_dir / category / source.name
            found.append((source, destination, state_dir.name, category, table))

    counts: dict[str, int] = {}
    for _, _, _, _, table in found:
        counts[table] = counts.get(table, 0) + 1
    if counts != EXPECTED_COUNTS:
        raise RuntimeError(
            f"Unexpected flat trimmed-PDF counts: {counts}; expected {EXPECTED_COUNTS}"
        )

    destinations: set[str] = set()
    for source, destination, *_ in found:
        key = str(destination).casefold()
        if key in destinations:
            raise RuntimeError(f"Duplicate destination: {destination}")
        destinations.add(key)
        if destination.exists():
            raise RuntimeError(f"Destination already exists: {destination}")
        if source.parent == destination.parent:
            raise RuntimeError(f"Source is already in destination folder: {source}")
    return found


def preflight(root: Path, found: list[tuple[Path, Path, str, str, str]]) -> list[Record]:
    records: list[Record] = []
    for index, (source, destination, state, category, table) in enumerate(found, 1):
        records.append(
            Record(
                state=state,
                category=category,
                table=table,
                filename=source.name,
                destination=relative(destination, root),
                sha256=sha256(source),
                page_count=page_count(source),
            )
        )
        if index % 50 == 0 or index == len(found):
            print(f"Preflighted {index}/{len(found)} PDFs")
    return records


def move_files(found: list[tuple[Path, Path, str, str, str]]) -> None:
    for _, destination, *_ in found:
        destination.parent.mkdir(parents=True, exist_ok=True)
    for source, destination, *_ in found:
        source.rename(destination)


def update_metadata(root: Path, records: list[Record]) -> int:
    replacements: dict[str, str] = {}
    base = root / "output" / "pdf" / "1981_trimmed"
    for record in records:
        old = relative(base / record.state / record.filename, root)
        new = record.destination
        replacements[old] = new
        replacements[old.replace("/", "\\")] = new.replace("/", "\\")

    preflight_names = {
        "1981_reorganization_preflight.json",
        "1981_reorganization_preflight.csv",
    }
    changed = 0
    for path in sorted((root / "output").rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in {".json", ".csv"}:
            continue
        if path.name in preflight_names:
            continue
        original = path.read_text(encoding="utf-8-sig")
        updated = original
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        if updated != original:
            with path.open("w", encoding="utf-8", newline="") as stream:
                stream.write(updated)
            changed += 1
    return changed


def load_preflight(root: Path) -> list[Record]:
    path = root / "output" / "audit" / "1981_reorganization_preflight.json"
    if not path.is_file():
        raise RuntimeError(f"Missing preflight snapshot: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [Record(**item) for item in payload]


def validate(root: Path, records: list[Record]) -> None:
    base = root / "output" / "pdf" / "1981_trimmed"
    counts: dict[str, int] = {}
    for record in records:
        path = root / Path(record.destination)
        if not path.is_file():
            raise RuntimeError(f"Moved PDF missing: {path}")
        if sha256(path) != record.sha256:
            raise RuntimeError(f"Hash changed: {path}")
        if page_count(path) != record.page_count:
            raise RuntimeError(f"Page count changed: {path}")
        counts[record.table] = counts.get(record.table, 0) + 1

    direct_pdfs = [
        path
        for state_dir in base.iterdir()
        if state_dir.is_dir()
        for path in state_dir.iterdir()
        if path.is_file() and path.suffix.casefold() == ".pdf"
    ]
    if direct_pdfs:
        raise RuntimeError(f"Flat PDFs remain: {direct_pdfs[:5]}")
    if counts != EXPECTED_COUNTS:
        raise RuntimeError(f"Unexpected organized counts: {counts}")
    print(f"Validated {len(records)} moved PDFs; counts={counts}")


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if args.finalize:
        records = load_preflight(root)
        changed = update_metadata(root, records)
        validate(root, records)
        print(f"Updated {changed} JSON/CSV metadata files")
        print("1981 trimmed-PDF reorganization finalized successfully")
        return 0
    found = collect_flat(root)
    records = preflight(root, found)
    write_preflight(root, records)
    print(f"Preflight snapshot written for {len(records)} PDFs")
    if not args.apply:
        print("Dry run complete; pass --apply to move PDFs and update metadata.")
        return 0
    move_files(found)
    changed = update_metadata(root, records)
    validate(root, records)
    print(f"Updated {changed} JSON/CSV metadata files")
    print("1981 trimmed-PDF reorganization completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
