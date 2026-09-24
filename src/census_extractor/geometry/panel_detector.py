"""Printed-column driven discovery of physical table panels."""

from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import median

import numpy as np

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
    body_end_source: str = "page_content"


@dataclass(frozen=True, slots=True)
class DetectedNote:
    page_number: int
    panel_id: str
    bbox: tuple[int, int, int, int]
    text: str
    detection_source: str = "embedded_text"


@dataclass(slots=True)
class _Candidate:
    tokens: list[NumberToken]
    score: float
    heading_score: float
    page_number: int
    discovery_source: str = "embedded_text"

    @property
    def center_y(self) -> float:
        return median(token.center_y for token in self.tokens)

    @property
    def horizontal_span(self) -> float:
        centers = sorted(token.center_x for token in self.tokens)
        return centers[-1] - centers[0] if len(centers) > 1 else 0.0

    @property
    def grid_score(self) -> float:
        centers = sorted(token.center_x for token in self.tokens)
        gaps = [right - left for left, right in zip(centers, centers[1:], strict=False)]
        if not gaps or median(gaps) <= 0:
            return 0.0
        return min(gaps) / median(gaps)

    @property
    def header_likeness(self) -> float:
        widths = [max(1, token.bbox[2] - token.bbox[0]) for token in self.tokens]
        return self.horizontal_span * self.grid_score / max(1.0, median(widths))


