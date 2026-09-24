"""Conservative, resumable strict-cell OCR decisions for automatic workflows."""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml
from pydantic import BaseModel, Field, model_validator

from census_extractor.config import PipelineConfig
from census_extractor.geometry.column_detector import ColumnSpan
from census_extractor.metadata import DocumentMetadata
from census_extractor.normalization import review_flag, type_value
from census_extractor.ocr.client import NovitaDeepSeekOCRClient, OCRRequestContext, OCRResult
from census_extractor.ocr.column_assigner import ColumnAssigner
from census_extractor.ocr.prompts import (
    build_autocorrect_field_prompt,
    build_autocorrect_minimal_prompt,
    build_row_grounding_prompt,
)
from census_extractor.pipeline.runner import PipelineRunner
from census_extractor.preprocessing.pdf_loader import PDFLoader, RenderedPage
from census_extractor.schemas import ColumnDefinition, SchemaRegistry, TableSchema

AUTOMATIC_LEDGER_VERSION = 2
AUTO_UNRESOLVED_FLAG = "AUTOCORRECTION_UNRESOLVED"

_CONTAMINATION = re.compile(
    r"(?:"
    r"this (?:image|cell|value)|does not contain|expected[- ]?value|expected integer|"
    r"possible printed forms|return only|field\s*:|number of [a-z ]+\s*:|"
    r"validation finding|review[_ ]flag|parse[_ ]error|ambiguous_ocr|"
    r"\bBANKING\b|\bTRADE\b|\bIMPORT(?:ED|S)?\b|\bEXPORT(?:ED|S)?\b|"
    r"<smiles>|<table>|[\u0600-\u06ff\u0900-\u097f\u0e00-\u0e7f\u3400-\u9fff]"
    r")",
    re.IGNORECASE,
)
_SERIAL = re.compile(r"(?:\d+|\(?[ivxlcdm]+\)?[.)]?)", re.IGNORECASE)
_PLACEHOLDER = re.compile(r"(?:nil|n\.?a\.?|[-–—.·…]+)", re.IGNORECASE)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value)


class AutoSelector(BaseModel):
    row_index: int | None = Field(default=None, ge=0)
    parent_row_index: int | None = Field(default=None, ge=0)
    subrow_index: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_selector(self) -> "AutoSelector":
        if (self.row_index is None) == (self.parent_row_index is None):
            raise ValueError("selector requires a flat row or a hierarchy parent")
        if self.subrow_index is not None and self.parent_row_index is None:
            raise ValueError("subrow_index requires parent_row_index")
        return self


class AutomaticCandidate(BaseModel):
    source: Literal[
        "original",
        "embedded_text",
        "row_panel",
        "strict_cell",
        "retry_1",
        "retry_2",
    ]
    value: str
    canonical: str
    valid: bool
    crop_scope: Literal[
        "coordinate_grounded",
        "embedded_text",
        "row_panel",
        "strict_cell",
    ] | None = None
    crop_sha256: str | None = Field(default=None, pattern=r"^[0-9A-F]{64}$")
    prompt_sha256: str | None = Field(default=None, pattern=r"^[0-9A-F]{64}$")
    cache_hit: bool = False
    cache_key: str | None = None
    response_sha256: str | None = None
    error: str | None = None
    rejection_reason: str | None = None


class AutomaticCellDecision(BaseModel):
    selector: AutoSelector
    scope: Literal["row", "parent"]
    variable: str
    original: str
    selected: str
    status: Literal["AUTO_CORRECTED", "AUTO_CONFIRMED", "UNRESOLVED"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str]
    source_page: int = Field(ge=1)
    panel_id: str
    bbox: tuple[int, int, int, int]
    crop_sha256: str = Field(pattern=r"^[0-9A-F]{64}$")
    candidates: list[AutomaticCandidate]

    @model_validator(mode="after")
    def validate_decision(self) -> "AutomaticCellDecision":
        if self.status == "AUTO_CORRECTED" and self.selected == self.original:
            raise ValueError("AUTO_CORRECTED must change the value")
        if self.status != "AUTO_CORRECTED" and self.selected != self.original:
            raise ValueError("only AUTO_CORRECTED may change the value")
        if self.status != "UNRESOLVED":
            groups: dict[str, list[AutomaticCandidate]] = {}
            for candidate in self.candidates:
                if candidate.valid:
                    groups.setdefault(candidate.canonical, []).append(candidate)
            uses_full_cell_strategy = any(
                candidate.source in {"row_panel", "strict_cell"}
                for candidate in self.candidates
            )
            if uses_full_cell_strategy:
                agreed = [
                    group
                    for group in groups.values()
                    if len(
                        {
                            candidate.crop_scope
                            for candidate in group
                            if candidate.crop_scope
                            in {"coordinate_grounded", "row_panel", "strict_cell"}
                        }
                    )
                    >= 2
                    and self.selected in {candidate.value for candidate in group}
                ]
            else:
                agreed = [
                    group
                    for group in groups.values()
                    if len({candidate.source for candidate in group}) >= 2
                    and any(candidate.source.startswith("retry_") for candidate in group)
                    and self.selected in {candidate.value for candidate in group}
                ]
            if len(agreed) != 1:
                raise ValueError("automatic selection requires one two-reading consensus")
        return self


