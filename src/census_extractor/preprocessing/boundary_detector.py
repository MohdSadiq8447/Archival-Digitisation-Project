"""Resolved table boundary record.

Generic density-based boundary guessing was removed: production boundaries
are created by printed-number panel discovery and fail closed when unresolved.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class TableBoundary:
    page_number: int
    table_bbox: tuple[int, int, int, int]
    header_bbox: tuple[int, int, int, int]
    body_bbox: tuple[int, int, int, int]
    footer_bbox: tuple[int, int, int, int] | None
    is_stacked_statement: bool = False
    title: str = ""
