import csv
import re
from pathlib import Path

ROOT = Path(r"E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh")
SRC = ROOT / "outputs/postprocessed/up1971-remaining48-novita-sourcechecked-v1/csv"
OUT_ROOT = ROOT / "outputs/postprocessed"
META = {
    "row_index", "pdf_id", "district", "state", "year", "format_id", "table_id",
    "source_pdf", "source_pdf_sha256", "source_page_start", "source_page_end",
    "anchor_printed_page", "continuation_printed_page", "metadata_workbook",
    "metadata_workbook_sha256", "extracted_at", "parent_row_index", "subrow_index",
    "subrow_count", "requires_review", "row_type", "reference_target",
}
PROMPT = re.compile(r"\\sum|prompt|ocr explanation|validation label|foreign script", re.I)
REPEAT = re.compile(r"(?P<w>\\b[\\w()./*+-]+\\b)(?:\\s+(?P=w)){1,}", re.I)

def clean(v: str) -> str:
    if not v:
        return ""
    s = " ".join(v.replace("\u00a0", " ").split()).strip()
    for _ in range(3):
        n = REPEAT.sub(r"\g<w>", s)
        if n == s:
            break
        s = n
    if re.fullmatch(r"(?:\.\.\.|…|·){2,}(?:\\s+(?:\.\.\.|…|·))+", s):
        s = "..."
    return s

def main() -> None:
    done = skipped = 0
    for src in sorted(SRC.glob("*.csv")):
        pdf_id = src.stem
        out = OUT_ROOT / f"up1971-{pdf_id}-regex-cleaned-v1"
        if out.exists():
            skipped += 1
            continue
        (out / "csv").mkdir(parents=True, exist_ok=True)
        with src.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f)); fields = list(rows[0].keys()) if rows else []
        changes=[]; unresolved=[]
        for r in rows:
            for k in fields:
                if k in META or k.endswith("_flag"):
                    continue
                old=r.get(k,""); new=clean(old)
                if new != old:
                    r[k]=new; changes.append((r.get("row_index",""),k,old,new,"regex cleanup"))
            for k in fields:
                if k in META or k.endswith("_flag"):
                    continue
                if PROMPT.search(r.get(k,"")):
                    old=r[k]; r[k]=""; r[f"{k}_flag"]="AUTOMATIC_CLEANUP_UNRESOLVED"; r["requires_review"]="True"
                    changes.append((r.get("row_index",""),k,old,"","prompt/metadata contamination removed"))
                    unresolved.append((r.get("row_index",""),k,"","AUTOMATIC_CLEANUP_UNRESOLVED"))
            if any(r.get(k,"") for k in fields if k.endswith("_flag")) or r.get("requires_review","").lower()=="true":
                r["requires_review"]="True"
                for k in fields:
                    if k.endswith("_flag") and r.get(k):
                        unresolved.append((r.get("row_index",""),k.removesuffix("_flag"),r.get(k.removesuffix("_flag"),""),r[k]))
        with (out/"csv"/src.name).open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
        with (out/"CORRECTION_LOG.csv").open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.writer(f); w.writerow(["row_index","variable","original_value","corrected_value","reason"]); w.writerows(changes)
        with (out/"UNRESOLVED_CELLS.csv").open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.writer(f); w.writerow(["row_index","variable","value","flag"]); w.writerows(unresolved)
        status="REGEX_CLEANED_WITH_UNRESOLVED" if unresolved else "REGEX_CLEANED"
        (out/"AUTOMATIC_CLEANUP_REPORT.md").write_text(f"# {pdf_id} automatic cleanup\n\n- Status: `{status}`\n- Rows retained: {len(rows)}\n- Regex changes: {len(changes)}\n- Unresolved flagged cells: {len(unresolved)}\n\nThis sequential cleanup retains uncertainty flags and is separate from manually source-inspected folders.\n",encoding="utf-8")
        done += 1; print(f"{done}: {pdf_id} ({len(rows)} rows, {len(unresolved)} unresolved)", flush=True)
    print(f"completed={done} skipped={skipped}")

if __name__ == "__main__":
    main()
