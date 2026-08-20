"""
Visual Debug Overlays for Table Boundaries, Rows, Columns, and Continuation Match Lines.
"""

from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw

from census_extractor.geometry.aligner import MatchedRowPair
from census_extractor.geometry.column_detector import ColumnSpan
from census_extractor.geometry.row_segmenter import RowCrop
from census_extractor.preprocessing.boundary_detector import TableBoundary
from census_extractor.preprocessing.pdf_loader import RenderedPage


class TableVisualizer:
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir

    def draw_page_segmentation(
        self,
        page: RenderedPage,
        boundary: TableBoundary,
        row_crops: List[RowCrop],
        column_spans: List[ColumnSpan],
        save_path: Optional[Path] = None,
    ) -> Image.Image:
        """Draws bounding boxes for table, header, columns, and rows on page image."""
        img = page.image.copy()
        draw = ImageDraw.Draw(img)

        # 1. Draw Table Bounding Box in Green
        tx0, ty0, tx1, ty1 = boundary.table_bbox
        draw.rectangle([tx0, ty0, tx1, ty1], outline="green", width=4)

        # 2. Draw Header Bounding Box in Blue
        hx0, hy0, hx1, hy1 = boundary.header_bbox
        draw.rectangle([hx0, hy0, hx1, hy1], outline="blue", width=3)

        # 3. Draw Column Vertical Lines in Cyan
        for col in column_spans:
            draw.line([(col.x_start, ty0), (col.x_start, ty1)], fill="cyan", width=2)
            draw.line([(col.x_end, ty0), (col.x_end, ty1)], fill="cyan", width=2)

        # 4. Draw Row Bounding Boxes in Red / Orange
        for row in row_crops:
            rx0, ry0, rx1, ry1 = row.bbox
            draw.rectangle([rx0, ry0, rx1, ry1], outline="red", width=2)

        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(save_path)

        return img

    def draw_continuation_alignment(
        self,
        page1: RenderedPage,
        page2: RenderedPage,
        matched_pairs: List[MatchedRowPair],
        save_path: Optional[Path] = None,
    ) -> Image.Image:
        """Draws side-by-side comparison of facing pages with matching alignment lines."""
        # Create side-by-side composite canvas
        w1, h1 = page1.image.size
        w2, h2 = page2.image.size
        total_w = w1 + w2 + 50
        max_h = max(h1, h2)

        canvas = Image.new("RGB", (total_w, max_h), color=(240, 240, 240))
        canvas.paste(page1.image, (0, 0))
        canvas.paste(page2.image, (w1 + 50, 0))

        draw = ImageDraw.Draw(canvas)
        p2_offset_x = w1 + 50

        # Draw matching lines between aligned rows
        for pair in matched_pairs:
            a_row = pair.anchor_row
            c_row = pair.continuation_row

            # Anchor right edge
            a_x = a_row.bbox[2]
            a_y = (a_row.bbox[1] + a_row.bbox[3]) // 2

            # Draw anchor box
            draw.rectangle(a_row.bbox, outline="red", width=2)

            if c_row:
                # Continuation left edge
                c_x = p2_offset_x + c_row.bbox[0]
                c_y = (c_row.bbox[1] + c_row.bbox[3]) // 2

                # Draw continuation box
                c_bbox = (
                    p2_offset_x + c_row.bbox[0],
                    c_row.bbox[1],
                    p2_offset_x + c_row.bbox[2],
                    c_row.bbox[3],
                )
                draw.rectangle(c_bbox, outline="blue", width=2)

                # Connecting line (Green if aligned, Yellow if large distance)
                line_color = "green" if pair.is_aligned else "orange"
                draw.line([(a_x, a_y), (c_x, c_y)], fill=line_color, width=3)

        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(save_path)

        return canvas
