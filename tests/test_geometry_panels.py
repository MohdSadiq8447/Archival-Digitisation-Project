from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from census_extractor.geometry.panel_detector import PanelDetector
from census_extractor.geometry.row_segmenter import RowCrop, RowSegmenter
from census_extractor.pipeline.runner import PipelineRunner
from census_extractor.preprocessing.boundary_detector import TableBoundary
from census_extractor.preprocessing.pdf_loader import PDFLoader, RenderedPage
from census_extractor.schemas import SchemaRegistry


def boundary(panel):
    return TableBoundary(
        panel.page_number, panel.table_bbox, panel.header_bbox, panel.body_bbox, None
    )


def test_printed_number_matching_is_order_sensitive():
    detector = PanelDetector()
    assert detector.printed_number_match([1, 2, 3, 4], [1, 2, 3, 4]) == 1
    assert detector.printed_number_match([1, 2, 3, 4], [4, 3, 2, 1]) < 0.4
    assert detector.printed_number_match([1, 2, 3, 4], [1, 2, 4]) > 0.6


def test_agra_civic_has_exactly_21_data_rows(project_config):
    pages = PDFLoader(300, False).render_pdf(project_config.pdfs_dir / "agra_civic_1971.pdf")
    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    panels = PanelDetector().discover(pages, schema)
    anchor = next(panel for panel in panels if panel.definition.row_anchor)
    rows = RowSegmenter().segment_rows(pages[0], boundary(anchor))
    assert len(rows) == 21
    assert all(row.bbox[1] > anchor.header_bbox[3] for row in rows)


def test_agra_civic_last_column_crop_contains_complete_night_soil_value(project_config):
    pages = PDFLoader(300, False).render_pdf(project_config.pdfs_dir / "agra_civic_1971.pdf")
    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    anchor = next(
        panel for panel in PanelDetector().discover(pages, schema) if panel.definition.row_anchor
    )
    last_column = anchor.columns[-1]
    source_value = next(word for word in pages[0].pdf_words if word["text"] == "HC/MT/B")
    rows = RowSegmenter().segment_rows(pages[0], boundary(anchor))

    assert last_column.variable == "night_soil_disposal_method"
    assert last_column.x_start <= source_value["bbox"][0]
    assert source_value["bbox"][2] < last_column.x_end
    assert source_value["bbox"][2] < rows[0].bbox[2]


def test_agra_tahsil_has_four_panels_and_eight_aligned_rows(project_config, tmp_path):
    config = project_config.with_overrides(output_dir=tmp_path)
    runner = PipelineRunner(config, run_id="geometry")
    pages = runner.pdf_loader.render_pdf(config.pdfs_dir / "agra_tehsil_1971.pdf")
    schema = runner.schema_registry.require("format_003")
    panels = runner.panel_detector.discover(pages, schema)
    rows = runner._segment_and_align_rows(pages, schema, panels)
    assert len(panels) == 4
    assert set(rows) == {panel.panel_id for panel in schema.panels}
    assert {len(value) for value in rows.values()} == {8}


def test_compressed_almora_and_uttar_kashi_select_requested_statement(project_config):
    loader = PDFLoader(300, False)
    schemas = SchemaRegistry(project_config.schemas_dir)
    detector = PanelDetector()
    for district in ("almora", "uttar_kashi"):
        civic_pages = loader.render_pdf(project_config.pdfs_dir / f"{district}_civic_1971.pdf")
        med_pages = loader.render_pdf(project_config.pdfs_dir / f"{district}_mededu_1971.pdf")
        civic = detector.discover(civic_pages, schemas.require("format_001"))[0]
        mededu = detector.discover(med_pages, schemas.require("format_002"))[0]
        assert civic.header_bbox[1] < mededu.header_bbox[1]
        assert civic.body_bbox[3] <= mededu.header_bbox[1]


def test_previously_failing_aligarh_and_jhansi_have_aligned_rows(project_config, tmp_path):
    config = project_config.with_overrides(output_dir=tmp_path)
    runner = PipelineRunner(config, run_id="failures")
    schema = runner.schema_registry.require("format_001")
    for district in ("aligarh", "jhansi"):
        pages = runner.pdf_loader.render_pdf(config.pdfs_dir / f"{district}_civic_1971.pdf")
        panels = runner.panel_detector.discover(pages, schema)
        rows = runner._segment_and_align_rows(pages, schema, panels)
        counts = {len(value) for value in rows.values()}
        assert len(counts) == 1
        assert counts.pop() > 0


def test_word_bbox_rotation_keeps_monotonic_bounds():
    bbox = PDFLoader._rotate_bbox((10, 20, 30, 40), 1.5, (100, 100))
    assert bbox[0] < bbox[2]
    assert bbox[1] < bbox[3]


