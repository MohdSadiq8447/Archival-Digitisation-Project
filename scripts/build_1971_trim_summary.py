from __future__ import annotations

import ast
import csv
import json
import os
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "1971"
OUTPUT_ROOT = ROOT / "output" / "pdf" / "1971_trimmed"
AUDIT_PATH = ROOT / "output" / "audit" / "1971_trimmed_span_audit.json"
SUMMARY_ROOT = ROOT / "output" / "audit"

TABLES = (
    ("civic_amenities", "Civic Amenities"),
    ("medical_educational_amenities", "Medical and Educational Amenities"),
    ("tehsil_appendix", "Tehsil Appendix"),
)

STATE_ALIASES = {"Darman & Diu": "Daman & Diu"}
STATE_SCRIPTS = {
    "Andra Pradesh": "extract_andhra_tables.py",
    "Arunachal Pradesh": "extract_arunachal_tables.py",
    "Bihar": "extract_bihar_tables.py",
    "Dadra & Nagar Haveli": "extract_dadra_nagar_haveli_tables.py",
    "Darman & Diu": "extract_daman_diu_tables.py",
    "Gujarat": "extract_gujarat_tables.py",
    "Haryana": "extract_haryana_tables.py",
    "Jammu & Kashmir": "extract_jammu_kashmir_tables.py",
    "Karnataka": "extract_karnataka_tables.py",
    "Kerala": "extract_kerala_tables.py",
    "Madhya Pradesh": "extract_madhya_pradesh_tables.py",
    "Maharashtra": "extract_maharashtra_tables.py",
    "Manipur": "extract_manipur_tables.py",
    "Meghalaya": "extract_meghalaya_tables.py",
    "Nagaland": "extract_nagaland_tables.py",
    "Orissa": "extract_orissa_tables.py",
    "Punjab": "extract_punjab_tables.py",
    "Rajasthan": "extract_rajasthan_tables.py",
    "Sikkim": "extract_sikkim_tables.py",
    "Tamil Nadu": "extract_tamil_nadu_tables.py",
    "Tripura": "extract_tripura_tables.py",
    "West Bengal": "extract_west_bengal_tables.py",
}

BIHAR_SOURCE_DISTRICTS = {
    "24656_1971_BHA.pdf": "Bhagalpur",
    "24912_1971_DHA.pdf": "Dhanbad",
    "25098_1971_HAZ.pdf": "Hazaribagh",
    "25194_1971_RAN.pdf": "Ranchi",
    "25257_1971_MON.pdf": "Monghyr",
    "25312_1971_PAT.pdf": "Patna",
    "25599_1971_CHA.pdf": "Champaran",
    "26051_1971_SAH.pdf": "Saharsa",
    "40512_1971_PUR.pdf": "Purnea",
    "41313_1971_SHA.pdf": "Shahabad",
    "41339_1971_SIN.pdf": "Singhbhum",
    "41344_1971_PAL.pdf": "Palamau",
    "41669_1971_SAR.pdf": "Saran",
    "43128_1971_GAY.pdf": "Gaya",
    "43891_1971_DAR.pdf": "Darbhanga",
    "47756_1971_SAN.pdf": "Santal Parganas",
}

SPECIAL_SOURCE_DISTRICTS = {
    ("Gujarat", "39986_1971_TD.pdf"): "The Dangs",
    ("Maharashtra", "44875_1971_AUR.pdf"): "Aurangabad",
}


def literal_assignment(script: Path, name: str):
    if not script.exists():
        return None
    tree = ast.parse(script.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            try:
                return ast.literal_eval(node.value)
            except Exception:
                return None
    return None


def source_basename(value: str) -> str:
    return value.replace("/", "\\").rsplit("\\", 1)[-1]


def district_from_source(source_name: str, state: str | None = None) -> str:
    if state == "Bihar" and source_name in BIHAR_SOURCE_DISTRICTS:
        return BIHAR_SOURCE_DISTRICTS[source_name]
    if state and (state, source_name) in SPECIAL_SOURCE_DISTRICTS:
        return SPECIAL_SOURCE_DISTRICTS[(state, source_name)]
    return Path(source_name).stem.removeprefix("1971 ").strip()


def source_files_for_state(state: str, source_dir: Path) -> list[Path]:
    # Bihar's newly supplied DCHBs use numeric prefixes (for example,
    # 24656_1971_BHA.pdf); the older 1971 Saran Part X-C volume is excluded
    # because it is not the Part X-A Town/Village Directory source.
    if state == "Bihar":
        paths = list(source_dir.glob("*1971_*.pdf"))
    else:
        paths = list(source_dir.glob("1971 *.pdf"))
        special_names = {
            "Gujarat": "39986_1971_TD.pdf",
            "Maharashtra": "44875_1971_AUR.pdf",
        }
        special = special_names.get(state)
        if special and (source_dir / special).exists():
            paths.append(source_dir / special)
    return sorted(paths, key=lambda path: path.name.lower())


def resolve_source_name(source_dir: Path, key: str, state: str | None = None) -> str | None:
    actual = {path.name: path.name for path in source_files_for_state(state or "", source_dir)}
    if key in actual:
        return key
    matches = [
        name
        for name in actual
        if district_from_source(name, state) == str(key).strip()
    ]
    return matches[0] if len(matches) == 1 else None


def script_page_map(state: str, source_dir: Path) -> dict[tuple[str, str], list[int]]:
    script = ROOT / "scripts" / STATE_SCRIPTS[state]
    raw = literal_assignment(script, "PAGE_MAP")
    if raw is not None:
        result: dict[tuple[str, str], list[int]] = {}
        for key, tables in raw.items():
            source_name = resolve_source_name(source_dir, str(key), state)
            if not source_name:
                continue
            for table, pages in tables.items():
                result[(source_name, table)] = [int(page) for page in pages]
        return result

    raw = literal_assignment(script, "DISTRICTS") or {}
    result = {}
    for spec in raw.values():
        if not isinstance(spec, dict) or "source" not in spec:
            continue
        source_name = resolve_source_name(source_dir, str(spec["source"]), state)
        if not source_name:
            continue
        for table, pages in spec.items():
            if table in {name for name, _ in TABLES}:
                result[(source_name, table)] = [int(page) for page in pages]
    return result


def load_json_records(directory: Path, suffix: str) -> list[dict]:
    paths = sorted(directory.glob(f"*{suffix}.json"))
    records: list[dict] = []
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, list):
            records.extend(value)
    return records


