"""Deterministic assignment of explicit Novita 0..1000 boxes to columns."""

from __future__ import annotations

from dataclasses import dataclass

from census_extractor.geometry.column_detector import ColumnSpan
from census_extractor.ocr.client import OCRResult, OCRToken


@dataclass(slots=True)
class ExtractedCell:
    column_no: int
    variable: str
    column_name: str
    raw_value: str
    tokens: list[OCRToken]


class ColumnAssigner:
    @staticmethod
    def scale_bbox_1000(
        bbox: list[float], crop_bbox: tuple[int, int, int, int]
    ) -> tuple[float, float, float, float]:
        if len(bbox) != 4 or not (
            0 <= bbox[0] < bbox[2] <= 1000 and 0 <= bbox[1] < bbox[3] <= 1000
        ):
            raise ValueError(f"Invalid normalized-1000 bounding box: {bbox}")
        x0, y0, x1, y1 = crop_bbox
        width, height = max(1, x1 - x0), max(1, y1 - y0)
        return (
            x0 + bbox[0] / 1000 * width,
            y0 + bbox[1] / 1000 * height,
            x0 + bbox[2] / 1000 * width,
            y0 + bbox[3] / 1000 * height,
        )

    def assign_cells(
        self,
        ocr_result: OCRResult,
        column_spans: list[ColumnSpan],
        row_crop_bbox: tuple[int, int, int, int],
    ) -> list[ExtractedCell]:
        buckets: dict[int, list[tuple[float, OCRToken]]] = {
            span.column_no: [] for span in column_spans
        }
        for token in ocr_result.tokens:
            if token.bbox is None or token.coordinate_system != "normalized_1000":
                continue
            absolute = self.scale_bbox_1000(token.bbox, row_crop_bbox)
            center_x = (absolute[0] + absolute[2]) / 2
            containing = [span for span in column_spans if span.x_start <= center_x <= span.x_end]
            if not containing:
                continue
            buckets[containing[0].column_no].append((absolute[0], token))

        cells: list[ExtractedCell] = []
        for span in column_spans:
            ordered = [
                token for _, token in sorted(buckets[span.column_no], key=lambda item: item[0])
            ]
            cells.append(
                ExtractedCell(
                    column_no=span.column_no,
                    variable=span.variable,
                    column_name=span.column_name,
                    raw_value=" ".join(
                        token.text.strip() for token in ordered if token.text.strip()
                    ),
                    tokens=ordered,
                )
            )
        return cells

    def assign_tokens_to_columns(
        self,
        ocr_result: OCRResult,
        column_spans: list[ColumnSpan],
        row_crop_bbox: tuple[int, int, int, int],
    ) -> dict[str, str]:
        """Compatibility wrapper; it deliberately has no sequential fallback."""
        return {
            cell.variable: cell.raw_value
            for cell in self.assign_cells(ocr_result, column_spans, row_crop_bbox)
        }
