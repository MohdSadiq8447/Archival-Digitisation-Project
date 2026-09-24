import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "output" / "audit" / "1981_full_manifest.json"
spec = importlib.util.spec_from_file_location("trim", Path(__file__).with_name("1981_trim.py"))
trim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trim)

records = json.loads(MANIFEST.read_text(encoding="utf-8"))
restored = 0
for record in records:
    verification = record.get("verification") or {}
    flags = verification.get("audit_flags") or []
    if record.get("status") != "Needs review" or flags != ["first_page_heading_not_confirmed"]:
        continue
    pages = record.get("source_pages_selected") or []
    if not pages:
        continue
    destination = trim.output_path(record, record["table"])
    trim.extract_pages(ROOT / record["source"], pages, destination)
    record["output"] = str(destination.relative_to(ROOT)).replace("\\", "/")
    record["status"] = "Trimmed"
    record["reason"] = "Located from directory headings and continuation boundaries; continuation start retained after final audit."
    record["flags"] = [f for f in record.get("flags", []) if f != "first_page_heading_not_confirmed"]
    verification["restored_continuation_start"] = True
    record["verification"] = verification
    restored += 1

MANIFEST.write_text(json.dumps(records, indent=2), encoding="utf-8")
print(f"restored={restored}")