class AutomaticTableDecision(BaseModel):
    pdf_id: str
    format_id: str
    source_csv_sha256: str = Field(pattern=r"^[0-9A-F]{64}$")
    geometry_sha256: str = Field(pattern=r"^[0-9A-F]{64}$")
    source_pdf_sha256: str = Field(pattern=r"^[0-9A-F]{64}$")
    expected_rows: int = Field(ge=1)
    expected_parent_rows: int = Field(ge=1)
    suspicious_cells: int = Field(ge=0)
    unique_cells: int | None = Field(default=None, ge=0)
    decisions: list[AutomaticCellDecision]

    @model_validator(mode="after")
    def validate_count(self) -> "AutomaticTableDecision":
        expected = self.unique_cells if self.unique_cells is not None else self.suspicious_cells
        if len(self.decisions) != expected:
            raise ValueError("automatic decision count does not match source-cell coverage")
        return self


class AutomaticDecisionLedger(BaseModel):
    version: Literal[1, 2] = AUTOMATIC_LEDGER_VERSION
    mode: Literal["automatic"] = "automatic"
    verification_strategy: Literal["suspicious_cells", "full_cell_consensus"] = (
        "full_cell_consensus"
    )
    source_run_id: str
    source_manifest_sha256: str = Field(pattern=r"^[0-9A-F]{64}$")
    max_cell_retries: int = Field(ge=1, le=2)
    uncertain_policy: Literal["keep_value_and_flag"] = "keep_value_and_flag"
    tables: dict[str, AutomaticTableDecision]

    @classmethod
    def load(cls, path: Path) -> "AutomaticDecisionLedger":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.model_validate(yaml.safe_load(handle))


@dataclass(frozen=True, slots=True)
class SuspiciousCell:
    selector: AutoSelector
    scope: Literal["row", "parent"]
    variable: str
    original: str
    reasons: tuple[str, ...]
    frame_indices: tuple[int, ...]

    @property
    def key(self) -> tuple[str, int, int | None, str]:
        if self.selector.row_index is not None:
            return ("row", self.selector.row_index, None, self.variable)
        assert self.selector.parent_row_index is not None
        return (
            self.scope,
            self.selector.parent_row_index,
            self.selector.subrow_index,
            self.variable,
        )


@dataclass(frozen=True, slots=True)
class AutomaticCorrectionResult:
    ledger_path: Path
    included_pdf_ids: list[str]
    exclusions: list[dict[str, str]]
    corrected_cells: int
    confirmed_cells: int
    unresolved_cells: int
    cache_hits: int
    cache_misses: int


def _cell_contamination(value: str) -> str | None:
    collapsed = " ".join(value.split())
    if len(collapsed) > 250:
        return "excessively long OCR text"
    if _CONTAMINATION.search(collapsed):
        return "probable prompt, metadata, foreign-script, or section contamination"
    words = re.findall(r"\b[\w.()/-]+\b", collapsed.casefold())
    if words and max((words.count(word) for word in set(words)), default=0) >= 5:
        return "repeated spill text"
    return None


def _candidate_valid(value: str, column: ColumnDefinition) -> tuple[bool, str | None]:
    contamination = _cell_contamination(value)
    if contamination:
        return False, contamination
    _, parse_error = type_value(value, column)
    if parse_error:
        return False, parse_error
    flag = review_flag(value, column, parse_error)
    if flag:
        return False, flag
    if column.variable in {"town_name", "tahsil_name"} and not value.strip():
        return False, "blank identity"
    if column.variable == "sl_no" and value.strip() and not _SERIAL.fullmatch(value.strip()):
        return False, "invalid serial"
    return True, None


def canonical_value(value: str, column: ColumnDefinition) -> str:
    collapsed = " ".join(value.replace("\u00a0", " ").split()).strip()
    if not collapsed:
        return "<BLANK>"
    if _PLACEHOLDER.fullmatch(collapsed):
        if re.fullmatch(r"[.·…]+", collapsed):
            return "<ELLIPSIS>"
        if re.fullmatch(r"[-–—]+", collapsed):
            return "<DASH>"
        if collapsed.casefold() == "nil":
            return "<NIL>"
        return "<NOT_AVAILABLE>"
    if column.data_type.casefold() in {"integer", "float"}:
        return collapsed.replace(",", "").replace(" ", "").replace("O", "0").replace(
            "o", "0"
        )
    return collapsed.casefold()


