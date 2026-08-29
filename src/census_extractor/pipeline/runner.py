"""Production runner for geometry, Novita OCR, validation, quarantine, and resume."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from census_extractor.config import PipelineConfig, default_config
from census_extractor.geometry.aligner import ContinuationAligner
from census_extractor.geometry.column_detector import ColumnSpan
from census_extractor.geometry.panel_detector import (
    DetectedNote,
    PanelDetector,
    PanelDiscoveryError,
    PanelGeometry,
)
from census_extractor.geometry.row_segmenter import RowCrop, RowSegmenter, SubRowCrop
from census_extractor.metadata import DocumentMetadata, MetadataRegistry
from census_extractor.normalization import NormalizedRow, normalize_rows
from census_extractor.ocr.client import (
    NovitaConfigurationError,
    NovitaDeepSeekOCRClient,
    OCRRequestContext,
    OCRResult,
)
from census_extractor.ocr.column_assigner import ColumnAssigner
from census_extractor.ocr.prompts import (
    build_cell_free_ocr_prompt,
    build_columns_grounding_prompt,
    build_page_grounding_prompt,
    build_row_grounding_prompt,
)
from census_extractor.pipeline.exporter import RunLayout, TableExporter
from census_extractor.preprocessing.boundary_detector import TableBoundary
from census_extractor.preprocessing.pdf_loader import PDFLoader, RenderedPage
from census_extractor.schemas import ColumnDefinition, SchemaRegistry, TableSchema
from census_extractor.validation.validator import TableValidationReport, TableValidator
from census_extractor.visualization.overlay import TableVisualizer

RUN_STATUSES = {"SUCCESS", "QUARANTINED", "ERROR", "DRY_RUN"}


@dataclass(slots=True)
class ExtractionSummary:
    run_id: str
    pdf_name: str
    pdf_id: str
    district: str
    format_id: str
    status: str
    total_rows: int
    parent_rows: int
    valid_rows: int
    quality_score: float
    quality_components: dict[str, float] = field(default_factory=dict)
    exported_files: dict[str, Path] = field(default_factory=dict)
    cache_metrics: dict[str, int] = field(default_factory=dict)
    actionable_failures: list[str] = field(default_factory=list)
    notes: list[dict[str, Any]] = field(default_factory=list)
    error_message: str | None = None

    @property
    def confidence_score(self) -> float:
        return self.quality_score

    def manifest_record(self) -> dict[str, Any]:
        value = asdict(self)
        value["exported_files"] = {key: str(path) for key, path in self.exported_files.items()}
        value["completed_at"] = datetime.now(UTC).isoformat()
        return value


class PipelineRunner:
    def __init__(
        self,
        config: PipelineConfig | None = None,
        *,
        run_id: str | None = None,
        resume: bool = False,
        ocr_client: NovitaDeepSeekOCRClient | None = None,
    ):
        self.config = config or default_config
        self.run_id = run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.layout = RunLayout.create(self.config.runs_dir, self.run_id)
        if resume and not self.layout.manifest.is_file():
            raise FileNotFoundError(f"Cannot resume missing run {self.run_id!r}")
        self.schema_registry = SchemaRegistry(self.config.schemas_dir)
        self.metadata_registry = MetadataRegistry(self.config.metadata_path)
        self.pdf_loader = PDFLoader(self.config.render_dpi, self.config.auto_deskew)
        self.panel_detector = PanelDetector()
        self.row_segmenter = RowSegmenter(crop_padding_px=self.config.crop_padding_px)
        self.aligner = ContinuationAligner(max_distance_tolerance=0.15)
        self.column_assigner = ColumnAssigner()
        self.validator = TableValidator(self.config.quality_threshold)
        self.ocr_client = ocr_client or NovitaDeepSeekOCRClient(self.config)
        self.exporter = TableExporter(self.layout)
        self.visualizer = TableVisualizer(self.layout.viz)
        self._manifest_lock = asyncio.Lock()
        self._manifest = self._load_or_create_manifest(resume)

    def _load_or_create_manifest(self, resume: bool) -> dict[str, Any]:
        if resume:
            return json.loads(self.layout.manifest.read_text(encoding="utf-8"))
        manifest = {
            "run_id": self.run_id,
            "created_at": datetime.now(UTC).isoformat(),
            "novita_model": self.config.novita_model,
            "prompt_version": self.config.prompt_version,
            "quality_threshold": self.config.quality_threshold,
            "results": {},
        }
        self.exporter.write_manifest(self.layout.manifest, manifest)
        return manifest

    async def process_pdf_async(
        self,
        pdf_path: Path,
        format_id: str | None = None,
        save_viz: bool = True,
        is_dry_run: bool = False,
        enable_retry: bool = True,
    ) -> ExtractionSummary:
        pdf_path = Path(pdf_path).resolve()
        metadata: DocumentMetadata | None = None
        try:
            if not pdf_path.is_file():
                raise FileNotFoundError(f"PDF not found: {pdf_path}")
            metadata = self.metadata_registry.get_for_pdf(pdf_path)
            if format_id is not None and format_id != metadata.format_id:
                raise ValueError(
                    f"Format override {format_id!r} conflicts with workbook value {metadata.format_id!r}"
                )
            schema = self.schema_registry.require(metadata.format_id)
            if not is_dry_run and not self.ocr_client.is_configured():
                raise NovitaConfigurationError(
                    "NOVITA_API_KEY is required for process/batch. Use --dry-run for geometry inspection only."
                )
            pdf_sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
            pages = self.pdf_loader.render_pdf(pdf_path)
            audit_records: list[dict[str, Any]] = []
            panels = await self._discover_panels(
                pages, schema, metadata, pdf_sha256, audit_records, is_dry_run
            )
            notes = self.panel_detector.capture_notes(pages, panels)
            note_payload = [asdict(note) for note in notes]
            audit_records.extend(
                {"record_type": "source_note", **record} for record in note_payload
            )
            panel_rows = self._segment_and_align_rows(
                pages, schema, panels, audit_records
            )
            anchor_count = len(panel_rows[schema.row_anchor_panel.panel_id])
            if anchor_count == 0:
                raise PanelDiscoveryError("Anchor panel contains zero usable data rows")
            hierarchy_rows = self._segment_hierarchy_rows(pages, schema, panels, panel_rows)
            expanded_count = (
                sum(len(rows) for rows in hierarchy_rows.values())
                if schema.hierarchy is not None
                else anchor_count
            )
            geometry_payload = self._geometry_payload(
                metadata,
                schema,
                pages,
                panels,
                panel_rows,
                hierarchy_rows,
                pdf_sha256,
                notes,
            )
            geometry_path = self.exporter.write_geometry(metadata.pdf_id, geometry_payload)
            if save_viz:
                self._save_visualizations(
                    metadata, pages, panels, panel_rows, hierarchy_rows, notes
                )
            if is_dry_run:
                summary = ExtractionSummary(
                    run_id=self.run_id,
                    pdf_name=metadata.file_name,
                    pdf_id=metadata.pdf_id,
                    district=metadata.district,
                    format_id=metadata.format_id,
                    status="DRY_RUN",
                    total_rows=expanded_count,
                    parent_rows=anchor_count,
                    valid_rows=0,
                    quality_score=min(self._panel_quality(panel) for panel in panels),
                    quality_components={
                        "geometry": min(self._panel_quality(panel) for panel in panels)
                    },
                    exported_files={"geometry": geometry_path},
                    cache_metrics={"hits": 0, "misses": 0},
                    notes=note_payload,
                )
                await self._record_summary(summary)
                return summary

            raw_rows, panel_results = await self._extract_all_panels(
                pages, schema, panels, panel_rows, pdf_sha256, audit_records
            )
            if schema.hierarchy is not None:
                raw_rows, hierarchy_results = await self._expand_hierarchy_rows(
                    pages,
                    schema,
                    panels,
                    raw_rows,
                    hierarchy_rows,
                    pdf_sha256,
                    audit_records,
                )
                panel_results.extend(hierarchy_results)
            normalized = normalize_rows(raw_rows, schema)
            report = self._validate(schema, metadata, normalized, panels, panel_rows, panel_results)
            if enable_retry and not report.is_valid:
                changed = await self._retry_failing_cells(
                    pages,
                    schema,
                    panels,
                    panel_rows,
                    hierarchy_rows,
                    raw_rows,
                    report,
                    pdf_sha256,
                    audit_records,
                )
                if changed:
                    normalized = normalize_rows(raw_rows, schema)
                    report = self._validate(
                        schema, metadata, normalized, panels, panel_rows, panel_results
                    )
            status = "SUCCESS" if report.is_valid else "QUARANTINED"
            exported = self.exporter.export_table(
                metadata, schema, normalized, report, status, pdf_sha256
            )
            audit_records.append(
                {"record_type": "raw_rows", "pdf_id": metadata.pdf_id, "rows": raw_rows}
            )
            audit_path = self.exporter.write_audit(metadata.pdf_id, audit_records)
            exported["audit"] = audit_path
            exported["geometry"] = geometry_path
            quality = asdict(report.quality)
            summary = ExtractionSummary(
                run_id=self.run_id,
                pdf_name=metadata.file_name,
                pdf_id=metadata.pdf_id,
                district=metadata.district,
                format_id=metadata.format_id,
                status=status,
                total_rows=report.total_rows,
                parent_rows=report.parent_rows_count,
                valid_rows=report.valid_rows_count,
                quality_score=report.quality.overall,
                quality_components=quality,
                exported_files=exported,
                cache_metrics={
                    "hits": self.ocr_client.cache_hits,
                    "misses": self.ocr_client.cache_misses,
                },
                actionable_failures=[
                    finding.message
                    for finding in report.findings
                    if finding.severity.value == "ERROR"
                ],
                notes=note_payload,
            )
            await self._record_summary(summary)
            return summary
        except Exception as exc:
            summary = ExtractionSummary(
                run_id=self.run_id,
                pdf_name=pdf_path.name,
                pdf_id=metadata.pdf_id if metadata else pdf_path.stem,
                district=metadata.district if metadata else "",
                format_id=metadata.format_id if metadata else (format_id or "unknown"),
                status="ERROR",
                total_rows=0,
                parent_rows=0,
                valid_rows=0,
                quality_score=0.0,
                cache_metrics={
                    "hits": self.ocr_client.cache_hits,
                    "misses": self.ocr_client.cache_misses,
                },
                actionable_failures=[str(exc)],
                error_message=str(exc),
            )
            await self._record_summary(summary)
            return summary

    async def _discover_panels(
        self,
        pages: list[RenderedPage],
        schema: TableSchema,
        metadata: DocumentMetadata,
        pdf_sha256: str,
        audit: list[dict[str, Any]],
        dry_run: bool,
    ) -> list[PanelGeometry]:
        try:
            return self.panel_detector.discover(pages, schema)
        except PanelDiscoveryError:
            if dry_run or not self.ocr_client.is_configured():
                raise
            grounded_pages: list[RenderedPage] = []
            for page in pages:
                context = OCRRequestContext(
                    pdf_sha256,
                    (0, 0, page.width, page.height),
                    -1,
                    page.page_number,
                    "page_grounding",
                    build_page_grounding_prompt(schema, page.page_number),
                )
                result = await self.ocr_client.ocr_crop_async(page.image, context)
                audit.append(
                    {"record_type": "page_grounding", **self.ocr_client.audit_record(result)}
                )
                if not result.has_usable_boxes:
                    raise PanelDiscoveryError(
                        f"Novita page grounding did not yield usable boxes on page {page.page_number}"
                    ) from None
                words = self._grounded_tokens_to_words(result, page.width, page.height)
                grounded_pages.append(replace(page, pdf_words=words))
            discovered = self.panel_detector.discover(grounded_pages, schema)
            for panel in discovered:
                panel.discovery_source = "novita_page_grounding"
            return discovered

    @staticmethod
    def _grounded_tokens_to_words(
        result: OCRResult, width: int, height: int
    ) -> list[dict[str, Any]]:
        """Expand a grounded OCR line into positioned words inside its box."""
        words: list[dict[str, Any]] = []
        for token in result.tokens:
            if token.bbox is None:
                continue
            x0, y0, x1, y1 = ColumnAssigner.scale_bbox_1000(token.bbox, (0, 0, width, height))
            parts = token.text.split() or [token.text]
            step = (x1 - x0) / len(parts)
            for index, part in enumerate(parts):
                words.append(
                    {
                        "text": part,
                        "bbox": (
                            round(x0 + index * step),
                            round(y0),
                            round(x0 + (index + 1) * step),
                            round(y1),
                        ),
                    }
                )
        return words

    def _segment_and_align_rows(
        self,
        pages: list[RenderedPage],
        schema: TableSchema,
        panels: list[PanelGeometry],
        audit: list[dict[str, Any]] | None = None,
    ) -> dict[str, list[RowCrop]]:
        by_id = {panel.definition.panel_id: panel for panel in panels}
        anchor_geometry = by_id[schema.row_anchor_panel.panel_id]
        anchor_page = pages[anchor_geometry.page_number - 1]
        anchor_rows = self.row_segmenter.segment_rows(anchor_page, self._boundary(anchor_geometry))
        if len(schema.row_anchor_panel.identity_columns) >= 2:
            serial_number, name_number = schema.row_anchor_panel.identity_columns[:2]
            serial_span = next(
                (span for span in anchor_geometry.columns if span.column_no == serial_number),
                None,
            )
            name_span = next(
                (span for span in anchor_geometry.columns if span.column_no == name_number),
                None,
            )
            if serial_span is not None and name_span is not None:
                identity_rows = self.row_segmenter.segment_parent_rows_from_identity(
                    anchor_page,
                    self._boundary(anchor_geometry),
                    (serial_span.x_start, serial_span.x_end),
                    (name_span.x_start, name_span.x_end),
                )
                if identity_rows:
                    anchor_rows = identity_rows
        if not anchor_rows and schema.row_anchor_panel.identity_columns:
            identity_numbers = set(schema.row_anchor_panel.identity_columns)
            identity_spans = [
                span for span in anchor_geometry.columns if span.column_no in identity_numbers
            ]
            if identity_spans:
                identity_bbox = (
                    anchor_geometry.body_bbox[0],
                    anchor_geometry.body_bbox[1],
                    max(span.x_end for span in identity_spans),
                    anchor_geometry.body_bbox[3],
                )
                identity_boundary = TableBoundary(
                    anchor_geometry.page_number,
                    anchor_geometry.table_bbox,
                    anchor_geometry.header_bbox,
                    identity_bbox,
                    None,
                )
                identity_rows = self.row_segmenter.segment_rows(anchor_page, identity_boundary)
                anchor_rows = self._widen_rows(
                    anchor_page, identity_rows, anchor_geometry.body_bbox
                )
        anchor_rows = self._exclude_note_rows(anchor_page, anchor_geometry, anchor_rows)
        for index, row in enumerate(anchor_rows):
            row.row_index = index
        result = {schema.row_anchor_panel.panel_id: anchor_rows}
        if audit is not None:
            audit.append(self._row_segmentation_audit(anchor_geometry, anchor_rows))
        for definition in schema.panels:
            if definition.row_anchor:
                continue
            geometry = by_id[definition.panel_id]
            page = pages[geometry.page_number - 1]
            aligned: list[RowCrop] = []
            if len(definition.identity_columns) >= 2:
                serial_number, name_number = definition.identity_columns[:2]
                serial_span = next(
                    (span for span in geometry.columns if span.column_no == serial_number), None
                )
                name_span = next(
                    (span for span in geometry.columns if span.column_no == name_number), None
                )
                if serial_span is not None and name_span is not None:
                    aligned = self.row_segmenter.segment_parent_rows_from_identity(
                        page,
                        self._boundary(geometry),
                        (serial_span.x_start, serial_span.x_end),
                        (name_span.x_start, name_span.x_end),
                    )
                    aligned = self._exclude_note_rows(page, geometry, aligned)
            if len(aligned) != len(anchor_rows):
                aligned = self.row_segmenter.segment_expected_rows(
                    page,
                    self._boundary(geometry),
                    len(anchor_rows),
                    anchor_rows,
                )
            for index, row in enumerate(aligned):
                row.row_index = index
            result[definition.panel_id] = aligned
            if audit is not None:
                audit.append(self._row_segmentation_audit(geometry, aligned))
        return result

    @staticmethod
    def _exclude_note_rows(
        page: RenderedPage,
        anchor_geometry: PanelGeometry,
        rows: list[RowCrop],
    ) -> list[RowCrop]:
        identity_numbers = set(anchor_geometry.definition.identity_columns)
        identity_spans = [
            span for span in anchor_geometry.columns if span.column_no in identity_numbers
        ]
        if not identity_spans:
            return rows
        x0 = min(span.x_start for span in identity_spans)
        x1 = max(span.x_end for span in identity_spans)
        retained: list[RowCrop] = []
        for row in rows:
            words = [
                word
                for word in page.pdf_words
                if word["bbox"][2] >= x0
                and word["bbox"][0] <= x1
                and row.bbox[1]
                <= (word["bbox"][1] + word["bbox"][3]) / 2
                <= row.bbox[3]
            ]
            text = " ".join(
                str(word["text"])
                for word in sorted(words, key=lambda item: (item["bbox"][1], item["bbox"][0]))
            ).strip()
            if re.search(r"(?:^|\s)notes?\b|\bdenotes?\b", text, re.IGNORECASE):
                continue
            retained.append(row)
        return retained

    @staticmethod
    def _row_segmentation_audit(
        panel: PanelGeometry, rows: list[RowCrop]
    ) -> dict[str, Any]:
        return {
            "record_type": "row_segmentation",
            "panel_id": panel.definition.panel_id,
            "page_number": panel.page_number,
            "body_end_source": panel.body_end_source,
            "row_count": len(rows),
            "rows": [
                {
                    "row_index": row.row_index,
                    "bbox": row.bbox,
                    "source": row.source,
                    "alignment_confidence": row.alignment_confidence,
                    "interpolated": row.interpolated,
                }
                for row in rows
            ],
        }

    def _segment_hierarchy_rows(
        self,
        pages: list[RenderedPage],
        schema: TableSchema,
        panels: list[PanelGeometry],
        panel_rows: dict[str, list[RowCrop]],
    ) -> dict[int, list[SubRowCrop]]:
        hierarchy = schema.hierarchy
        if hierarchy is None:
            return {}
        anchor_panel = next(
            panel for panel in panels if panel.definition.panel_id == schema.row_anchor_panel.panel_id
        )
        anchor_page = pages[anchor_panel.page_number - 1]
        anchor_column = schema.get_column_by_var(hierarchy.anchor_variable)
        if anchor_column is None:
            raise PanelDiscoveryError(
                f"Hierarchy anchor variable {hierarchy.anchor_variable!r} is undefined"
            )
        anchor_span = next(
            (span for span in anchor_panel.columns if span.column_no == anchor_column.column_no),
            None,
        )
        hierarchy_columns = [
            schema.get_column_by_var(variable) for variable in hierarchy.child_variables
        ]
        if any(column is None for column in hierarchy_columns):
            raise PanelDiscoveryError("Hierarchy child variable is undefined")
        child_numbers = {
            column.column_no for column in hierarchy_columns if column is not None
        }
        child_spans = [
            span for span in anchor_panel.columns if span.column_no in child_numbers
        ]
        if anchor_span is None or len(child_spans) != len(child_numbers):
            raise PanelDiscoveryError("Hierarchy columns were not located in the anchor panel")
        crop_x_range = (
            min(span.x_start for span in child_spans),
            max(span.x_end for span in child_spans),
        )
        result: dict[int, list[SubRowCrop]] = {}
        for parent in panel_rows[schema.row_anchor_panel.panel_id]:
            result[parent.row_index] = self.row_segmenter.segment_subrows(
                anchor_page,
                parent,
                (anchor_span.x_start, anchor_span.x_end),
                crop_x_range,
            )
        return result

    def _widen_rows(
        self,
        page: RenderedPage,
        rows: list[RowCrop],
        full_body_bbox: tuple[int, int, int, int],
    ) -> list[RowCrop]:
        widened: list[RowCrop] = []
        x0 = max(0, full_body_bbox[0] - self.config.crop_padding_px)
        x1 = min(page.width, full_body_bbox[2] + self.config.crop_padding_px)
        for row in rows:
            bbox = (x0, row.bbox[1], x1, row.bbox[3])
            widened.append(
                RowCrop(
                    row.row_index,
                    row.page_number,
                    bbox,
                    row.y_normalized,
                    page.image.crop(bbox),
                    row.height_px,
                    x1 - x0,
                )
            )
        return widened

    async def _extract_all_panels(
        self,
        pages: list[RenderedPage],
        schema: TableSchema,
        panels: list[PanelGeometry],
        panel_rows: dict[str, list[RowCrop]],
        pdf_sha256: str,
        audit: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[OCRResult]]:
        anchor_count = len(panel_rows[schema.row_anchor_panel.panel_id])
        raw_rows = [
            {column.variable: "" for column in schema.get_all_columns()}
            for _ in range(anchor_count)
        ]
        tasks: list[
            tuple[
                PanelGeometry,
                RowCrop,
                tuple[int, int, int, int],
                asyncio.Task[OCRResult],
            ]
        ] = []
        for panel in panels:
            prompt = build_row_grounding_prompt(schema, panel.definition)
            for row in panel_rows[panel.definition.panel_id]:
                ocr_bbox = self._row_ocr_bbox(panel, row)
                page = pages[panel.page_number - 1]
                context = OCRRequestContext(
                    pdf_sha256,
                    ocr_bbox,
                    row.row_index,
                    panel.page_number,
                    panel.definition.panel_id,
                    prompt,
                )
                tasks.append(
                    (
                        panel,
                        row,
                        ocr_bbox,
                        asyncio.create_task(
                            self.ocr_client.ocr_crop_async(page.image.crop(ocr_bbox), context)
                        ),
                    )
                )
        results: list[OCRResult] = []
        for panel, row, ocr_bbox, task in tasks:
            result = await task
            results.append(result)
            audit.append(
                {
                    "record_type": "row_ocr",
                    "panel_id": panel.definition.panel_id,
                    **self.ocr_client.audit_record(result),
                }
            )
            assigned = (
                self.column_assigner.assign_tokens_to_columns(result, panel.columns, ocr_bbox)
                if result.has_usable_boxes
                else {}
            )
            repeated_grounding = self._has_repeated_grounded_row(result, panel)
            if panel.definition.row_anchor:
                assigned = self._apply_anchor_identity(schema, panel, ocr_bbox, result, assigned)
                assigned = self._apply_embedded_anchor_identity(
                    pages[panel.page_number - 1], schema, panel, row.bbox, assigned
                )
            elif self._is_cross_reference(raw_rows[row.row_index], schema):
                continue
            if not result.has_usable_boxes or repeated_grounding:
                if repeated_grounding:
                    audit.append(
                        {
                            "record_type": "row_ocr_recovery",
                            "panel_id": panel.definition.panel_id,
                            "row_index": row.row_index,
                            "reason": "repeated_grounded_row",
                            "fallback": "strict_cell_ocr",
                        }
                    )
                assigned.update(
                    await self._fallback_entire_row(
                        pages[panel.page_number - 1],
                        schema,
                        panel,
                        row,
                        pdf_sha256,
                        audit,
                    )
                )
            else:
                crossed = self._cross_boundary_variables(
                    schema, panel, result, ocr_bbox
                )
                joined_recovery = self._recover_joined_numeric_cells(
                    schema, panel, result, ocr_bbox
                )
                if joined_recovery:
                    assigned.update(joined_recovery)
                    crossed.difference_update(joined_recovery)
                    audit.append(
                        {
                            "record_type": "cross_boundary_recovery",
                            "panel_id": panel.definition.panel_id,
                            "row_index": row.row_index,
                            "source": "grounded_token_comma_partition",
                            "values": joined_recovery,
                        }
                    )
                if crossed:
                    assigned.update(
                        await self._fallback_entire_row(
                            pages[panel.page_number - 1],
                            schema,
                            panel,
                            row,
                            pdf_sha256,
                            audit,
                            variables=crossed,
                        )
                    )
            if panel.definition.row_anchor and not self._is_cross_reference(assigned, schema):
                await self._refine_night_soil_column(
                    pages[panel.page_number - 1],
                    schema,
                    panel,
                    row,
                    result,
                    assigned,
                    pdf_sha256,
                    audit,
                )
            for variable, value in assigned.items():
                if not panel.definition.row_anchor and variable in {
                    "sl_no",
                    "town_name",
                    "tahsil_name",
                }:
                    continue
                raw_rows[row.row_index][variable] = value
        return raw_rows, results

    async def _expand_hierarchy_rows(
        self,
        pages: list[RenderedPage],
        schema: TableSchema,
        panels: list[PanelGeometry],
        parent_rows: list[dict[str, Any]],
        hierarchy_rows: dict[int, list[SubRowCrop]],
        pdf_sha256: str,
        audit: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[OCRResult]]:
        hierarchy = schema.hierarchy
        if hierarchy is None:
            return parent_rows, []
        anchor_panel = next(
            panel for panel in panels if panel.definition.panel_id == schema.row_anchor_panel.panel_id
        )
        page = pages[anchor_panel.page_number - 1]
        child_columns = [
            schema.get_column_by_var(variable) for variable in hierarchy.child_variables
        ]
        if any(column is None for column in child_columns):
            raise PanelDiscoveryError("Hierarchy child column is undefined")
        columns = [column for column in child_columns if column is not None]
        child_numbers = {column.column_no for column in columns}
        child_spans = [
            span for span in anchor_panel.columns if span.column_no in child_numbers
        ]
        if len(child_spans) != len(columns):
            raise PanelDiscoveryError("Hierarchy child column geometry is incomplete")
        prompt = build_columns_grounding_prompt(columns)

        tasks: dict[tuple[int, int], asyncio.Task[OCRResult]] = {}
        expanded_index = 0
        for parent_index, parent in enumerate(parent_rows):
            for subrow in hierarchy_rows[parent_index]:
                if not self._is_cross_reference(parent, schema):
                    context = OCRRequestContext(
                        pdf_sha256,
                        subrow.bbox,
                        expanded_index,
                        anchor_panel.page_number,
                        (
                            f"{anchor_panel.definition.panel_id}:hierarchy:"
                            f"{parent_index}:{subrow.subrow_index}"
                        ),
                        prompt,
                    )
                    tasks[(parent_index, subrow.subrow_index)] = asyncio.create_task(
                        self.ocr_client.ocr_crop_async(
                            self._prepare_hierarchy_crop(subrow.image_crop), context
                        )
                    )
                expanded_index += 1

        expanded: list[dict[str, Any]] = []
        results: list[OCRResult] = []
        for parent_index, parent in enumerate(parent_rows):
            subrows = hierarchy_rows[parent_index]
            parent_anchor_candidates = self._parent_hierarchy_anchor_candidates(
                str(parent.get(hierarchy.anchor_variable, ""))
            )
            for subrow in subrows:
                assigned = {variable: "" for variable in hierarchy.child_variables}
                task = tasks.get((parent_index, subrow.subrow_index))
                if task is not None:
                    result = await task
                    results.append(result)
                    audit.append(
                        {
                            "record_type": "hierarchy_child_ocr",
                            "panel_id": anchor_panel.definition.panel_id,
                            "parent_row_index": parent_index,
                            "subrow_index": subrow.subrow_index,
                            "crop_bbox": subrow.bbox,
                            **self.ocr_client.audit_record(result),
                        }
                    )
                    if result.has_usable_boxes:
                        assigned.update(
                            self.column_assigner.assign_tokens_to_columns(
                                result, child_spans, subrow.bbox
                            )
                        )
                        fallback_columns = [
                            column
                            for column in columns
                            if column.variable == hierarchy.anchor_variable
                            and self._hierarchy_cell_needs_fallback(
                                assigned.get(column.variable, ""),
                                is_anchor=True,
                                data_type=column.data_type,
                            )
                        ]
                        if fallback_columns:
                            recovered = await self._fallback_hierarchy_subrow(
                                page,
                                schema,
                                anchor_panel,
                                subrow,
                                fallback_columns,
                                child_spans,
                                len(expanded),
                                pdf_sha256,
                                audit,
                            )
                            for variable, text in recovered.items():
                                if text.strip():
                                    assigned[variable] = text
                    else:
                        assigned.update(
                            await self._fallback_hierarchy_subrow(
                                page,
                                schema,
                                anchor_panel,
                                subrow,
                                columns,
                                child_spans,
                                len(expanded),
                                pdf_sha256,
                                audit,
                            )
                        )

                spans_by_number = {span.column_no: span for span in child_spans}
                for column in columns:
                    current = assigned.get(column.variable, "")
                    is_anchor = column.variable == hierarchy.anchor_variable
                    if not self._hierarchy_cell_needs_fallback(
                        current, is_anchor=is_anchor, data_type=column.data_type
                    ):
                        continue
                    span = spans_by_number[column.column_no]
                    embedded_bbox = (
                        span.x_start,
                        subrow.bbox[1],
                        span.x_end,
                        subrow.bbox[3],
                    )
                    embedded = self._embedded_hierarchy_cell_text(page, embedded_bbox)
                    if self._hierarchy_cell_needs_fallback(
                        embedded, is_anchor=is_anchor, data_type=column.data_type
                    ):
                        continue
                    assigned[column.variable] = embedded
                    audit.append(
                        {
                            "record_type": "hierarchy_value_selection",
                            "parent_row_index": parent_index,
                            "subrow_index": subrow.subrow_index,
                            "variable": column.variable,
                            "selected_source": "embedded_text",
                            "grounded_or_fallback_candidate": current,
                            "embedded_candidate": embedded,
                        }
                    )

                anchor_value = assigned.get(hierarchy.anchor_variable, "")
                anchor_column = schema.get_column_by_var(hierarchy.anchor_variable)
                if (
                    anchor_column is not None
                    and self._hierarchy_cell_needs_fallback(
                        anchor_value,
                        is_anchor=True,
                        data_type=anchor_column.data_type,
                    )
                    and len(parent_anchor_candidates) == len(subrows)
                ):
                    selected = parent_anchor_candidates[subrow.subrow_index]
                    assigned[hierarchy.anchor_variable] = selected
                    audit.append(
                        {
                            "record_type": "hierarchy_value_selection",
                            "parent_row_index": parent_index,
                            "subrow_index": subrow.subrow_index,
                            "variable": hierarchy.anchor_variable,
                            "selected_source": "parent_row_ocr",
                            "grounded_or_fallback_candidate": anchor_value,
                            "parent_candidate": selected,
                        }
                    )

                record: dict[str, Any]
                if hierarchy.repeat_parent_values:
                    record = dict(parent)
                else:
                    record = {column.variable: "" for column in schema.get_all_columns()}
                    for identity in ("sl_no", "town_name", "tahsil_name"):
                        if identity in parent:
                            record[identity] = parent[identity]
                    if subrow.subrow_index == 0:
                        record.update(parent)
                for variable in hierarchy.child_variables:
                    record[variable] = assigned.get(variable, "")
                record["__parent_row_index"] = parent_index
                record["__subrow_index"] = subrow.subrow_index
                record["__subrow_count"] = len(subrows)
                expanded.append(record)
        return expanded, results

    @staticmethod
    def _hierarchy_cell_needs_fallback(
        value: str, *, is_anchor: bool, data_type: str = "string"
    ) -> bool:
        text = value.strip()
        if not text:
            return True
        placeholder = r"(?:nil|n\.?a\.?|[-–—.·…]+)"
        if data_type == "integer":
            return re.fullmatch(rf"(?:{placeholder}|\d[\d,]*(?:\.\d+)?)", text, re.I) is None
        if not is_anchor:
            return False
        if re.fullmatch(rf"(?:see(?:\s+.*)?|{placeholder}|\d+(?:\.\d+)?)", text, re.I):
            return False
        institution_code = r"\*?\s*[A-Za-z]+(?:\s*/\s*[A-Za-z]+)*\s*\(\s*\d+(?:\.\d+)?\s*\)\.?"
        return re.fullmatch(institution_code, text) is None

    @staticmethod
    def _parent_hierarchy_anchor_candidates(value: str) -> list[str]:
        institution_code = r"\*?\s*[A-Za-z]+(?:\s*/\s*[A-Za-z]+)*\s*\(\s*\d+(?:\.\d+)?\s*\)\.?"
        return [match.group(0).strip() for match in re.finditer(institution_code, value)]

    @staticmethod
    def _prepare_hierarchy_crop(image: Image.Image) -> Image.Image:
        """Upscale a thin child row with vertical whitespace but unchanged x proportions."""
        padding = max(8, image.height // 2)
        padded = ImageOps.expand(image.convert("RGB"), border=(0, padding, 0, padding), fill="white")
        return padded.resize((padded.width * 2, padded.height * 2), Image.Resampling.LANCZOS)

    async def _fallback_hierarchy_subrow(
        self,
        page: RenderedPage,
        schema: TableSchema,
        panel: PanelGeometry,
        subrow: SubRowCrop,
        columns: list[ColumnDefinition],
        spans: list[ColumnSpan],
        expanded_index: int,
        pdf_sha256: str,
        audit: list[dict[str, Any]],
    ) -> dict[str, str]:
        values: dict[str, str] = {}
        spans_by_number = {span.column_no: span for span in spans}
        for column in columns:
            span = spans_by_number[column.column_no]
            bbox = (
                max(0, span.x_start),
                subrow.bbox[1],
                min(page.width, span.x_end),
                subrow.bbox[3],
            )
            context = OCRRequestContext(
                pdf_sha256,
                bbox,
                expanded_index,
                panel.page_number,
                (
                    f"{panel.definition.panel_id}:{column.variable}:hierarchy:"
                    f"{subrow.parent_row_index}:{subrow.subrow_index}"
                ),
                build_cell_free_ocr_prompt(schema, panel.definition, column),
            )
            result = await self.ocr_client.ocr_cell_async(
                self._prepare_hierarchy_crop(page.image.crop(bbox)), context
            )
            values[column.variable] = self._cell_text(result)
            audit.append(
                {
                    "record_type": "hierarchy_cell_fallback",
                    "variable": column.variable,
                    "parent_row_index": subrow.parent_row_index,
                    "subrow_index": subrow.subrow_index,
                    **self.ocr_client.audit_record(result),
                }
            )
        return values

    def _row_ocr_bbox(self, panel: PanelGeometry, row: RowCrop) -> tuple[int, int, int, int]:
        """Keep whole-row OCR compact while physical edge columns remain complete."""
        if len(panel.columns) < 2:
            return row.bbox
        previous = panel.columns[-2]
        last = panel.columns[-1]
        standard_width = previous.x_end - previous.x_start
        standard_right = last.x_start + standard_width + self.config.crop_padding_px
        return (row.bbox[0], row.bbox[1], min(row.bbox[2], standard_right), row.bbox[3])

    async def _refine_night_soil_column(
        self,
        page: RenderedPage,
        schema: TableSchema,
        panel: PanelGeometry,
        row: RowCrop,
        row_result: OCRResult,
        assigned: dict[str, str],
        pdf_sha256: str,
        audit: list[dict[str, Any]],
    ) -> None:
        column = schema.get_column_by_var("night_soil_disposal_method")
        if column is None:
            return
        span = next((item for item in panel.columns if item.column_no == column.column_no), None)
        if span is None:
            return
        current = assigned.get(column.variable, "").strip()
        touches_edge = any(
            token.bbox is not None and token.bbox[2] >= 980 for token in row_result.tokens
        )
        if self._valid_night_soil_code(current) and not touches_edge:
            return

        bbox = (
            max(0, span.x_start - self.config.crop_padding_px),
            max(0, row.bbox[1] - self.config.crop_padding_px),
            min(page.width, span.x_end + self.config.crop_padding_px),
            min(page.height, row.bbox[3] + self.config.crop_padding_px),
        )
        embedded = self._embedded_cell_text(page, bbox)
        selected, selected_source = current, "row_grounding"
        if embedded and self._valid_night_soil_code(embedded):
            selected, selected_source = embedded, "embedded_text"
        else:
            context = OCRRequestContext(
                pdf_sha256,
                bbox,
                row.row_index,
                panel.page_number,
                f"{panel.definition.panel_id}:{column.variable}:edge_refinement",
                build_cell_free_ocr_prompt(schema, panel.definition, column),
            )
            result = await self.ocr_client.ocr_cell_async(page.image.crop(bbox), context)
            cell_text = self._cell_text(result)
            audit.append(
                {
                    "record_type": "edge_cell_refinement",
                    "variable": column.variable,
                    "row_candidate": current,
                    "embedded_candidate": embedded,
                    **self.ocr_client.audit_record(result),
                }
            )
            if cell_text and self._valid_night_soil_code(cell_text):
                selected, selected_source = cell_text, "cell_free_ocr"
            elif (
                cell_text
                and not self._valid_night_soil_code(current)
                and len(cell_text) > len(selected)
            ):
                selected, selected_source = cell_text, "cell_free_ocr"
        assigned[column.variable] = selected
        audit.append(
            {
                "record_type": "edge_value_selection",
                "row_index": row.row_index,
                "variable": column.variable,
                "selected_value": selected,
                "selected_source": selected_source,
                "row_candidate": current,
                "embedded_candidate": embedded,
            }
        )

    @staticmethod
    def _embedded_cell_text(page: RenderedPage, bbox: tuple[int, int, int, int]) -> str:
        x0, y0, x1, y1 = bbox
        words = [
            word
            for word in page.pdf_words
            if word["bbox"][0] >= x0
            and word["bbox"][2] <= x1
            and word["bbox"][1] < y1
            and word["bbox"][3] > y0
        ]
        return " ".join(
            str(word["text"])
            for word in sorted(words, key=lambda item: (item["bbox"][1], item["bbox"][0]))
        ).strip()

    @staticmethod
    def _embedded_hierarchy_cell_text(
        page: RenderedPage, bbox: tuple[int, int, int, int]
    ) -> str:
        """Read only words whose centres belong to this thin child cell."""
        x0, y0, x1, y1 = bbox
        words = [
            word
            for word in page.pdf_words
            if x0 <= (word["bbox"][0] + word["bbox"][2]) / 2 <= x1
            and y0 <= (word["bbox"][1] + word["bbox"][3]) / 2 <= y1
        ]
        return " ".join(
            str(word["text"])
            for word in sorted(words, key=lambda item: (item["bbox"][1], item["bbox"][0]))
        ).strip()

    @staticmethod
    def _valid_night_soil_code(value: str) -> bool:
        text = " ".join(value.split()).strip()
        if not text or re.fullmatch(r"(?:nil|[-–—.·…]+)", text, re.IGNORECASE):
            return True
        codes = r"(?:HC|HL|MT|WB|B|C|T)"
        return bool(re.fullmatch(rf"{codes}(?:/{codes})*", text, re.IGNORECASE))

    async def _fallback_entire_row(
        self,
        page: RenderedPage,
        schema: TableSchema,
        panel: PanelGeometry,
        row: RowCrop,
        pdf_sha256: str,
        audit: list[dict[str, Any]],
        variables: set[str] | None = None,
    ) -> dict[str, str]:
        values: dict[str, str] = {}
        strict_bboxes = self._strict_cell_bboxes(page, panel, row.bbox)
        for span in panel.columns:
            column = schema.get_column_by_no(span.column_no)
            if column is None or (variables is not None and column.variable not in variables):
                continue
            bbox = strict_bboxes[span.column_no]
            image = page.image.crop(bbox)
            context = OCRRequestContext(
                pdf_sha256,
                bbox,
                row.row_index,
                panel.page_number,
                f"{panel.definition.panel_id}:{column.variable}",
                build_cell_free_ocr_prompt(schema, panel.definition, column),
            )
            result = await self.ocr_client.ocr_cell_async(image, context)
            text = self._cell_text(result)
            embedded = self._cell_text(
                OCRResult(
                    row.row_index,
                    panel.page_number,
                    self._embedded_hierarchy_cell_text(page, bbox),
                )
            )
            selected_source = "cell_free_ocr"
            if not text.strip() and embedded.strip():
                text = embedded
                selected_source = "embedded_text"
            audit.append(
                {
                    "record_type": "cell_fallback",
                    "variable": column.variable,
                    "embedded_candidate": embedded,
                    "selected_source": selected_source,
                    "selected_value": text,
                    **self.ocr_client.audit_record(result),
                }
            )
            values[column.variable] = text
        return values

    @staticmethod
    def _strict_cell_bboxes(
        page: RenderedPage,
        panel: PanelGeometry,
        row_bbox: tuple[int, int, int, int],
    ) -> dict[int, tuple[int, int, int, int]]:
        """Move midpoint boundaries into observed inter-cell whitespace gaps."""
        if not panel.columns:
            return {}
        y0, y1 = max(0, row_bbox[1]), min(page.height, row_bbox[3])
        words = [
            word
            for word in page.pdf_words
            if y0 <= (word["bbox"][1] + word["bbox"][3]) / 2 <= y1
        ]
        boundaries = [panel.columns[0].x_start]
        for left, right in zip(panel.columns, panel.columns[1:], strict=False):
            nominal = left.x_end
            left_words = [
                word
                for word in words
                if left.x_start
                <= (word["bbox"][0] + word["bbox"][2]) / 2
                <= nominal
            ]
            right_words = [
                word
                for word in words
                if nominal
                < (word["bbox"][0] + word["bbox"][2]) / 2
                <= right.x_end
            ]
            boundary = nominal
            if left_words and right_words:
                left_edge = max(int(word["bbox"][2]) for word in left_words)
                right_edge = min(int(word["bbox"][0]) for word in right_words)
                candidate = (left_edge + right_edge) // 2
                maximum_shift = max(
                    4,
                    round(min(left.x_end - left.x_start, right.x_end - right.x_start) * 0.3),
                )
                if left_edge < right_edge and abs(candidate - nominal) <= maximum_shift:
                    boundary = candidate
            boundaries.append(boundary)
        boundaries.append(panel.columns[-1].x_end)
        return {
            span.column_no: (
                max(0, boundaries[index]),
                y0,
                min(page.width, boundaries[index + 1]),
                y1,
            )
            for index, span in enumerate(panel.columns)
        }

    @staticmethod
    def _cross_boundary_variables(
        schema: TableSchema,
        panel: PanelGeometry,
        result: OCRResult,
        row_bbox: tuple[int, int, int, int],
    ) -> set[str]:
        """Find data columns touched by a multi-value token crossing a cell boundary."""
        identity_numbers = set(panel.definition.identity_columns)
        targets: set[str] = set()
        for token in result.tokens:
            if token.bbox is None or token.coordinate_system != "normalized_1000":
                continue
            numeric_parts = re.findall(r"\d[\d,]*(?:\.\d+)?|\.{2,}|[-–—]", token.text)
            malformed_join = bool(
                re.fullmatch(r"\d[\d,]*", token.text.strip())
                and "," in token.text
                and not re.fullmatch(r"(?:\d{1,3}(?:,\d{3})+|\d+)", token.text.strip())
            )
            if len(numeric_parts) < 2 and not malformed_join:
                continue
            absolute = ColumnAssigner.scale_bbox_1000(token.bbox, row_bbox)
            for left, right in zip(panel.columns, panel.columns[1:], strict=False):
                boundary = left.x_end
                if absolute[0] < boundary - 2 and absolute[2] > boundary + 2:
                    for span in (left, right):
                        column = schema.get_column_by_no(span.column_no)
                        if column is not None and span.column_no not in identity_numbers:
                            targets.add(column.variable)
        return targets

    @staticmethod
    def _recover_joined_numeric_cells(
        schema: TableSchema,
        panel: PanelGeometry,
        result: OCRResult,
        row_bbox: tuple[int, int, int, int],
    ) -> dict[str, str]:
        """Split two valid integers that OCR joined across one physical boundary."""
        recovered: dict[str, str] = {}
        identity_numbers = set(panel.definition.identity_columns)
        integer_pattern = re.compile(r"(?:\d+|\d{1,3}(?:,\d{3})+)")
        for token in result.tokens:
            if token.bbox is None or token.coordinate_system != "normalized_1000":
                continue
            text = token.text.strip()
            if not re.fullmatch(r"\d[\d,]*", text) or "," not in text:
                continue
            if integer_pattern.fullmatch(text):
                continue
            groups = text.split(",")
            partitions = [
                (",".join(groups[:index]), ",".join(groups[index:]))
                for index in range(1, len(groups))
                if integer_pattern.fullmatch(",".join(groups[:index]))
                and integer_pattern.fullmatch(",".join(groups[index:]))
            ]
            if len(partitions) != 1:
                continue
            absolute = ColumnAssigner.scale_bbox_1000(token.bbox, row_bbox)
            crossed_pairs = [
                (left, right)
                for left, right in zip(panel.columns, panel.columns[1:], strict=False)
                if absolute[0] < left.x_end - 2 and absolute[2] > left.x_end + 2
            ]
            if not crossed_pairs:
                continue
            token_centre = (absolute[0] + absolute[2]) / 2
            left, right = min(
                crossed_pairs, key=lambda pair: abs(pair[0].x_end - token_centre)
            )
            if abs(left.x_end - token_centre) > max(
                left.x_end - left.x_start, right.x_end - right.x_start
            ) * 0.5:
                continue
            left_column = schema.get_column_by_no(left.column_no)
            right_column = schema.get_column_by_no(right.column_no)
            if (
                left_column is None
                or right_column is None
                or left.column_no in identity_numbers
                or right.column_no in identity_numbers
                or left_column.data_type != "integer"
                or right_column.data_type != "integer"
            ):
                continue
            left_value, right_value = partitions[0]
            recovered[left_column.variable] = left_value
            recovered[right_column.variable] = right_value
        return recovered

    @staticmethod
    def _has_repeated_grounded_row(result: OCRResult, panel: PanelGeometry) -> bool:
        """Detect OCR that vertically tiles one thin printed row in its response."""
        if not result.has_usable_boxes or len(result.tokens) < len(panel.columns) * 2:
            return False
        occurrences: dict[tuple[str, int], int] = {}
        for token in result.tokens:
            assert token.bbox is not None
            text = " ".join(token.text.casefold().split())
            if not text:
                continue
            centre_x_bucket = round(((token.bbox[0] + token.bbox[2]) / 2) / 20)
            key = (text, centre_x_bucket)
            occurrences[key] = occurrences.get(key, 0) + 1
        repeated_positions = sum(count >= 3 for count in occurrences.values())
        return repeated_positions >= max(2, len(panel.columns) // 3)

    async def _retry_failing_cells(
        self,
        pages: list[RenderedPage],
        schema: TableSchema,
        panels: list[PanelGeometry],
        panel_rows: dict[str, list[RowCrop]],
        hierarchy_rows: dict[int, list[SubRowCrop]],
        raw_rows: list[dict[str, Any]],
        report: TableValidationReport,
        pdf_sha256: str,
        audit: list[dict[str, Any]],
    ) -> bool:
        targets = {
            (finding.row_index, finding.variable)
            for finding in report.findings
            if finding.row_index is not None
            and finding.variable
            and finding.code
            in {"type_parse", "identity_missing", "ocr_completeness", "serial_progression"}
        }
        if not targets:
            return False
        changed = False
        for row_index, variable in targets:
            if row_index >= len(raw_rows):
                continue
            column = schema.get_column_by_var(variable)
            if column is None:
                continue
            located = next(
                (
                    panel
                    for panel in panels
                    if any(span.column_no == column.column_no for span in panel.columns)
                ),
                None,
            )
            parent_index = int(raw_rows[row_index].get("__parent_row_index", row_index))
            subrow_index = int(raw_rows[row_index].get("__subrow_index", 0))
            child_scoped = bool(
                schema.hierarchy is not None
                and variable in set(schema.hierarchy.child_variables)
            )
            if located is None or parent_index >= len(panel_rows[located.definition.panel_id]):
                continue
            span = next(span for span in located.columns if span.column_no == column.column_no)
            page = pages[located.page_number - 1]
            if child_scoped:
                candidates = hierarchy_rows.get(parent_index, [])
                if subrow_index >= len(candidates):
                    continue
                row_bbox = candidates[subrow_index].bbox
            else:
                row_bbox = panel_rows[located.definition.panel_id][parent_index].bbox
            bbox = self._strict_cell_bboxes(page, located, row_bbox)[span.column_no]
            context = OCRRequestContext(
                pdf_sha256,
                bbox,
                row_index,
                located.page_number,
                f"{located.definition.panel_id}:{variable}:validation",
                build_cell_free_ocr_prompt(schema, located.definition, column),
            )
            result = await self.ocr_client.ocr_cell_async(page.image.crop(bbox), context)
            text = self._cell_text(result)
            embedded = self._cell_text(
                OCRResult(
                    row_index,
                    located.page_number,
                    self._embedded_hierarchy_cell_text(page, bbox),
                )
            )
            selected_source = "cell_free_ocr"
            if not text.strip() and embedded.strip():
                text = embedded
                selected_source = "embedded_text"
            audit.append(
                {
                    "record_type": "validation_cell_retry",
                    "variable": variable,
                    "parent_row_index": parent_index,
                    "subrow_index": subrow_index if child_scoped else None,
                    "embedded_candidate": embedded,
                    "selected_source": selected_source,
                    "selected_value": text,
                    **self.ocr_client.audit_record(result),
                }
            )
            if text and not result.error:
                if (
                    schema.hierarchy is not None
                    and schema.hierarchy.repeat_parent_values
                    and not child_scoped
                ):
                    for candidate in raw_rows:
                        if int(candidate.get("__parent_row_index", -1)) == parent_index:
                            candidate[variable] = text
                else:
                    raw_rows[row_index][variable] = text
                changed = True
        return changed

    @staticmethod
    def _apply_anchor_identity(
        schema: TableSchema,
        panel: PanelGeometry,
        row_bbox: tuple[int, int, int, int],
        result: OCRResult,
        assigned: dict[str, str],
    ) -> dict[str, str]:
        """Recover left-aligned identity text and spanning cross-references."""
        identity_numbers = panel.definition.identity_columns
        if len(identity_numbers) < 2 or not result.has_usable_boxes:
            return assigned
        serial_column = schema.get_column_by_no(identity_numbers[0])
        name_column = schema.get_column_by_no(identity_numbers[1])
        data_spans = [span for span in panel.columns if span.column_no not in set(identity_numbers)]
        if serial_column is None or name_column is None or not data_spans:
            return assigned

        positioned: list[tuple[float, str]] = []
        for token in result.tokens:
            if token.bbox is None:
                continue
            absolute = ColumnAssigner.scale_bbox_1000(token.bbox, row_bbox)
            positioned.append(((absolute[0] + absolute[2]) / 2, token.text.strip()))
        positioned.sort(key=lambda item: item[0])
        if not positioned:
            return assigned

        first_data_x = min(span.x_start for span in data_spans)
        identity_texts = [text for center, text in positioned if center < first_data_x and text]
        serial_pattern = re.compile(r"(?:\d+|\(?[ivxlcdm]+\)?[.)]?)", re.IGNORECASE)
        serial = (
            identity_texts[0]
            if identity_texts and serial_pattern.fullmatch(identity_texts[0])
            else ""
        )
        name_start = 1 if serial else 0
        name_parts = identity_texts[name_start:]
        all_parts = [text for _, text in positioned if text]
        reference_index = next(
            (
                index
                for index, text in enumerate(all_parts)
                if re.fullmatch(r"se[ec]", text, re.IGNORECASE)
            ),
            None,
        )
        if reference_index is not None:
            name_parts = all_parts[name_start:]
            for column in schema.columns_for_panel(panel.definition):
                if column.column_no not in identity_numbers:
                    assigned[column.variable] = ""

        assigned[serial_column.variable] = serial
        assigned[name_column.variable] = " ".join(name_parts).strip()
        return assigned

    @classmethod
    def _apply_embedded_anchor_identity(
        cls,
        page: RenderedPage,
        schema: TableSchema,
        panel: PanelGeometry,
        row_bbox: tuple[int, int, int, int],
        assigned: dict[str, str],
    ) -> dict[str, str]:
        """Prefer embedded identity cells while retaining spanning references."""
        identity_numbers = panel.definition.identity_columns
        if len(identity_numbers) < 2:
            return assigned
        serial_column = schema.get_column_by_no(identity_numbers[0])
        name_column = schema.get_column_by_no(identity_numbers[1])
        spans = {span.column_no: span for span in panel.columns}
        if (
            serial_column is None
            or name_column is None
            or serial_column.column_no not in spans
            or name_column.column_no not in spans
        ):
            return assigned
        serial_span = spans[serial_column.column_no]
        serial_text = cls._embedded_hierarchy_cell_text(
            page,
            (serial_span.x_start, row_bbox[1], serial_span.x_end, row_bbox[3]),
        )
        serial_value = serial_text.strip()
        if not re.fullmatch(
            r"(?:\d+|\(?[ivxlcdm]+\)?[.)]?)", serial_value, re.IGNORECASE
        ):
            embedded_candidates = re.findall(
                r"\([ivxlcdm]+\)|\b\d+\b", serial_value, re.IGNORECASE
            )
            serial_value = embedded_candidates[0] if len(embedded_candidates) == 1 else ""
        current_serial = str(assigned.get(serial_column.variable, "")).strip()
        current_is_valid = bool(
            re.fullmatch(
                r"(?:\d+|\(?[ivxlcdm]+\)?[.)]?)", current_serial, re.IGNORECASE
            )
        )
        embedded_is_component = bool(
            re.fullmatch(r"\([ivxlcdm]+\)", serial_value, re.IGNORECASE)
        )
        if serial_value and (embedded_is_component or not current_is_valid):
            assigned[serial_column.variable] = serial_value
        if cls._is_cross_reference(assigned, schema):
            return assigned
        name_span = spans[name_column.column_no]
        name_text = cls._embedded_hierarchy_cell_text(
            page,
            (name_span.x_start, row_bbox[1], name_span.x_end, row_bbox[3]),
        )
        if name_text.strip():
            assigned[name_column.variable] = name_text.strip()
        return assigned

    @staticmethod
    def _is_cross_reference(row: dict[str, Any], schema: TableSchema) -> bool:
        identity_var = "town_name" if schema.get_column_by_var("town_name") else "tahsil_name"
        return bool(re.search(r"\bse[ec]\b", row.get(identity_var, ""), re.IGNORECASE))

    @classmethod
    def _cell_text(cls, result: OCRResult) -> str:
        if result.error:
            return ""
        text = cls._plain_text(result.raw_text)
        lowered = text.casefold()
        leakage_markers = (
            "<table>",
            "does not contain any data",
            "expected-value examples",
            "expected value",
            "field | expected",
            "formulas, or tables",
            "no. of villages",
            "number of villages",
            "villages having",
            "pucca road",
            "kachcha road",
            "post office",
            "telegraph office",
            "post and telegraph",
            "post & telegraph",
            "power supply",
            "drinking water",
            "possible printed forms",
            "return only the visible cell text",
            "title slide",
            "title page",
            "cover page",
            "panel:",
            "this is an archival 1971",
            "ambiguous_ocr",
            "ambiguous historic",
            "parse_error",
            "review_flag",
            "expected integer",
            "validation finding",
        )
        explanatory = re.match(
            r"^(?:the|this)\s+(?:image|cell|value)\b|^i\s+(?:can(?:not|'t)|see)\b",
            lowered,
        )
        if len(text) > 250 or explanatory or any(marker in lowered for marker in leakage_markers):
            result.parse_issues.append("Rejected probable schema/prompt leakage from cell OCR")
            return ""
        return text

    def _validate(
        self,
        schema: TableSchema,
        metadata: DocumentMetadata,
        rows: list[NormalizedRow],
        panels: list[PanelGeometry],
        panel_rows: dict[str, list[RowCrop]],
        results: list[OCRResult],
    ) -> TableValidationReport:
        return self.validator.validate(
            metadata.pdf_id,
            schema,
            rows,
            panels_complete=len(panels) == len(schema.panels),
            aligned_row_counts={key: len(value) for key, value in panel_rows.items()},
            panel_scores=[self._panel_quality(panel) for panel in panels],
            ocr_row_successes=sum(
                not result.error and (result.has_usable_boxes or bool(result.raw_text.strip()))
                for result in results
            ),
            ocr_row_total=len(results),
            parent_row_count=len(panel_rows[schema.row_anchor_panel.panel_id]),
            alignment_confidences={
                panel_id: min(
                    (row.alignment_confidence for row in rows), default=0.0
                )
                for panel_id, rows in panel_rows.items()
            },
        )

    def _panel_quality(self, panel: PanelGeometry) -> float:
        """Accepted, monotonic sequences are complete geometry with a small confidence margin."""
        minimum = self.panel_detector.min_sequence_score
        normalized = max(0.0, min(1.0, (panel.sequence_score - minimum) / (1 - minimum)))
        return round(0.95 + normalized * 0.05, 4)

    @staticmethod
    def _plain_text(content: str) -> str:
        text = re.sub(r"<\|/?(?:ref|det)\|>", " ", content)
        text = re.sub(r"\[\[[^]]*\]\]", " ", text)
        return " ".join(text.split()).strip()

    @staticmethod
    def _boundary(panel: PanelGeometry) -> TableBoundary:
        return TableBoundary(
            panel.page_number,
            panel.table_bbox,
            panel.header_bbox,
            panel.body_bbox,
            None,
            False,
            panel.definition.panel_id,
        )

    @staticmethod
    def _geometry_payload(
        metadata: DocumentMetadata,
        schema: TableSchema,
        pages: list[RenderedPage],
        panels: list[PanelGeometry],
        panel_rows: dict[str, list[RowCrop]],
        hierarchy_rows: dict[int, list[SubRowCrop]],
        pdf_sha256: str,
        notes: list[DetectedNote] | None = None,
    ) -> dict[str, Any]:
        parent_row_count = len(panel_rows[schema.row_anchor_panel.panel_id])
        expanded_row_count = (
            sum(len(rows) for rows in hierarchy_rows.values())
            if schema.hierarchy is not None
            else parent_row_count
        )
        panel_payloads: list[dict[str, Any]] = []
        for panel in panels:
            payload: dict[str, Any] = {
                "panel_id": panel.definition.panel_id,
                "page": panel.page_number,
                "printed_columns": panel.definition.printed_columns,
                "matched_numbers": panel.matched_numbers,
                "sequence_score": panel.sequence_score,
                "source": panel.discovery_source,
                "body_end_source": panel.body_end_source,
                "table_bbox": panel.table_bbox,
                "header_bbox": panel.header_bbox,
                "body_bbox": panel.body_bbox,
                "row_count": len(panel_rows[panel.definition.panel_id]),
                "rows": [
                    {
                        "row_index": row.row_index,
                        "bbox": row.bbox,
                        "source": row.source,
                        "alignment_confidence": row.alignment_confidence,
                        "interpolated": row.interpolated,
                    }
                    for row in panel_rows[panel.definition.panel_id]
                ],
                "row_bboxes": [row.bbox for row in panel_rows[panel.definition.panel_id]],
                "column_centers": {
                    span.column_no: (span.x_start + span.x_end) / 2
                    for span in panel.columns
                },
            }
            if panel.definition.row_anchor and schema.hierarchy is not None:
                payload["hierarchy"] = {
                    "anchor_variable": schema.hierarchy.anchor_variable,
                    "child_variables": schema.hierarchy.child_variables,
                    "repeat_parent_values": schema.hierarchy.repeat_parent_values,
                    "parents": [
                        {
                            "parent_row_index": parent_index,
                            "subrow_count": len(subrows),
                            "subrows": [
                                {
                                    "subrow_index": subrow.subrow_index,
                                    "bbox": subrow.bbox,
                                    "source": subrow.source,
                                }
                                for subrow in subrows
                            ],
                        }
                        for parent_index, subrows in sorted(hierarchy_rows.items())
                    ],
                }
            panel_payloads.append(payload)
        return {
            "pdf_id": metadata.pdf_id,
            "source_pdf": metadata.file_name,
            "source_pdf_sha256": pdf_sha256,
            "format_id": schema.format_id,
            "page_count": len(pages),
            "parent_row_count": parent_row_count,
            "expanded_row_count": expanded_row_count,
            "notes": [asdict(note) for note in notes or []],
            "panels": panel_payloads,
            "provenance": metadata.provenance_dict(),
        }

    def _save_visualizations(
        self,
        metadata: DocumentMetadata,
        pages: list[RenderedPage],
        panels: list[PanelGeometry],
        panel_rows: dict[str, list[RowCrop]],
        hierarchy_rows: dict[int, list[SubRowCrop]],
        notes: list[DetectedNote] | None = None,
    ) -> None:
        target = self.layout.viz / metadata.pdf_id
        for panel in panels:
            self.visualizer.draw_page_segmentation(
                pages[panel.page_number - 1],
                self._boundary(panel),
                panel_rows[panel.definition.panel_id],
                panel.columns,
                target / f"{panel.definition.panel_id}.png",
                (
                    [subrow for rows in hierarchy_rows.values() for subrow in rows]
                    if panel.definition.row_anchor
                    else None
                ),
                [
                    note
                    for note in notes or []
                    if note.page_number == panel.page_number
                    and note.panel_id == panel.definition.panel_id
                ],
            )

    async def _record_summary(self, summary: ExtractionSummary) -> None:
        async with self._manifest_lock:
            self._manifest["results"][summary.pdf_id] = summary.manifest_record()
            self._manifest["updated_at"] = datetime.now(UTC).isoformat()
            counts = {status: 0 for status in RUN_STATUSES}
            for record in self._manifest["results"].values():
                counts[record["status"]] += 1
            self._manifest["status_counts"] = counts
            self.exporter.write_manifest(self.layout.manifest, self._manifest)

    def process_pdf(self, pdf_path: Path, **kwargs: Any) -> ExtractionSummary:
        return asyncio.run(self.process_pdf_async(pdf_path, **kwargs))

    async def process_batch_async(
        self,
        pdf_paths: list[Path],
        save_viz: bool = True,
        is_dry_run: bool = False,
        concurrency: int = 2,
    ) -> list[ExtractionSummary]:
        semaphore = asyncio.Semaphore(max(1, concurrency))

        async def worker(path: Path) -> ExtractionSummary:
            async with semaphore:
                return await self.process_pdf_async(path, save_viz=save_viz, is_dry_run=is_dry_run)

        try:
            return list(await asyncio.gather(*(worker(Path(path)) for path in pdf_paths)))
        finally:
            await self.ocr_client.aclose()