def page_geometry(path: Path) -> list[tuple[float, float, int]]:
    document = fitz.open(str(path))
    return [
        (round(float(page.rect.width), 3), round(float(page.rect.height), 3), int(page.rotation))
        for page in document
    ]


def output_path_for(state: str, district: str, table: str) -> Path:
    output_state = STATE_ALIASES.get(state, state)
    directory = OUTPUT_ROOT / output_state
    for path in directory.glob(f"1971_*_{table}.pdf"):
        prefix = "1971_"
        suffix = f"_{table}.pdf"
        if path.name.startswith(prefix) and path.name.endswith(suffix):
            candidate = path.name[len(prefix) : -len(suffix)].replace("_", " ").strip()
            if candidate == district:
                return path
    safe_district = district.replace(" ", "_")
    return directory / f"1971_{safe_district}_{table}.pdf"


def special_reason(state: str, district: str, table: str) -> str | None:
    if state == "Gujarat" and district == "Junagadh":
        return "1971 Part C full-count/statistical volume; the requested Town Directory Statement IV/V and tehsil/taluk amenities appendix are absent."
    if state == "Gujarat" and district == "The Dangs" and table in {"civic_amenities", "medical_educational_amenities"}:
        return "The district volume states that The Dangs is entirely rural with no town; the corresponding Statement IV/V town tables do not exist."
    if state == "Maharashtra" and district == "Greater Maharashtra":
        return "Greater Bombay primary census abstract volume, not a district Part X-A Town/Village Directory volume; the requested tables are absent."
    return None


