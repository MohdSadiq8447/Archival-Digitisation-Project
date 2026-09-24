"""Validate the 1981 PDF reorganization, metadata paths, and YAML schemas."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import yaml
from pypdf import PdfReader


EXPECTED_COUNTS = {
    "civic_amenities": 279,
    "medical_educational_amenities": 280,
    "tehsil_appendix": 277,
}
EXPECTED_FOLDERS = {
    "civic_amenities": "civic amenities",
    "medical_educational_amenities": "mededu",
    "tehsil_appendix": "tehsil appendix",
}
STALE_FLAT_PATH = re.compile(
    r"output[/\\]pdf[/\\]1981_trimmed[/\\][^/\\]+[/\\]1981_.+_(?:civic_amenities|medical_educational_amenities|tehsil_appendix)\.pdf"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    base = root / "output" / "pdf" / "1981_trimmed"
    audit = root / "output" / "audit"
    preflight = json.loads((audit / "1981_reorganization_preflight.json").read_text(encoding="utf-8"))
    manifest = json.loads((audit / "1981_full_manifest.json").read_text(encoding="utf-8"))

    counts = Counter()
    for record in preflight:
        destination = root / Path(record["destination"])
        if not destination.is_file():
            fail(f"Missing moved PDF: {destination}")
        if sha256(destination) != record["sha256"]:
            fail(f"Hash mismatch: {destination}")
        if len(PdfReader(str(destination), strict=False).pages) != record["page_count"]:
            fail(f"Page-count mismatch: {destination}")
        counts[record["table"]] += 1
    if dict(counts) != EXPECTED_COUNTS:
        fail(f"PDF counts differ: {dict(counts)}")

    direct = [
        path
        for state_dir in base.iterdir()
        if state_dir.is_dir()
        for path in state_dir.iterdir()
        if path.is_file() and path.suffix.casefold() == ".pdf"
    ]
    if direct:
        fail(f"Direct state-root PDFs remain: {direct[:3]}")

    stale = []
    for path in (root / "output").rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in {".json", ".csv"}:
            continue
        text = path.read_text(encoding="utf-8-sig")
        if STALE_FLAT_PATH.search(text):
            stale.append(str(path))
    if stale:
        fail(f"Stale flat-path references remain: {stale[:5]}")

    completed = [row for row in manifest if row.get("status") == "Trimmed"]
    by_state_table: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in completed:
        by_state_table.setdefault((str(row["state"]), str(row["table"])), []).append(row)
    manifest_state_counts = Counter((str(row["state"]), str(row["table"])) for row in completed)
    preflight_state_counts = Counter((str(row["state"]), str(row["table"])) for row in preflight)
    if manifest_state_counts != preflight_state_counts:
        fail("State-by-state PDF counts differ between the manifest and preflight snapshot")

    schema_paths = sorted((root / "schemas").glob("*/format_*.yaml"))
    if len(schema_paths) != 44:
        fail(f"Expected 44 YAML schemas, found {len(schema_paths)}")
    if list((root / "schemas").glob("*/format_003.yaml")):
        fail("Unexpected format_003.yaml found")

    states = sorted({str(row["state"]) for row in completed})
    if sorted({path.parent.name for path in schema_paths}) != states:
        fail("Schema state directories do not match completed manifest states")

    for path in schema_paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            fail(f"Schema is not a mapping: {path}")
        state = str(data.get("state"))
        table = "civic_amenities" if data.get("format_id") == "format_001" else "medical_educational_amenities"
        rows = by_state_table.get((state, table), [])
        expected_columns = 19 if table == "civic_amenities" else 20
        expected_panels = ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], list(range(11, 20))) if table == "civic_amenities" else (list(range(1, 12)), list(range(12, 21)))
        if data.get("source_year") != 1981:
            fail(f"Wrong source year in {path}")
        if data.get("availability", {}).get("trimmed_pdf_count") != len(rows):
            fail(f"Availability count mismatch in {path}")
        assignments = data.get("district_format_assignments", {}).get(data.get("format_id"), [])
        if sorted(assignments) != sorted(str(row["district"]) for row in rows):
            fail(f"District assignment mismatch in {path}")
        columns = data.get("column_definitions", [])
        if len(columns) != expected_columns:
            fail(f"Column count mismatch in {path}")
        panels = data.get("page_layout", {}).get("panels", [])
        if len(panels) != 2 or panels[0].get("printed_columns") != expected_panels[0] or panels[1].get("printed_columns") != expected_panels[1]:
            fail(f"Panel layout mismatch in {path}")
        expected_folder = EXPECTED_FOLDERS[table]
        for output in data.get("availability", {}).get("output_files", []):
            if f"/{expected_folder}/" not in str(output):
                fail(f"Wrong category folder in {path}: {output}")
            if not (root / Path(str(output))).is_file():
                fail(f"Schema output missing in {path}: {output}")

    print(f"Validated {sum(counts.values())} PDFs; counts={dict(counts)}")
    print(f"Validated {len(schema_paths)} YAML schemas across {len(states)} states/UTs")
    print("No stale flat-path references found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