@pytest.mark.parametrize(
    ("district", "kind", "format_id", "expected_parents", "expected_expanded"),
    [
        ("aligarh", "civic", "format_001", 6, 6),
        ("aligarh", "mededu", "format_002", 6, 16),
        ("aligarh", "tehsil", "format_003", 7, 7),
        ("allahabad", "civic", "format_001", 11, 11),
        ("allahabad", "mededu", "format_002", 11, 22),
        ("allahabad", "tehsil", "format_003", 9, 9),
        ("almora", "civic", "format_001", 7, 7),
        ("almora", "mededu", "format_002", 7, 17),
        ("almora", "tehsil", "format_003", 4, 4),
        ("azamgarh", "civic", "format_001", 5, 5),
        ("azamgarh", "mededu", "format_002", 5, 14),
        ("azamgarh", "tehsil", "format_003", 7, 7),
        ("bahraich", "civic", "format_001", 3, 3),
        ("bahraich", "mededu", "format_002", 3, 10),
        ("bahraich", "tehsil", "format_003", 4, 4),
    ],
)
def test_five_district_structural_row_counts(
    project_config,
    tmp_path,
    district,
    kind,
    format_id,
    expected_parents,
    expected_expanded,
):
    config = project_config.with_overrides(output_dir=tmp_path, auto_deskew=False)
    runner = PipelineRunner(config, run_id=f"matrix-{district}-{kind}")
    pages = runner.pdf_loader.render_pdf(config.pdfs_dir / f"{district}_{kind}_1971.pdf")
    schema = runner.schema_registry.require(format_id)
    panels = runner.panel_detector.discover(pages, schema)
    rows = runner._segment_and_align_rows(pages, schema, panels)
    anchor_rows = rows[schema.row_anchor_panel.panel_id]
    hierarchy = runner._segment_hierarchy_rows(pages, schema, panels, rows)
    expanded = sum(len(value) for value in hierarchy.values()) if schema.hierarchy else len(anchor_rows)

    assert len(anchor_rows) == expected_parents
    assert expanded == expected_expanded
    assert {len(value) for value in rows.values()} == {expected_parents}
    assert all(
        row.alignment_confidence >= 0.5
        for panel_rows in rows.values()
        for row in panel_rows
    )


def test_allahabad_mededu_keeps_special_parents_and_excludes_banking(project_config, tmp_path):
    config = project_config.with_overrides(output_dir=tmp_path, auto_deskew=False)
    runner = PipelineRunner(config, run_id="allahabad-special")
    pages = runner.pdf_loader.render_pdf(config.pdfs_dir / "allahabad_mededu_1971.pdf")
    schema = runner.schema_registry.require("format_002")
    panels = runner.panel_detector.discover(pages, schema)
    rows = runner._segment_and_align_rows(pages, schema, panels)
    anchor = next(panel for panel in panels if panel.definition.row_anchor)
    continuation = next(panel for panel in panels if not panel.definition.row_anchor)
    anchor_text = [
        PipelineRunner._embedded_cell_text(pages[0], row.bbox)
        for row in rows[anchor.definition.panel_id][:6]
    ]
    continuation_text = " ".join(
        PipelineRunner._embedded_cell_text(pages[1], row.bbox)
        for row in rows[continuation.definition.panel_id]
    ).casefold()

    assert "Allahabad" in anchor_text[0]
    assert "Cantt" in anchor_text[1]
    assert "ALLAHABAD" in anchor_text[2]
    assert "(i)" in anchor_text[3]
    assert "(ii)" in anchor_text[4]
    assert "(iii)" in anchor_text[5]
    assert "banking" not in continuation_text
    assert continuation.body_end_source == "next_table:banking"


def test_allahabad_mededu_captures_footnote_before_trade_section(project_config, tmp_path):
    config = project_config.with_overrides(output_dir=tmp_path, auto_deskew=False)
    runner = PipelineRunner(config, run_id="allahabad-footnote")
    pages = runner.pdf_loader.render_pdf(config.pdfs_dir / "allahabad_mededu_1971.pdf")
    schema = runner.schema_registry.require("format_002")
    panels = runner.panel_detector.discover(pages, schema)
    anchor = next(panel for panel in panels if panel.definition.row_anchor)
    notes = runner.panel_detector.capture_notes(pages, panels)

    assert anchor.body_end_source == "section_title"
    assert any("Maternity & Child Welfare Centre" in note.text for note in notes)
    assert all(note.panel_id == "mededu_anchor" for note in notes)


