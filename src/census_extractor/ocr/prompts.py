"""Schema-aware prompts built on Novita's DeepSeek OCR 2 presets."""

from __future__ import annotations

from collections.abc import Iterable

from census_extractor.schemas import ColumnDefinition, PanelDefinition, TableSchema

GROUNDING_PROMPT = "<|grounding|>OCR this image."
FREE_OCR_PROMPT = "Free OCR."

_ARCHIVAL_CONTEXT = (
    "This is an archival 1971 Uttar Pradesh District Census Handbook table. "
    "The scan may contain faded type, historic spellings, abbreviations, ditto marks, "
    "dashes, ellipses, Nil values, and cross-references."
)

_TRANSCRIPTION_RULES = (
    "Transcribe only text visible in the image. Preserve the printed spelling, case, "
    "punctuation, abbreviations, codes, Nil, dashes, ellipses, and cross-references. "
    "Do not infer, calculate, normalize, correct, or fill a value from the context or "
    "examples. Expected-value examples are recognition hints, never answers. Do not "
    "emit a value for a truly blank cell."
)


def _column_context(column: ColumnDefinition) -> str:
    parts = [
        f"{column.column_no}: {column.column_name}",
        f"field={column.variable}",
        f"type={column.data_type}",
    ]
    if column.description:
        parts.append(column.description)
    if column.value_examples:
        parts.append(f"possible printed forms: {' | '.join(column.value_examples)}")
    return "; ".join(parts)


def _columns_block(columns: Iterable[ColumnDefinition]) -> str:
    return "\n".join(f"- {_column_context(column)}" for column in columns)


def build_columns_grounding_prompt(columns: Iterable[ColumnDefinition]) -> str:
    """Build a generic row prompt when only expected columns are available."""
    column_list = list(columns)
    if not column_list:
        return GROUNDING_PROMPT
    return "\n\n".join(
        [
            GROUNDING_PROMPT,
            _ARCHIVAL_CONTEXT,
            "This crop is one table row. Expected printed columns, left to right:\n"
            + _columns_block(column_list),
            _TRANSCRIPTION_RULES,
        ]
    )


def build_row_grounding_prompt(schema: TableSchema, panel: PanelDefinition) -> str:
    """Describe a historical table row without suggesting its actual cell values."""
    description = schema.table_description or schema.name
    columns = schema.columns_for_panel(panel)
    return "\n\n".join(
        [
            GROUNDING_PROMPT,
            _ARCHIVAL_CONTEXT,
            f"Table: {schema.name}. {description}",
            (
                f"This crop is one row from panel {panel.panel_id}. Expected printed "
                "columns, left to right:\n" + _columns_block(columns)
            ),
            _TRANSCRIPTION_RULES,
        ]
    )


def build_page_grounding_prompt(schema: TableSchema, page_number: int) -> str:
    """Provide expected physical panels when OCR is locating page geometry."""
    panels = [panel for panel in schema.panels if panel.page == page_number]
    panel_lines = [
        (
            f"- {panel.panel_id}: printed column sequence "
            f"{', '.join(str(number) for number in panel.printed_columns)}; "
            f"heading cues: {', '.join(panel.headings) or 'none'}"
        )
        for panel in panels
    ]
    return "\n\n".join(
        [
            GROUNDING_PROMPT,
            _ARCHIVAL_CONTEXT,
            f"Table: {schema.name}. {schema.table_description or schema.name}",
            (
                f"This is full physical page {page_number}, used to locate table panels. "
                "Expected layout:\n" + "\n".join(panel_lines)
            ),
            _TRANSCRIPTION_RULES
            + " Return grounded text and bounding boxes for all visible page text.",
        ]
    )


def build_cell_free_ocr_prompt(
    schema: TableSchema, panel: PanelDefinition, column: ColumnDefinition
) -> str:
    """Describe one cell while retaining Novita's Free OCR preset first line."""
    return "\n\n".join(
        [
            FREE_OCR_PROMPT,
            _ARCHIVAL_CONTEXT,
            f"Table: {schema.name}; panel: {panel.panel_id}.",
            "This image contains one cell for expected " + _column_context(column) + ".",
            _TRANSCRIPTION_RULES + " Return only the visible cell text.",
        ]
    )
