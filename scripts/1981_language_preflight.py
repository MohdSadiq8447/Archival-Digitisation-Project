import importlib.util
import json
import unicodedata
from pathlib import Path

spec = importlib.util.spec_from_file_location("trim", Path(__file__).with_name("1981_trim.py"))
trim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trim)

inventory = json.loads((trim.AUDIT_ROOT / "1981_inventory.json").read_text(encoding="utf-8"))
rows = []
for index, record in enumerate(inventory, start=1):
    texts = trim.read_page_texts(Path(record["source_path"]), page_limit=12)
    sample = "\n".join(texts)
    latin = 0
    nonlatin = 0
    scripts = {}
    for char in sample:
        if not char.isalpha():
            continue
        name = unicodedata.name(char, "")
        if "LATIN" in name:
            latin += 1
        else:
            nonlatin += 1
            script = name.split(" ")[0] if name else "UNKNOWN"
            scripts[script] = scripts.get(script, 0) + 1
    upper = trim.upper(sample)
    english_signals = sum(
        term in upper
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
    rows.append({
        "source": record["source"],
        "state": record["state"],
        "source_state": record["source_state"],
        "district": record["district"],
        "source_pages": record["source_pages"],
        "text_chars": len(sample),
        "latin_letters": latin,
        "nonlatin_letters": nonlatin,
        "nonlatin_ratio": round(nonlatin / max(1, latin + nonlatin), 4),
        "scripts": scripts,
        "english_signals": english_signals,
        "opening_text": sample[:1200],
    })
    if index % 25 == 0:
        print(f"preflight={index}/{len(inventory)}", flush=True)

(trim.AUDIT_ROOT / "1981_language_preflight.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
for row in rows:
    if row["english_signals"] == 0 or row["nonlatin_ratio"] > 0.45:
        print(row["source"], row["english_signals"], row["latin_letters"], row["nonlatin_letters"], row["scripts"])
