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
    source: str = "raster_projection"
    alignment_confidence: float = 1.0
    interpolated: bool = False


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
        source = "raster_projection"
        if not valid_bands:
            valid_bands = self._bands_from_embedded_words(page, (x0, y_body_top, x1, y_body_bottom))
            source = "embedded_text"
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
                    source=source,
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
        """Build logical parent bands from serial/name baselines for every format."""
        import re
        from statistics import median

        body_x0, body_y0, body_x1, body_y1 = boundary.body_bbox
        identity_x0 = min(serial_x_range[0], name_x_range[0])
        identity_x1 = max(serial_x_range[1], name_x_range[1])
        words: List[Tuple[float, float, dict]] = []
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

        starts: List[Tuple[float, float]] = []
        content_bottoms: List[float] = []
        stop_y: float | None = None
        heights: List[int] = []
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
            normalized = " ".join(re.findall(r"[a-z0-9]+", lowered))
            if re.search(
                r"\bnotes?\b|\bdenotes?\b|\bsource\b|\bbanking\b|"
                r"\bcultural\s+facilit|\bco\s*mmunications?\b|\bcommunications?\b|"
                r"\bpower\s+supply\b|\bamenities\b|\btrade\b|\bindustr(?:y|ial)\b|"
                r"\bmaternity\b|\bnot\s+available\b|\bn\s+a\b.*\bnot\s+ava|"
                r"\bfigures?\s+(?:indicate|relate)\b|"
                r"\bpsup\b|\bbooks?\b",
                normalized,
            ):
                stop_y = min(float(item[2]["bbox"][1]) for item in group)
                break
            if re.search(
                r"\bsl\.?\s*(?:no\.?)?\b|\bname\s+of\s+(?:town|tahsil)\b",
                lowered,
            ):
                stop_y = min(float(item[2]["bbox"][1]) for item in group)
                break
            identity_text = name_text or combined
            if not re.search(r"[A-Za-z]", identity_text):
                continue
            letters = re.sub(r"[^A-Za-z]", "", identity_text)
            all_upper = bool(letters) and letters == letters.upper()
            serial_mark = bool(serial_text.strip())
            identity_heading = bool(
                re.search(
                    r"\bdistrict\s+total\b|\burban\s+agglomeration\b",
                    combined,
                    re.I,
                )
                or (all_upper and len(letters) >= 6)
            )
            large_gap = bool(starts) and center - starts[-1][1] >= max(50, page.dpi // 5)
            if not starts or serial_mark or identity_heading or large_gap:
                line_top = min(float(item[2]["bbox"][1]) for item in group)
                starts.append((line_top, center))
                content_bottoms.append(max(float(item[2]["bbox"][3]) for item in group))
                heights.extend(int(item[2]["bbox"][3] - item[2]["bbox"][1]) for item in group)
            elif starts:
                content_bottoms[-1] = max(
                    content_bottoms[-1],
                    max(float(item[2]["bbox"][3]) for item in group),
                )

        if not starts:
            return []
        typical_height = median(heights) if heights else max(14, page.dpi / 8)
        top_offset = max(8, round(typical_height * 0.48))
        rows: List[RowCrop] = []
        for index, (_, center) in enumerate(starts):
            y0 = max(body_y0, round(center - top_offset))
            if index + 1 < len(starts):
                y1 = min(body_y1, round(starts[index + 1][1] - top_offset))
            else:
                previous_spacing = center - starts[index - 1][1] if index else top_offset * 4
                tail_lines: List[List[Tuple[float, float]]] = []
                for word in page.pdf_words:
                    wx0, wy0, wx1, wy1 = word["bbox"]
                    word_center_x = (wx0 + wx1) / 2
                    word_center_y = (wy0 + wy1) / 2
                    if not (
                        body_x0 <= word_center_x <= body_x1
                        and center - top_offset <= word_center_y <= body_y1
                    ):
                        continue
                    item = (float(word_center_y), float(wy1))
                    if not tail_lines:
                        tail_lines.append([item])
                    else:
                        line_center = sum(value[0] for value in tail_lines[-1]) / len(
                            tail_lines[-1]
                        )
                        if abs(word_center_y - line_center) <= tolerance:
                            tail_lines[-1].append(item)
                        else:
                            tail_lines.append([item])
                tail_content_bottom = content_bottoms[index]
                previous_line_center = center
                tail_gap_limit = max(page.dpi * 0.16, previous_spacing * 0.75)
                for line in tail_lines:
                    line_center = sum(value[0] for value in line) / len(line)
                    if line_center < center - top_offset:
                        continue
                    if line_center - previous_line_center > tail_gap_limit:
                        break
                    tail_content_bottom = max(
                        tail_content_bottom,
                        max(value[1] for value in line),
                    )
                    previous_line_center = line_center
                natural_bottom = max(
                    tail_content_bottom + max(4, page.dpi // 60),
                    center + max(top_offset * 2, previous_spacing / 2),
                )
                y1 = min(body_y1, round(natural_bottom))
                if stop_y is not None and stop_y - center <= page.dpi * 0.65:
                    y1 = min(body_y1, round(stop_y - top_offset))
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
                    source="identity_columns",
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

    def segment_expected_rows(
        self,
        page: RenderedPage,
        boundary: TableBoundary,
        expected_count: int,
        reference_rows: List[RowCrop] | None = None,
    ) -> List[RowCrop]:
        """Segment a continuation panel into the known parent count using target-page ink."""
        import re
        from statistics import median

        if expected_count <= 0:
            return []
        x0, body_top, x1, body_bottom = boundary.body_bbox
        positioned: List[Tuple[float, float, float, str]] = []
        for word in page.pdf_words:
            wx0, wy0, wx1, wy1 = word["bbox"]
            center_x, center_y = (wx0 + wx1) / 2, (wy0 + wy1) / 2
            if not (x0 <= center_x <= x1 and body_top <= center_y <= body_bottom):
                continue
            positioned.append((center_y, float(wy0), float(wy1), str(word["text"])))

        tolerance = max(6, page.dpi // 45)
        groups: List[List[Tuple[float, float, float, str]]] = []
        for item in sorted(positioned, key=lambda value: value[0]):
            if not groups:
                groups.append([item])
                continue
            group_center = sum(value[0] for value in groups[-1]) / len(groups[-1])
            if abs(item[0] - group_center) <= tolerance:
                groups[-1].append(item)
            else:
                groups.append([item])

        line_bands: List[Tuple[float, float, float]] = []
        rejected = re.compile(
            r"\b(?:statement|directory|appendix|banking|communications?|amenities|"
            r"cultural\s+facilit|power\s+supply|trade|industry|industrial|notes?|"
            r"source|denotes?|psup|books?|post\s+office|telegraph|telephone|"
            r"number\s+of\s+villages|name\s+of\s+tahsil)\b|"
            r"\bco\s*mmunications?\b",
            re.IGNORECASE,
        )
        for group in groups:
            text = " ".join(value[3] for value in group).strip()
            if not text or rejected.search(text):
                continue
            if not re.search(r"[A-Za-z0-9]|\.{2,}|[-–—]", text):
                continue
            normalized = re.sub(r"[^A-Za-z]", "", text)
            if normalized and len(normalized) <= 2 and not re.search(r"\d|\.{2,}|[-–—]", text):
                continue
            top = min(value[1] for value in group)
            bottom = max(value[2] for value in group)
            line_bands.append(((top + bottom) / 2, top, bottom))

        if not line_bands:
            raster_rows = self.segment_rows(page, boundary)
            line_bands = [
                ((row.bbox[1] + row.bbox[3]) / 2, float(row.bbox[1]), float(row.bbox[3]))
                for row in raster_rows
            ]
        if not line_bands:
            step = (body_bottom - body_top) / expected_count
            line_bands = [
                (body_top + (index + 0.5) * step, body_top + index * step, body_top + (index + 1) * step)
                for index in range(expected_count)
            ]

        line_bands.sort()
        embedded_candidates = list(line_bands)
        merge_distance = max(18, page.dpi // 16)
        merged: List[List[Tuple[float, float, float]]] = []
        for band in line_bands:
            if merged and band[0] - median(value[0] for value in merged[-1]) <= merge_distance:
                merged[-1].append(band)
            else:
                merged.append([band])
        line_bands = [
            (
                median(value[0] for value in group),
                min(value[1] for value in group),
                max(value[2] for value in group),
            )
            for group in merged
        ]

        raster_rows = self.segment_rows(page, boundary)
        raster_bands: List[Tuple[float, float, float]] = []
        section_text = re.compile(
            r"\b(?:statement|directory|appendix|banking|communications?|amenities|"
            r"cultural\s+facilit|power\s+supply|trade|industry|industrial|notes?|"
            r"source|denotes?|psup|books?)\b",
            re.IGNORECASE,
        )
        for row in raster_rows:
            row_words = [
                str(word["text"])
                for word in page.pdf_words
                if row.bbox[0] <= (word["bbox"][0] + word["bbox"][2]) / 2 <= row.bbox[2]
                and row.bbox[1] <= (word["bbox"][1] + word["bbox"][3]) / 2 <= row.bbox[3]
            ]
            row_text = " ".join(row_words).strip()
            normalized_row = " ".join(re.findall(r"[a-z0-9]+", row_text.casefold()))
            if section_text.search(normalized_row) or re.fullmatch(
                r"[ivxlcdm]+", normalized_row
            ):
                continue
            raster_bands.append(
                (
                    (row.bbox[1] + row.bbox[3]) / 2,
                    float(row.bbox[1]),
                    float(row.bbox[3]),
                )
            )
        while len(raster_bands) < expected_count:
            split_candidates: List[Tuple[float, int, float, List[float]]] = []
            for band_index, band in enumerate(raster_bands):
                centers = sorted(
                    candidate[0]
                    for candidate in embedded_candidates
                    if band[1] <= candidate[0] <= band[2]
                )
                if len(centers) < 2:
                    continue
                band_center = (band[1] + band[2]) / 2
                gaps = [
                    (right - left, (left + right) / 2)
                    for left, right in zip(centers, centers[1:], strict=False)
                    if right - left >= max(12, page.dpi // 30)
                ]
                if not gaps:
                    continue
                gap, split_y = min(
                    gaps,
                    key=lambda item: (abs(item[1] - band_center), -item[0]),
                )
                split_candidates.append((band[2] - band[1] + gap, band_index, split_y, centers))
            if not split_candidates:
                break
            _, band_index, split_y, centers = max(split_candidates, key=lambda item: item[0])
            _, top, bottom = raster_bands[band_index]
            left_centers = [value for value in centers if value < split_y]
            right_centers = [value for value in centers if value > split_y]
            if not left_centers or not right_centers:
                break
            raster_bands[band_index : band_index + 1] = [
                (median(left_centers), top, split_y),
                (median(right_centers), split_y, bottom),
            ]
        use_raster_bands = (
            max(1, round(expected_count * 0.6))
            <= len(raster_bands)
            <= expected_count
        )
        if use_raster_bands:
            line_bands = raster_bands

        target_first, target_last = line_bands[0][0], line_bands[-1][0]
        if reference_rows and len(reference_rows) == expected_count and expected_count > 1:
            reference_marks = [float((row.bbox[1] + row.bbox[3]) / 2) for row in reference_rows]
            reference_span = max(1.0, reference_marks[-1] - reference_marks[0])
            predicted = [
                target_first
                + (mark - reference_marks[0]) / reference_span * (target_last - target_first)
                for mark in reference_marks
            ]
        elif expected_count == 1:
            predicted = [(target_first + target_last) / 2]
        else:
            predicted = [
                target_first + index / (expected_count - 1) * (target_last - target_first)
                for index in range(expected_count)
            ]

        assignments: List[List[Tuple[float, float, float]]] = [[] for _ in predicted]
        if use_raster_bands:
            observed = [band[0] for band in line_bands]
            observed_count = len(observed)
            expected_slots = len(predicted)
            infinity = float("inf")
            costs = [
                [infinity] * (expected_slots + 1)
                for _ in range(observed_count + 1)
            ]
            choices = [
                [False] * (expected_slots + 1)
                for _ in range(observed_count + 1)
            ]
            for slot in range(expected_slots + 1):
                costs[0][slot] = 0.0
            for item in range(1, observed_count + 1):
                for slot in range(1, expected_slots + 1):
                    skip_cost = costs[item][slot - 1]
                    assign_cost = costs[item - 1][slot - 1] + (
                        observed[item - 1] - predicted[slot - 1]
                    ) ** 2
                    if assign_cost <= skip_cost:
                        costs[item][slot] = assign_cost
                        choices[item][slot] = True
                    else:
                        costs[item][slot] = skip_cost
            item, slot = observed_count, expected_slots
            matches: List[Tuple[int, int]] = []
            while item > 0 and slot > 0:
                if choices[item][slot]:
                    matches.append((item - 1, slot - 1))
                    item -= 1
                slot -= 1
            for observed_index, expected_index in reversed(matches):
                assignments[expected_index].append(line_bands[observed_index])
                predicted[expected_index] = line_bands[observed_index][0]
        else:
            for _ in range(3):
                assignments = [[] for _ in predicted]
                for band in line_bands:
                    index = min(range(len(predicted)), key=lambda item: abs(predicted[item] - band[0]))
                    assignments[index].append(band)
                updated = list(predicted)
                for index, values in enumerate(assignments):
                    if values:
                        updated[index] = median(value[0] for value in values)
                predicted = [
                    max(body_top, min(body_bottom, value)) for value in updated
                ]
                for index in range(1, len(predicted)):
                    if predicted[index] <= predicted[index - 1]:
                        predicted[index] = predicted[index - 1] + 1

        boundaries: List[float] = [float(body_top)]
        boundaries.extend(
            (left + right) / 2 for left, right in zip(predicted, predicted[1:], strict=False)
        )
        if len(predicted) > 1:
            tail_half_spacing = max(
                self.min_row_height / 2,
                (predicted[-1] - predicted[-2]) / 2,
            )
        else:
            tail_half_spacing = float(self.min_row_height)
        last_content_bottom = max(
            (value[2] for value in assignments[-1]),
            default=predicted[-1],
        )
        detected_bottom = max(
            predicted[-1] + tail_half_spacing,
            last_content_bottom + max(4, page.dpi // 60),
        )
        minimum_bottom = boundaries[-1] + self.min_row_height
        effective_bottom = min(float(body_bottom), max(minimum_bottom, detected_bottom))
        boundaries.append(effective_bottom)
        rows: List[RowCrop] = []
        for index, center in enumerate(predicted):
            y0 = max(body_top, round(boundaries[index]))
            y1 = min(body_bottom, round(boundaries[index + 1]))
            if y1 <= y0:
                y1 = min(body_bottom, y0 + self.min_row_height)
            values = assignments[index]
            interpolated = not values
            if values:
                local_spacing = max(1.0, y1 - y0)
                distance = abs(median(value[0] for value in values) - center)
                confidence = max(0.55, min(1.0, 1.0 - distance / local_spacing))
                source = "raster_expected" if use_raster_bands else "embedded_text_expected"
            else:
                confidence = 0.65 if 0 < index < len(predicted) - 1 else 0.4
                source = "local_interpolation"
            crop_x0 = max(0, x0 - self.crop_padding)
            crop_x1 = min(page.width, x1 + self.crop_padding)
            bbox = (crop_x0, y0, crop_x1, y1)
            rows.append(
                RowCrop(
                    row_index=index,
                    page_number=page.page_number,
                    bbox=bbox,
                    y_normalized=(center - body_top) / max(1, body_bottom - body_top),
                    image_crop=page.image.crop(bbox),
                    height_px=y1 - y0,
                    width_px=crop_x1 - crop_x0,
                    source=source,
                    alignment_confidence=round(confidence, 4),
                    interpolated=interpolated,
                )
            )
        return rows

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
