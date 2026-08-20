"""Printed-column driven discovery of physical table panels."""

from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import median

from census_extractor.geometry.column_detector import ColumnSpan
from census_extractor.preprocessing.pdf_loader import RenderedPage
from census_extractor.schemas import PanelDefinition, TableSchema


class PanelDiscoveryError(ValueError):
    """A required panel or printed column sequence could not be resolved."""


@dataclass(frozen=True, slots=True)
class NumberToken:
    value: int
    text: str
    bbox: tuple[int, int, int, int]

    @property
    def center_x(self) -> float:
        return (self.bbox[0] + self.bbox[2]) / 2.0

    @property
    def center_y(self) -> float:
        return (self.bbox[1] + self.bbox[3]) / 2.0


@dataclass(slots=True)
class PanelGeometry:
    definition: PanelDefinition
    page_number: int
    table_bbox: tuple[int, int, int, int]
    header_bbox: tuple[int, int, int, int]
    body_bbox: tuple[int, int, int, int]
    columns: list[ColumnSpan]
    matched_numbers: list[int]
    sequence_score: float
    discovery_source: str = "embedded_text"


@dataclass(slots=True)
class _Candidate:
    tokens: list[NumberToken]
    score: float
    heading_score: float

    @property
    def center_y(self) -> float:
        return median(token.center_y for token in self.tokens)


