import importlib.util
import json
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("trim", Path(__file__).with_name("1981_trim.py"))
trim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trim)

state = sys.argv[1]
manifest = json.loads((ROOT / "output" / "audit" / "1981_full_manifest.json").read_text(encoding="utf-8"))
for row in manifest:
    if row["state"] != state or row["status"] != "Needs review":
        continue
    source = ROOT / row["source"]
    doc = fitz.open(str(source))
    candidates = []
    for index, page in enumerate(doc):
        text = page.get_text("text")
        upper = trim.upper(text)
        signals = []
        if row["table"] == "civic_amenities":
            if "CIVIC" in upper and ("STATEMENT" in upper or "TOWN" in upper):
                signals.append("civic")
            if "NUMBER OF LATRINES" in upper or "PROTECTED WATER" in upper or "CLASS AND NAME" in upper:
                signals.append("columns")
        elif row["table"] == "medical_educational_amenities":
            if "MEDICAL" in upper and "EDUCATIONAL" in upper:
                signals.append("medical")
            if "CLASS AND NAME" in upper or "MEDICAL FACILIT" in upper or "DISPENS" in upper:
                signals.append("columns")
        else:
            if "APPENDIX" in upper or "ABSTRACT" in upper:
                signals.append("appendix")
            if "PRIMARY SCHOOL" in upper or "DISPENS" in upper or "HEALTH CENTRE" in upper:
                signals.append("columns")
            if "LAND UTILISATION" in upper or "LIST OF VILLAGES" in upper:
                signals.append("next")
        if len(signals) >= 2:
            snippet = re.sub(r"\s+", " ", text).strip()[:260]
            candidates.append({"page": index + 1, "signals": signals, "text": snippet})
    print(json.dumps({"district": row["district"], "table": row["table"], "source_pages": row.get("source_pages_selected", []), "candidates": candidates}, ensure_ascii=False))
    doc.close()