def _identity_similarity(identity: str, district: str) -> float:
    def clean(value: str) -> str:
        return re.sub(r"[^a-z]", "", value.casefold())

    left, right = clean(identity), clean(district)
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _unique_cells(frame: pd.DataFrame, schema: TableSchema) -> list[SuspiciousCell]:
    cells: list[SuspiciousCell] = []
    variables = schema.get_all_variables()
    if schema.hierarchy is None:
        for index, row in frame.iterrows():
            row_index = int(text(row["row_index"]))
            for variable in variables:
                cells.append(
                    SuspiciousCell(
                        AutoSelector(row_index=row_index),
                        "row",
                        variable,
                        text(row[variable]),
                        (),
                        (int(text(index)),),
                    )
                )
        return cells
    child_variables = set(schema.hierarchy.child_variables)
    for parent_value, group in frame.groupby("parent_row_index", sort=True):
        parent_index = int(text(parent_value))
        ordered = group.sort_values("subrow_index", key=lambda values: values.astype(int))
        first_index = int(text(ordered.index[0]))
        for variable in variables:
            if variable in child_variables:
                for index, row in ordered.iterrows():
                    subrow_index = int(text(row["subrow_index"]))
                    cells.append(
                        SuspiciousCell(
                            AutoSelector(
                                parent_row_index=parent_index,
                                subrow_index=subrow_index,
                            ),
                            "row",
                            variable,
                            text(row[variable]),
                            (),
                            (int(text(index)),),
                        )
                    )
            else:
                cells.append(
                    SuspiciousCell(
                        AutoSelector(parent_row_index=parent_index),
                        "parent",
                        variable,
                        text(frame.at[first_index, variable]),
                        (),
                        tuple(int(text(index)) for index in ordered.index),
                    )
                )
    return cells


def enumerate_unique_cells(
    frame: pd.DataFrame, schema: TableSchema
) -> list[SuspiciousCell]:
    """Public stable enumeration used by ledger coverage and verification packets."""
    return _unique_cells(frame, schema)


def detect_suspicious_cells(
    frame: pd.DataFrame,
    schema: TableSchema,
    report: dict[str, Any],
    *,
    district: str = "",
) -> list[SuspiciousCell]:
    """Return each unique source cell that requires an automatic decision."""
    finding_reasons: dict[tuple[int, str], list[str]] = {}
    for finding in report.get("findings", []):
        variable = finding.get("variable")
        row_index = finding.get("row_index")
        if variable in schema.get_all_variables() and row_index is not None:
            finding_reasons.setdefault((int(row_index), str(variable)), []).append(
                str(finding.get("message") or finding.get("code") or "validation finding")
            )

    suspicious: list[SuspiciousCell] = []
    for cell in _unique_cells(frame, schema):
        reasons: list[str] = []
        flags = {
            text(frame.at[index, f"{cell.variable}_flag"]).strip()
            for index in cell.frame_indices
            if f"{cell.variable}_flag" in frame
        }
        reasons.extend(f"extraction flag: {flag}" for flag in sorted(flags) if flag)
        for index in cell.frame_indices:
            row_number = int(text(frame.at[index, "row_index"]))
            reasons.extend(finding_reasons.get((row_number, cell.variable), []))
        contamination = _cell_contamination(cell.original)
        if contamination:
            reasons.append(contamination)
        if cell.variable == "sl_no" and cell.original.strip() and not _SERIAL.fullmatch(
            cell.original.strip()
        ):
            reasons.append("invalid serial identity")
        if cell.variable in {"town_name", "tahsil_name"}:
            if not cell.original.strip():
                reasons.append("blank identity")
            elif district and 0.65 <= _identity_similarity(cell.original, district) < 1.0:
                reasons.append("identity resembles district name but differs")
        if reasons:
            suspicious.append(
                SuspiciousCell(
                    cell.selector,
                    cell.scope,
                    cell.variable,
                    cell.original,
                    tuple(dict.fromkeys(reasons)),
                    cell.frame_indices,
                )
            )
    return suspicious


