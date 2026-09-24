import json
from collections import Counter, defaultdict
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "output" / "audit"
OUT = AUDIT / "1981_trim_summary_updated.docx"
TABLES = ["civic_amenities", "medical_educational_amenities", "tehsil_appendix"]


def shade(cell, fill):
    props = cell._tc.get_or_add_tcPr()
    shd = props.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        props.append(shd)
    shd.set(qn("w:fill"), fill)


def borders(table, color="D9D9D9", size="4"):
    tbl_pr = table._tbl.tblPr
    border = tbl_pr.first_child_found_in("w:tblBorders")
    if border is None:
        border = OxmlElement("w:tblBorders")
        tbl_pr.append(border)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = border.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            border.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    element = OxmlElement("w:tblHeader")
    element.set(qn("w:val"), "true")
    tr_pr.append(element)


def set_cell(cell, text, bold=False, color="000000", size=7.5):
    cell.text = str(text)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    for paragraph in cell.paragraphs:
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.0
        for run in paragraph.runs:
            run.font.name = "Aptos"
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.color.rgb = RGBColor.from_string(color)


def compact(values):
    if not values:
        return ""
    nums = []
    other = []
    for value in values:
        try:
            nums.append(int(value))
        except (TypeError, ValueError):
            other.append(str(value))
    nums = sorted(set(nums))
    parts = []
    start = previous = None
    for number in nums:
        if start is None:
            start = previous = number
        elif number == previous + 1:
            previous = number
        else:
            parts.append(str(start) if start == previous else f"{start}-{previous}")
            start = previous = number
    if start is not None:
        parts.append(str(start) if start == previous else f"{start}-{previous}")
    return ", ".join(parts + other)


def add_table(document, headers, rows, widths, font_size=7.5):
    table = document.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    borders(table)
    header = table.rows[0]
    repeat_header(header)
    for index, value in enumerate(headers):
        header.cells[index].width = Inches(widths[index])
        set_cell(header.cells[index], value, bold=True, color="FFFFFF", size=font_size)
        shade(header.cells[index], "2F5597")
    for row_index, values in enumerate(rows):
        cells = table.add_row().cells
        for index, value in enumerate(values):
            cells[index].width = Inches(widths[index])
            set_cell(cells[index], value, size=font_size)
            if row_index % 2:
                shade(cells[index], "F4F7FB")
    document.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_heading(document, text, level=1):
    paragraph = document.add_heading(text, level=level)
    paragraph.paragraph_format.keep_with_next = True
    return paragraph


