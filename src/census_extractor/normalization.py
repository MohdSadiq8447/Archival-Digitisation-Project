"""Typed nullable normalization while preserving raw OCR separately."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from census_extractor.schemas import ColumnDefinition, TableSchema

NULL_PATTERN = re.compile(r"^(?:nil|n\.?a\.?|none|[-–—.·…]+|\.{2,})$", re.IGNORECASE)


@dataclass(slots=True)
class NormalizedCell:
    variable: str
    raw_value: str
    value: Any
    parse_error: str | None = None


@dataclass(slots=True)
class NormalizedRow:
    values: dict[str, Any]
    cells: list[NormalizedCell]
    row_type: str
    reference_target: str | None = None
    parse_errors: list[str] = field(default_factory=list)


def normalize_null(raw: str) -> str | None:
    value = " ".join(str(raw).replace("\u00a0", " ").split()).strip()
    return None if not value or NULL_PATTERN.fullmatch(value) else value


def _clean_number(value: str) -> str:
    return value.replace(",", "").replace("O", "0").replace("o", "0").strip()


def type_value(raw: str, column: ColumnDefinition) -> tuple[Any, str | None]:
    value = normalize_null(raw)
    if value is None:
        return None, None
    data_type = column.data_type.casefold()
    numeric = _clean_number(value)
    try:
        if data_type == "integer":
            if not re.fullmatch(r"[+-]?\d+", numeric):
                raise ValueError("expected integer")
            return int(numeric), None
        if data_type == "float":
            return float(numeric), None
        if data_type == "integer_or_roman":
            return value, None
        if data_type in {"integer_or_string", "integer_or_code"}:
            return value, None
        if data_type in {"float_or_string", "float_or_code"}:
            return value, None
        return value, None
    except ValueError as exc:
        return None, f"{column.variable}: {exc} for {value!r}"


def classify_row(identity: str, serial: Any) -> tuple[str, str | None]:
    name, serial_text = identity.strip(), str(serial or "").strip()
    lowered = name.casefold()
    if re.search(r"\bsee\b", lowered):
        target_match = re.search(r"\bsee\b\s*(.*)", name, re.IGNORECASE)
        return "CROSS_REFERENCE", target_match.group(1).strip() if target_match else name
    if "district total" in lowered or lowered == "total" or lowered.endswith(" total"):
        return "TOTAL", None
    if re.match(r"^\(?[ivxlcdm]+\)?[.)]?\s", name, re.IGNORECASE) or re.fullmatch(
        r"\(?[ivxlcdm]+\)?", serial_text, re.IGNORECASE
    ):
        return "COMPONENT", None
    if "urban agglomeration" in lowered or "(u.a" in lowered or "(ua" in lowered:
        return "AGGREGATE", None
    return "ORDINARY", None


def parse_road_lengths(raw: str) -> dict[str, float | None]:
    value = (normalize_null(raw) or "").upper()
    result: dict[str, float | None] = {"pucca_road_km": None, "kutcha_road_km": None}
    for labels, variable in (
        (r"(?:PR|PUCCA)", "pucca_road_km"),
        (r"(?:KR|K[AU]TCH?A)", "kutcha_road_km"),
    ):
        match = re.search(labels + r"\s*[:=-]?\s*(\d+(?:\.\d+)?)", value)
        if match:
            result[variable] = float(match.group(1))
    return result


def normalize_rows(raw_rows: list[dict[str, str]], schema: TableSchema) -> list[NormalizedRow]:
    normalized: list[NormalizedRow] = []
    columns = schema.get_all_columns()
    identity_var = "town_name" if schema.get_column_by_var("town_name") else "tahsil_name"
    for raw_row in raw_rows:
        values: dict[str, Any] = {}
        cells: list[NormalizedCell] = []
        errors: list[str] = []
        for column in columns:
            raw_value = str(raw_row.get(column.variable, "") or "")
            value, error = type_value(raw_value, column)
            values[column.variable] = value
            cells.append(NormalizedCell(column.variable, raw_value, value, error))
            if error:
                errors.append(error)
        row_type, reference_target = classify_row(
            str(values.get(identity_var) or ""), values.get("sl_no")
        )
        if row_type == "CROSS_REFERENCE":
            for column in columns:
                if column.variable not in {"sl_no", identity_var}:
                    values[column.variable] = None
        if schema.format_id == "format_001":
            values.update(parse_road_lengths(str(raw_row.get("road_length_km", ""))))
        values["row_type"] = row_type
        values["reference_target"] = reference_target
        normalized.append(NormalizedRow(values, cells, row_type, reference_target, errors))
    return normalized
