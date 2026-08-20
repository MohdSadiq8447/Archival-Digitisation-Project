"""
Horizontal Row Segmentation using Image Geometry and Projection Profiles.
Extracts individual row bands without assuming fixed row counts.
"""

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from PIL import Image

from census_extractor.preprocessing.boundary_detector import TableBoundary
from census_extractor.preprocessing.pdf_loader import RenderedPage


@dataclass
class RowCrop:
    row_index: int  # 0-indexed relative to table
    page_number: int
    bbox: Tuple[int, int, int, int]  # (x0, y0, x1, y1) in image space
    y_normalized: float  # Normalized vertical center (0.0 to 1.0 within body)
    image_crop: Image.Image
    height_px: int
    width_px: int


class RowSegmenter:
    def __init__(
        self,
        min_row_height_px: int = 14,
        max_row_height_px: int = 220,
        merge_gap_px: int = 6,
        crop_padding_px: int = 4,
        density_threshold_ratio: float = 0.015,
    ):
        self.min_row_height = min_row_height_px
        self.max_row_height = max_row_height_px
        self.merge_gap = merge_gap_px
        self.crop_padding = crop_padding_px
        self.density_threshold_ratio = density_threshold_ratio

    def segment_rows(self, page: RenderedPage, boundary: TableBoundary) -> List[RowCrop]:
        """Segments the table body into discrete horizontal row crops."""
        x0, y_body_top, x1, y_body_bottom = boundary.body_bbox
        body_height = max(1, y_body_bottom - y_body_top)

        # Slice binary image for table body
        body_binary = page.binary[y_body_top:y_body_bottom, x0:x1]
        if body_binary.size == 0 or body_binary.shape[0] < self.min_row_height:
            return []

        # Calculate Horizontal Projection Profile (HPP)
        hpp = np.sum(body_binary, axis=1, dtype=np.float64)
        if len(hpp) == 0:
            return []

        max_val = np.max(hpp) if np.max(hpp) > 0 else 1.0
        threshold = max_val * self.density_threshold_ratio

        # Identify continuous bands of foreground pixels
        raw_bands: List[Tuple[int, int]] = []
        in_band = False
        band_start = 0

        for y, val in enumerate(hpp):
            if val > threshold:
                if not in_band:
                    in_band = True
                    band_start = y
            else:
                if in_band:
                    in_band = False
                    raw_bands.append((band_start, y))

        if in_band:
            raw_bands.append((band_start, len(hpp)))

        # Merge close bands (multi-line rows or descenders)
        merged_bands = self._merge_close_bands(raw_bands)

        # Filter out tiny noise artifacts and enforce height bounds
        valid_bands = [
            (s, e)
            for s, e in merged_bands
            if (e - s) >= self.min_row_height and (e - s) <= self.max_row_height
        ]
        if not valid_bands:
            valid_bands = self._bands_from_embedded_words(page, (x0, y_body_top, x1, y_body_bottom))
        valid_bands = self._truncate_after_section_gap(valid_bands)

        # Generate RowCrop objects
        row_crops: List[RowCrop] = []
        for idx, (b_start, b_end) in enumerate(valid_bands):
            # Compute absolute pixel bounding box with padding
            abs_y0 = max(0, y_body_top + b_start - self.crop_padding)
            abs_y1 = min(page.height, y_body_top + b_end + self.crop_padding)
            abs_x0 = max(0, x0 - self.crop_padding)
            abs_x1 = min(page.width, x1 + self.crop_padding)

            # Compute normalized vertical center relative to body
            mid_y = (b_start + b_end) / 2.0
            y_norm = float(mid_y / body_height)

            # Crop from high-res image
            crop_img = page.image.crop((abs_x0, abs_y0, abs_x1, abs_y1))

            row_crops.append(
                RowCrop(
                    row_index=idx,
                    page_number=page.page_number,
                    bbox=(abs_x0, abs_y0, abs_x1, abs_y1),
                    y_normalized=y_norm,
                    image_crop=crop_img,
                    height_px=abs_y1 - abs_y0,
                    width_px=abs_x1 - abs_x0,
                )
            )

        return row_crops

    def _bands_from_embedded_words(
        self,
        page: RenderedPage,
        body_bbox: Tuple[int, int, int, int],
    ) -> List[Tuple[int, int]]:
        """Fallback for ruled scans whose vertical lines swamp the projection."""
        import re

        x0, y0, x1, y1 = body_bbox
        bands: List[Tuple[int, int]] = []
        for word in page.pdf_words:
            wx0, wy0, wx1, wy1 = word["bbox"]
            if wx1 < x0 or wx0 > x1 or wy1 < y0 or wy0 > y1:
                continue
            if not re.search(r"[A-Za-z0-9]", str(word["text"])):
                continue
            start, end = max(y0, wy0) - y0, min(y1, wy1) - y0
            if end > start:
                bands.append((start, end))
        if not bands:
            return []
        bands.sort()
        merged: List[Tuple[int, int]] = [bands[0]]
        word_gap = max(8, page.dpi // 35)
        for start, end in bands[1:]:
            previous_start, previous_end = merged[-1]
            if start <= previous_end + word_gap:
                merged[-1] = (previous_start, max(previous_end, end))
            else:
                merged.append((start, end))
        return [
            band
            for band in merged
            if self.min_row_height <= band[1] - band[0] <= self.max_row_height
        ]

    @staticmethod
    def _truncate_after_section_gap(bands: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Stop before notes or a lower table section after a conspicuous gap."""
        if len(bands) < 4:
            return bands
        gaps = [right[0] - left[1] for left, right in zip(bands, bands[1:], strict=False)]
        ordinary = sorted(gap for gap in gaps if gap >= 0)
        typical = ordinary[len(ordinary) // 2] if ordinary else 0
        cutoff = max(150, typical * 4)
        for index, gap in enumerate(gaps):
            if index >= 1 and gap > cutoff:
                return bands[: index + 1]
        return bands

    def project_rows(
        self,
        page: RenderedPage,
        source_rows: List[RowCrop],
        source_body_bbox: Tuple[int, int, int, int],
        target_body_bbox: Tuple[int, int, int, int],
    ) -> List[RowCrop]:
        """Affine row-band projection used when a continuation panel is faint."""
        if not source_rows:
            return []
        source_top, source_bottom = source_body_bbox[1], source_body_bbox[3]
        target_x0, target_top, target_x1, target_bottom = target_body_bbox
        source_height = max(1, source_bottom - source_top)
        target_height = max(1, target_bottom - target_top)
        projected: List[RowCrop] = []
        for index, row in enumerate(source_rows):
            relative_top = (row.bbox[1] - source_top) / source_height
            relative_bottom = (row.bbox[3] - source_top) / source_height
            y0 = max(target_top, round(target_top + relative_top * target_height))
            y1 = min(target_bottom, round(target_top + relative_bottom * target_height))
            if y1 <= y0:
                y1 = min(target_bottom, y0 + self.min_row_height)
            x0 = max(0, target_x0 - self.crop_padding)
            x1 = min(page.width, target_x1 + self.crop_padding)
            crop = page.image.crop((x0, y0, x1, y1))
            projected.append(
                RowCrop(
                    row_index=index,
                    page_number=page.page_number,
                    bbox=(x0, y0, x1, y1),
                    y_normalized=((y0 + y1) / 2 - target_top) / target_height,
                    image_crop=crop,
                    height_px=y1 - y0,
                    width_px=x1 - x0,
                )
            )
        return projected

    def _merge_close_bands(self, bands: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Merges bands that are separated by less than merge_gap_px."""
        if not bands:
            return []

        merged: List[Tuple[int, int]] = []
        cur_start, cur_end = bands[0]

        for s, e in bands[1:]:
            if s - cur_end <= self.merge_gap:
                cur_end = max(cur_end, e)
            else:
                merged.append((cur_start, cur_end))
                cur_start, cur_end = s, e

        merged.append((cur_start, cur_end))
        return merged