def build() -> tuple[list[dict], dict]:
    audit_records = []
    if AUDIT_PATH.exists():
        audit_records = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    audit_index = {
        (item.get("state"), item.get("district"), item.get("table")): item
        for item in audit_records
    }

    rows: list[dict] = []
    states_summary: list[dict] = []
    unaccounted: list[dict] = []
    geometry_cache: dict[str, list[tuple[float, float, int]]] = {}

    def cached_geometry(path: Path) -> list[tuple[float, float, int]]:
        key = str(path)
        if key not in geometry_cache:
            geometry_cache[key] = page_geometry(path)
        return geometry_cache[key]

    for source_state_dir in sorted(SOURCE_ROOT.iterdir(), key=lambda path: path.name.lower()):
        if not source_state_dir.is_dir() or source_state_dir.name == "Uttar Pradesh":
            continue
        state = source_state_dir.name
        display_state = STATE_ALIASES.get(state, state)
        output_state_dir = OUTPUT_ROOT / display_state
        manifest_records = load_json_records(output_state_dir, "manifest")
        review_records = load_json_records(output_state_dir, "review")
        manifest_index = {
            (source_basename(str(item.get("source", ""))), item.get("table")): item
            for item in manifest_records
            if item.get("table")
        }
        review_index: dict[tuple[str, str | None], dict] = {}
        review_source_index: dict[str, dict] = {}
        for item in review_records:
            source = source_basename(str(item.get("source", "")))
            review_index[(source, item.get("table"))] = item
            review_source_index.setdefault(source, item)

        page_map = script_page_map(state, source_state_dir) if state in STATE_SCRIPTS else {}
        state_rows: list[dict] = []
        for source_path in source_files_for_state(state, source_state_dir):
            source_name = source_path.name
            district = district_from_source(source_name, state)
            for table, label in TABLES:
                key = (source_name, table)
                manifest_item = manifest_index.get(key)
                pages = None
                output_path = None
                if manifest_item:
                    pages = [int(page) for page in manifest_item.get("source_pages", [])]
                    output_value = str(manifest_item.get("output", ""))
                    output_path = ROOT / output_value.replace("\\", os.sep).replace("/", os.sep)
                elif key in page_map:
                    pages = page_map[key]
                    output_path = output_path_for(state, district, table)

                if pages and output_path and output_path.exists():
                    source_geom = cached_geometry(source_path)
                    output_geom = cached_geometry(output_path)
                    geometry_ok = len(output_geom) == len(pages) and all(
                        output_geom[index] == source_geom[page - 1]
                        for index, page in enumerate(pages)
                        if 1 <= page <= len(source_geom)
                    )
                    if len(output_geom) != len(pages) or any(page < 1 or page > len(source_geom) for page in pages):
                        geometry_ok = False
                    status = "Trimmed"
                    reason = "Complete source-page span extracted; page order, geometry, rotation, margins, and scan content preserved."
                    if not geometry_ok:
                        status = "Needs review"
                        reason = "Output page count or source-page geometry did not match the recorded span."
                        unaccounted.append({"state": display_state, "district": district, "table": table, "reason": reason})
                    audit_item = audit_index.get((state, district, table), {})
                    flags = audit_item.get("flags", [])
                    if flags and all(flag == "selected_pages_do_not_text-match_table" for flag in flags):
                        reason += " Automated text check was inconclusive because the scan has weak/no text extraction; the page span was verified from the printed table layout."
                    row = {
                        "state": display_state,
                        "source_state_folder": state,
                        "district": district,
                        "source": str(source_path.relative_to(ROOT)),
                        "table": table,
                        "table_label": label,
                        "status": status,
                        "source_pages": pages,
                        "output": str(output_path.relative_to(ROOT)),
                        "output_page_count": len(output_geom),
                        "geometry_ok": geometry_ok,
                        "reason": reason,
                    }
                else:
                    review_item = review_index.get(key) or review_source_index.get(source_name)
                    reason = special_reason(state, district, table)
                    if reason is None and review_item:
                        reason = str(review_item.get("reason", "No matching table was retained."))
                    if reason is None:
                        reason = "No output or review record was found for this source table."
                        unaccounted.append({"state": display_state, "district": district, "table": table, "reason": reason})
                    row = {
                        "state": display_state,
                        "source_state_folder": state,
                        "district": district,
                        "source": str(source_path.relative_to(ROOT)),
                        "table": table,
                        "table_label": label,
                        "status": "Needs review" if reason.startswith("No output or review") else "Not trimmed",
                        "source_pages": [],
                        "output": "",
                        "output_page_count": 0,
                        "geometry_ok": False,
                        "reason": reason,
                    }
                    if reason.startswith("No output or review"):
                        row["status"] = "Needs review"
                rows.append(row)
                state_rows.append(row)
        state_summary = {
            "state": display_state,
            "source_state_folder": state,
            "district_count": len({row["district"] for row in state_rows}),
            "table_count": len(state_rows),
            "trimmed": sum(row["status"] == "Trimmed" for row in state_rows),
            "not_trimmed": sum(row["status"] == "Not trimmed" for row in state_rows),
            "needs_review": sum(row["status"] == "Needs review" for row in state_rows),
            "rows": state_rows,
        }
        states_summary.append(state_summary)

    overall = {
        "source_year": 1971,
        "excluded_states": ["Uttar Pradesh"],
        "excluded_non_1971_files": "All source files not beginning with '1971 ' (including Rajasthan 1981 PDFs) were excluded.",
        "state_count": len(states_summary),
        "district_count": sum(item["district_count"] for item in states_summary),
        "table_count": len(rows),
        "trimmed": sum(row["status"] == "Trimmed" for row in rows),
        "not_trimmed": sum(row["status"] == "Not trimmed" for row in rows),
        "needs_review": sum(row["status"] == "Needs review" for row in rows),
        "states": states_summary,
        "unaccounted": unaccounted,
        "audit_source": str(AUDIT_PATH.relative_to(ROOT)) if AUDIT_PATH.exists() else "",
    }
    return rows, overall


def main() -> None:
    rows, overall = build()
    SUMMARY_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = SUMMARY_ROOT / "1971_trimmed_summary.json"
    csv_path = SUMMARY_ROOT / "1971_trimmed_summary.csv"
    json_path.write_text(json.dumps(overall, indent=2), encoding="utf-8")
    fields = [
        "state", "source_state_folder", "district", "source", "table", "table_label",
        "status", "source_pages", "output", "output_page_count", "geometry_ok", "reason",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            item = dict(row)
            item["source_pages"] = ",".join(str(page) for page in item["source_pages"])
            writer.writerow({field: item.get(field, "") for field in fields})
    print(f"Wrote {len(rows)} state/district/table rows across {overall['state_count']} states")
    print(f"Trimmed={overall['trimmed']} Not trimmed={overall['not_trimmed']} Needs review={overall['needs_review']}")
    print(f"Unaccounted={len(overall['unaccounted'])}")
    for item in overall["unaccounted"]:
        print("UNACCOUNTED", item)
    print(json_path)
    print(csv_path)


if __name__ == "__main__":
    main()