class PanelDetector:
    """Locates header number rows and derives physical column centres from them."""

    def __init__(self, min_sequence_score: float = 0.62):
        self.min_sequence_score = min_sequence_score

    def discover(self, pages: list[RenderedPage], schema: TableSchema) -> list[PanelGeometry]:
        if not pages:
            raise PanelDiscoveryError(f"No rendered pages supplied for {schema.format_id}")

        selected: dict[str, _Candidate] = {}
        candidates_by_panel: dict[str, list[_Candidate]] = {}
        for panel in schema.panels:
            # A schema page is the normal layout, not a hard physical-page constraint.
            # Several handbooks stack two statements on one page or swap the medical
            # and power/water Tahsil panels. Search the complete trimmed source and let
            # printed column order plus heading evidence identify the physical panel.
            candidates = [
                candidate
                for page in pages
                for candidate in (
                    self._find_candidates(page, panel)
                    + self._find_raster_candidates(page, panel)
                )
            ]
            if not candidates:
                raise PanelDiscoveryError(
                    f"Missing printed column sequence {panel.printed_columns} for panel "
                    f"{panel.panel_id} on all {len(pages)} physical pages"
                )
            candidates_by_panel[panel.panel_id] = candidates

        anchor = schema.row_anchor_panel
        anchor_options = candidates_by_panel[anchor.panel_id]
        nominal_options = [
            item for item in anchor_options if item.page_number == anchor.page
        ]
        anchor_options = nominal_options or anchor_options
        heading_options = [item for item in anchor_options if item.heading_score > 0]
        anchor_pool = heading_options or anchor_options
        trusted_sources = {
            "embedded_text",
            "embedded_text_raster_prefix",
            "raster_number_row_inferred",
        }
        trusted_options = [
            item for item in anchor_pool if item.discovery_source in trusted_sources
        ]
        if trusted_options:
            anchor_pool = trusted_options
            selected[anchor.panel_id] = max(
                anchor_pool,
                key=lambda item: (
                    item.page_number == anchor.page,
                    item.heading_score,
                    -item.center_y,
                    item.score,
                    item.header_likeness,
                ),
            )
        else:
            selected[anchor.panel_id] = max(
                anchor_pool,
                key=lambda item: (
                    item.page_number == anchor.page,
                    item.heading_score,
                    item.header_likeness,
                    item.score,
                    -item.center_y,
                ),
            )
        anchor_candidate = selected[anchor.panel_id]
        anchor_y_ratio = (
            anchor_candidate.center_y / pages[anchor_candidate.page_number - 1].height
        )

        for panel in schema.panels:
            if panel.panel_id == anchor.panel_id:
                continue
            options = candidates_by_panel[panel.panel_id]
            # Printed sequences usually make the choice unique. Heading evidence is
            # authoritative when a page contains multiple statements (for example,
            # Muzaffarnagar Municipal Finance above Civic Amenities). Normalized row
            # position is a tie-breaker for ordinary two-page continuation layouts.
            selected[panel.panel_id] = max(
                options,
                key=lambda item: (
                    item.discovery_source == "embedded_text",
                    item.heading_score,
                    item.score,
                    item.page_number == panel.page,
                    -abs(
                        item.center_y / pages[item.page_number - 1].height - anchor_y_ratio
                    ),
                ),
            )

        result: list[PanelGeometry] = []
        for panel in schema.panels:
            candidate = selected[panel.panel_id]
            page = pages[candidate.page_number - 1]
            all_header_ys = sorted(
                {
                    option.center_y
                    for definition in schema.panels
                    for option in candidates_by_panel[definition.panel_id]
                    if option.page_number == candidate.page_number
                }
            )
            geometry = self._build_geometry(page, schema, panel, candidate, all_header_ys)
            geometry.discovery_source = candidate.discovery_source
            result.append(geometry)
        self._clamp_to_selected_panels(result)
        return result

    @staticmethod
    def _clamp_to_selected_panels(panels: list[PanelGeometry]) -> None:
        """Use the next selected same-page panel as an authoritative table boundary."""
        by_page: dict[int, list[PanelGeometry]] = {}
        for panel in panels:
            by_page.setdefault(panel.page_number, []).append(panel)
        for page_panels in by_page.values():
            ordered = sorted(page_panels, key=lambda item: item.header_bbox[1])
            for current, following in zip(ordered, ordered[1:], strict=False):
                padding = max(4, round((current.header_bbox[3] - current.header_bbox[1]) * 0.08))
                bottom = following.header_bbox[1] - padding
                if current.body_bbox[1] < bottom < current.body_bbox[3]:
                    current.body_bbox = (*current.body_bbox[:3], bottom)
                    current.table_bbox = (*current.table_bbox[:3], bottom)
                    current.body_end_source = f"next_panel:{following.definition.panel_id}"

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
            ordered = self._augment_fuzzy_header_tokens(page, panel, group, tolerance)
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
            candidate = _Candidate(deduplicated, score, heading_score, page.page_number)
            candidates.append(candidate)
            raster_prefix = self._augment_embedded_header_with_raster_prefix(
                page, panel, candidate
            )
            if raster_prefix is not None:
                candidates.append(raster_prefix)
        return candidates

    @staticmethod
    def _augment_embedded_header_with_raster_prefix(
        page: RenderedPage,
        panel: PanelDefinition,
        candidate: _Candidate,
    ) -> _Candidate | None:
        """Ground missing identity ordinals from pixels beside an embedded suffix.

        Degraded pages often retain columns 3..N in the native text layer but lose
        the small printed ``1`` and ``2``. Raster glyphs on that exact baseline are
        safer than extrapolating an irregular town-name column or accepting a later
        data row as a complete number grid.
        """
        observed = [token.value for token in candidate.tokens]
        expected = panel.printed_columns
        if not observed or observed[-1] != expected[-1] or observed[0] not in expected:
            return None
        missing_count = expected.index(observed[0])
        expected_suffix = expected[missing_count:]
        if (
            missing_count not in {1, 2, 3}
            or any(value not in expected_suffix for value in observed)
            or observed != sorted(observed, key=expected_suffix.index)
        ):
            return None
        known_centers = [token.center_x for token in candidate.tokens]
        known_gaps = [
            right - left
            for left, right in zip(known_centers, known_centers[1:], strict=False)
        ]
        typical_gap = median(known_gaps) if known_gaps else page.width * 0.08
        y0 = max(0, min(token.bbox[1] for token in candidate.tokens) - 4)
        y1 = min(page.height, max(token.bbox[3] for token in candidate.tokens) + 4)
        dark = np.asarray(page.image.crop((0, y0, page.width, y1)).convert("L")) < 165
        runs = PanelDetector._projection_runs(dark.sum(axis=0) >= 2)
        runs = PanelDetector._merge_runs(runs, max(5, round(page.dpi * 0.05)))
        runs = [
            run
            for run in runs
            if 2 <= run[1] - run[0] + 1 <= max(45, round(page.dpi * 0.16))
            and (run[0] + run[1]) / 2 < known_centers[0] - typical_gap * 0.25
        ]
        if not runs:
            return None
        # A damaged ``1`` can be split into two close raster components. Combine
        # components much closer than the ordinary header-column spacing.
        clustered: list[tuple[int, int]] = []
        for run in runs:
            center = (run[0] + run[1]) / 2
            previous_center = (
                (clustered[-1][0] + clustered[-1][1]) / 2 if clustered else None
            )
            if (
                previous_center is not None
                and center - previous_center < typical_gap * 0.45
            ):
                clustered[-1] = (clustered[-1][0], run[1])
            else:
                clustered.append(run)
        if len(clustered) == missing_count - 1 and missing_count == 2:
            last_center = (clustered[-1][0] + clustered[-1][1]) / 2
            if known_centers[0] - last_center >= typical_gap * 1.35:
                inferred_center = round((last_center + known_centers[0]) / 2)
                inferred_half_width = max(
                    2,
                    round(
                        median(token.bbox[2] - token.bbox[0] for token in candidate.tokens)
                        / 2
                    ),
                )
                clustered.append(
                    (
                        inferred_center - inferred_half_width,
                        inferred_center + inferred_half_width,
                    )
                )
        if len(clustered) < missing_count:
            return None
        prefix_runs = clustered[-missing_count:]
        prefix_tokens = [
            NumberToken(value, str(value), (x0, y0, x1 + 1, y1))
            for value, (x0, x1) in zip(
                expected[:missing_count], prefix_runs, strict=True
            )
        ]
        tokens = prefix_tokens + candidate.tokens
        return _Candidate(
            tokens=tokens,
            score=PanelDetector.printed_number_match(expected, [t.value for t in tokens]),
            heading_score=candidate.heading_score,
            page_number=candidate.page_number,
            discovery_source="embedded_text_raster_prefix",
        )

    def _find_raster_candidates(
        self, page: RenderedPage, panel: PanelDefinition
    ) -> list[_Candidate]:
        """Recover a printed-number row from pixels when the PDF text layer is absent.

        Some handbooks contain a usable text layer for only the upper statement on a
        page. The printed number row remains strong raster evidence: every logical
        column has one compact mark group and the groups are monotonic. We deliberately
        use this only after embedded-text discovery fails for that physical page.
        """
        grayscale = np.asarray(page.image.convert("L"))
        dark = grayscale < 165
        row_projection = dark.sum(axis=1)
        minimum_ink = max(8, round(page.width * 0.003))
        active = row_projection >= minimum_ink
        bands: list[tuple[int, int]] = []
        start: int | None = None
        for y, is_active in enumerate(active):
            if bool(is_active) and start is None:
                start = y
            elif not bool(is_active) and start is not None:
                if 3 <= y - start <= max(70, round(page.dpi * 0.24)):
                    bands.append((start, y - 1))
                start = None
        if start is not None and 3 <= len(active) - start <= max(70, round(page.dpi * 0.24)):
            bands.append((start, len(active) - 1))

        candidates: list[_Candidate] = []
        expected_count = len(panel.printed_columns)
        merge_gaps = sorted(
            {
                max(5, round(page.dpi * ratio))
                for ratio in (0.02, 0.05, 0.09, 0.13, 0.17)
            }
        )
        for y0, y1 in bands:
            x_projection = dark[y0 : y1 + 1].sum(axis=0)
            runs = self._projection_runs(x_projection >= 2)
            heading_score = self._heading_score(page, panel, (y0 + y1) / 2)
            for gap in merge_gaps:
                merged = self._merge_runs(runs, gap)
                merged = [run for run in merged if run[1] - run[0] >= 2]
                selected_runs: list[tuple[int, int]] | None = None
                discovery_source = "raster_number_row"
                if len(merged) == expected_count:
                    selected_runs = merged
                elif len(merged) == expected_count - 1 and heading_score >= 0.45:
                    # A single faint printed number can disappear while the other
                    # ordinals remain a compact, well-spaced row. Infer only that
                    # missing centre from an abnormally large gap. This is notably
                    # different from accepting a complete-looking data row beneath
                    # the same heading (Kheri MedEdu).
                    centers = [(x0 + x1) / 2 for x0, x1 in merged]
                    gaps = [
                        right - left
                        for left, right in zip(centers, centers[1:], strict=False)
                    ]
                    typical_gap = median(gaps) if gaps else 0.0
                    largest_gap = max(gaps, default=0.0)
                    if typical_gap > 0 and largest_gap >= typical_gap * 1.55:
                        missing_after = gaps.index(largest_gap)
                        inferred_center = round(
                            (centers[missing_after] + centers[missing_after + 1]) / 2
                        )
                        inferred_half_width = max(
                            2,
                            round(
                                median(end - start + 1 for start, end in merged) / 2
                            ),
                        )
                        selected_runs = list(merged)
                        selected_runs.insert(
                            missing_after + 1,
                            (
                                inferred_center - inferred_half_width,
                                inferred_center + inferred_half_width,
                            ),
                        )
                        discovery_source = "raster_number_row_inferred"
                elif (
                    panel.printed_columns
                    == list(
                        range(
                            panel.printed_columns[0],
                            panel.printed_columns[0] + expected_count,
                        )
                    )
                    and len(merged) >= max(panel.printed_columns)
                ):
                    # Combined Tahsil pages print columns 1-24 in one number row.
                    # Select the schema panel's ordinal slice from that shared grid.
                    selected_runs = [merged[number - 1] for number in panel.printed_columns]
                if selected_runs is None:
                    continue
                if (
                    selected_runs[-1][1] - selected_runs[0][0]
                    < page.width * 0.45
                ):
                    continue
                widths = [x1 - x0 + 1 for x0, x1 in selected_runs]
                # Number-row glyph groups are compact; this rejects table rules and
                # most prose lines that happen to have the same component count.
                if median(widths) > max(45, page.dpi * 0.16):
                    continue
                tokens = [
                    NumberToken(number, str(number), (x0, y0, x1 + 1, y1 + 1))
                    for number, (x0, x1) in zip(
                        panel.printed_columns, selected_runs, strict=True
                    )
                ]
                candidates.append(
                    _Candidate(
                        tokens=tokens,
                        score=1.0,
                        heading_score=heading_score,
                        page_number=page.page_number,
                        discovery_source=discovery_source,
                    )
                )
                break
        return candidates

    @staticmethod
    def _projection_runs(mask: np.ndarray) -> list[tuple[int, int]]:
        runs: list[tuple[int, int]] = []
        start: int | None = None
        for position, active in enumerate(mask):
            if bool(active) and start is None:
                start = position
            elif not bool(active) and start is not None:
                runs.append((start, position - 1))
                start = None
        if start is not None:
            runs.append((start, len(mask) - 1))
        return runs

    @staticmethod
    def _merge_runs(runs: list[tuple[int, int]], maximum_gap: int) -> list[tuple[int, int]]:
        merged: list[tuple[int, int]] = []
        for start, end in runs:
            if merged and start - merged[-1][1] - 1 <= maximum_gap:
                merged[-1] = (merged[-1][0], end)
            else:
                merged.append((start, end))
        return merged

    @staticmethod
    def _augment_fuzzy_header_tokens(
        page: RenderedPage,
        panel: PanelDefinition,
        known: list[NumberToken],
        tolerance: int,
    ) -> list[NumberToken]:
        """Recover short OCR-confused header numbers by their ordinal position."""
        if len(known) < 2:
            return sorted(known, key=lambda item: item.center_x)
        center_y = median(token.center_y for token in known)
        known_bboxes = {token.bbox for token in known}
        fuzzy: list[tuple[str, tuple[int, int, int, int]]] = []
        for word in page.pdf_words:
            raw_bbox = word["bbox"]
            bbox = (
                int(raw_bbox[0]),
                int(raw_bbox[1]),
                int(raw_bbox[2]),
                int(raw_bbox[3]),
            )
            if bbox in known_bboxes:
                continue
            word_center_y = (bbox[1] + bbox[3]) / 2
            compact = re.sub(r"[^a-z0-9]", "", str(word["text"]).casefold())
            if (
                abs(word_center_y - center_y) <= tolerance
                and compact
                and len(compact) <= 3
            ):
                fuzzy.append((str(word["text"]), bbox))
        items: list[tuple[NumberToken | None, str, tuple[int, int, int, int]]] = [
            (token, token.text, token.bbox) for token in known
        ]
        items.extend((None, text, bbox) for text, bbox in fuzzy)
        items.sort(key=lambda item: (item[2][0] + item[2][2]) / 2)
        expected_indexes = {value: index for index, value in enumerate(panel.printed_columns)}
        offsets = {
            expected_indexes[item[0].value] - index
            for index, item in enumerate(items)
            if item[0] is not None and item[0].value in expected_indexes
        }
        if len(offsets) != 1:
            return sorted(known, key=lambda item: item.center_x)
        offset = offsets.pop()
        recovered = list(known)
        known_values = {token.value for token in known}
        for index, (token, text, bbox) in enumerate(items):
            expected_index = index + offset
            if token is not None or not 0 <= expected_index < len(panel.printed_columns):
                continue
            expected_value = panel.printed_columns[expected_index]
            if (
                expected_value not in known_values
                and expected_value not in set(panel.identity_columns)
            ):
                recovered.append(NumberToken(expected_value, text, bbox))
        return sorted(recovered, key=lambda item: item.center_x)

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
            if center_y - page.dpi * 2.8 <= (word["bbox"][1] + word["bbox"][3]) / 2 < center_y
        ]
        context = " ".join(words)
        if not panel.headings:
            return 0.0
        generic = {"statement", "directory", "appendix", "the", "and", "iv", "v"}
        parts = {
            part
            for heading in panel.headings
            for part in re.findall(r"[a-z0-9]+", heading.casefold())
            if len(part) > 1 and part not in generic
        }
        return sum(part in context for part in parts) / len(parts) if parts else 0.0

    def _build_geometry(
        self,
        page: RenderedPage,
        schema: TableSchema,
        panel: PanelDefinition,
        candidate: _Candidate,
        _header_ys: list[float],
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

        header_top = min(token.bbox[1] for token in candidate.tokens)
        header_bottom = max(token.bbox[3] for token in candidate.tokens)
        body_top = min(page.height, header_bottom + max(5, page.dpi // 60))
        body_bottom = self._content_bottom(page, body_top)
        body_end_source = "page_content"
        next_section = self._next_section_boundary(page, body_top)
        if next_section is not None:
            next_title, next_source = next_section
            next_bottom = next_title - max(4, page.dpi // 30)
            if next_bottom < body_bottom:
                body_bottom = next_bottom
                body_end_source = next_source
        if body_bottom <= body_top:
            raise PanelDiscoveryError(f"Empty body for panel {panel.panel_id}")

        right_edge = self._expand_last_column_edge(
            page, resolved, body_top, body_bottom, right_edge
        )
        boundaries = [left_edge]
        boundaries.extend(
            int((left + right) / 2) for left, right in zip(resolved, resolved[1:], strict=False)
        )
        boundaries.append(right_edge)
        boundaries = self._fit_boundaries_within_table(
            boundaries,
            left_edge=left_edge,
            right_edge=right_edge,
        )

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
        if any(
            span.x_start < left_edge
            or span.x_start >= span.x_end
            or span.x_end > right_edge
            for span in columns
        ):
            raise PanelDiscoveryError(
                f"Invalid column bounds remain for panel {panel.panel_id}"
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
            body_end_source=body_end_source,
        )

    @staticmethod
    def _fit_boundaries_within_table(
        boundaries: list[int], *, left_edge: int, right_edge: int
    ) -> list[int]:
        """Keep extrapolated trailing columns positive and inside the page.

        Some compressed Tahsil statements print a shorter terminal column
        sequence than the common logical schema. Missing trailing number tokens
        are extrapolated by the detector; those estimates can extend beyond the
        physical page. Preserve every grounded prefix boundary and divide the
        remaining visible margin between the inferred logical columns.
        """
        column_count = len(boundaries) - 1
        if column_count < 1 or right_edge - left_edge < column_count:
            raise PanelDiscoveryError("Table is too narrow for positive column spans")

        first_invalid: int | None = None
        previous = left_edge - 1
        for index, boundary in enumerate(boundaries):
            is_terminal = index == column_count
            valid = (
                boundary == right_edge
                if is_terminal
                else left_edge <= boundary < right_edge
            )
            if not valid or boundary <= previous:
                first_invalid = index
                break
            previous = boundary
        if first_invalid is None:
            return boundaries

        prefix_index = max(0, first_invalid - 1)
        prefix = list(boundaries[: prefix_index + 1])
        remaining_columns = column_count - prefix_index
        pivot = prefix[-1]
        if right_edge - pivot < remaining_columns:
            prefix_index = 0
            prefix = [left_edge]
            remaining_columns = column_count
            pivot = left_edge

        available = right_edge - pivot
        suffix = [
            pivot + round(available * step / remaining_columns)
            for step in range(1, remaining_columns + 1)
        ]
        repaired = prefix + suffix
        if (
            len(repaired) != len(boundaries)
            or repaired[0] != left_edge
            or repaired[-1] != right_edge
            or any(
                left >= right
                for left, right in zip(repaired, repaired[1:], strict=False)
            )
        ):
            raise PanelDiscoveryError("Unable to fit column spans inside table bounds")
        return repaired

    @staticmethod
    def _expand_last_column_edge(
        page: RenderedPage,
        centers: list[float],
        body_top: int,
        body_bottom: int,
        current_edge: int,
    ) -> int:
        """Keep wide final-column values inside row crops."""
        if len(centers) < 2:
            return current_edge
        last_gap = centers[-1] - centers[-2]
        last_column_start = (centers[-2] + centers[-1]) / 2
        content_right = [
            int(word["bbox"][2])
            for word in page.pdf_words
            if word["bbox"][1] < body_bottom
            and word["bbox"][3] > body_top
            and word["bbox"][0] >= last_column_start
        ]
        safety_edge = int(centers[-1] + last_gap * 0.65)
        content_edge = max(content_right, default=current_edge) + max(4, page.dpi // 50)
        return min(page.width, max(current_edge, safety_edge, content_edge))

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
        boundary = PanelDetector._next_section_boundary(page, body_top)
        return boundary[0] if boundary is not None else None

    @staticmethod
    def _line_groups(page: RenderedPage, minimum_y: int = 0) -> list[list[dict]]:
        words = [
            word
            for word in page.pdf_words
            if (word["bbox"][1] + word["bbox"][3]) / 2 >= minimum_y
        ]
        if not words:
            return []
        tolerance = max(5, page.dpi // 50)
        groups: list[list[dict]] = []
        for word in sorted(words, key=lambda item: ((item["bbox"][1] + item["bbox"][3]) / 2, item["bbox"][0])):
            center = (word["bbox"][1] + word["bbox"][3]) / 2
            if not groups:
                groups.append([word])
                continue
            previous_center = sum(
                (item["bbox"][1] + item["bbox"][3]) / 2 for item in groups[-1]
            ) / len(groups[-1])
            if abs(center - previous_center) <= tolerance:
                groups[-1].append(word)
            else:
                groups.append([word])
        return groups

    @staticmethod
    def _next_section_boundary(page: RenderedPage, body_top: int) -> tuple[int, str] | None:
        """Find a later table, note, or printer footer from whole-line heading cues."""
        minimum_y = body_top + page.dpi * 0.35
        heading_patterns = (
            (
                r"\b(?:statemen(?:t|r)?|state[a-z0-9]{0,5}ent|directory|appendix)\b",
                "section_title",
            ),
            (r"\bbanking\b", "next_table:banking"),
            (r"\bcultural\s+facilit", "next_table:cultural_facilities"),
            (
                r"\bco\s*mmunications?\b|\bcommunica\s*tions?\b|\bcommunications?\b",
                "next_panel:communications",
            ),
            (r"\bpower\s+supply\b", "next_panel:power_water"),
            (r"\bamenit(?:y|ies)\b", "next_panel:amenities"),
            (r"\btrade\b|\bindustr(?:y|ial)\b", "next_table:trade_industry"),
            (r"\bnotes?\b|\bsource\b|\bdenotes?\b", "note"),
            (
                r"\b(?:dc\s*lotr|denotr|ll?i?clud\w*)\b.*\bmedical\b|"
                r"\b[i1l]\s*iote\b",
                "note",
            ),
            (
                r"\b(?:sl|si|s1)\s*no\b.*\bname\s+of\b",
                "next_table:column_header",
            ),
            (r"\bpsup\b|\bbooks?\b.*\b(?:pp|census)\b", "publication_footer"),
        )
        candidates: list[tuple[int, str]] = []
        for group in PanelDetector._line_groups(page, int(minimum_y)):
            ordered = sorted(group, key=lambda item: item["bbox"][0])
            text = " ".join(str(item["text"]) for item in ordered)
            normalized = " ".join(re.findall(r"[a-z0-9]+", text.casefold()))
            if not normalized:
                continue
            y0 = min(int(item["bbox"][1]) for item in group)
            for pattern, source in heading_patterns:
                if re.search(pattern, normalized):
                    candidates.append((y0, source))
                    break
        return min(candidates, default=None, key=lambda item: item[0])

    @staticmethod
    def capture_notes(
        pages: list[RenderedPage], panels: list[PanelGeometry]
    ) -> list[DetectedNote]:
        """Retain explanatory source notes as metadata without creating data rows."""
        notes: list[DetectedNote] = []
        panels_by_page: dict[int, list[PanelGeometry]] = {}
        for panel in panels:
            panels_by_page.setdefault(panel.page_number, []).append(panel)
        for page in pages:
            page_panels = panels_by_page.get(page.page_number, [])
            for group in PanelDetector._line_groups(page):
                ordered = sorted(group, key=lambda item: item["bbox"][0])
                text = " ".join(str(item["text"]) for item in ordered).strip()
                normalized = " ".join(re.findall(r"[a-z0-9*]+", text.casefold()))
                is_note = bool(
                    re.search(
                        r"(?:^|\s)notes?(?:\s|$)|\bdenotes?\b|"
                        r"\bn\s+a\b.*\bnot\s+ava",
                        normalized,
                    )
                    or re.match(r"^\s*source\s*[:\-–—]", text, re.IGNORECASE)
                    or (
                        re.match(r"^\s*(?:\*|•|�)", text)
                        and re.search(r"maternity\s*&?\s*child\s+welfare", text, re.IGNORECASE)
                    )
                )
                if not is_note:
                    continue
                x0 = min(int(item["bbox"][0]) for item in group)
                y0 = min(int(item["bbox"][1]) for item in group)
                x1 = max(int(item["bbox"][2]) for item in group)
                y1 = max(int(item["bbox"][3]) for item in group)
                candidates = [
                    panel
                    for panel in page_panels
                    if panel.body_bbox[1] <= y0 <= panel.body_bbox[3] + page.dpi * 0.3
                ]
                panel = max(candidates, key=lambda item: item.body_bbox[1], default=None)
                if panel is None:
                    continue
                notes.append(
                    DetectedNote(
                        page_number=page.page_number,
                        panel_id=panel.definition.panel_id,
                        bbox=(x0, y0, x1, y1),
                        text=text,
                    )
                )
        return notes
