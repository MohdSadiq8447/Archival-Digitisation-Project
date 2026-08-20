from __future__ import annotations

from census_extractor.geometry.panel_detector import PanelDetector
from census_extractor.geometry.row_segmenter import RowSegmenter
from census_extractor.pipeline.runner import PipelineRunner
from census_extractor.preprocessing.boundary_detector import TableBoundary
from census_extractor.preprocessing.pdf_loader import PDFLoader
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
