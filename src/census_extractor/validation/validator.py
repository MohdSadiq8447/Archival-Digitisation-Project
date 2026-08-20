"""Fail-closed geometry, OCR, parsing, and semantic validation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from census_extractor.normalization import NormalizedRow
from census_extractor.schemas import TableSchema


class FindingSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(slots=True)
class ValidationFinding:
    code: str
    severity: FindingSeverity
    message: str
    row_index: int | None = None
    variable: str | None = None


@dataclass(slots=True)
class QualityComponents:
    geometry: float
    ocr: float
    parsing: float
    semantic: float

    @property
    def overall(self) -> float:
        return round(
            self.geometry * 0.30 + self.ocr * 0.35 + self.parsing * 0.15 + self.semantic * 0.20, 4
        )


@dataclass(slots=True)
class TableValidationReport:
    table_name: str
    format_id: str
    total_rows: int
    valid_rows_count: int
    findings: list[ValidationFinding] = field(default_factory=list)
    quality: QualityComponents = field(default_factory=lambda: QualityComponents(0, 0, 0, 0))
    quality_threshold: float = 0.95
    panels_complete: bool = False
    alignment_complete: bool = False

    @property
    def confidence_score(self) -> float:
        return self.quality.overall

    @property
    def issues(self) -> list[ValidationFinding]:
        return self.findings

    @property
    def failing_row_indices(self) -> list[int]:
        return sorted(
            {
                finding.row_index
                for finding in self.findings
                if finding.row_index is not None and finding.severity == FindingSeverity.ERROR
            }
        )

    @property
    def is_valid(self) -> bool:
        return (
            self.panels_complete
            and self.alignment_complete
            and not any(finding.severity == FindingSeverity.ERROR for finding in self.findings)
            and self.quality.overall >= self.quality_threshold
        )


class TableValidator:
    def __init__(self, quality_threshold: float = 0.95):
        self.quality_threshold = quality_threshold

    def validate(
        self,
        table_name: str,
        schema: TableSchema,
        rows: list[NormalizedRow],
        *,
        panels_complete: bool,
        aligned_row_counts: dict[str, int],
        panel_scores: list[float],
        ocr_row_successes: int,
        ocr_row_total: int,
    ) -> TableValidationReport:
        findings: list[ValidationFinding] = []
        expected_count = len(rows)
        alignment_complete = bool(rows) and all(
            count == expected_count for count in aligned_row_counts.values()
        )
        if not panels_complete:
            findings.append(
                ValidationFinding(
                    "panel_discovery",
                    FindingSeverity.ERROR,
                    "One or more required panels were not discovered",
                )
            )
        if not rows:
            findings.append(
                ValidationFinding(
                    "row_count", FindingSeverity.ERROR, "No anchor data rows were segmented"
                )
            )
        if not alignment_complete:
            findings.append(
                ValidationFinding(
                    "panel_alignment",
                    FindingSeverity.ERROR,
                    f"Panel row counts are not aligned: {aligned_row_counts}",
                )
            )

        parse_total, parse_failures = 0, 0
        identity_var = "town_name" if schema.get_column_by_var("town_name") else "tahsil_name"
        seen: dict[str, int] = {}
        last_serial = 0
        data_variables = [
            column.variable
            for column in schema.get_all_columns()
            if column.variable not in {"sl_no", identity_var}
        ]
        for index, row in enumerate(rows):
            for cell in row.cells:
                if cell.raw_value.strip():
                    parse_total += 1
                if cell.parse_error:
                    parse_failures += 1
                    findings.append(
                        ValidationFinding(
                            "type_parse",
                            FindingSeverity.ERROR,
                            cell.parse_error,
                            index,
                            cell.variable,
                        )
                    )
                elif cell.review_flag:
                    findings.append(
                        ValidationFinding(
                            "ambiguous_ocr",
                            FindingSeverity.ERROR,
                            f"{cell.variable}: {cell.review_flag} for {cell.raw_value!r}",
                            index,
                            cell.variable,
                        )
                    )
                if (
                    isinstance(cell.value, (int, float))
                    and cell.variable != "sl_no"
                    and cell.value < 0
                ):
                    findings.append(
                        ValidationFinding(
                            "nonnegative",
                            FindingSeverity.ERROR,
                            f"Negative count/value {cell.value}",
                            index,
                            cell.variable,
                        )
                    )
            serial = row.values.get("sl_no")
            serial_text = str(serial or "").strip()
            if re.fullmatch(r"\d+", serial_text):
                serial_number = int(serial_text)
                if serial_number <= last_serial:
                    findings.append(
                        ValidationFinding(
                            "serial_progression",
                            FindingSeverity.ERROR,
                            f"Serial {serial_number} follows {last_serial}",
                            index,
                            "sl_no",
                        )
                    )
                last_serial = serial_number
            identity = str(row.values.get(identity_var) or "").strip()
            normalized_identity = re.sub(r"\W+", " ", identity.casefold()).strip()
            if not identity:
                findings.append(
                    ValidationFinding(
                        "identity_missing",
                        FindingSeverity.ERROR,
                        "Row identity is blank",
                        index,
                        identity_var,
                    )
                )
            elif row.row_type == "ORDINARY" and normalized_identity in seen:
                findings.append(
                    ValidationFinding(
                        "duplicate_identity",
                        FindingSeverity.ERROR,
                        f"Duplicate identity {identity!r}",
                        index,
                        identity_var,
                    )
                )
            else:
                seen[normalized_identity] = index
            if row.row_type == "CROSS_REFERENCE":
                ignored = {
                    "sl_no",
                    identity_var,
                    "row_type",
                    "reference_target",
                    "pucca_road_km",
                    "kutcha_road_km",
                }
                impure = [
                    key
                    for key, value in row.values.items()
                    if key not in ignored and value is not None
                ]
                if impure:
                    findings.append(
                        ValidationFinding(
                            "cross_reference_purity",
                            FindingSeverity.ERROR,
                            f"Cross-reference has data in {impure}",
                            index,
                        )
                    )
            else:
                raw_by_variable = {cell.variable: cell.raw_value.strip() for cell in row.cells}
                if not any(raw_by_variable.get(variable) for variable in data_variables):
                    for variable in data_variables:
                        findings.append(
                            ValidationFinding(
                                "ocr_completeness",
                                FindingSeverity.ERROR,
                                "Row has no transcribed data cells",
                                index,
                                variable,
                            )
                        )

        ordinary_rows = [row for row in rows if row.row_type != "CROSS_REFERENCE"]
        for variable in data_variables:
            if ordinary_rows and not any(
                next(
                    (cell.raw_value.strip() for cell in row.cells if cell.variable == variable), ""
                )
                for row in ordinary_rows
            ):
                findings.append(
                    ValidationFinding(
                        "column_ocr_completeness",
                        FindingSeverity.ERROR,
                        f"Column {variable!r} has no transcribed values",
                        variable=variable,
                    )
                )

        if schema.format_id == "format_003":
            self._validate_tahsil_totals(rows, schema, findings)

        geometry_score = min(panel_scores, default=0.0) * (1.0 if alignment_complete else 0.5)
        ocr_score = ocr_row_successes / ocr_row_total if ocr_row_total else 0.0
        parsing_score = 1 - parse_failures / parse_total if parse_total else 0.0
        semantic_errors = sum(
            finding.severity == FindingSeverity.ERROR
            and finding.code not in {"panel_discovery", "panel_alignment", "type_parse"}
            for finding in findings
        )
        semantic_score = max(0.0, 1 - semantic_errors / max(1, len(rows)))
        error_rows = {
            finding.row_index
            for finding in findings
            if finding.severity == FindingSeverity.ERROR and finding.row_index is not None
        }
        return TableValidationReport(
            table_name=table_name,
            format_id=schema.format_id,
            total_rows=len(rows),
            valid_rows_count=max(0, len(rows) - len(error_rows)),
            findings=findings,
            quality=QualityComponents(geometry_score, ocr_score, parsing_score, semantic_score),
            quality_threshold=self.quality_threshold,
            panels_complete=panels_complete,
            alignment_complete=alignment_complete,
        )

    @staticmethod
    def _validate_tahsil_totals(
        rows: list[NormalizedRow], schema: TableSchema, findings: list[ValidationFinding]
    ) -> None:
        totals = [(index, row) for index, row in enumerate(rows) if row.row_type == "TOTAL"]
        if len(totals) != 1:
            findings.append(
                ValidationFinding(
                    "tahsil_total_presence",
                    FindingSeverity.ERROR,
                    f"Expected one district total row; found {len(totals)}",
                )
            )
            return
        total_index, total = totals[0]
        components = [row for row in rows if row.row_type != "TOTAL"]
        for column in schema.get_all_columns():
            if column.data_type != "integer" or column.variable == "sl_no":
                continue
            values = [row.values.get(column.variable) for row in components]
            total_value = total.values.get(column.variable)
            if (
                values
                and all(isinstance(value, int) for value in values)
                and isinstance(total_value, int)
            ):
                expected = sum(int(value) for value in values if isinstance(value, int))
                if expected != total_value:
                    findings.append(
                        ValidationFinding(
                            "tahsil_total_sum",
                            FindingSeverity.ERROR,
                            f"District total {total_value} != component sum {expected}",
                            total_index,
                            column.variable,
                        )
                    )
