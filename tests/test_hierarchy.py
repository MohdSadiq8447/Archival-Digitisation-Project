from __future__ import annotations

import asyncio
import json

import httpx
import numpy as np
import pandas as pd
import pytest
from PIL import Image

from census_extractor.geometry.row_segmenter import RowCrop, RowSegmenter
from census_extractor.metadata import MetadataRegistry
from census_extractor.normalization import normalize_rows
from census_extractor.ocr.client import NovitaDeepSeekOCRClient
from census_extractor.pipeline.exporter import RunLayout, TableExporter
from census_extractor.pipeline.runner import PipelineRunner
from census_extractor.preprocessing.pdf_loader import RenderedPage
from census_extractor.schemas import SchemaRegistry
from census_extractor.validation.validator import TableValidator


def test_subrow_segmentation_groups_embedded_words_by_baseline():
    image = Image.new("RGB", (220, 120), "white")
    empty = np.zeros((120, 220), dtype=np.uint8)
    page = RenderedPage(
        page_number=1,
        dpi=300,
        image=image,
        np_image=np.array(image),
        grayscale=empty,
        binary=empty,
        pdf_text="",
        pdf_words=[
            {"text": "H(8)", "bbox": (55, 18, 90, 38)},
            {"text": "D(1)", "bbox": (55, 48, 90, 68)},
            {"text": "FC(4)", "bbox": (55, 78, 95, 98)},
        ],
        width=220,
        height=120,
    )
    parent = RowCrop(0, 1, (0, 10, 210, 110), 0.5, image, 100, 210)

    subrows = RowSegmenter().segment_subrows(page, parent, (45, 110), (45, 190))

    assert len(subrows) == 3
    assert [row.subrow_index for row in subrows] == [0, 1, 2]
    assert all(row.source == "embedded_text" for row in subrows)
    assert subrows[0].bbox[3] < subrows[1].bbox[3] < subrows[2].bbox[3]


def test_hierarchy_cell_fallback_targets_missing_and_ambiguous_codes():
    needs_fallback = PipelineRunner._hierarchy_cell_needs_fallback

    assert needs_fallback("", is_anchor=True)
    assert needs_fallback("TBC(I)", is_anchor=True)
    assert needs_fallback("*0(1)", is_anchor=True)
    assert not needs_fallback("TBC(1)", is_anchor=True)
    assert not needs_fallback("*O(1)", is_anchor=True)
    assert not needs_fallback("...", is_anchor=True)
    assert not needs_fallback("25", is_anchor=False, data_type="integer")
    assert not needs_fallback("...", is_anchor=False, data_type="integer")
    assert needs_fallback("| 4 | 0 | 0", is_anchor=False, data_type="integer")


def test_hierarchy_embedded_recovery_uses_word_centres():
    image = Image.new("RGB", (120, 80), "white")
    empty = np.zeros((80, 120), dtype=np.uint8)
    page = RenderedPage(
        page_number=1,
        dpi=300,
        image=image,
        np_image=np.array(image),
        grayscale=empty,
        binary=empty,
        pdf_text="",
        pdf_words=[
            {"text": "712", "bbox": (60, 10, 90, 44)},
            {"text": "...", "bbox": (60, 42, 90, 62)},
        ],
        width=120,
        height=80,
    )

    assert PipelineRunner._embedded_hierarchy_cell_text(page, (50, 38, 100, 70)) == "..."


def test_parent_row_ocr_can_recover_missing_child_anchor():
    candidates = PipelineRunner._parent_hierarchy_anchor_candidates(
        "H(2) 16 *O(1) ..."
    )

    assert candidates == ["H(2)", "*O(1)"]


