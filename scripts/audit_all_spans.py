from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "1971"
OUTPUT_ROOT = ROOT / "output" / "pdf" / "1971_trimmed"
TABLES = ("civic_amenities", "medical_educational_amenities", "tehsil_appendix")

STATE_OUTPUT_ALIASES = {"Darman & Diu": "Daman & Diu"}
MAP_SCRIPTS = {
    "Andra Pradesh": ROOT / "scripts" / "extract_andhra_tables.py",
    "Bihar": ROOT / "scripts" / "extract_bihar_tables.py",
    "Gujarat": ROOT / "scripts" / "extract_gujarat_tables.py",
}

SPECIAL_SOURCE_DISTRICTS = {
    ("Gujarat", "39986_1971_TD.pdf"): "The Dangs",
    ("Maharashtra", "44875_1971_AUR.pdf"): "Aurangabad",
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


def normalized_district(source_name: str, state: str | None = None) -> str:
    if state == "Bihar" and source_name in BIHAR_SOURCE_DISTRICTS:
        return BIHAR_SOURCE_DISTRICTS[source_name]
    if state and (state, source_name) in SPECIAL_SOURCE_DISTRICTS:
        return SPECIAL_SOURCE_DISTRICTS[(state, source_name)]
    return Path(source_name).stem.removeprefix("1971 ").strip()


def compact(text: str) -> str:
    return " ".join(text.split())


def literal_assignment(script: Path, name: str):
    tree = ast.parse(script.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return ast.literal_eval(node.value)
    return None


def script_page_map(state: str) -> dict[tuple[str, str], list[int]]:
    script = MAP_SCRIPTS.get(state)
    if not script:
        return {}
    raw = literal_assignment(script, "PAGE_MAP") or {}
    result: dict[tuple[str, str], list[int]] = {}
    source_names = {path.name: path for path in (SOURCE_ROOT / state).glob("*.pdf")}
    if not raw:
        raw = {
            str(spec["source"]): {
                table: pages
                for table, pages in spec.items()
                if table != "source"
            }
            for spec in (literal_assignment(script, "DISTRICTS") or {}).values()
            if isinstance(spec, dict) and "source" in spec
        }
    for source_key, tables in raw.items():
        source_name = str(source_key)
        if source_name not in source_names:
            matches = [name for name in source_names if Path(name).stem.removeprefix("1971 ").strip() == source_name]
            if len(matches) == 1:
                source_name = matches[0]
        for table, pages in tables.items():
            result[(source_name, table)] = [int(page) for page in pages]
    return result


def manifest_items(state: str) -> list[dict[str, object]]:
    output_state = STATE_OUTPUT_ALIASES.get(state, state)
    directory = OUTPUT_ROOT / output_state
    paths = sorted(directory.glob("*manifest.json"))
    if not paths:
        return []
    return json.loads(paths[0].read_text(encoding="utf-8"))


def review_items(state: str) -> list[dict[str, object]]:
    output_state = STATE_OUTPUT_ALIASES.get(state, state)
    directory = OUTPUT_ROOT / output_state
    paths = sorted(directory.glob("*review.json"))
    if not paths:
        return []
    return json.loads(paths[0].read_text(encoding="utf-8"))


def page_texts(source_path: Path) -> list[str]:
    document = fitz.open(str(source_path))
    return [compact(page.get_text("text")) for page in document]


def target_terms(table: str) -> tuple[str, ...]:
    if table == "civic_amenities":
        return ("CIVIC", "OTHER AMENITIES")
    if table == "medical_educational_amenities":
        return ("MEDICAL", "CULTURAL FACILITIES")
    return ("TAHSIL", "TEHSIL", "ABSTRACT OF AMENITIES")


def relevant(text: str, table: str) -> bool:
    upper = text.upper()
    return any(term in upper for term in target_terms(table))


def heading_or_continuation(text: str, table: str) -> bool:
    upper = text.upper()
    if table == "civic_amenities":
        return bool(re.search(r"\b(TABLE IV|STATEMENT IV)\b", upper)) or any(term in upper for term in ("CIVIC AND", "OTHER AMENITIES"))
    if table == "medical_educational_amenities":
        return bool(re.search(r"\b(TABLE V|STATEMENT V)\b", upper)) or any(term in upper for term in ("MEDICAL,", "AND CULTURAL FACILITIES"))
    return ("AMENITIES" in upper and any(term in upper for term in ("TAHSIL", "TEHSIL", "TALUK"))) or "ABSTRACT OF AMENITIES" in upper


def marker(text: str) -> str:
    return compact(text)[:220]


def audit_item(item: dict[str, object], text_cache: dict[str, list[str]]) -> dict[str, object]:
    source_path = ROOT / str(item["source"])
    pages = [int(page) for page in item["source_pages"]]
    table = str(item["table"])
    cache_key = str(source_path)
    if cache_key not in text_cache:
        text_cache[cache_key] = page_texts(source_path)
    texts = text_cache[cache_key]
    before_number = pages[0] - 1
    after_number = pages[-1] + 1
    flags: list[str] = []
    evidence: dict[str, object] = {}

    if before_number >= 1:
        before = texts[before_number - 1]
        evidence["before"] = {"page": before_number, "text": marker(before)}
        if heading_or_continuation(before, table):
            flags.append("possible_missing_start_page")
    if after_number <= len(texts):
        after = texts[after_number - 1]
        evidence["after"] = {"page": after_number, "text": marker(after)}
        if heading_or_continuation(after, table):
            flags.append("possible_missing_end_page")
    first = texts[pages[0] - 1]
    last = texts[pages[-1] - 1]
    evidence["first"] = {"page": pages[0], "text": marker(first)}
    evidence["last"] = {"page": pages[-1], "text": marker(last)}
    if table != "tehsil_appendix" and not relevant(first, table) and not relevant(last, table):
        flags.append("selected_pages_do_not_text-match_table")

    item_copy = {
        "district": item.get("district"),
        "table": table,
        "source": str(item["source"]),
        "output": item.get("output"),
        "source_pages": pages,
        "flags": flags,
        "evidence": evidence,
    }
    return item_copy


def main() -> None:
    records: list[dict[str, object]] = []
    text_cache: dict[str, list[str]] = {}
    for source_state_dir in sorted(SOURCE_ROOT.iterdir(), key=lambda path: path.name.lower()):
        if not source_state_dir.is_dir() or source_state_dir.name == "Uttar Pradesh":
            continue
        state = source_state_dir.name
        manifest = manifest_items(state)
        if not manifest:
            page_map = script_page_map(state)
            source_glob = "*1971_*.pdf" if state == "Bihar" else "*.pdf"
            source_paths = list(source_state_dir.glob(source_glob))
            if state == "Gujarat":
                source_paths = [path for path in source_paths if path.name != "39986_1971_TD.pdf"]
            for source_path in sorted(source_paths, key=lambda path: path.name.lower()):
                district = normalized_district(source_path.name, state)
                for table in TABLES:
                    pages = page_map.get((source_path.name, table))
                    if pages:
                        output_state = STATE_OUTPUT_ALIASES.get(state, state)
                        safe_district = district.replace(" ", "_")
                        output = OUTPUT_ROOT / output_state / f"1971_{safe_district}_{table}.pdf"
                        manifest.append(
                            {
                                "district": district,
                                "table": table,
                                "source": str(source_path.relative_to(ROOT)),
                                "output": str(output.relative_to(ROOT)),
                                "source_pages": pages,
                            }
                        )
        for item in manifest:
            records.append({"state": state, **audit_item(item, text_cache)})

    out = ROOT / "output" / "audit"
    out.mkdir(parents=True, exist_ok=True)
    output_path = out / "1971_trimmed_span_audit.json"
    output_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    flagged = [item for item in records if item["flags"]]
    print(f"Audited {len(records)} trimmed table PDFs across {len({item['state'] for item in records})} states")
    print(f"Flagged {len(flagged)} records")
    for item in flagged:
        print(f"{item['state']} | {item['district']} | {item['table']} | pages={item['source_pages']} | {','.join(item['flags'])}")
    print(output_path)


if __name__ == "__main__":
    main()
