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

from census_extractor.config import PipelineConfig, default_config
from census_extractor.geometry.aligner import ContinuationAligner
from census_extractor.geometry.panel_detector import (
    PanelDetector,
    PanelDiscoveryError,
    PanelGeometry,
)
from census_extractor.geometry.row_segmenter import RowCrop, RowSegmenter
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
    build_page_grounding_prompt,
    build_row_grounding_prompt,
)
from census_extractor.pipeline.exporter import RunLayout, TableExporter
from census_extractor.preprocessing.boundary_detector import TableBoundary
from census_extractor.preprocessing.pdf_loader import PDFLoader, RenderedPage
from census_extractor.schemas import SchemaRegistry, TableSchema
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
    valid_rows: int
    quality_score: float
    quality_components: dict[str, float] = field(default_factory=dict)
    exported_files: dict[str, Path] = field(default_factory=dict)
    cache_metrics: dict[str, int] = field(default_factory=dict)
    actionable_failures: list[str] = field(default_factory=list)
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
            panel_rows = self._segment_and_align_rows(pages, schema, panels)
            anchor_count = len(panel_rows[schema.row_anchor_panel.panel_id])
            if anchor_count == 0:
                raise PanelDiscoveryError("Anchor panel contains zero usable data rows")
            geometry_payload = self._geometry_payload(
                metadata, schema, pages, panels, panel_rows, pdf_sha256
            )
            geometry_path = self.exporter.write_geometry(metadata.pdf_id, geometry_payload)
            if save_viz:
                self._save_visualizations(metadata, pages, panels, panel_rows)
            if is_dry_run:
                summary = ExtractionSummary(
                    run_id=self.run_id,
                    pdf_name=metadata.file_name,
                    pdf_id=metadata.pdf_id,
                    district=metadata.district,
                    format_id=metadata.format_id,
                    status="DRY_RUN",
                    total_rows=anchor_count,
                    valid_rows=0,
                    quality_score=min(self._panel_quality(panel) for panel in panels),
                    quality_components={
                        "geometry": min(self._panel_quality(panel) for panel in panels)
                    },
                    exported_files={"geometry": geometry_path},
                    cache_metrics={"hits": 0, "misses": 0},
                )
                await self._record_summary(summary)
                return summary

            raw_rows, panel_results = await self._extract_all_panels(
                pages, schema, panels, panel_rows, pdf_sha256, audit_records
            )
            normalized = normalize_rows(raw_rows, schema)
            report = self._validate(schema, metadata, normalized, panels, panel_rows, panel_results)
            if enable_retry and not report.is_valid:
                changed = await self._retry_failing_cells(
                    pages, schema, panels, panel_rows, raw_rows, report, pdf_sha256, audit_records
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
        self, pages: list[RenderedPage], schema: TableSchema, panels: list[PanelGeometry]
    ) -> dict[str, list[RowCrop]]:
        by_id = {panel.definition.panel_id: panel for panel in panels}
        anchor_geometry = by_id[schema.row_anchor_panel.panel_id]
        anchor_page = pages[anchor_geometry.page_number - 1]
        anchor_rows = self.row_segmenter.segment_rows(anchor_page, self._boundary(anchor_geometry))
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
        result = {schema.row_anchor_panel.panel_id: anchor_rows}
        for definition in schema.panels:
            if definition.row_anchor:
                continue
            geometry = by_id[definition.panel_id]
            page = pages[geometry.page_number - 1]
            candidates = self.row_segmenter.segment_rows(page, self._boundary(geometry))
            pairs = self.aligner.align_rows(anchor_rows, candidates)
            aligned = [pair.continuation_row for pair in pairs if pair.continuation_row is not None]
            if len(aligned) != len(anchor_rows):
                aligned = self.row_segmenter.project_rows(
                    page, anchor_rows, anchor_geometry.body_bbox, geometry.body_bbox
                )
            for index, row in enumerate(aligned):
                row.row_index = index
            result[definition.panel_id] = aligned
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
    ) -> tuple[list[dict[str, str]], list[OCRResult]]:
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
            if panel.definition.row_anchor:
                assigned = self._apply_anchor_identity(schema, panel, ocr_bbox, result, assigned)
            elif self._is_cross_reference(raw_rows[row.row_index], schema):
                continue
            if not result.has_usable_boxes:
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
    ) -> dict[str, str]:
        values: dict[str, str] = {}
        for span in panel.columns:
            column = schema.get_column_by_no(span.column_no)
            if column is None:
                continue
            bbox = (
                max(0, span.x_start - 4),
                max(0, row.bbox[1] - 4),
                min(page.width, span.x_end + 4),
                min(page.height, row.bbox[3] + 4),
            )
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
            audit.append(
                {
                    "record_type": "cell_fallback",
                    "variable": column.variable,
                    **self.ocr_client.audit_record(result),
                }
            )
            values[column.variable] = text
        return values

    async def _retry_failing_cells(
        self,
        pages: list[RenderedPage],
        schema: TableSchema,
        panels: list[PanelGeometry],
        panel_rows: dict[str, list[RowCrop]],
        raw_rows: list[dict[str, str]],
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
            if located is None or row_index >= len(panel_rows[located.definition.panel_id]):
                continue
            span = next(span for span in located.columns if span.column_no == column.column_no)
            row = panel_rows[located.definition.panel_id][row_index]
            page = pages[located.page_number - 1]
            bbox = (
                max(0, span.x_start - 4),
                max(0, row.bbox[1] - 4),
                min(page.width, span.x_end + 4),
                min(page.height, row.bbox[3] + 4),
            )
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
            audit.append(
                {
                    "record_type": "validation_cell_retry",
                    "variable": variable,
                    **self.ocr_client.audit_record(result),
                }
            )
            if text and not result.error:
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

    @staticmethod
    def _is_cross_reference(row: dict[str, str], schema: TableSchema) -> bool:
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
            "expected-value examples",
            "possible printed forms",
            "return only the visible cell text",
            "this is an archival 1971",
        )
        if len(text) > 250 or any(marker in lowered for marker in leakage_markers):
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
        pdf_sha256: str,
    ) -> dict[str, Any]:
        return {
            "pdf_id": metadata.pdf_id,
            "source_pdf": metadata.file_name,
            "source_pdf_sha256": pdf_sha256,
            "format_id": schema.format_id,
            "page_count": len(pages),
            "panels": [
                {
                    "panel_id": panel.definition.panel_id,
                    "page": panel.page_number,
                    "printed_columns": panel.definition.printed_columns,
                    "matched_numbers": panel.matched_numbers,
                    "sequence_score": panel.sequence_score,
                    "source": panel.discovery_source,
                    "table_bbox": panel.table_bbox,
                    "header_bbox": panel.header_bbox,
                    "body_bbox": panel.body_bbox,
                    "row_count": len(panel_rows[panel.definition.panel_id]),
                    "row_bboxes": [row.bbox for row in panel_rows[panel.definition.panel_id]],
                    "column_centers": {
                        span.column_no: (span.x_start + span.x_end) / 2 for span in panel.columns
                    },
                }
                for panel in panels
            ],
            "provenance": metadata.provenance_dict(),
        }

    def _save_visualizations(
        self,
        metadata: DocumentMetadata,
        pages: list[RenderedPage],
        panels: list[PanelGeometry],
        panel_rows: dict[str, list[RowCrop]],
    ) -> None:
        target = self.layout.viz / metadata.pdf_id
        for panel in panels:
            self.visualizer.draw_page_segmentation(
                pages[panel.page_number - 1],
                self._boundary(panel),
                panel_rows[panel.definition.panel_id],
                panel.columns,
                target / f"{panel.definition.panel_id}.png",
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