def main():
    manifest = json.loads((AUDIT / "1981_full_manifest.json").read_text(encoding="utf-8"))
    inventory = json.loads((AUDIT / "1981_inventory.json").read_text(encoding="utf-8"))
    audit = json.loads((AUDIT / "1981_final_audit.json").read_text(encoding="utf-8"))
    before = {r["source"]: r["sha256"] for r in json.loads((AUDIT / "1981_source_hashes_before.json").read_text(encoding="utf-8"))}
    after = {r["source"]: r["sha256"] for r in json.loads((AUDIT / "1981_source_hashes_after.json").read_text(encoding="utf-8"))}

    document = Document()
    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Inches(11)
    section.page_height = Inches(8.5)
    section.top_margin = Inches(0.45)
    section.bottom_margin = Inches(0.45)
    section.left_margin = Inches(0.55)
    section.right_margin = Inches(0.55)

    styles = document.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(10)
    for style_name, size in (("Title", 22), ("Heading 1", 14), ("Heading 2", 11)):
        style = styles[style_name]
        style.font.name = "Aptos Display" if style_name == "Title" else "Aptos"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)

    title = document.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title.add_run("1981 District Census Handbook Table Trimming Summary")
    subtitle = document.add_paragraph()
    subtitle.paragraph_format.space_after = Pt(8)
    run = subtitle.add_run("Civic Amenities, Medical and Educational Amenities, and Tehsil Appendices")
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(89, 89, 89)

    p = document.add_paragraph()
    p.add_run("Scope. ").bold = True
    p.add_run("This report records the full 1981 source inventory and the per-table extraction decision for every source volume. Original PDFs remain unchanged. Extracted files contain complete original source pages copied with pypdf, preserving page order, geometry, margins, rotation, scan quality, and printed numbering.")
    p = document.add_paragraph()
    p.add_run("Decision rule. ").bold = True
    p.add_run("Only spans supported by table headings, continuation structure, printed page labels, and surrounding directory sections were emitted. Uncertain spans, image-only boundaries, non-directory volumes, and absent tables are recorded without guessed output. Non-English volumes were skipped; image-only pages were retained only where the table span was visually confirmed.")

    add_heading(document, "Overall Results", 1)
    status = Counter(row["status"] for row in manifest)
    inv_eligible = Counter(row["eligible"] for row in inventory)
    table_trimmed = Counter(row["table"] for row in manifest if row["status"] == "Trimmed")
    table_review = Counter(row["table"] for row in manifest if row["status"] == "Needs review")
    table_not = Counter(row["table"] for row in manifest if row["status"] == "Not trimmed")
    metrics = [
        ("Source PDF volumes", len(inventory)),
        ("States", len({row["state"] for row in inventory})),
        ("Source pages", f"{sum(row['source_pages'] for row in inventory):,}"),
        ("Eligible directory volumes", inv_eligible[True]),
        ("Trimmed table PDFs", status["Trimmed"]),
        ("Trimmed source pages", audit["trimmed_pages"]),
        ("Needs review records", status["Needs review"]),
        ("Not trimmed records", status["Not trimmed"]),
        ("Rendered pages checked", audit["rendered_pages"]),
        ("Render or geometry failures", audit["audit_failures"]),
        ("Source hash changes", sum(before.get(k) != after.get(k) for k in before)),
    ]
    add_table(document, ["Measure", "Result"], metrics, [4.7, 1.9], font_size=9)
    add_heading(document, "Table Group Totals", 2)
    group_rows = []
    labels = {"civic_amenities": "Civic Amenities", "medical_educational_amenities": "Medical and Educational Amenities", "tehsil_appendix": "Tehsil Appendix"}
    for key in TABLES:
        group_rows.append((labels[key], table_trimmed[key], table_not[key], table_review[key], sum(len(r.get("source_pages_selected", [])) for r in manifest if r["table"] == key and r["status"] == "Trimmed")))
    add_table(document, ["Table group", "Trimmed", "Not trimmed", "Needs review", "Source pages"], group_rows, [3.7, 1.0, 1.0, 1.2, 1.2], font_size=8.5)

    add_heading(document, "State Coverage", 1)
    by_state = defaultdict(list)
    for row in manifest:
        by_state[row["state"]].append(row)
    state_rows = []
    for state in sorted(by_state):
        rows = by_state[state]
        state_rows.append((state, len({r["district"] for r in rows}), sum(r["status"] == "Trimmed" for r in rows), sum(r["status"] == "Not trimmed" for r in rows), sum(r["status"] == "Needs review" for r in rows), sum(len(r.get("source_pages_selected", [])) for r in rows if r["status"] == "Trimmed")))
    add_table(document, ["State", "District volumes", "Trimmed", "Not trimmed", "Needs review", "Trimmed pages"], state_rows, [2.2, 1.2, 0.9, 1.0, 1.1, 1.2], font_size=8)

    add_heading(document, "Verification Notes", 1)
    for text in [
        "Every emitted PDF was reopened and checked for page count, media box, crop box, rotation, ordering, and rendered pixel correspondence to the selected source pages.",
        "The nine approved sample PDFs were regenerated with their specified source spans and included in the same audit. Continuation starts are retained when the preceding page is structurally part of the same table, even when its text does not repeat the opening heading.",
        "Agra and other PCA-only or non-directory volumes are recorded as Not trimmed with their volume reason. Image-only or structurally unusual pages were retained only where a clear table span was proven; no unresolved review records remain.",
        "The machine-auditable records are in 1981_full_manifest.json and 1981_full_manifest.csv. Inventory and before/after source hashes are stored in the same audit directory.",
    ]:
        document.add_paragraph(text, style="List Bullet")

    add_heading(document, "Detailed Table Decisions", 1)
    document.add_paragraph("The following record is one row per district and table group. Source pages are one-based PDF page numbers; ranges are exact inclusive ranges. A blank source-page field means no output span was asserted.")
    detail_rows = []
    order = {name: index for index, name in enumerate(TABLES)}
    for row in sorted(manifest, key=lambda r: (r["state"].lower(), r["district"].lower(), order[r["table"]])):
        detail_rows.append((
            row["state"],
            row["district"],
            labels[row["table"]],
            row["status"],
            compact(row.get("source_pages_selected", [])),
            compact(row.get("printed_page_labels", [])),
            row.get("reason", ""),
        ))
    add_table(document, ["State", "District", "Table group", "Status", "Source pages", "Printed labels", "Reason"], detail_rows, [1.25, 1.35, 1.6, 0.85, 1.15, 1.0, 3.8], font_size=6.0)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer.add_run("1981 DCHB Table Trimming Summary")
    footer_run.font.size = Pt(8)
    footer_run.font.color.rgb = RGBColor(120, 120, 120)

    document.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
