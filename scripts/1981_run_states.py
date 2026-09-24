import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("trim", Path(__file__).with_name("1981_trim.py"))
trim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trim)

requested_states = set(sys.argv[1:])
if not requested_states:
    raise SystemExit("Pass one or more canonical state names.")

records = json.loads((trim.AUDIT_ROOT / "1981_inventory.json").read_text(encoding="utf-8"))
results = []
for record in records:
    if record["state"] not in requested_states:
        continue
    record["page_texts"] = []
    record["page_labels"] = []
    for table in trim.TABLES:
        key = (str(record["source_state"]), str(record["district"]))
        manual_pages = trim.SAMPLE_PAGE_MAP.get(key, {}).get(table)
        result = trim.process_record(record, table, manual_pages=manual_pages, compare_render=manual_pages is not None)
        results.append(result)
        print(f"{result['state']} | {result['district']} | {table} | {result['status']} | {result['source_pages_selected']}", flush=True)

for state in sorted(requested_states):
    safe_state = trim.safe_filename(state).replace(" ", "_")
    state_records = [result for result in results if result["state"] == state]
    if not state_records:
        continue
    state_dir = trim.OUTPUT_ROOT / state
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / f"1981_{safe_state}_manifest.json").write_text(json.dumps(state_records, indent=2), encoding="utf-8")
    reviews = [result for result in state_records if result["status"] == "Needs review"]
    (state_dir / f"1981_{safe_state}_review.json").write_text(json.dumps(reviews, indent=2), encoding="utf-8")
    (trim.AUDIT_ROOT / f"1981_{safe_state}_results.json").write_text(json.dumps(state_records, indent=2), encoding="utf-8")
print(f"completed_states={','.join(sorted(requested_states))} records={len(results)}", flush=True)
