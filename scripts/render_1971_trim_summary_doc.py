from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "output" / "audit" / "1971_trimmed_summary.json"
OUTPUT_PATH = ROOT / "output" / "audit" / "1971_trimmed_summary.docx"


def set_cell_shading(cell, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:fill"), fill)


def set_cell_width(cell, width_inches: float) -> None:
    cell.width = Inches(width_inches)
    properties = cell._tc.get_or_add_tcPr()
    width = properties.find(qn("w:tcW"))
    if width is None:
        width = OxmlElement("w:tcW")
        properties.append(width)
    width.set(qn("w:w"), str(int(width_inches * 1440)))
    width.set(qn("w:type"), "dxa")


def set_repeat_table_header(row) -> None:
    properties = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    properties.append(repeat)


def set_cell_margins(cell, top=45, start=45, bottom=45, end=45) -> None:
    properties = cell._tc.get_or_add_tcPr()
    margins = properties.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        properties.append(margins)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_cell_text(cell, text: str, *, bold=False, color=None, size=7.2) -> None:
    cell.text = ""
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
    set_cell_margins(cell)
    for index, line in enumerate(text.split("\n")):
        paragraph = cell.paragraphs[0] if index == 0 else cell.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.line_spacing = 0.9
        run = paragraph.add_run(line)
        run.font.name = "Arial"
        run.font.size = Pt(size)
        run.bold = bold
        if color:
            run.font.color.rgb = RGBColor(*color)


def page_range(pages: list[int]) -> str:
    if not pages:
        return ""
    if len(pages) == 1:
        return f"source p. {pages[0]}"
    return f"source pp. {pages[0]}–{pages[-1]}"


def cell_status(row: dict) -> str:
    if row["status"] == "Trimmed":
        return f"TRIMMED\n{page_range(row['source_pages'])}"
    return f"NOT TRIMMED\n{row['reason']}"


def configure_document(document: Document) -> None:
    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Inches(11)
    section.page_height = Inches(8.5)
    section.top_margin = Inches(0.25)
    section.bottom_margin = Inches(0.25)
    section.left_margin = Inches(0.35)
    section.right_margin = Inches(0.35)
    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(8)
    normal.paragraph_format.space_after = Pt(2)


def add_footer(section) -> None:
    paragraph = section.footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.text = "1971 Census Table Extraction Audit  |  "
    run = paragraph.add_run("Page ")
    run.font.name = "Arial"
    run.font.size = Pt(7)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    paragraph._p.append(field)


def add_state_table(document: Document, state_data: dict) -> None:
    heading = document.add_heading(state_data["state"], level=2)
    heading.paragraph_format.space_before = Pt(4)
    heading.paragraph_format.space_after = Pt(2)
    run = heading.runs[0]
    run.font.name = "Arial"
    run.font.size = Pt(11)
    run.font.bold = True

    summary = document.add_paragraph(
        f"{state_data['district_count']} districts; {state_data['trimmed']} trimmed table PDFs; "
        f"{state_data['not_trimmed']} not trimmed."
    )
    summary.paragraph_format.space_after = Pt(3)
    summary.runs[0].font.size = Pt(7.5)

    table = document.add_table(rows=1, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    widths = [1.35, 2.98, 2.98, 2.98]
    headers = ["District", "Civic Amenities", "Medical and Educational Amenities", "Tehsil Appendix"]
    header_row = table.rows[0]
    set_repeat_table_header(header_row)
    for cell, width, header in zip(header_row.cells, widths, headers):
        set_cell_width(cell, width)
        set_cell_shading(cell, "D9EAF7")
        set_cell_text(cell, header, bold=True, size=7.2)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    rows_by_district: dict[str, dict[str, dict]] = {}
    for row in state_data["rows"]:
        rows_by_district.setdefault(row["district"], {})[row["table"]] = row
    for district in sorted(rows_by_district, key=str.lower):
        row_cells = table.add_row().cells
        for cell, width in zip(row_cells, widths):
            set_cell_width(cell, width)
        set_cell_text(row_cells[0], district, bold=True, size=7.2)
        row_cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
        for column, table_key in enumerate(("civic_amenities", "medical_educational_amenities", "tehsil_appendix"), start=1):
            row_data = rows_by_district[district][table_key]
            text = cell_status(row_data)
            if row_data["status"] == "Trimmed":
                set_cell_text(row_cells[column], text, bold=True, color=(0, 96, 0), size=7.0)
            else:
                set_cell_text(row_cells[column], text, bold=False, color=(150, 0, 0), size=6.4)
        for cell in row_cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP


def main() -> None:
    data = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    document = Document()
    configure_document(document)
    add_footer(document.sections[0])

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(3)
    run = title.add_run("1971 Census Table Trimming Audit Summary")
    run.font.name = "Arial"
    run.font.size = Pt(16)
    run.bold = True

    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(8)
    run = subtitle.add_run("All non-Uttar Pradesh source states, district by district")
    run.font.name = "Arial"
    run.font.size = Pt(9)

    document.add_heading("Scope and verification", level=1)
    scope = [
        f"Inventory: {data['district_count']} source districts and {data['table_count']} requested table slots across {data['state_count']} states.",
        f"Result: {data['trimmed']} table PDFs trimmed; {data['not_trimmed']} not trimmed because the source volume did not contain the requested table or the equivalent appendix.",
        "Only filenames beginning with 1971 were included. Uttar Pradesh was excluded. Rajasthan 1981 files were excluded.",
        "Trimmed means the complete original source-page span was extracted in order, without OCR, reflow, cropping, or geometry changes. Page numbers below are one-based source PDF page numbers.",
        "The source district PDFs were left unchanged. Automated text checks were treated as advisory for scanned pages; final boundaries were checked against printed headings, continuation pages, and table layout.",
    ]
    for item in scope:
        paragraph = document.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.space_after = Pt(1)
        run = paragraph.add_run(item)
        run.font.name = "Arial"
        run.font.size = Pt(8)

    document.add_heading("Corrections made during this audit", level=1)
    corrections = [
        "Andra Pradesh — Hyderabad Civic Amenities corrected to source pp. 148–149, excluding the preceding Statement III page; Nizamabad's tehsil appendix corrected to source pp. 102–105 to include the communications continuation page.",
        "West Bengal — Calcutta Civic Amenities corrected from source p. 14 to pp. 13–14; p. 13 contains the beginning of Statement IV.",
        "West Bengal — all Statement IV/V spans were rechecked against the printed headings and continuation pages; Murshidabad Statement V ends on source p. 55 before Statement VI, and no omitted page was found.",
        "Arunachal Pradesh — Kameng's circle-wise appendix corrected to source pp. 67–68; the previous span began on a staple-food page and included only the first Circle Abstract page.",
        "Daman & Diu — Civic Amenities source p. 39 was rechecked and retained as the complete Statement IV page.",
        "Jammu & Kashmir — Doda Medical/Educational Amenities corrected to source p. 45; source p. 46 is Statement VI.",
        "Kerala — Idikki Civic Amenities source p. 22 and Medical/Educational Amenities source pp. 23–24 were rechecked and retained; Kottayam Civic Amenities corrected to source p. 24 only while its Medical/Educational span remains pp. 24–25. Ernakulam was confirmed as Part X-C.",
        "Jammu & Kashmir — six tehsil abstracts now include their preceding title pages: Baramula, Jammu, Ladakh, Punch, Rajauri, and Srinagar.",
        "Tamil Nadu — North Arcot Statement IV/V ranges corrected to the actual printed Town Directory spans, and Ramanathapuram Statement V now includes its continuation page (source p. 299).",
        "Arunachal Pradesh — circle-wise abstracts added for Kameng, Lohit, Subansiri, Tirap, and Siang; Siang printed pp. 60 and 68–69 correspond to PDF source pp. 80 and 88–89.",
        "Bihar — 15 Part X-A/B DCHBs trimmed across all three requested tables; Dhanbad Statement IV/V were corrected to include their source starts on pp. 33 and 35. Shahabad was recorded as not trimmed because its supplied volume is Part X-C, and the older Saran Part X-C file was superseded by the supplied Saran DCHB.",
        "Gujarat — the replacement numbered Dangs Town Directory source was used; the stale Dangs appendix output was removed because the replacement file contains no equivalent district appendix. Junagadh remains correctly untrimmed as Part C.",
        "Maharashtra — all previously generated tehsil-appendix PDFs were removed after audit because their spans were incorrect; the 25 district tehsil entries are recorded as not retained pending correct spans. The 50 Civic/Medical PDFs remain, and Greater Maharashtra remains excluded as a municipal-corporation volume.",
        "Nagaland — Tuensang's circle-wise appendix corrected to source pp. 34–35; source p. 36 is blank/Part X-B material.",
        "Punjab — Sangrur Medical/Educational Amenities corrected from source p. 92 (Statement IV) to source p. 93 (Statement V).",
        "Haryana, Manipur, Meghalaya, Nagaland, Punjab, and Sikkim — the not-trimmed entries were rechecked against the supplied volume types and retained with their documented absence reasons; Garo Hills and Kapurthala remain Part X-C exceptions.",
    ]
    for item in corrections:
        paragraph = document.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.space_after = Pt(1)
        run = paragraph.add_run(item)
        run.font.name = "Arial"
        run.font.size = Pt(8)

    document.add_heading("State totals", level=1)
    totals_table = document.add_table(rows=1, cols=5)
    totals_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    totals_table.autofit = False
    widths = [2.4, 1.0, 1.2, 1.2, 1.2]
    for cell, width, header in zip(
        totals_table.rows[0].cells,
        widths,
        ["State", "Districts", "Trimmed", "Not trimmed", "Needs review"],
    ):
        set_cell_width(cell, width)
        set_cell_shading(cell, "D9EAF7")
        set_cell_text(cell, header, bold=True, size=7.2)
    set_repeat_table_header(totals_table.rows[0])
    for state_data in data["states"]:
        cells = totals_table.add_row().cells
        for cell, width in zip(cells, widths):
            set_cell_width(cell, width)
        values = [
            state_data["state"],
            str(state_data["district_count"]),
            str(state_data["trimmed"]),
            str(state_data["not_trimmed"]),
            str(state_data["needs_review"]),
        ]
        for cell, value in zip(cells, values):
            set_cell_text(cell, value, size=7.2)

    for state_index, state_data in enumerate(data["states"]):
        if state_index > 0:
            document.add_page_break()
        add_state_table(document, state_data)

    document.save(OUTPUT_PATH)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
