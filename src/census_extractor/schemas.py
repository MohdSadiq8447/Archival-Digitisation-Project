"""Typed logical columns and physical panel definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator


class ColumnDefinition(BaseModel):
    column_no: int
    column_name: str
    variable: str
    data_type: str = "string"
    description: str | None = None
    value_examples: list[str] = Field(default_factory=list)


class PanelDefinition(BaseModel):
    panel_id: str
    page: int = Field(ge=1)
    printed_columns: list[int]
    identity_columns: list[int] = Field(default_factory=list)
    headings: list[str] = Field(default_factory=list)
    row_anchor: bool = False
    align_to: str | None = None

    @model_validator(mode="after")
    def validate_panel(self) -> "PanelDefinition":
        if not self.printed_columns:
            raise ValueError("printed_columns cannot be empty")
        if len(set(self.printed_columns)) != len(self.printed_columns):
            raise ValueError("printed_columns must be unique within a panel")
        if self.row_anchor and self.align_to:
            raise ValueError("a row anchor cannot align to another panel")
        return self


class TableSchema(BaseModel):
    format_id: str
    name: str
    table_description: str | None = None
    anchor_page: list[ColumnDefinition] = Field(default_factory=list)
    continuation_page: list[ColumnDefinition] = Field(default_factory=list)
    panels: list[PanelDefinition] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_layout(self) -> "TableSchema":
        all_numbers = {column.column_no for column in self.get_all_columns()}
        if not self.panels:
            raise ValueError(f"{self.format_id} has no physical panel definitions")
        panel_numbers = {number for panel in self.panels for number in panel.printed_columns}
        if all_numbers.difference(panel_numbers):
            raise ValueError(
                f"{self.format_id} panels do not cover logical columns {sorted(all_numbers.difference(panel_numbers))}"
            )
        panel_ids = {panel.panel_id for panel in self.panels}
        for panel in self.panels:
            if panel.align_to and panel.align_to not in panel_ids:
                raise ValueError(f"Unknown align_to panel {panel.align_to!r}")
        if sum(panel.row_anchor for panel in self.panels) != 1:
            raise ValueError(f"{self.format_id} must define exactly one row anchor")
        return self

    @property
    def total_columns(self) -> int:
        return len(self.get_all_columns())

    def get_all_columns(self) -> list[ColumnDefinition]:
        combined = {column.column_no: column for column in self.anchor_page}
        combined.update({column.column_no: column for column in self.continuation_page})
        return [combined[number] for number in sorted(combined)]

    def get_column_by_no(self, col_no: int) -> ColumnDefinition | None:
        return next((c for c in self.get_all_columns() if c.column_no == col_no), None)

    def get_column_by_var(self, variable_name: str) -> ColumnDefinition | None:
        return next((c for c in self.get_all_columns() if c.variable == variable_name), None)

    def columns_for_panel(self, panel: PanelDefinition) -> list[ColumnDefinition]:
        result: list[ColumnDefinition] = []
        for number in panel.printed_columns:
            column = self.get_column_by_no(number)
            if column is None:
                raise ValueError(f"Panel {panel.panel_id!r} references undefined column {number}")
            result.append(column)
        return result

    def get_all_variables(self) -> list[str]:
        return [column.variable for column in self.get_all_columns()]

    @property
    def row_anchor_panel(self) -> PanelDefinition:
        return next(panel for panel in self.panels if panel.row_anchor)


class SchemaRegistry:
    def __init__(self, schemas_dir: Path):
        self.schemas_dir = Path(schemas_dir)
        self._schemas: dict[str, TableSchema] = {}
        self.load_all()

    def load_all(self) -> None:
        if not self.schemas_dir.is_dir():
            raise FileNotFoundError(f"Schema directory not found: {self.schemas_dir}")
        for yaml_path in sorted(self.schemas_dir.glob("*.yaml")):
            with yaml_path.open("r", encoding="utf-8") as handle:
                data: dict[str, Any] = yaml.safe_load(handle)
            schema = TableSchema.model_validate(data)
            if schema.format_id in self._schemas:
                raise ValueError(f"Duplicate format id {schema.format_id!r}")
            self._schemas[schema.format_id] = schema
            self._schemas[schema.name] = schema

    def get(self, key: str) -> TableSchema | None:
        return self._schemas.get(key)

    def require(self, key: str) -> TableSchema:
        schema = self.get(key)
        if schema is None:
            raise ValueError(f"Unknown format id {key!r}; refusing schema fallback")
        return schema

    def all_formats(self) -> list[TableSchema]:
        unique = {schema.format_id: schema for schema in self._schemas.values()}
        return sorted(unique.values(), key=lambda schema: schema.format_id)