@pytest.fixture(scope="module")
def aligarh_hierarchy(project_config, tmp_path_factory):
    output = tmp_path_factory.mktemp("aligarh-hierarchy")
    config = project_config.with_overrides(output_dir=output, auto_deskew=False)
    runner = PipelineRunner(config, run_id="geometry")
    pdf = config.pdfs_dir / "aligarh_mededu_1971.pdf"
    pages = runner.pdf_loader.render_pdf(pdf)
    schema = runner.schema_registry.require("format_002")
    panels = runner.panel_detector.discover(pages, schema)
    parent_rows = runner._segment_and_align_rows(pages, schema, panels)
    hierarchy = runner._segment_hierarchy_rows(pages, schema, panels, parent_rows)
    return config, pdf, pages, schema, panels, parent_rows, hierarchy


def test_aligarh_mededu_has_six_parents_and_sixteen_children(aligarh_hierarchy):
    _, _, pages, schema, panels, parent_rows, hierarchy = aligarh_hierarchy
    anchor_id = schema.row_anchor_panel.panel_id

    assert len(parent_rows[anchor_id]) == 6
    assert [len(hierarchy[index]) for index in range(6)] == [3, 2, 5, 2, 2, 2]
    assert sum(map(len, hierarchy.values())) == 16

    tbc = hierarchy[2][3]
    text = PipelineRunner._embedded_cell_text(pages[0], tbc.bbox)
    assert "TBC" in text
    assert "25" in text
    anchor_panel = next(panel for panel in panels if panel.definition.row_anchor)
    last_parent = parent_rows[anchor_id][-1]
    identity_spans = [
        span
        for span in anchor_panel.columns
        if span.column_no in set(anchor_panel.definition.identity_columns)
    ]
    identity_bbox = (
        min(span.x_start for span in identity_spans),
        last_parent.bbox[1],
        max(span.x_end for span in identity_spans),
        last_parent.bbox[3],
    )
    centered_identity = " ".join(
        str(word["text"])
        for word in pages[0].pdf_words
        if word["bbox"][2] >= identity_bbox[0]
        and word["bbox"][0] <= identity_bbox[2]
        and identity_bbox[1]
        <= (word["bbox"][1] + word["bbox"][3]) / 2
        <= identity_bbox[3]
    )
    assert "Sikandr" in centered_identity
    assert "Note" not in centered_identity


@pytest.mark.parametrize(
    ("district", "expected_child_counts"),
    [
        ("allahabad", [1, 1, 6, 6, 1, 1, 1, 1, 2, 1, 1]),
        ("almora", [1, 1, 4, 4, 1, 2, 4]),
    ],
)
def test_hierarchy_keeps_aggregate_and_component_parents_separate(
    project_config, tmp_path, district, expected_child_counts
):
    config = project_config.with_overrides(output_dir=tmp_path, auto_deskew=False)
    runner = PipelineRunner(config, run_id=f"{district}-geometry")
    pages = runner.pdf_loader.render_pdf(
        config.pdfs_dir / f"{district}_mededu_1971.pdf"
    )
    schema = runner.schema_registry.require("format_002")
    panels = runner.panel_detector.discover(pages, schema)
    parent_rows = runner._segment_and_align_rows(pages, schema, panels)
    hierarchy = runner._segment_hierarchy_rows(pages, schema, panels, parent_rows)
    anchor_id = schema.row_anchor_panel.panel_id

    assert len(parent_rows[anchor_id]) == len(expected_child_counts)
    assert [
        len(hierarchy[index]) for index in range(len(expected_child_counts))
    ] == expected_child_counts
    assert sum(map(len, hierarchy.values())) == sum(expected_child_counts)


