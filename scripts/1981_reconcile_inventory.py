import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "output" / "audit"
spec = importlib.util.spec_from_file_location("trim", Path(__file__).with_name("1981_trim.py"))
trim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trim)

inventory_path = AUDIT / "1981_inventory.json"
records = json.loads(inventory_path.read_text(encoding="utf-8"))
manifest = json.loads((AUDIT / "1981_full_manifest.json").read_text(encoding="utf-8"))
before = {row["source"]: row["sha256"] for row in json.loads((AUDIT / "1981_source_hashes_before.json").read_text(encoding="utf-8"))}
metadata = {}
for row in manifest:
    metadata.setdefault(row["source"], row)
for record in records:
    row = metadata[record["source"]]
    record["volume_type"] = row["volume_type"]
    record["eligible"] = row["eligible"]
    record["eligibility_reason"] = row["eligibility_reason"]
    record["language_status"] = row["language_status"]
    record["language_reason"] = row["language_reason"]
    record["source_sha256"] = before.get(record["source"])
trim.write_inventory(records)
print(f"reconciled_inventory={len(records)}")