def test_baliya_mededu_stops_at_ocr_distorted_statement_heading(
    project_config, tmp_path
):
    config = project_config.with_overrides(output_dir=tmp_path, auto_deskew=False)
    runner = PipelineRunner(config, run_id="baliya-mededu-section-end")
    pages = runner.pdf_loader.render_pdf(config.pdfs_dir / "baliya_mededu_1971.pdf")
    schema = runner.schema_registry.require("format_002")
    panels = runner.panel_detector.discover(pages, schema)
    rows = runner._segment_and_align_rows(pages, schema, panels)
    hierarchy = runner._segment_hierarchy_rows(pages, schema, panels, rows)
    anchor = next(panel for panel in panels if panel.definition.row_anchor)

    assert anchor.body_end_source == "section_title"
    assert len(rows[anchor.definition.panel_id]) == 3
    assert [len(hierarchy[index]) for index in range(3)] == [2, 2, 3]
    assert sum(len(subrows) for subrows in hierarchy.values()) == 7


@pytest.mark.parametrize(
    ("district", "kind", "format_id", "expected_parents"),
    [
        ("baliya", "civic", "format_001", 3),
        ("baliya", "tehsil", "format_003", 4),
        ("garhwal", "tehsil", "format_003", 3),
        ("kanpur", "tehsil", "format_003", 7),
        ("muzaffarnagar", "civic", "format_001", 7),
        ("parthpgad", "tehsil", "format_003", 4),
        ("peelibhit", "tehsil", "format_003", 4),
        ("uttar_kashi", "tehsil", "format_003", 5),
        ("budaun", "tehsil", "format_003", 6),
        ("meerut", "tehsil", "format_003", 7),
    ],
)
def test_v3_blocker_layouts_resolve_authoritative_parent_rows(
    project_config, tmp_path, district, kind, format_id, expected_parents
):
    config = project_config.with_overrides(output_dir=tmp_path, auto_deskew=False)
    runner = PipelineRunner(config, run_id=f"v3-{district}-{kind}")
    pages = runner.pdf_loader.render_pdf(config.pdfs_dir / f"{district}_{kind}_1971.pdf")
    schema = runner.schema_registry.require(format_id)
    panels = runner.panel_detector.discover(pages, schema)
    rows = runner._segment_and_align_rows(pages, schema, panels)

    assert len(rows[schema.row_anchor_panel.panel_id]) == expected_parents
    assert len(panels) == len(schema.panels)
    assert {len(panel_rows) for panel_rows in rows.values()} == {expected_parents}


def test_kheri_compressed_tahsil_columns_stay_inside_physical_panel(
    project_config, tmp_path
):
    config = project_config.with_overrides(output_dir=tmp_path, auto_deskew=False)
    runner = PipelineRunner(config, run_id="kheri-compressed-columns")
    pages = runner.pdf_loader.render_pdf(config.pdfs_dir / "kheri_tehsil_1971.pdf")
    schema = runner.schema_registry.require("format_003")
    panels = runner.panel_detector.discover(pages, schema)
    communications = next(
        panel
        for panel in panels
        if panel.definition.panel_id == "tahsil_communications"
    )
    left_edge, _, right_edge, _ = communications.body_bbox

    assert len(communications.columns) == 12
    assert all(
        left_edge <= column.x_start < column.x_end <= right_edge
        for column in communications.columns
    )
    assert communications.columns[-1].x_end == right_edge


def test_continuation_last_row_stops_before_next_section_marker(project_config, tmp_path):
    config = project_config.with_overrides(output_dir=tmp_path, auto_deskew=False)
    runner = PipelineRunner(config, run_id="continuation-tail")
    pages = runner.pdf_loader.render_pdf(config.pdfs_dir / "aligarh_mededu_1971.pdf")
    schema = runner.schema_registry.require("format_002")
    panels = runner.panel_detector.discover(pages, schema)
    rows = runner._segment_and_align_rows(pages, schema, panels)
    continuation = next(panel for panel in panels if not panel.definition.row_anchor)
    continuation_rows = rows[continuation.definition.panel_id]

    assert continuation.body_end_source == "next_table:banking"
    assert continuation.body_bbox[3] - continuation_rows[-1].bbox[3] > pages[1].dpi * 0.5


def test_aligarh_civic_recovers_ocr_confused_early_column_numbers(
    project_config, tmp_path
):
    config = project_config.with_overrides(output_dir=tmp_path, auto_deskew=False)
    runner = PipelineRunner(config, run_id="aligarh-civic-columns")
    pages = runner.pdf_loader.render_pdf(config.pdfs_dir / "aligarh_civic_1971.pdf")
    schema = runner.schema_registry.require("format_001")
    panels = runner.panel_detector.discover(pages, schema)
    continuation = next(
        panel for panel in panels if panel.definition.panel_id == "civic_continuation"
    )
    by_number = {span.column_no: span for span in continuation.columns}

    assert {9, 10, 11} <= set(continuation.matched_numbers)
    assert by_number[9].x_start < 341 < by_number[9].x_end
    assert by_number[10].x_start < 524 < by_number[10].x_end