def test_mocked_hierarchy_ocr_expands_values_and_exports_lineage(
    aligarh_hierarchy, tmp_path
):
    base_config, pdf, pages, schema, panels, parent_rows, hierarchy = aligarh_hierarchy
    facilities = [
        "H(8)",
        "D(1)",
        "FC(4)",
        "H(1)",
        "D(1)",
        "H(4)",
        "D(2)",
        "NH(1)",
        "TBC(1)",
        "FC(1)",
        "H(1)",
        "HC(1)",
        "H(1)",
        "*O(1)",
        "H(2)",
        "*O(1)",
    ]
    beds = [
        "712",
        "...",
        "...",
        "6",
        "...",
        "337",
        "...",
        "...",
        "25",
        "...",
        "4",
        "6",
        "4",
        "...",
        "16",
        "...",
    ]
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        facility, bed = facilities[calls], beds[calls]
        calls += 1
        content = (
            f"<|ref|>{facility}<|/ref|><|det|>[[50,100,450,900]]<|/det|>"
            f"<|ref|>{bed}<|/ref|><|det|>[[650,100,900,900]]<|/det|>"
        )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": content}}]},
            request=request,
        )

    config = base_config.with_overrides(
        output_dir=tmp_path,
        cache_path=tmp_path / "cache",
        novita_api_key="test-key-valid",
    )
    raw_parents = [
        {column.variable: "" for column in schema.get_all_columns()} for _ in range(6)
    ]
    names = ["Aligarh", "Atrauli", "Hathras", "Mursan", "Sasni", "Sikandra Rao"]
    for index, (row, name) in enumerate(zip(raw_parents, names, strict=True), start=1):
        row.update(
            {
                "sl_no": str(index),
                "town_name": name,
                "degree_colleges": "AS(2)",
                "higher_secondary_schools": "20",
            }
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = NovitaDeepSeekOCRClient(config, http)
            runner = PipelineRunner(config, run_id="mock-hierarchy", ocr_client=client)
            return await runner._expand_hierarchy_rows(
                pages,
                schema,
                panels,
                raw_parents,
                hierarchy,
                "f" * 64,
                [],
            )

    expanded, results = asyncio.run(run())

    assert calls == 16
    assert len(results) == 16
    assert len(expanded) == 16
    assert [row["hospitals_dispensaries"] for row in expanded[:3]] == [
        "H(8)",
        "D(1)",
        "FC(4)",
    ]
    assert [row["med_beds"] for row in expanded[:3]] == ["712", "...", "..."]
    assert all(row["town_name"] == "Aligarh" for row in expanded[:3])
    assert all(row["degree_colleges"] == "AS(2)" for row in expanded[:3])
    assert all(row["higher_secondary_schools"] == "20" for row in expanded[:3])
    assert expanded[8]["hospitals_dispensaries"] == "TBC(1)"
    assert expanded[8]["med_beds"] == "25"

    normalized = normalize_rows(expanded, schema)
    report = TableValidator(quality_threshold=0).validate(
        "aligarh",
        schema,
        normalized,
        panels_complete=True,
        aligned_row_counts={"anchor": 6, "continuation": 6},
        panel_scores=[1, 1],
        ocr_row_successes=16,
        ocr_row_total=16,
        parent_row_count=6,
    )
    hierarchy_errors = {
        finding.code
        for finding in report.findings
        if finding.code.startswith("hierarchy_")
        or finding.code in {"duplicate_identity", "serial_progression"}
    }
    assert not hierarchy_errors
    assert report.parent_rows_count == 6
    assert report.total_rows == 16

    metadata = MetadataRegistry(config.metadata_path).get_for_pdf(pdf)
    paths = TableExporter(RunLayout.create(tmp_path / "export-runs", "r1")).export_table(
        metadata, schema, normalized, report, "QUARANTINED", "f" * 64
    )
    frame = pd.read_parquet(paths["parquet"])
    first = json.loads(paths["jsonl"].read_text(encoding="utf-8").splitlines()[0])
    assert frame["parent_row_index"].dtype == "Int64"
    assert frame.loc[0, "parent_row_index"] == 0
    assert frame.loc[0, "subrow_index"] == 0
    assert frame.loc[0, "subrow_count"] == 3
    assert first["parent_row_index"] == 0
    assert first["subrow_count"] == 3


def test_flat_formats_do_not_emit_hierarchy_lineage(project_config):
    schemas = SchemaRegistry(project_config.schemas_dir)
    for format_id in ("format_001", "format_003"):
        rows = normalize_rows([{"sl_no": "1", "town_name": "Town"}], schemas.require(format_id))
        assert rows[0].parent_row_index is None
        assert rows[0].subrow_index is None
        assert rows[0].subrow_count is None