class AutomaticTranscriptionCorrector:
    """Retry suspicious strict cells and record consensus or unresolved decisions."""

    def __init__(
        self,
        config: PipelineConfig,
        *,
        max_cell_retries: int = 2,
        ocr_client: NovitaDeepSeekOCRClient | None = None,
    ):
        if not 1 <= max_cell_retries <= 2:
            raise ValueError("max_cell_retries must be one or two")
        self.config = config
        self.max_cell_retries = max_cell_retries
        self.schemas = SchemaRegistry(config.schemas_dir)
        self.loader = PDFLoader(target_dpi=config.render_dpi, auto_deskew=config.auto_deskew)
        self.client = ocr_client or NovitaDeepSeekOCRClient(config)
        self._owns_client = ocr_client is None
        self._row_panel_cache: dict[
            tuple[str, int, str, tuple[int, int, int, int]],
            tuple[OCRResult, dict[str, str], str, str, str | None],
        ] = {}

    async def run_async(
        self,
        *,
        manifest_path: Path,
        documents: list[DocumentMetadata],
        decision_root: Path,
    ) -> AutomaticCorrectionResult:
        manifest_path = Path(manifest_path).resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        results = manifest.get("results", {})
        manifest_sha = sha256_file(manifest_path)
        decision_root.mkdir(parents=True, exist_ok=True)
        tables: dict[str, AutomaticTableDecision] = {}
        exclusions: list[dict[str, str]] = []
        corrected = confirmed = unresolved = 0
        try:
            for document in documents:
                record = results.get(document.pdf_id)
                try:
                    if record is None:
                        raise ValueError("missing extraction manifest record")
                    table = await self._process_table(
                        document,
                        record,
                        manifest_sha=manifest_sha,
                        decision_root=decision_root,
                    )
                except Exception as exc:
                    exclusions.append(
                        {
                            "pdf_id": document.pdf_id,
                            "stage": "automatic_correction",
                            "reason": str(exc),
                        }
                    )
                    continue
                tables[document.pdf_id] = table
                corrected += sum(item.status == "AUTO_CORRECTED" for item in table.decisions)
                confirmed += sum(item.status == "AUTO_CONFIRMED" for item in table.decisions)
                unresolved += sum(item.status == "UNRESOLVED" for item in table.decisions)
        finally:
            if self._owns_client:
                await self.client.aclose()

        ledger = AutomaticDecisionLedger(
            source_run_id=manifest_path.parent.name,
            source_manifest_sha256=manifest_sha,
            max_cell_retries=self.max_cell_retries,
            tables=tables,
        )
        ledger_path = decision_root.parent / "automatic_decisions.yaml"
        self._atomic_text(
            ledger_path,
            yaml.safe_dump(ledger.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        )
        return AutomaticCorrectionResult(
            ledger_path=ledger_path,
            included_pdf_ids=list(tables),
            exclusions=exclusions,
            corrected_cells=corrected,
            confirmed_cells=confirmed,
            unresolved_cells=unresolved,
            cache_hits=self.client.cache_hits,
            cache_misses=self.client.cache_misses,
        )

    async def _process_table(
        self,
        document: DocumentMetadata,
        record: dict[str, Any],
        *,
        manifest_sha: str,
        decision_root: Path,
    ) -> AutomaticTableDecision:
        exported = record.get("exported_files", {})
        csv_path = Path(exported.get("csv", ""))
        geometry_path = Path(exported.get("geometry", ""))
        report_path = Path(exported.get("report", ""))
        pdf_path = self.config.pdfs_dir / document.file_name
        for label, path in (
            ("CSV", csv_path),
            ("geometry", geometry_path),
            ("validation report", report_path),
            ("source PDF", pdf_path),
        ):
            if not path.is_file():
                raise FileNotFoundError(f"{label} not found: {path}")
        source_csv_sha = sha256_file(csv_path)
        geometry_sha = sha256_file(geometry_path)
        source_pdf_sha = sha256_file(pdf_path)
        decision_path = decision_root / f"{document.pdf_id}.json"
        if decision_path.is_file():
            existing = AutomaticTableDecision.model_validate_json(
                decision_path.read_text(encoding="utf-8")
            )
            if (
                existing.source_csv_sha256 == source_csv_sha
                and existing.geometry_sha256 == geometry_sha
                and existing.source_pdf_sha256 == source_pdf_sha
            ):
                return existing
            raise ValueError("stale per-PDF automatic decision checkpoint")

        frame = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        self._row_panel_cache.clear()
        schema = self.schemas.require(document.format_id)
        geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if str(geometry.get("source_pdf_sha256") or source_pdf_sha).upper() != source_pdf_sha:
            raise ValueError("source PDF hash differs from geometry lineage")
        suspicious = detect_suspicious_cells(
            frame,
            schema,
            report,
            district=document.district,
        )
        suspicious_by_key = {cell.key: cell for cell in suspicious}
        source_cells = _unique_cells(frame, schema)
        verification_cells = [
            SuspiciousCell(
                selector=cell.selector,
                scope=cell.scope,
                variable=cell.variable,
                original=cell.original,
                reasons=(
                    suspicious_by_key[cell.key].reasons
                    if cell.key in suspicious_by_key
                    else ("full-cell independent verification",)
                ),
                frame_indices=cell.frame_indices,
            )
            for cell in source_cells
        ]
        pages = self.loader.render_pdf(pdf_path) if verification_cells else []
        decisions = [
            await self._decide_cell(
                document,
                schema,
                geometry,
                pages,
                cell,
                source_pdf_sha,
            )
            for cell in verification_cells
        ]
        parent_count = (
            int(text(frame["parent_row_index"].nunique()))
            if schema.hierarchy is not None
            else len(frame)
        )
        table = AutomaticTableDecision(
            pdf_id=document.pdf_id,
            format_id=document.format_id,
            source_csv_sha256=source_csv_sha,
            geometry_sha256=geometry_sha,
            source_pdf_sha256=source_pdf_sha,
            expected_rows=len(frame),
            expected_parent_rows=parent_count,
            suspicious_cells=len(suspicious),
            unique_cells=len(verification_cells),
            decisions=decisions,
        )
        payload = table.model_dump_json(indent=2)
        self._atomic_text(decision_path, payload + "\n")
        lineage_path = decision_root.parent / "manifest_lineage.json"
        if not lineage_path.exists():
            self._atomic_text(
                lineage_path,
                json.dumps(
                    {"source_manifest_sha256": manifest_sha}, indent=2, sort_keys=True
                )
                + "\n",
            )
        return table

    async def _decide_cell(
        self,
        document: DocumentMetadata,
        schema: TableSchema,
        geometry: dict[str, Any],
        pages: list[RenderedPage],
        cell: SuspiciousCell,
        pdf_sha: str,
    ) -> AutomaticCellDecision:
        column = schema.get_column_by_var(cell.variable)
        if column is None:
            raise ValueError(f"unknown schema variable {cell.variable!r}")
        panel_definition = next(
            panel for panel in schema.panels if column.column_no in panel.printed_columns
        )
        panel = next(
            item for item in geometry["panels"] if item["panel_id"] == panel_definition.panel_id
        )
        bbox = self._cell_bbox(panel, schema, column, cell.selector)
        page_number = int(panel["page"])
        page = pages[page_number - 1]
        clipped = self._clip_bbox(bbox, page)
        crop = page.image.crop(clipped)
        crop_sha = hashlib.sha256(self.client.image_to_png(crop)).hexdigest().upper()
        visible_ink = self._has_visible_ink(crop)

        candidates = [
            self._candidate(
                "original",
                cell.original,
                column,
                crop_scope="coordinate_grounded",
            )
        ]
        embedded = self._embedded_text(page, clipped)
        if embedded is not None:
            candidates.append(
                self._candidate(
                    "embedded_text",
                    embedded,
                    column,
                    crop_scope="embedded_text",
                )
            )
        selected: str | None = None
        if hasattr(self.client, "ocr_row_async"):
            row_bbox = self._row_bbox(panel, schema, column, cell.selector)
            row_candidate = await self._row_panel_candidate(
                page,
                schema,
                panel_definition,
                panel,
                column,
                cell,
                pdf_sha,
                row_bbox,
            )
            candidates.append(row_candidate)
            selected = self._full_consensus(candidates)
            if selected is None:
                strict_prompts = [
                    build_autocorrect_field_prompt(column),
                    build_autocorrect_minimal_prompt(),
                ]
                for retry_index in range(self.max_cell_retries):
                    prompt = strict_prompts[retry_index]
                    context = OCRRequestContext(
                        pdf_sha256=pdf_sha,
                        crop_bbox=clipped,
                        row_index=self._selector_number(cell.selector),
                        page_number=page_number,
                        panel_id=(
                            f"{panel_definition.panel_id}:verify:strict:"
                            f"{retry_index + 1}:{cell.variable}"
                        ),
                        prompt=prompt,
                    )
                    result = await self._safe_cell_ocr(crop, context)
                    strict_candidate = self._ocr_candidate(
                        "strict_cell",
                        result,
                        column,
                        crop_scope="strict_cell",
                        crop_sha256=crop_sha,
                        prompt_sha256=self._text_sha256(prompt),
                    )
                    if (
                        not strict_candidate.value.strip()
                        and visible_ink
                        and strict_candidate.valid
                    ):
                        strict_candidate.valid = False
                        strict_candidate.rejection_reason = (
                            "blank reading conflicts with visible crop ink"
                        )
                    candidates.append(strict_candidate)
                    selected = self._full_consensus(candidates)
                    if selected is not None or strict_candidate.valid:
                        break
        else:
            # Compatibility for version-1 mocked clients and ledgers. Production v3
            # always uses row/panel plus strict-cell crop scopes above.
            prompts = [build_autocorrect_field_prompt(column), build_autocorrect_minimal_prompt()]
            for retry_index in range(self.max_cell_retries):
                if selected is not None:
                    break
                source = "retry_1" if retry_index == 0 else "retry_2"
                context = OCRRequestContext(
                    pdf_sha256=pdf_sha,
                    crop_bbox=clipped,
                    row_index=self._selector_number(cell.selector),
                    page_number=page_number,
                    panel_id=f"{panel_definition.panel_id}:autocorrect:{source}:{cell.variable}",
                    prompt=prompts[retry_index],
                )
                result = await self._safe_cell_ocr(crop, context)
                retry_candidate = self._ocr_candidate(source, result, column)
                if not retry_candidate.value.strip() and visible_ink and retry_candidate.valid:
                    retry_candidate.valid = False
                    retry_candidate.rejection_reason = (
                        "blank reading conflicts with visible crop ink"
                    )
                candidates.append(retry_candidate)
                selected = self._consensus(candidates)

        if selected is None:
            status: Literal["AUTO_CORRECTED", "AUTO_CONFIRMED", "UNRESOLVED"] = "UNRESOLVED"
            chosen = cell.original
            confidence = 0.0
        else:
            chosen = selected
            status = "AUTO_CONFIRMED" if chosen == cell.original else "AUTO_CORRECTED"
            confidence = 1.0
        return AutomaticCellDecision(
            selector=cell.selector,
            scope=cell.scope,
            variable=cell.variable,
            original=cell.original,
            selected=chosen,
            status=status,
            confidence=confidence,
            reasons=list(cell.reasons),
            source_page=page_number,
            panel_id=panel_definition.panel_id,
            bbox=clipped,
            crop_sha256=crop_sha,
            candidates=candidates,
        )

    async def _row_panel_candidate(
        self,
        page: RenderedPage,
        schema: TableSchema,
        panel_definition: Any,
        panel: dict[str, Any],
        column: ColumnDefinition,
        cell: SuspiciousCell,
        pdf_sha: str,
        row_bbox: tuple[int, int, int, int],
    ) -> AutomaticCandidate:
        clipped = self._clip_bbox(row_bbox, page)
        row_crop = page.image.crop(clipped)
        prompt = build_row_grounding_prompt(schema, panel_definition)
        cache_key = (pdf_sha, page.page_number, panel_definition.panel_id, clipped)
        cached = self._row_panel_cache.get(cache_key)
        if cached is None:
            try:
                result = await self.client.ocr_row_async(
                    row_crop,
                    row_index=self._selector_number(cell.selector),
                    page_number=page.page_number,
                    expected_columns=schema.columns_for_panel(panel_definition),
                    pdf_sha256=pdf_sha,
                    crop_bbox=clipped,
                    panel_id=f"{panel_definition.panel_id}:verify:row_panel",
                    prompt=prompt,
                )
            except Exception as exc:
                result = OCRResult(
                    row_index=self._selector_number(cell.selector),
                    page_number=page.page_number,
                    raw_text="",
                    prompt=prompt,
                    error=f"{type(exc).__name__}: {exc}",
                )
            assigned: dict[str, str] = {}
            error = result.error
            if error is None and result.has_usable_boxes:
                spans = []
                body_x0, _, body_x1, _ = panel["body_bbox"]
                table_width = max(1, int(body_x1) - int(body_x0))
                for expected in schema.columns_for_panel(panel_definition):
                    x0, x1 = self._column_span(panel, expected.column_no)
                    spans.append(
                        ColumnSpan(
                            column_no=expected.column_no,
                            column_name=expected.column_name,
                            variable=expected.variable,
                            x_start=x0,
                            x_end=x1,
                            relative_start=(x0 - int(body_x0)) / table_width,
                            relative_end=(x1 - int(body_x0)) / table_width,
                        )
                    )
                assigned = ColumnAssigner().assign_tokens_to_columns(result, spans, clipped)
            elif error is None:
                error = "row/panel OCR returned no usable grounded boxes"
            crop_sha = hashlib.sha256(
                self.client.image_to_png(row_crop)
            ).hexdigest().upper()
            prompt_sha = self._text_sha256(prompt)
            cached = (result, assigned, crop_sha, prompt_sha, error)
            self._row_panel_cache[cache_key] = cached
        result, assigned, crop_sha, prompt_sha, error = cached
        value = assigned.get(column.variable, "")
        return self._candidate(
            "row_panel",
            value,
            column,
            crop_scope="row_panel",
            crop_sha256=crop_sha,
            prompt_sha256=prompt_sha,
            cache_hit=result.cache_hit,
            cache_key=result.cache_key,
            response_sha256=result.response_hash,
            error=error,
        )

    async def _safe_cell_ocr(
        self, crop: Any, context: OCRRequestContext
    ) -> OCRResult:
        try:
            return await self.client.ocr_cell_async(crop, context)
        except Exception as exc:
            return OCRResult(
                row_index=context.row_index,
                page_number=context.page_number,
                raw_text="",
                prompt=context.prompt,
                error=f"{type(exc).__name__}: {exc}",
            )

    @classmethod
    def _row_bbox(
        cls,
        panel: dict[str, Any],
        schema: TableSchema,
        column: ColumnDefinition,
        selector: AutoSelector,
    ) -> tuple[int, int, int, int]:
        if schema.hierarchy is not None and column.variable in schema.hierarchy.child_variables:
            hierarchy = panel.get("hierarchy")
            if hierarchy is None:
                raise ValueError("hierarchy geometry is missing")
            parent = next(
                item
                for item in hierarchy["parents"]
                if int(item["parent_row_index"]) == selector.parent_row_index
            )
            row = next(
                item
                for item in parent["subrows"]
                if int(item["subrow_index"]) == selector.subrow_index
            )
        else:
            target = selector.row_index if selector.row_index is not None else selector.parent_row_index
            row = next(item for item in panel["rows"] if int(item["row_index"]) == target)
        body_x0, _, body_x1, _ = panel["body_bbox"]
        return int(body_x0), int(row["bbox"][1]), int(body_x1), int(row["bbox"][3])

    @staticmethod
    def _text_sha256(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()

    @staticmethod
    def _candidate(
        source: Literal[
            "original",
            "embedded_text",
            "row_panel",
            "strict_cell",
            "retry_1",
            "retry_2",
        ],
        value: str,
        column: ColumnDefinition,
        *,
        crop_scope: Literal[
            "coordinate_grounded",
            "embedded_text",
            "row_panel",
            "strict_cell",
        ]
        | None = None,
        crop_sha256: str | None = None,
        prompt_sha256: str | None = None,
        cache_hit: bool = False,
        cache_key: str | None = None,
        response_sha256: str | None = None,
        error: str | None = None,
    ) -> AutomaticCandidate:
        valid, reason = _candidate_valid(value, column)
        if error:
            valid, reason = False, error
        return AutomaticCandidate(
            source=source,
            value=value,
            canonical=canonical_value(value, column),
            valid=valid,
            crop_scope=crop_scope,
            crop_sha256=crop_sha256,
            prompt_sha256=prompt_sha256,
            cache_hit=cache_hit,
            cache_key=cache_key,
            response_sha256=response_sha256,
            error=error,
            rejection_reason=reason,
        )

    @classmethod
    def _ocr_candidate(
        cls,
        source: Literal["strict_cell", "retry_1", "retry_2"],
        result: OCRResult,
        column: ColumnDefinition,
        *,
        crop_scope: Literal["strict_cell"] | None = None,
        crop_sha256: str | None = None,
        prompt_sha256: str | None = None,
    ) -> AutomaticCandidate:
        value = PipelineRunner._cell_text(result)
        return cls._candidate(
            source,
            value,
            column,
            crop_scope=crop_scope,
            crop_sha256=crop_sha256,
            prompt_sha256=prompt_sha256,
            cache_hit=result.cache_hit,
            cache_key=result.cache_key,
            response_sha256=result.response_hash,
            error=result.error,
        )

    @staticmethod
    def _consensus(candidates: list[AutomaticCandidate]) -> str | None:
        groups: dict[str, list[AutomaticCandidate]] = {}
        for candidate in candidates:
            if candidate.valid:
                groups.setdefault(candidate.canonical, []).append(candidate)
        winners = [
            group
            for group in groups.values()
            if len({item.source for item in group}) >= 2
            and any(item.source.startswith("retry_") for item in group)
        ]
        if len(winners) != 1:
            return None
        preference = {"original": 0, "retry_1": 1, "retry_2": 2, "embedded_text": 3}
        winner = min(winners[0], key=lambda item: preference[item.source])
        return winner.value

    @staticmethod
    def _full_consensus(candidates: list[AutomaticCandidate]) -> str | None:
        """Require agreement across two genuinely different image/crop scopes."""
        groups: dict[str, list[AutomaticCandidate]] = {}
        for candidate in candidates:
            if candidate.valid:
                groups.setdefault(candidate.canonical, []).append(candidate)
        eligible_scopes = {"coordinate_grounded", "row_panel", "strict_cell"}
        winners = [
            group
            for group in groups.values()
            if len(
                {
                    item.crop_scope
                    for item in group
                    if item.crop_scope in eligible_scopes
                }
            )
            >= 2
        ]
        if len(winners) != 1:
            return None
        preference = {
            "original": 0,
            "row_panel": 1,
            "strict_cell": 2,
            "embedded_text": 3,
            "retry_1": 4,
            "retry_2": 5,
        }
        return min(winners[0], key=lambda item: preference[item.source]).value

    @staticmethod
    def _selector_number(selector: AutoSelector) -> int:
        if selector.row_index is not None:
            return selector.row_index
        assert selector.parent_row_index is not None
        return selector.parent_row_index * 1000 + (selector.subrow_index or 0)

    @staticmethod
    def _column_span(panel: dict[str, Any], column_no: int) -> tuple[int, int]:
        entry = panel.get("column_spans", {}).get(str(column_no))
        if entry:
            return int(entry["x_start"]), int(entry["x_end"])
        centers = {int(number): float(value) for number, value in panel["column_centers"].items()}
        ordered = sorted(centers)
        position = ordered.index(column_no)
        body_x0, _, body_x1, _ = panel["body_bbox"]
        x0 = int(body_x0) if position == 0 else round(
            (centers[ordered[position - 1]] + centers[column_no]) / 2
        )
        x1 = int(body_x1) if position == len(ordered) - 1 else round(
            (centers[column_no] + centers[ordered[position + 1]]) / 2
        )
        return x0, x1

    @classmethod
    def _cell_bbox(
        cls,
        panel: dict[str, Any],
        schema: TableSchema,
        column: ColumnDefinition,
        selector: AutoSelector,
    ) -> tuple[int, int, int, int]:
        x0, x1 = cls._column_span(panel, column.column_no)
        if schema.hierarchy is not None and column.variable in schema.hierarchy.child_variables:
            hierarchy = panel.get("hierarchy")
            if hierarchy is None:
                raise ValueError("hierarchy geometry is missing")
            parent = next(
                item
                for item in hierarchy["parents"]
                if int(item["parent_row_index"]) == selector.parent_row_index
            )
            subrow = next(
                item
                for item in parent["subrows"]
                if int(item["subrow_index"]) == selector.subrow_index
            )
            y0, y1 = int(subrow["bbox"][1]), int(subrow["bbox"][3])
        else:
            target = (
                selector.row_index
                if selector.row_index is not None
                else selector.parent_row_index
            )
            row = next(item for item in panel["rows"] if int(item["row_index"]) == target)
            y0, y1 = int(row["bbox"][1]), int(row["bbox"][3])
        # A tiny horizontal inset prevents anti-aliased glyphs from an adjacent column
        # from entering a retry while retaining the full printed cell content.
        inset = min(2, max(0, (x1 - x0 - 1) // 4))
        return x0 + inset, y0, x1 - inset, y1

    @staticmethod
    def _clip_bbox(
        bbox: tuple[int, int, int, int], page: RenderedPage
    ) -> tuple[int, int, int, int]:
        x0, y0, x1, y1 = bbox
        clipped = (
            max(0, min(page.width, x0)),
            max(0, min(page.height, y0)),
            max(0, min(page.width, x1)),
            max(0, min(page.height, y1)),
        )
        if clipped[2] <= clipped[0] or clipped[3] <= clipped[1]:
            raise ValueError("strict cell crop is empty")
        return clipped

    @staticmethod
    def _embedded_text(
        page: RenderedPage, bbox: tuple[int, int, int, int]
    ) -> str | None:
        x0, y0, x1, y1 = bbox
        words = []
        for word in page.pdf_words:
            wx0, wy0, wx1, wy1 = word["bbox"]
            cx, cy = (wx0 + wx1) / 2, (wy0 + wy1) / 2
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                words.append((int(wy0), int(wx0), str(word["text"])))
        if not words:
            return None
        words.sort(key=lambda item: (round(item[0] / 8), item[1]))
        return " ".join(item[2] for item in words).strip()

    @staticmethod
    def _has_visible_ink(image: Any) -> bool:
        """Reject an OCR blank when the strict crop visibly contains printed marks."""
        grayscale = image.convert("L")
        histogram = grayscale.histogram()
        dark_pixels = sum(histogram[:180])
        minimum = max(12, round(grayscale.width * grayscale.height * 0.0015))
        return dark_pixels >= minimum

    @staticmethod
    def _atomic_text(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{time.time_ns()}.tmp")
        temporary.write_text(content, encoding="utf-8", newline="\n")
        temporary.replace(path)