def test_allahabad_tahsil_medical_stops_before_communications_heading(
    project_config, tmp_path
):
    config = project_config.with_overrides(output_dir=tmp_path, auto_deskew=False)
    runner = PipelineRunner(config, run_id="allahabad-tahsil-medical-end")
    pages = runner.pdf_loader.render_pdf(config.pdfs_dir / "allahabad_tehsil_1971.pdf")
    schema = runner.schema_registry.require("format_003")
    panels = runner.panel_detector.discover(pages, schema)
    medical = next(
        panel for panel in panels if panel.definition.panel_id == "tahsil_medical"
    )
    rows = runner._segment_and_align_rows(pages, schema, panels)

    assert medical.body_end_source == "next_panel:amenities"
    assert medical.body_bbox[3] < 1887
    assert len(rows[medical.definition.panel_id]) == 9


@pytest.mark.parametrize(
    ("district", "expected_blank_indexes"),
    [("allahabad", []), ("almora", [])],
)
def test_mededu_continuation_uses_detected_parent_bands_without_false_blanks(
    project_config, tmp_path, district, expected_blank_indexes
):
    config = project_config.with_overrides(output_dir=tmp_path, auto_deskew=False)
    runner = PipelineRunner(config, run_id=f"continuation-blank-{district}")
    pages = runner.pdf_loader.render_pdf(config.pdfs_dir / f"{district}_mededu_1971.pdf")
    schema = runner.schema_registry.require("format_002")
    panels = runner.panel_detector.discover(pages, schema)
    rows = runner._segment_and_align_rows(pages, schema, panels)
    continuation = next(panel for panel in panels if not panel.definition.row_anchor)

    blank_indexes = [
        row.row_index
        for row in rows[continuation.definition.panel_id]
        if row.interpolated
    ]

    assert blank_indexes == expected_blank_indexes


def test_count_constrained_mapping_interpolates_a_true_internal_blank(monkeypatch):
    image = Image.new("RGB", (200, 200), "white")
    rgb = np.full((200, 200, 3), 255, dtype=np.uint8)
    gray = np.full((200, 200), 255, dtype=np.uint8)
    page = RenderedPage(
        page_number=1,
        dpi=100,
        image=image,
        np_image=rgb,
        grayscale=gray,
        binary=np.zeros((200, 200), dtype=np.uint8),
        pdf_text="1\n3",
        pdf_words=[
            {"text": "1", "bbox": (20, 45, 30, 55)},
            {"text": "3", "bbox": (20, 145, 30, 155)},
        ],
        width=200,
        height=200,
    )
    boundary = TableBoundary(1, (0, 0, 200, 180), (0, 0, 200, 20), (0, 20, 200, 180), None)
    segmenter = RowSegmenter()

    def crop(index, y0, y1):
        bbox = (0, y0, 200, y1)
        return RowCrop(index, 1, bbox, 0.0, image.crop(bbox), y1 - y0, 200)

    observed = [crop(0, 40, 60), crop(1, 140, 160)]
    reference = [crop(0, 40, 60), crop(1, 90, 110), crop(2, 140, 160)]
    monkeypatch.setattr(segmenter, "segment_rows", lambda *_: observed)

    rows = segmenter.segment_expected_rows(page, boundary, 3, reference)

    assert [row.interpolated for row in rows] == [False, True, False]
    assert rows[1].source == "local_interpolation"
    assert rows[1].alignment_confidence == 0.65


def test_aligarh_note_is_metadata_not_a_parent(project_config, tmp_path):
    config = project_config.with_overrides(output_dir=tmp_path, auto_deskew=False)
    runner = PipelineRunner(config, run_id="notes")
    pages = runner.pdf_loader.render_pdf(config.pdfs_dir / "aligarh_mededu_1971.pdf")
    schema = runner.schema_registry.require("format_002")
    panels = runner.panel_detector.discover(pages, schema)
    rows = runner._segment_and_align_rows(pages, schema, panels)
    notes = runner.panel_detector.capture_notes(pages, panels)

    assert len(rows[schema.row_anchor_panel.panel_id]) == 6
    assert any("denotes Maternity" in note.text for note in notes)
    assert all(note.panel_id == "mededu_anchor" for note in notes)


def test_civic_does_not_capture_notes_from_a_later_table(project_config, tmp_path):
    config = project_config.with_overrides(output_dir=tmp_path, auto_deskew=False)
    runner = PipelineRunner(config, run_id="note-ownership")
    pages = runner.pdf_loader.render_pdf(config.pdfs_dir / "bahraich_civic_1971.pdf")
    schema = runner.schema_registry.require("format_001")
    panels = runner.panel_detector.discover(pages, schema)

    notes = runner.panel_detector.capture_notes(pages, panels)

    assert notes == []
