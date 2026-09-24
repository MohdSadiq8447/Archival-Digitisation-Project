from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("trim1981", ROOT / "scripts" / "1981_trim.py")
trim = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(trim)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def state_stem(state: str) -> str:
    return trim.safe_filename(state).replace(" ", "_")


def apply_state(state: str) -> None:
    inventory_path = ROOT / "output" / "audit" / "1981_inventory.json"
    inventory = load_json(inventory_path)
    overrides = [item for item in load_json(ROOT / "scripts" / "1981_manual_overrides.json") if item["state"] == state]
    if not overrides:
        raise ValueError(f"No overrides found for {state}")

    inventory_by_key = {(item["state"], item["district"]): item for item in inventory}
    for item in overrides:
        key = (item["state"], item["district"])
        if key not in inventory_by_key:
            raise KeyError(f"Inventory record not found: {key}")
    for item in overrides:
        if item.get("district") == "Visakhapatnam":
            record = inventory_by_key[(state, "Visakhapatnam")]
            record["eligible"] = False
            record["volume_type"] = "PCA-only / non-directory volume"
            record["eligibility_reason"] = "Visual contents show Part-B Primary Census Abstract only; no Village/Town Directory section."
        if "inventory_eligible" in item:
            record = inventory_by_key[(state, item["district"])]
            record["eligible"] = bool(item["inventory_eligible"])
            if not record["eligible"]:
                record["volume_type"] = item.get("volume_type", "PCA-only / non-directory volume")
                record["eligibility_reason"] = item.get("reason", "Volume does not contain the requested directory tables.")
    inventory_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    result_path = ROOT / "output" / "audit" / f"1981_{state_stem(state)}_results.json"
    existing = load_json(result_path) if result_path.exists() else []
    result_by_key = {(item["district"], item["table"]): item for item in existing}

    for item in overrides:
        record = inventory_by_key[(state, item["district"])]
        table = item["table"]
        if item.get("status") == "Not trimmed":
            result = trim.base_record(record, table)
            result["status"] = "Not trimmed"
            result["reason"] = item["reason"]
            result["flags"] = ["manual_absent_or_ineligible"]
        else:
            result = trim.process_record(record, table, manual_pages=item["source_pages"], compare_render=True)
            result["reason"] = item.get("note", result["reason"])
            result["flags"] = ["manual_verified"]
        result_by_key[(item["district"], table)] = result

    state_results = [item for item in existing if item["state"] == state]
    state_results_by_key = {(item["district"], item["table"]): item for item in state_results}
    state_results_by_key.update(result_by_key)
    state_results = list(state_results_by_key.values())
    state_results.sort(key=lambda item: (item["district"], item["table"]))
    trim.write_manifests(state_results, f"1981_{state_stem(state)}_results")

    state_dir = trim.OUTPUT_ROOT / state
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / f"1981_{state_stem(state)}_manifest.json").write_text(json.dumps(state_results, indent=2), encoding="utf-8")
    reviews = [item for item in state_results if item["status"] == "Needs review"]
    (state_dir / f"1981_{state_stem(state)}_review.json").write_text(json.dumps(reviews, indent=2), encoding="utf-8")
    print(f"state={state} overrides={len(overrides)} trimmed={sum(item['status'] == 'Trimmed' for item in state_results)} review={len(reviews)} not_trimmed={sum(item['status'] == 'Not trimmed' for item in state_results)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: 1981_apply_overrides.py <state>")
    apply_state(sys.argv[1])
