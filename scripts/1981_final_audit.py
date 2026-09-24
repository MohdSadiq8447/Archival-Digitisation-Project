import hashlib
import importlib.util
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "output" / "audit"
OUTPUT_ROOT = ROOT / "output" / "pdf" / "1981_trimmed"
MANIFEST_PATH = AUDIT_ROOT / "1981_full_manifest.json"

spec = importlib.util.spec_from_file_location("trim", Path(__file__).with_name("1981_trim.py"))
trim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trim)

from pypdf import PdfReader
import fitz


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def box_tuple(box):
    return tuple(round(float(v), 4) for v in (box.left, box.bottom, box.right, box.top))


def render_hash(page) -> str:
    pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
    return sha256_bytes(pix.tobytes("png"))


def text_flags(table: str, first_text: str, last_text: str) -> list[str]:
    first = trim.upper(first_text)
    last = trim.upper(last_text)
    flags = []
    if table == "civic_amenities":
        if not ("CIVIC" in first and ("STATEMENT" in first or "TOWN" in first)):
            flags.append("first_page_heading_not_confirmed")
        if "STATEMENT IV-A" in last or "STATEMENT V" in last:
            flags.append("last_page_contains_next_statement")
    elif table == "medical_educational_amenities":
        if not ("MEDICAL" in first and "EDUCATIONAL" in first):
            flags.append("first_page_heading_not_confirmed")
        if "STATEMENT VI" in last or "APPENDIX" in last:
            flags.append("last_page_contains_next_section")
    else:
        if not ("APPENDIX" in first and ("ABSTRACT" in first or "EDUCATIONAL" in first)):
            flags.append("first_page_heading_not_confirmed")
        if "LAND UTILISATION" in last or "LIST OF VILLAGES" in last or "PROPORTION OF SCHEDULED" in last:
            flags.append("last_page_contains_next_appendix")
    return flags


def audit_record(record: dict) -> dict:
    result = dict(record)
    if result.get("status") != "Trimmed":
        return result
    source = ROOT / result["source"]
    output = ROOT / result["output"]
    pages = list(result.get("source_pages_selected", []))
    failures = []
    render_checks = []
    if not output.exists():
        failures.append("missing_output")
    else:
        source_reader = PdfReader(str(source))
        output_reader = PdfReader(str(output))
        if len(output_reader.pages) != len(pages):
            failures.append("page_count_mismatch")
        source_doc = fitz.open(str(source))
        output_doc = fitz.open(str(output))
        if len(output_doc) != len(pages):
            failures.append("render_page_count_mismatch")
        for index, source_number in enumerate(pages):
            if index >= len(output_reader.pages) or source_number > len(source_reader.pages):
                failures.append("source_page_out_of_range")
                continue
            source_page = source_reader.pages[source_number - 1]
            output_page = output_reader.pages[index]
            if box_tuple(source_page.mediabox) != box_tuple(output_page.mediabox):
                failures.append("media_box_mismatch")
            if box_tuple(source_page.cropbox) != box_tuple(output_page.cropbox):
                failures.append("crop_box_mismatch")
            if int(source_page.rotation or 0) != int(output_page.rotation or 0):
                failures.append("rotation_mismatch")
            if index < len(output_doc) and source_number - 1 < len(source_doc):
                source_hash = render_hash(source_doc[source_number - 1])
                output_hash = render_hash(output_doc[index])
                render_checks.append({
                    "source_page": source_number,
                    "output_page": index + 1,
                    "source_png_sha256": source_hash,
                    "output_png_sha256": output_hash,
                    "match": source_hash == output_hash,
                })
                if source_hash != output_hash:
                    failures.append("render_content_mismatch")
        first_text = source_doc[pages[0] - 1].get_text("text") if pages and pages[0] <= len(source_doc) else ""
        last_text = source_doc[pages[-1] - 1].get_text("text") if pages and pages[-1] <= len(source_doc) else ""
        source_doc.close()
        output_doc.close()
    verification = dict(result.get("verification") or {})
    content_flags = text_flags(result["table"], first_text if output.exists() and pages else "", last_text if output.exists() and pages else "") if output.exists() else []
    verification["content_flags"] = content_flags
    verification["audit_status"] = "pass" if not failures else "fail"
    verification["render_checks"] = render_checks
    verification["rendered_pages"] = len(render_checks)
    verification["audit_flags"] = sorted(set(failures))
    result["verification"] = verification
    if failures:
        result["status"] = "Needs review"
        result["reason"] = "Final audit found: " + ", ".join(sorted(set(failures)))
        result["flags"] = sorted(set(list(result.get("flags", [])) + failures))
        if output.exists():
            output.unlink()
        result["output"] = None
    return result


def main():
    records = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    audited = [audit_record(record) for record in records]
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(audited, indent=2), encoding="utf-8")
    grouped = defaultdict(list)
    for record in audited:
        grouped[record["state"]].append(record)
    for state, state_records in grouped.items():
        safe_state = trim.safe_filename(state).replace(" ", "_")
        (AUDIT_ROOT / f"1981_{safe_state}_results.json").write_text(json.dumps(state_records, indent=2), encoding="utf-8")
        state_dir = OUTPUT_ROOT / state
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / f"1981_{safe_state}_manifest.json").write_text(json.dumps(state_records, indent=2), encoding="utf-8")
        (state_dir / f"1981_{safe_state}_review.json").write_text(json.dumps([r for r in state_records if r["status"] == "Needs review"], indent=2), encoding="utf-8")
    expected = {str(Path(r["output"]).resolve()) for r in audited if r.get("status") == "Trimmed" and r.get("output")}
    actual = {str(p.resolve()) for p in OUTPUT_ROOT.rglob("*.pdf")}
    stale = sorted(actual - expected)
    for path in stale:
        Path(path).unlink()
    summary = {
        "records": len(audited),
        "status": dict(Counter(r["status"] for r in audited)),
        "trimmed_pages": sum(len(r.get("source_pages_selected", [])) for r in audited if r["status"] == "Trimmed"),
        "rendered_pages": sum((r.get("verification") or {}).get("rendered_pages", 0) for r in audited),
        "audit_failures": sum(1 for r in audited if (r.get("verification") or {}).get("audit_status") == "fail"),
        "stale_outputs_removed": stale,
    }
    (AUDIT_ROOT / "1981_final_audit.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
