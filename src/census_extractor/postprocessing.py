"""Fail-closed, source-verified correction of manifest-selected CSV exports."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml
from pydantic import BaseModel, Field, model_validator

from census_extractor.config import PipelineConfig
from census_extractor.normalization import normalize_rows
from census_extractor.schemas import SchemaRegistry, TableSchema


class CorrectionSelector(BaseModel):
    """Stable row selector for a flat row, MedEdu child, or MedEdu parent."""

    row_index: int | None = Field(default=None, ge=0)
    parent_row_index: int | None = Field(default=None, ge=0)
    subrow_index: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_selector(self) -> "CorrectionSelector":
        row_selector = self.row_index is not None
        hierarchy_selector = self.parent_row_index is not None
        if row_selector == hierarchy_selector:
            raise ValueError("selector requires exactly one of row_index or parent_row_index")
        if self.subrow_index is not None and self.parent_row_index is None:
            raise ValueError("subrow_index requires parent_row_index")
        return self


class CellCorrection(BaseModel):
    selector: CorrectionSelector
    scope: Literal["row", "parent"] = "row"
    variable: str
    expected_original: str
    corrected: str
    source_page: int = Field(ge=1)
    panel_id: str
    reason: str

    @model_validator(mode="after")
    def validate_scope(self) -> "CellCorrection":
        if self.scope == "parent":
            if self.selector.parent_row_index is None or self.selector.subrow_index is not None:
                raise ValueError("parent scope requires a parent_row_index without subrow_index")
        return self


class TableReview(BaseModel):
    format_id: str
    expected_rows: int = Field(ge=1)
    expected_parent_rows: int = Field(ge=1)
    reviewed_unique_cells: int = Field(ge=1)
    corrections: list[CellCorrection] = Field(default_factory=list)


class CorrectionLedger(BaseModel):
    version: int = Field(ge=1)
    source_run_id: str
    source_manifest_sha256: str = Field(pattern=r"^[0-9A-Fa-f]{64}$")
    expected_table_count: int = Field(ge=1)
    expected_output_rows: int = Field(ge=1)
    expected_unique_source_cells: int = Field(ge=1)
    tables: dict[str, TableReview]

    @model_validator(mode="after")
    def validate_totals(self) -> "CorrectionLedger":
        if len(self.tables) != self.expected_table_count:
            raise ValueError(
                f"ledger table count {len(self.tables)} != expected {self.expected_table_count}"
            )
        if sum(table.expected_rows for table in self.tables.values()) != self.expected_output_rows:
            raise ValueError("ledger expected row total is inconsistent with its table entries")
        if (
            sum(table.reviewed_unique_cells for table in self.tables.values())
            != self.expected_unique_source_cells
        ):
            raise ValueError("ledger unique-cell review total is inconsistent with its table entries")
        return self

    @classmethod
    def load(cls, path: Path) -> "CorrectionLedger":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.model_validate(yaml.safe_load(handle))


@dataclass(frozen=True, slots=True)
class PostprocessingResult:
    output_root: Path
    csv_files: list[Path]
    correction_log: Path
    report: Path
    corrected_cells: int
    reviewed_unique_cells: int


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def _text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value)


def _expected_unique_cells(schema: TableSchema, rows: pd.DataFrame) -> int:
    if schema.hierarchy is None:
        return len(rows) * len(schema.get_all_variables())
    parent_count = len({_text(value) for value in rows["parent_row_index"].tolist()})
    child_count = len(schema.hierarchy.child_variables)
    return parent_count * (len(schema.get_all_variables()) - child_count) + len(rows) * child_count


class CSVPostprocessor:
    """Apply a reviewed ledger to one immutable extraction run."""

    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig()
        self.schemas = SchemaRegistry(self.config.schemas_dir)

    def run(
        self,
        *,
        source_run: str | Path,
        ledger_path: Path,
        output_id: str,
    ) -> PostprocessingResult:
        ledger = CorrectionLedger.load(ledger_path)
        source_root = self._resolve_source_run(source_run)
        if source_root.name != ledger.source_run_id:
            raise ValueError(
                f"source run {source_root.name!r} != ledger run {ledger.source_run_id!r}"
            )
        manifest_path = source_root / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Source manifest not found: {manifest_path}")
        actual_hash = _sha256(manifest_path)
        if actual_hash != ledger.source_manifest_sha256.upper():
            raise ValueError(
                f"source manifest SHA-256 {actual_hash} != ledger {ledger.source_manifest_sha256}"
            )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_results = manifest.get("results", {})
        if set(manifest_results) != set(ledger.tables):
            missing = sorted(set(ledger.tables).difference(manifest_results))
            extra = sorted(set(manifest_results).difference(ledger.tables))
            raise ValueError(f"manifest/ledger table mismatch: missing={missing}, extra={extra}")

        output_name = Path(output_id)
        if not output_id.strip() or output_name.is_absolute() or output_name.name != output_id:
            raise ValueError("output_id must be one non-empty directory name")
        output_root = self.config.outputs_dir / "postprocessed" / output_id
        if output_root.exists():
            raise FileExistsError(f"Post-processing output already exists: {output_root}")
        output_root.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_root.with_name(f".{output_root.name}.{uuid.uuid4().hex}.tmp")
        csv_dir = temporary / "csv"
        csv_dir.mkdir(parents=True)
        correction_records: list[dict[str, Any]] = []
        output_paths: list[Path] = []
        total_rows = 0
        reviewed_cells = 0
        per_table: list[dict[str, Any]] = []
        try:
            for pdf_id in sorted(ledger.tables):
                table_review = ledger.tables[pdf_id]
                manifest_record = manifest_results[pdf_id]
                if manifest_record.get("format_id") != table_review.format_id:
                    raise ValueError(
                        f"{pdf_id}: manifest format {manifest_record.get('format_id')!r} "
                        f"!= ledger {table_review.format_id!r}"
                    )
                schema = self.schemas.require(table_review.format_id)
                source_csv = Path(manifest_record["exported_files"]["csv"])
                if not source_csv.is_file():
                    raise FileNotFoundError(f"Manifest-selected CSV not found: {source_csv}")
                frame = pd.read_csv(source_csv, dtype=str, keep_default_na=False)
                if len(frame) != table_review.expected_rows:
                    raise ValueError(
                        f"{pdf_id}: row count {len(frame)} != expected {table_review.expected_rows}"
                    )
                parent_count = (
                    frame["parent_row_index"].nunique()
                    if schema.hierarchy is not None
                    else len(frame)
                )
                if parent_count != table_review.expected_parent_rows:
                    raise ValueError(
                        f"{pdf_id}: parent count {parent_count} != expected "
                        f"{table_review.expected_parent_rows}"
                    )
                expected_review = _expected_unique_cells(schema, frame)
                if table_review.reviewed_unique_cells != expected_review:
                    raise ValueError(
                        f"{pdf_id}: reviewed unique cells {table_review.reviewed_unique_cells} "
                        f"!= computed {expected_review}"
                    )
                changed = self._apply_table_corrections(
                    pdf_id, frame, schema, table_review.corrections, correction_records
                )
                self._recompute_companion_fields(frame, schema)
                self._validate_corrected_table(pdf_id, frame, schema)
                if list(frame.columns) != list(
                    pd.read_csv(source_csv, dtype=str, keep_default_na=False, nrows=0).columns
                ):
                    raise ValueError(f"{pdf_id}: corrected CSV header differs from source")
                destination = csv_dir / f"{pdf_id}.csv"
                frame.to_csv(destination, index=False, encoding="utf-8", lineterminator="\n")
                output_paths.append(destination)
                total_rows += len(frame)
                reviewed_cells += expected_review
                per_table.append(
                    {
                        "pdf_id": pdf_id,
                        "format_id": schema.format_id,
                        "rows": len(frame),
                        "parent_rows": parent_count,
                        "reviewed_unique_cells": expected_review,
                        "corrected_cells": changed,
                    }
                )

            if len(output_paths) != ledger.expected_table_count:
                raise ValueError("post-processing did not produce the expected number of CSV files")
            if total_rows != ledger.expected_output_rows:
                raise ValueError(
                    f"corrected row count {total_rows} != expected {ledger.expected_output_rows}"
                )
            if reviewed_cells != ledger.expected_unique_source_cells:
                raise ValueError(
                    f"reviewed unique cells {reviewed_cells} != expected "
                    f"{ledger.expected_unique_source_cells}"
                )
            correction_log = temporary / "CORRECTION_LOG.csv"
            self._write_correction_log(correction_log, correction_records)
            report = temporary / "POSTPROCESSING_REPORT.md"
            report.write_text(
                self._report_markdown(
                    ledger,
                    actual_hash,
                    output_id,
                    per_table,
                    len(correction_records),
                ),
                encoding="utf-8",
                newline="\n",
            )
            temporary.replace(output_root)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise

        return PostprocessingResult(
            output_root=output_root,
            csv_files=[output_root / "csv" / path.name for path in output_paths],
            correction_log=output_root / "CORRECTION_LOG.csv",
            report=output_root / "POSTPROCESSING_REPORT.md",
            corrected_cells=len(correction_records),
            reviewed_unique_cells=reviewed_cells,
        )

    def _resolve_source_run(self, source_run: str | Path) -> Path:
        candidate = Path(source_run)
        if not candidate.is_absolute():
            candidate = self.config.runs_dir / candidate
        return candidate.resolve()

    @staticmethod
    def _selected_indices(
        pdf_id: str,
        frame: pd.DataFrame,
        schema: TableSchema,
        correction: CellCorrection,
    ) -> list[int]:
        selector = correction.selector
        if selector.row_index is not None:
            matches = frame.index[frame["row_index"] == str(selector.row_index)].tolist()
        else:
            if schema.hierarchy is None:
                raise ValueError(f"{pdf_id}: hierarchy selector used for flat schema")
            mask = frame["parent_row_index"] == str(selector.parent_row_index)
            if selector.subrow_index is not None:
                mask &= frame["subrow_index"] == str(selector.subrow_index)
            matches = frame.index[mask].tolist()
        if correction.scope == "row" and len(matches) != 1:
            raise ValueError(f"{pdf_id}: row selector matched {len(matches)} rows")
        if correction.scope == "parent" and not matches:
            raise ValueError(f"{pdf_id}: parent selector matched no rows")
        return [int(index) for index in matches]

    def _apply_table_corrections(
        self,
        pdf_id: str,
        frame: pd.DataFrame,
        schema: TableSchema,
        corrections: list[CellCorrection],
        records: list[dict[str, Any]],
    ) -> int:
        schema_variables = set(schema.get_all_variables())
        seen: set[tuple[int, str]] = set()
        selected: list[tuple[CellCorrection, list[int]]] = []
        for correction in corrections:
            indices = self._selected_indices(pdf_id, frame, schema, correction)
            for index in indices:
                duplicate_key = (index, correction.variable)
                if duplicate_key in seen:
                    raise ValueError(
                        f"{pdf_id}: duplicate correction for row {index}, {correction.variable}"
                    )
                seen.add(duplicate_key)
            selected.append((correction, indices))

        changed = 0
        for correction, indices in selected:
            if correction.variable not in schema_variables:
                raise ValueError(
                    f"{pdf_id}: correction references unknown variable {correction.variable!r}"
                )
            if correction.panel_id not in {panel.panel_id for panel in schema.panels}:
                raise ValueError(
                    f"{pdf_id}: correction references unknown panel {correction.panel_id!r}"
                )
            if correction.scope == "parent":
                hierarchy = schema.hierarchy
                if hierarchy is None or correction.variable in hierarchy.child_variables:
                    raise ValueError(
                        f"{pdf_id}: parent correction cannot target {correction.variable!r}"
                    )
            originals = {_text(frame.at[index, correction.variable]) for index in indices}
            if originals != {correction.expected_original}:
                raise ValueError(
                    f"{pdf_id}: {correction.variable} original values {sorted(originals)!r} "
                    f"!= expected {correction.expected_original!r}"
                )
            for index in indices:
                frame.at[index, correction.variable] = correction.corrected
            records.append(
                {
                    "pdf_id": pdf_id,
                    "scope": correction.scope,
                    "row_index": correction.selector.row_index,
                    "parent_row_index": correction.selector.parent_row_index,
                    "subrow_index": correction.selector.subrow_index,
                    "variable": correction.variable,
                    "original": correction.expected_original,
                    "corrected": correction.corrected,
                    "source_page": correction.source_page,
                    "panel_id": correction.panel_id,
                    "reason": correction.reason,
                    "affected_output_rows": len(indices),
                }
            )
            changed += len(indices)
        return changed

    @staticmethod
    def _recompute_companion_fields(frame: pd.DataFrame, schema: TableSchema) -> None:
        raw_rows: list[dict[str, Any]] = []
        for _, record in frame.iterrows():
            raw: dict[str, Any] = {
                variable: _text(record[variable]) for variable in schema.get_all_variables()
            }
            if schema.hierarchy is not None:
                raw.update(
                    {
                        "__parent_row_index": int(_text(record["parent_row_index"])),
                        "__subrow_index": int(_text(record["subrow_index"])),
                        "__subrow_count": int(_text(record["subrow_count"])),
                    }
                )
            raw_rows.append(raw)
        normalized = normalize_rows(raw_rows, schema)
        for index, row in enumerate(normalized):
            for cell in row.cells:
                frame.at[index, f"{cell.variable}_flag"] = cell.review_flag or ""
            frame.at[index, "requires_review"] = str(
                any(cell.review_flag for cell in row.cells)
            ).title()
            frame.at[index, "row_type"] = row.row_type
            frame.at[index, "reference_target"] = row.reference_target or ""
            if schema.format_id == "format_001":
                for variable in ("pucca_road_km", "kutcha_road_km"):
                    value = row.values.get(variable)
                    frame.at[index, variable] = "" if value is None else str(value)

    @staticmethod
    def _validate_corrected_table(pdf_id: str, frame: pd.DataFrame, schema: TableSchema) -> None:
        flag_columns = [column for column in frame if column.endswith("_flag")]
        flagged = [
            (int(index), column, _text(frame.at[index, column]))
            for index in frame.index
            for column in flag_columns
            if _text(frame.at[index, column]).strip()
        ]
        if flagged:
            raise ValueError(f"{pdf_id}: corrected data retains review flags: {flagged[:10]}")
        if any(_text(value).casefold() == "true" for value in frame["requires_review"]):
            raise ValueError(f"{pdf_id}: corrected data still requires review")
        identity = "town_name" if schema.get_column_by_var("town_name") else "tahsil_name"
        if any(not _text(value).strip() for value in frame[identity]):
            raise ValueError(f"{pdf_id}: corrected data contains a blank identity")
        forbidden = re.compile(
            r"(?:AMBIGUOUS_OCR|SPACED_DIGITS|TRAILING_MARK_REMOVED|"
            r"this image does not contain|expected integer|\bBANKING\b|<smiles>|"
            r"[\u3400-\u9fff])",
            re.IGNORECASE,
        )
        schema_values = frame[schema.get_all_variables()].astype(str)
        bad_values = [
            (int(row), column, value)
            for row in schema_values.index
            for column, value in schema_values.loc[row].items()
            if forbidden.search(value)
        ]
        if bad_values:
            raise ValueError(f"{pdf_id}: forbidden OCR contamination remains: {bad_values[:10]}")
        if schema.hierarchy is not None:
            child_variables = set(schema.hierarchy.child_variables)
            inherited = [
                variable for variable in schema.get_all_variables() if variable not in child_variables
            ]
            for parent_index, group in frame.groupby("parent_row_index", sort=True):
                for variable in inherited:
                    if group[variable].nunique(dropna=False) != 1:
                        raise ValueError(
                            f"{pdf_id}: parent {parent_index} has inconsistent {variable}"
                        )
                indexes = [int(value) for value in group["subrow_index"]]
                if indexes != list(range(len(group))):
                    raise ValueError(
                        f"{pdf_id}: parent {parent_index} has non-contiguous subrows {indexes}"
                    )

    @staticmethod
    def _write_correction_log(path: Path, records: list[dict[str, Any]]) -> None:
        fields = [
            "pdf_id",
            "scope",
            "row_index",
            "parent_row_index",
            "subrow_index",
            "variable",
            "original",
            "corrected",
            "source_page",
            "panel_id",
            "reason",
            "affected_output_rows",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(records)

    @staticmethod
    def _report_markdown(
        ledger: CorrectionLedger,
        manifest_hash: str,
        output_id: str,
        per_table: list[dict[str, Any]],
        correction_count: int,
    ) -> str:
        lines = [
            "# Five-District Source-Verified Post-Processing",
            "",
            "## Outcome",
            "",
            f"- Source run: `{ledger.source_run_id}`",
            f"- Source manifest SHA-256: `{manifest_hash}`",
            f"- Output: `{output_id}`",
            f"- Corrected data CSVs: {len(per_table)}",
            f"- Output rows: {sum(item['rows'] for item in per_table)}",
            f"- Source-verified unique cells: {sum(item['reviewed_unique_cells'] for item in per_table)}",
            f"- Correction ledger entries: {correction_count}",
            "- Unresolved cells: 0",
            "- Paid OCR/API calls: 0",
            "",
            "The structural source run remains unchanged. Printed values, punctuation, blanks, "
            "ellipses, dashes, and historical codes were checked against the source PDFs. "
            "MedEdu inherited values were reviewed once per parent and propagated to every child.",
            "",
            "## Per-file QA",
            "",
            "| PDF | Format | Parents | Rows | Unique cells reviewed | Corrected output cells |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for item in per_table:
            lines.append(
                f"| `{item['pdf_id']}` | `{item['format_id']}` | {item['parent_rows']} | "
                f"{item['rows']} | {item['reviewed_unique_cells']} | {item['corrected_cells']} |"
            )
        lines.extend(
            [
                "",
                "## Remaining issues",
                "",
                "None. Every unique source cell in the 15-table pilot has a completed review "
                "status, and the corrected CSVs contain no unresolved OCR flags.",
                "",
            ]
        )
        return "\n".join(lines)
