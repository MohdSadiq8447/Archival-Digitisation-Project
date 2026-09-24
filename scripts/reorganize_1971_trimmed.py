"""Reorganize existing 1971 trimmed PDFs into state/category folders.

This utility deliberately moves files without opening and rewriting their PDF
content. It records hashes and page counts before the move, updates the known
JSON/CSV output references, and writes an inventory plus a missing-output
report for the existing audit baseline.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from pypdf import PdfReader


EXPECTED_COUNTS = {
    "civic_amenities": 221,
    "medical_educational_amenities": 221,
    "tehsil_appendix": 189,
}

TABLE_INFO = {
    "civic_amenities": ("civic amenities", "civic"),
    "medical_educational_amenities": ("mededu", "mededu"),
    "tehsil_appendix": ("tehsil appendix", "tehsil"),
}

STATE_RENAMES = {
    "Andra Pradesh": "Andhra Pradesh",
}

PDF_RE = re.compile(
    r"^1971_(?P<district>.+)_(?P<table>"
    r"civic_amenities|medical_educational_amenities|tehsil_appendix)\.pdf$",
    re.IGNORECASE,
)


@dataclass
class Record:
    source_state: str
    final_state: str
    district: str
    table: str
    category: str
    old_filename: str
    new_filename: str
    source_path: Path
    move_path: Path
    final_path: Path
    sha256: str = ""
    page_count: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Workspace root containing output/pdf/1971_trimmed",
    )
    return parser.parse_args()


def relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pdf_page_count(path: Path) -> int:
    reader = PdfReader(str(path), strict=False)
    return len(reader.pages)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def transform_paths(value: Any, remap: Dict[str, str]) -> Tuple[Any, bool]:
    """Replace known relative output paths while preserving slash style."""

    changed = False
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            new_item, item_changed = transform_paths(item, remap)
            result[key] = new_item
            changed = changed or item_changed
        return result, changed
    if isinstance(value, list):
        result = []
        for item in value:
            new_item, item_changed = transform_paths(item, remap)
            result.append(new_item)
            changed = changed or item_changed
        return result, changed
    if not isinstance(value, str):
        return value, False

    normalized = value.replace("\\", "/")
    replacement = remap.get(normalized)
    if replacement is None:
        return value, False
    if "\\" in value and "/" not in value:
        replacement = replacement.replace("/", "\\")
    return replacement, replacement != value


def rename_state_fields(value: Any) -> Tuple[Any, bool]:
    """Normalize generated state labels without changing source folder paths."""

    changed = False
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key == "state" and item in STATE_RENAMES:
                result[key] = STATE_RENAMES[item]
                changed = True
            else:
                new_item, item_changed = rename_state_fields(item)
                result[key] = new_item
                changed = changed or item_changed
        return result, changed
    if isinstance(value, list):
        result = []
        for item in value:
            new_item, item_changed = rename_state_fields(item)
            result.append(new_item)
            changed = changed or item_changed
        return result, changed
    return value, False


def update_json_file(path: Path, remap: Dict[str, str], rename_states: bool = False) -> bool:
    with path.open("r", encoding="utf-8") as stream:
        original = json.load(stream)
    updated, path_changed = transform_paths(original, remap)
    if rename_states:
        updated, state_changed = rename_state_fields(updated)
        path_changed = path_changed or state_changed
    if not path_changed:
        return False
    atomic_write(path, json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
    return True


def update_summary_csv(path: Path, remap: Dict[str, str]) -> bool:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    changed = False
    for row in rows:
        output = row.get("output", "")
        normalized = output.replace("\\", "/")
        replacement = remap.get(normalized)
        if replacement is not None:
            row["output"] = (
                replacement.replace("/", "\\")
                if "\\" in output and "/" not in output
                else replacement
            )
            changed = True
        if row.get("state") in STATE_RENAMES:
            row["state"] = STATE_RENAMES[row["state"]]
            changed = True
    if not changed:
        return False
    lines = []
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(path, buffer.getvalue())
    return True


def write_csv(path: Path, fieldnames: List[str], rows: Iterable[Dict[str, Any]]) -> None:
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(path, buffer.getvalue())


def build_records(base: Path, root: Path) -> List[Record]:
    if not base.is_dir():
        raise RuntimeError(f"Trimmed-PDF directory not found: {base}")

    state_dirs = sorted(path for path in base.iterdir() if path.is_dir())
    if not state_dirs:
        raise RuntimeError(f"No state directories found under {base}")

    records: List[Record] = []
    unmatched: List[Path] = []
    for state_dir in state_dirs:
        source_state = state_dir.name
        final_state = STATE_RENAMES.get(source_state, source_state)
        for path in sorted(state_dir.iterdir()):
            if not path.is_file() or path.suffix.lower() != ".pdf":
                continue
            match = PDF_RE.match(path.name)
            if not match:
                unmatched.append(path)
                continue
            district = match.group("district")
            table = match.group("table").lower()
            category, suffix = TABLE_INFO[table]
            new_filename = f"{district}_{suffix}_1971.pdf"
            move_path = state_dir / category / new_filename
            final_path = base / final_state / category / new_filename
            records.append(
                Record(
                    source_state=source_state,
                    final_state=final_state,
                    district=district,
                    table=table,
                    category=category,
                    old_filename=path.name,
                    new_filename=new_filename,
                    source_path=path,
                    move_path=move_path,
                    final_path=final_path,
                )
            )

    if unmatched:
        details = "\n".join(f"  {path}" for path in unmatched)
        raise RuntimeError(f"Unmatched direct PDFs found:\n{details}")

    counts = Counter(record.table for record in records)
    if counts != Counter(EXPECTED_COUNTS):
        raise RuntimeError(
            "Unexpected trimmed-PDF counts: "
            f"{dict(counts)}; expected {EXPECTED_COUNTS}"
        )

    final_state_dirs = {}
    for state_dir in state_dirs:
        final_state = STATE_RENAMES.get(state_dir.name, state_dir.name)
        final_state_dir = base / final_state
        previous = final_state_dirs.get(final_state)
        if previous is not None and previous != state_dir:
            raise RuntimeError(
                f"Multiple source state directories map to {final_state!r}: "
                f"{previous} and {state_dir}"
            )
        final_state_dirs[final_state] = state_dir
        if final_state != state_dir.name and final_state_dir.exists():
            raise RuntimeError(
                f"Cannot rename {state_dir.name!r}; destination already exists: "
                f"{final_state_dir}"
            )

    seen_targets = {}
    for record in records:
        target_key = str(record.final_path).casefold()
        if target_key in seen_targets:
            raise RuntimeError(
                f"Duplicate target path: {record.final_path}\n"
                f"  {seen_targets[target_key].source_path}\n"
                f"  {record.source_path}"
            )
        seen_targets[target_key] = record
        if record.final_path.exists():
            raise RuntimeError(f"Destination already exists: {record.final_path}")

    return records


def preflight_pdf_metadata(records: List[Record]) -> None:
    for index, record in enumerate(records, start=1):
        if not record.source_path.is_file():
            raise RuntimeError(f"Source disappeared during preflight: {record.source_path}")
        try:
            record.sha256 = sha256(record.source_path)
            record.page_count = pdf_page_count(record.source_path)
        except Exception as exc:
            raise RuntimeError(f"Unreadable PDF: {record.source_path}: {exc}") from exc
        if index % 50 == 0 or index == len(records):
            print(f"Preflighted {index}/{len(records)} PDFs")


def move_records(records: List[Record], base: Path) -> None:
    for record in records:
        record.move_path.parent.mkdir(parents=True, exist_ok=True)
    for record in records:
        record.source_path.rename(record.move_path)

    for old_state, new_state in STATE_RENAMES.items():
        old_path = base / old_state
        new_path = base / new_state
        if old_path.exists():
            old_path.rename(new_path)


def validate_moved_files(records: List[Record]) -> None:
    for index, record in enumerate(records, start=1):
        if record.source_path.exists():
            raise RuntimeError(f"Old flat PDF still exists: {record.source_path}")
        if not record.final_path.is_file():
            raise RuntimeError(f"Moved PDF missing: {record.final_path}")
        actual_hash = sha256(record.final_path)
        if actual_hash != record.sha256:
            raise RuntimeError(
                f"Hash changed for {record.final_path}: "
                f"{record.sha256} -> {actual_hash}"
            )
        actual_pages = pdf_page_count(record.final_path)
        if actual_pages != record.page_count:
            raise RuntimeError(
                f"Page count changed for {record.final_path}: "
                f"{record.page_count} -> {actual_pages}"
            )
        if index % 50 == 0 or index == len(records):
            print(f"Validated {index}/{len(records)} moved PDFs")


def update_known_metadata(root: Path, base: Path, records: List[Record]) -> int:
    remap = {
        relative_posix(record.source_path, root): relative_posix(record.final_path, root)
        for record in records
    }
    changed_files = 0

    for path in sorted(base.rglob("*_manifest.json")):
        changed_files += int(update_json_file(path, remap))

    span_audit = root / "output" / "audit" / "1971_trimmed_span_audit.json"
    if span_audit.is_file():
        changed_files += int(update_json_file(span_audit, remap, rename_states=True))

    summary_json = root / "output" / "audit" / "1971_trimmed_summary.json"
    if summary_json.is_file():
        changed_files += int(update_json_file(summary_json, remap, rename_states=True))

    summary_csv = root / "output" / "audit" / "1971_trimmed_summary.csv"
    if summary_csv.is_file():
        changed_files += int(update_summary_csv(summary_csv, remap))

    return changed_files


def write_reports(root: Path, records: List[Record]) -> Tuple[Path, Path]:
    audit_dir = root / "output" / "audit"
    inventory_path = audit_dir / "1971_trimmed_reorganization_inventory.csv"
    inventory_rows = []
    for record in sorted(records, key=lambda item: (item.final_state, item.category, item.new_filename)):
        inventory_rows.append(
            {
                "state": record.final_state,
                "district": record.district,
                "category": record.category,
                "table": record.table,
                "old_path": relative_posix(record.source_path, root),
                "new_path": relative_posix(record.final_path, root),
                "old_filename": record.old_filename,
                "new_filename": record.new_filename,
                "page_count": record.page_count,
                "sha256": record.sha256,
            }
        )
    write_csv(
        inventory_path,
        [
            "state",
            "district",
            "category",
            "table",
            "old_path",
            "new_path",
            "old_filename",
            "new_filename",
            "page_count",
            "sha256",
        ],
        inventory_rows,
    )

    summary_path = audit_dir / "1971_trimmed_summary.json"
    if not summary_path.is_file():
        raise RuntimeError(f"Missing audit summary needed for missing report: {summary_path}")
    with summary_path.open("r", encoding="utf-8") as stream:
        summary = json.load(stream)

    missing_rows = []
    for state_summary in summary.get("states", []):
        for row in state_summary.get("rows", []):
            if row.get("status") == "Trimmed":
                continue
            missing_rows.append(
                {
                    "state": row.get("state", state_summary.get("state", "")),
                    "source_state_folder": row.get("source_state_folder", ""),
                    "district": row.get("district", ""),
                    "table": row.get("table", ""),
                    "table_label": row.get("table_label", ""),
                    "status": row.get("status", ""),
                    "source": row.get("source", ""),
                    "reason": row.get("reason", ""),
                }
            )
    if len(missing_rows) != 110:
        raise RuntimeError(
            f"Unexpected missing-output count: {len(missing_rows)}; expected 110"
        )
    for row in missing_rows:
        row["state"] = STATE_RENAMES.get(row["state"], row["state"])

    missing_path = audit_dir / "1971_trimmed_missing_outputs.csv"
    write_csv(
        missing_path,
        [
            "state",
            "source_state_folder",
            "district",
            "table",
            "table_label",
            "status",
            "source",
            "reason",
        ],
        sorted(missing_rows, key=lambda row: (row["state"], row["district"], row["table"])),
    )
    return inventory_path, missing_path


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    base = root / "output" / "pdf" / "1971_trimmed"
    records = build_records(base, root)
    print(
        "Preflight passed: "
        f"{len(records)} PDFs; "
        f"{dict(Counter(record.table for record in records))}"
    )
    preflight_pdf_metadata(records)
    move_records(records, base)
    validate_moved_files(records)
    changed_metadata = update_known_metadata(root, base, records)
    inventory_path, missing_path = write_reports(root, records)
    print(f"Updated {changed_metadata} metadata files")
    print(f"Inventory: {inventory_path}")
    print(f"Missing report: {missing_path}")
    print("Reorganization completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
