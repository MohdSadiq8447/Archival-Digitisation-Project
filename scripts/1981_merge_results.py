import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("trim", Path(__file__).with_name("1981_trim.py"))
trim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trim)

files = sorted(trim.AUDIT_ROOT.glob("1981_*_results.json"))
results = []
for path in files:
    results.extend(json.loads(path.read_text(encoding="utf-8")))
if len(results) != len(set((item["source"], item["table"]) for item in results)):
    raise ValueError("Duplicate source/table records in state results.")
trim.write_manifests(results, "1981_full_manifest")
print(f"merged_files={len(files)} records={len(results)}")