class PanelDetector:
    """Locates header number rows and derives physical column centres from them."""

    def __init__(self, min_sequence_score: float = 0.62):
        self.min_sequence_score = min_sequence_score

    def discover(self, pages: list[RenderedPage], schema: TableSchema) -> list[PanelGeometry]:
        expected_pages = {panel.page for panel in schema.panels}
        if len(pages) != max(expected_pages):
            raise PanelDiscoveryError(
                f"Expected exactly {max(expected_pages)} pages for {schema.format_id}; got {len(pages)}"
            )

        selected: dict[str, _Candidate] = {}
        candidates_by_panel: dict[str, list[_Candidate]] = {}
        for panel in schema.panels:
            page = pages[panel.page - 1]
            candidates = self._find_candidates(page, panel)
            if not candidates:
                raise PanelDiscoveryError(
                    f"Missing printed column sequence {panel.printed_columns} for panel {panel.panel_id} on page {panel.page}"
                )
            candidates_by_panel[panel.panel_id] = candidates

        anchor = schema.row_anchor_panel
        selected[anchor.panel_id] = max(
            candidates_by_panel[anchor.panel_id],
            key=lambda item: (item.heading_score, item.score, -item.center_y),
        )
        anchor_y_ratio = selected[anchor.panel_id].center_y / pages[anchor.page - 1].height

        for panel in schema.panels:
            if panel.panel_id == anchor.panel_id:
                continue
            options = candidates_by_panel[panel.panel_id]
            # Separate same-page tahsil panels by their unique number ranges. For
            # stacked town statements, corresponding panels occupy the same
            # normalized vertical position on both PDF pages.
            selected[panel.panel_id] = min(
                options,
                key=lambda item: (
                    abs(item.center_y / pages[panel.page - 1].height - anchor_y_ratio)
                    if panel.page != anchor.page
                    else -item.score,
                    -item.heading_score,
                    -item.score,
                ),
            )

        result: list[PanelGeometry] = []
        for panel in schema.panels:
            page = pages[panel.page - 1]
            candidate = selected[panel.panel_id]
            all_header_ys = sorted(
                {
                    option.center_y
                    for definition in schema.panels
                    if definition.page == panel.page
                    for option in candidates_by_panel[definition.panel_id]
                }
            )
            geometry = self._build_geometry(page, schema, panel, candidate, all_header_ys)
            result.append(geometry)
        return result

    def _find_candidates(self, page: RenderedPage, panel: PanelDefinition) -> list[_Candidate]:
        tokens: list[NumberToken] = []
        for word in page.pdf_words:
            value = self._parse_number(str(word["text"]))
            if value is not None and value in panel.printed_columns:
                tokens.append(NumberToken(value, str(word["text"]), tuple(word["bbox"])))
        if not tokens:
            return []

        tolerance = max(14, round(page.dpi * 0.065))
        groups: list[list[NumberToken]] = []
        for token in sorted(tokens, key=lambda item: item.center_y):
            for group in groups:
                if abs(token.center_y - median(item.center_y for item in group)) <= tolerance:
                    group.append(token)
                    break
            else:
                groups.append([token])

        candidates: list[_Candidate] = []
        for group in groups:
            ordered = sorted(group, key=lambda item: item.center_x)
            # One value per physical x position; noisy text layers sometimes
            # duplicate a glyph in adjacent blocks.
            deduplicated: list[NumberToken] = []
            for token in ordered:
                if deduplicated and abs(token.center_x - deduplicated[-1].center_x) < 8:
                    continue
                deduplicated.append(token)
            observed = [item.value for item in deduplicated]
            score = self.printed_number_match(panel.printed_columns, observed)
            center_y = median(item.center_y for item in deduplicated)
            heading_score = self._heading_score(page, panel, center_y)
            accepted_partial = score >= 0.55 or (score >= 0.35 and heading_score >= 0.45)
            if score < self.min_sequence_score and not accepted_partial:
                continue
            candidates.append(_Candidate(deduplicated, score, heading_score))
        return candidates

    @staticmethod
    def _parse_number(text: str) -> int | None:
        cleaned = re.sub(r"^[^0-9]+|[^0-9]+$", "", text.strip())
        if not cleaned or len(cleaned) > 2:
            return None
        value = int(cleaned)
        return value if 1 <= value <= 50 else None

    @staticmethod
    def printed_number_match(expected: list[int], observed: list[int]) -> float:
        """Ordered LCS coverage, penalizing reversed or unrelated number lines."""
        if not expected or not observed:
            return 0.0
        rows = len(expected) + 1
        cols = len(observed) + 1
        table = [[0] * cols for _ in range(rows)]
        for i, target in enumerate(expected, start=1):
            for j, actual in enumerate(observed, start=1):
                table[i][j] = (
                    table[i - 1][j - 1] + 1
                    if target == actual
                    else max(table[i - 1][j], table[i][j - 1])
                )
        coverage = table[-1][-1] / len(expected)
        monotonic = sum(a < b for a, b in zip(observed, observed[1:], strict=False)) / max(
            1, len(observed) - 1
        )
        return round(coverage * (0.85 + 0.15 * monotonic), 4)

    @staticmethod
    def _heading_score(page: RenderedPage, panel: PanelDefinition, center_y: float) -> float:
        words = [
            str(word["text"]).casefold()
            for word in page.pdf_words
            if center_y - page.dpi * 2.0 <= (word["bbox"][1] + word["bbox"][3]) / 2 < center_y
        ]
        context = " ".join(words)
        if not panel.headings:
            return 0.0
        scores: list[float] = []
        for heading in panel.headings:
            parts = [part for part in re.findall(r"[a-z0-9]+", heading.casefold()) if len(part) > 1]
            if parts:
                scores.append(sum(part in context for part in parts) / len(parts))
        return sum(scores) / len(scores) if scores else 0.0

    def _build_geometry(
        self,
        page: RenderedPage,
        schema: TableSchema,
        panel: PanelDefinition,
        candidate: _Candidate,
        header_ys: list[float],
    ) -> PanelGeometry:
        tokens_by_value = self._align_tokens(panel.printed_columns, candidate.tokens)
        known_indices = [
            index for index, value in enumerate(panel.printed_columns) if value in tokens_by_value
        ]
        if len(known_indices) < 2:
            raise PanelDiscoveryError(f"Too few grounded column numbers for panel {panel.panel_id}")
        centers: list[float | None] = [
            tokens_by_value[value].center_x if value in tokens_by_value else None
            for value in panel.printed_columns
        ]
        self._interpolate_centers(centers)
        resolved = [float(value) for value in centers if value is not None]
        if len(resolved) != len(panel.printed_columns) or any(
            left >= right for left, right in zip(resolved, resolved[1:], strict=False)
        ):
            raise PanelDiscoveryError(
                f"Unresolved or non-monotonic column centres for panel {panel.panel_id}"
            )

        gaps = [right - left for left, right in zip(resolved, resolved[1:], strict=False)]
        left_edge = max(0, int(resolved[0] - (gaps[0] if gaps else 30) / 2))
        right_edge = min(page.width, int(resolved[-1] + (gaps[-1] if gaps else 30) / 2))
        boundaries = [left_edge]
        boundaries.extend(
            int((left + right) / 2) for left, right in zip(resolved, resolved[1:], strict=False)
        )
        boundaries.append(right_edge)

        header_top = min(token.bbox[1] for token in candidate.tokens)
        header_bottom = max(token.bbox[3] for token in candidate.tokens)
        body_top = min(page.height, header_bottom + max(5, page.dpi // 60))
        later_headers = [
            value for value in header_ys if value > candidate.center_y + page.dpi * 0.3
        ]
        body_bottom = (
            int(later_headers[0] - page.dpi * 0.35)
            if later_headers
            else self._content_bottom(page, body_top)
        )
        next_title = self._next_section_title(page, body_top)
        if next_title is not None:
            body_bottom = min(body_bottom, next_title - max(4, page.dpi // 30))
        if body_bottom <= body_top:
            raise PanelDiscoveryError(f"Empty body for panel {panel.panel_id}")

        columns: list[ColumnSpan] = []
        table_width = max(1, right_edge - left_edge)
        for index, number in enumerate(panel.printed_columns):
            column = schema.get_column_by_no(number)
            if column is None:
                raise PanelDiscoveryError(
                    f"Panel {panel.panel_id} references undefined logical column {number}"
                )
            x_start, x_end = boundaries[index], boundaries[index + 1]
            columns.append(
                ColumnSpan(
                    column_no=number,
                    column_name=column.column_name,
                    variable=column.variable,
                    x_start=x_start,
                    x_end=x_end,
                    relative_start=(x_start - left_edge) / table_width,
                    relative_end=(x_end - left_edge) / table_width,
                )
            )
        return PanelGeometry(
            definition=panel,
            page_number=page.page_number,
            table_bbox=(left_edge, header_top, right_edge, body_bottom),
            header_bbox=(left_edge, header_top, right_edge, header_bottom),
            body_bbox=(left_edge, body_top, right_edge, body_bottom),
            columns=columns,
            matched_numbers=sorted(tokens_by_value),
            sequence_score=candidate.score,
        )

    @staticmethod
    def _align_tokens(expected: list[int], tokens: list[NumberToken]) -> dict[int, NumberToken]:
        """LCS backtracking prevents duplicate OCR digits from crossing columns."""
        ordered = sorted(tokens, key=lambda token: token.center_x)
        rows, cols = len(expected) + 1, len(ordered) + 1
        table = [[0] * cols for _ in range(rows)]
        for i, target in enumerate(expected, start=1):
            for j, token in enumerate(ordered, start=1):
                if target == token.value:
                    table[i][j] = table[i - 1][j - 1] + 1
                else:
                    table[i][j] = max(table[i - 1][j], table[i][j - 1])
        assignments: dict[int, NumberToken] = {}
        i, j = len(expected), len(ordered)
        while i and j:
            if expected[i - 1] == ordered[j - 1].value:
                assignments[expected[i - 1]] = ordered[j - 1]
                i -= 1
                j -= 1
            elif table[i - 1][j] >= table[i][j - 1]:
                i -= 1
            else:
                j -= 1
        return assignments

    @staticmethod
    def _interpolate_centers(values: list[float | None]) -> None:
        known = [index for index, value in enumerate(values) if value is not None]
        for index in range(len(values)):
            if values[index] is not None:
                continue
            left = max((item for item in known if item < index), default=None)
            right = min((item for item in known if item > index), default=None)
            if left is not None and right is not None:
                left_value, right_value = values[left], values[right]
                assert left_value is not None and right_value is not None
                step = (right_value - left_value) / (right - left)
                values[index] = left_value + step * (index - left)
            elif left is not None and len(known) >= 2:
                previous = max(item for item in known if item < left)
                left_value, previous_value = values[left], values[previous]
                assert left_value is not None and previous_value is not None
                values[index] = left_value + (left_value - previous_value) * (index - left) / (
                    left - previous
                )
            elif right is not None and len(known) >= 2:
                following = min(item for item in known if item > right)
                right_value, following_value = values[right], values[following]
                assert right_value is not None and following_value is not None
                values[index] = right_value - (following_value - right_value) * (right - index) / (
                    following - right
                )

    @staticmethod
    def _content_bottom(page: RenderedPage, body_top: int) -> int:
        candidates = []
        footer_y: int | None = None
        for word in page.pdf_words:
            x0, y0, x1, y1 = word["bbox"]
            if y1 <= body_top:
                continue
            normalized = re.sub(r"[^a-z]", "", str(word["text"]).casefold())
            if (
                normalized in {"note", "notes", "source", "footnote"}
                and y0 > body_top + page.dpi * 0.4
            ):
                footer_y = y0 if footer_y is None else min(footer_y, y0)
            candidates.append(y1)
        bottom = min(page.height - max(6, page.dpi // 20), max(candidates, default=page.height))
        if footer_y is not None:
            bottom = min(bottom, footer_y - max(4, page.dpi // 60))
        return max(body_top + 1, int(bottom))

    @staticmethod
    def _next_section_title(page: RenderedPage, body_top: int) -> int | None:
        title_words = {"statement", "directory", "appendix"}
        ys = [
            int(word["bbox"][1])
            for word in page.pdf_words
            if str(word["text"]).casefold().strip(".,:-") in title_words
            and word["bbox"][1] > body_top + page.dpi * 0.35
        ]
        return min(ys) if ys else None
