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


@dataclass
class SubRowCrop:
    parent_row_index: int
    subrow_index: int
    page_number: int
    bbox: Tuple[int, int, int, int]
    y_normalized: float
    image_crop: Image.Image
    height_px: int
    width_px: int
    source: str


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

    def segment_parent_rows_from_identity(
        self,
        page: RenderedPage,
        boundary: TableBoundary,
        serial_x_range: Tuple[int, int],
        name_x_range: Tuple[int, int],
    ) -> List[RowCrop]:
        """Build hierarchy parent bands from serial/name baselines rather than data ink."""
        import re
        from statistics import median

        body_x0, body_y0, body_x1, body_y1 = boundary.body_bbox
        identity_x0 = min(serial_x_range[0], name_x_range[0])
        identity_x1 = max(serial_x_range[1], name_x_range[1])
        words = []
        for word in page.pdf_words:
            wx0, wy0, wx1, wy1 = word["bbox"]
            center_x, center_y = (wx0 + wx1) / 2, (wy0 + wy1) / 2
            if not (identity_x0 <= center_x <= identity_x1 and body_y0 <= center_y <= body_y1):
                continue
            words.append((center_y, center_x, word))
        if not words:
            return []
        words.sort(key=lambda item: (item[0], item[1]))
        tolerance = max(4, page.dpi // 60)
        line_groups: List[List[Tuple[float, float, dict]]] = [[words[0]]]
        for item in words[1:]:
            group_center = sum(value[0] for value in line_groups[-1]) / len(line_groups[-1])
            if abs(item[0] - group_center) <= tolerance:
                line_groups[-1].append(item)
            else:
                line_groups.append([item])

        starts: List[float] = []
        stop_center: float | None = None
        heights: List[int] = []
        minimum_new_parent_gap = max(50, page.dpi // 5)
        for group in line_groups:
            center = sum(item[0] for item in group) / len(group)
            ordered = sorted(group, key=lambda item: item[1])
            combined = " ".join(str(item[2]["text"]) for item in ordered).strip()
            serial_text = " ".join(
                str(item[2]["text"])
                for item in ordered
                if serial_x_range[0] <= item[1] <= serial_x_range[1]
            ).strip()
            name_text = " ".join(
                str(item[2]["text"])
                for item in ordered
                if name_x_range[0] <= item[1] <= name_x_range[1]
            ).strip()
            lowered = combined.casefold()
            if re.search(r"\bnotes?\b|\bdenotes?\b|\bmaternity\b", lowered):
                stop_center = center
                break
            if re.search(r"\bsl\.?\s*(?:no\.?)?\b", lowered) and not name_text:
                stop_center = center
                break
            if not name_text or not re.search(r"[A-Za-z]", name_text):
                continue
            letters = re.sub(r"[^A-Za-z]", "", name_text)
            all_upper = bool(letters) and letters == letters.upper()
            has_serial_mark = bool(serial_text)
            large_gap = bool(starts) and center - starts[-1] >= minimum_new_parent_gap
            if not starts or has_serial_mark or all_upper or "urban" in lowered or large_gap:
                starts.append(center)
                heights.extend(int(item[2]["bbox"][3] - item[2]["bbox"][1]) for item in group)

        if not starts:
            return []
        typical_height = median(heights) if heights else max(14, page.dpi / 8)
        top_offset = max(8, round(typical_height * 0.48))
        rows: List[RowCrop] = []
        for index, center in enumerate(starts):
            y0 = max(body_y0, round(center - top_offset))
            next_boundary = starts[index + 1] if index + 1 < len(starts) else stop_center
            y1 = (
                min(body_y1, round(next_boundary - top_offset))
                if next_boundary is not None
                else body_y1
            )
            if y1 <= y0:
                continue
            x0 = max(0, body_x0 - self.crop_padding)
            x1 = min(page.width, body_x1 + self.crop_padding)
            bbox = (x0, y0, x1, y1)
            rows.append(
                RowCrop(
                    row_index=len(rows),
                    page_number=page.page_number,
                    bbox=bbox,
                    y_normalized=(center - body_y0) / max(1, body_y1 - body_y0),
                    image_crop=page.image.crop(bbox),
                    height_px=y1 - y0,
                    width_px=x1 - x0,
                )
            )
        return rows

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

    def segment_subrows(
        self,
        page: RenderedPage,
        parent_row: RowCrop,
        anchor_x_range: Tuple[int, int],
        crop_x_range: Tuple[int, int],
    ) -> List[SubRowCrop]:
        """Find child baselines inside one parent using the hierarchy anchor column."""
        centers = self._subrow_centers_from_embedded_words(
            page, parent_row.bbox, anchor_x_range
        )
        source = "embedded_text"
        if not centers:
            centers = self._subrow_centers_from_raster(page, parent_row.bbox, anchor_x_range)
            source = "raster_projection"
        if not centers:
            centers = [(parent_row.bbox[1] + parent_row.bbox[3]) / 2]
            source = "single_row_fallback"

        parent_y0, parent_y1 = parent_row.bbox[1], parent_row.bbox[3]
        crop_x0 = max(0, crop_x_range[0] - self.crop_padding)
        crop_x1 = min(page.width, crop_x_range[1] + self.crop_padding)
        result: List[SubRowCrop] = []
        for index, center in enumerate(centers):
            if len(centers) == 1:
                y0, y1 = parent_y0, parent_y1
            else:
                distances = []
                if index > 0:
                    distances.append(center - centers[index - 1])
                if index + 1 < len(centers):
                    distances.append(centers[index + 1] - center)
                half_height = max(6, round(min(distances) * 0.44))
                y0 = max(parent_y0, round(center - half_height))
                y1 = min(parent_y1, round(center + half_height))
            if y1 <= y0:
                y1 = min(parent_y1, y0 + max(1, self.min_row_height))
            bbox = (crop_x0, y0, crop_x1, y1)
            result.append(
                SubRowCrop(
                    parent_row_index=parent_row.row_index,
                    subrow_index=index,
                    page_number=page.page_number,
                    bbox=bbox,
                    y_normalized=(center - parent_y0) / max(1, parent_y1 - parent_y0),
                    image_crop=page.image.crop(bbox),
                    height_px=y1 - y0,
                    width_px=crop_x1 - crop_x0,
                    source=source,
                )
            )
        return result

    @staticmethod
    def _subrow_centers_from_embedded_words(
        page: RenderedPage,
        parent_bbox: Tuple[int, int, int, int],
        anchor_x_range: Tuple[int, int],
    ) -> List[float]:
        import re

        _, parent_y0, _, parent_y1 = parent_bbox
        anchor_x0, anchor_x1 = anchor_x_range
        positioned_words: List[Tuple[float, float, str]] = []
        for word in page.pdf_words:
            wx0, wy0, wx1, wy1 = word["bbox"]
            if wx1 < anchor_x0 or wx0 > anchor_x1 or wy1 < parent_y0 or wy0 > parent_y1:
                continue
            if not re.search(r"[A-Za-z0-9]", str(word["text"])):
                continue
            center = (wy0 + wy1) / 2
            if parent_y0 <= center <= parent_y1:
                positioned_words.append((center, (wx0 + wx1) / 2, str(word["text"])))
        if not positioned_words:
            return []
        positioned_words.sort(key=lambda item: (item[0], item[1]))
        tolerance = max(4, page.dpi // 60)
        groups: List[List[Tuple[float, float, str]]] = [[positioned_words[0]]]
        for item in positioned_words[1:]:
            center = item[0]
            group_center = sum(value[0] for value in groups[-1]) / len(groups[-1])
            if abs(center - group_center) <= tolerance:
                groups[-1].append(item)
            else:
                groups.append([item])
        code_pattern = re.compile(
            r"(?:see|nil|[-–—.·…]+|\d+|\*?\s*[^(){}\[\]\s]+\s*[({\[]\s*[^(){}\[\]\s]+\s*[)}\]])",
            re.IGNORECASE,
        )
        candidates: List[float] = []
        for group in groups:
            text = " ".join(value[2] for value in sorted(group, key=lambda value: value[1])).strip()
            if code_pattern.fullmatch(text):
                candidates.append(sum(value[0] for value in group) / len(group))
        if candidates:
            return candidates
        # A populated anchor with no code-like line is a single logical value
        # (for example a cross-reference spill), not evidence for raster splitting.
        return [sum(value[0] for value in groups[0]) / len(groups[0])]

    @staticmethod
    def _subrow_centers_from_raster(
        page: RenderedPage,
        parent_bbox: Tuple[int, int, int, int],
        anchor_x_range: Tuple[int, int],
    ) -> List[float]:
        _, parent_y0, _, parent_y1 = parent_bbox
        anchor_x0, anchor_x1 = anchor_x_range
        inset = max(2, page.dpi // 100)
        x0, x1 = anchor_x0 + inset, anchor_x1 - inset
        if x1 <= x0 or parent_y1 <= parent_y0:
            return []
        raster = page.binary[parent_y0:parent_y1, x0:x1]
        if raster.size == 0:
            return []
        projection = np.sum(raster, axis=1, dtype=np.float64)
        maximum = float(np.max(projection)) if len(projection) else 0.0
        if maximum <= 0:
            return []
        active = projection > maximum * 0.08
        bands: List[Tuple[int, int]] = []
        start: int | None = None
        for y, is_active in enumerate(active):
            if is_active and start is None:
                start = y
            elif not is_active and start is not None:
                bands.append((start, y))
                start = None
        if start is not None:
            bands.append((start, len(active)))
        if not bands:
            return []
        merge_gap = max(2, page.dpi // 150)
        merged: List[Tuple[int, int]] = [bands[0]]
        for start, end in bands[1:]:
            previous_start, previous_end = merged[-1]
            if start <= previous_end + merge_gap:
                merged[-1] = (previous_start, max(previous_end, end))
            else:
                merged.append((start, end))
        minimum_height = max(3, page.dpi // 100)
        return [
            parent_y0 + (start + end) / 2
            for start, end in merged
            if end - start >= minimum_height
        ]

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
