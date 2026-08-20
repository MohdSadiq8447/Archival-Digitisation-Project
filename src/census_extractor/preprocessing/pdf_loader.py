"""
High-Performance PDF Loader and Image Renderer with High-DPI Support, Fast Deskewing, and Preprocessing.
"""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image

try:
    import pymupdf as fitz  # pyright: ignore[reportMissingImports]
except ImportError:  # PyMuPDF 1.23 compatibility
    import fitz  # type: ignore[no-redef]


@dataclass
class RenderedPage:
    page_number: int  # 1-indexed
    dpi: int
    image: Image.Image
    np_image: np.ndarray  # RGB uint8 array (H, W, 3)
    grayscale: np.ndarray  # Grayscale uint8 array (H, W)
    binary: np.ndarray  # Inverted binary (0: background, 255: foreground)
    pdf_text: str
    pdf_words: List[Dict[str, Any]]  # [{text, bbox: (x0, y0, x1, y1)}] in image pixel space
    width: int
    height: int
    skew_angle: float = 0.0


class PDFLoader:
    def __init__(self, target_dpi: int = 300, auto_deskew: bool = True):
        self.target_dpi = target_dpi
        self.auto_deskew = auto_deskew

    def render_pdf(self, pdf_path: Path) -> List[RenderedPage]:
        """Renders all pages of a PDF to high-resolution RenderedPage objects."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        doc = fitz.open(pdf_path)
        rendered_pages: List[RenderedPage] = []

        scale = self.target_dpi / 72.0
        matrix = fitz.Matrix(scale, scale)

        for page_idx in range(doc.page_count):
            page = doc.load_page(page_idx)
            pix = page.get_pixmap(matrix=matrix, alpha=False)  # pyright: ignore[reportAttributeAccessIssue]
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

            # Fast C-optimized grayscale conversion via PIL
            gray_img = img.convert("L")
            gray = np.array(gray_img)

            # Fast Otsu binarization
            thresh = self._compute_otsu_threshold(gray)
            binary = (gray < thresh).astype(np.uint8) * 255

            skew_angle = 0.0
            if self.auto_deskew:
                skew_angle = self._estimate_skew_angle(binary)
                if abs(skew_angle) >= 0.25:
                    # Rotate images to correct skew
                    img = img.rotate(
                        -skew_angle,
                        resample=Image.Resampling.BICUBIC,
                        expand=False,
                        fillcolor=(255, 255, 255),
                    )
                    gray_img = img.convert("L")
                    gray = np.array(gray_img)
                    binary = (gray < thresh).astype(np.uint8) * 255

            np_img = np.array(img)

            # Extract native PDF words and keep them synchronized with any
            # deskew rotation applied to the raster.
            pdf_text = page.get_text("text")  # pyright: ignore[reportAttributeAccessIssue]
            raw_words = page.get_text("words")  # pyright: ignore[reportAttributeAccessIssue]
            scaled_words = []
            for w in raw_words:
                x0, y0, x1, y1, text = w[0] * scale, w[1] * scale, w[2] * scale, w[3] * scale, w[4]
                if abs(skew_angle) >= 0.25:
                    x0, y0, x1, y1 = self._rotate_bbox(
                        (x0, y0, x1, y1),
                        angle_degrees=-skew_angle,
                        center=(img.width / 2.0, img.height / 2.0),
                    )
                scaled_words.append(
                    {
                        "text": text,
                        "bbox": (
                            max(0, int(round(x0))),
                            max(0, int(round(y0))),
                            min(img.width, int(round(x1))),
                            min(img.height, int(round(y1))),
                        ),
                    }
                )

            rendered_pages.append(
                RenderedPage(
                    page_number=page_idx + 1,
                    dpi=self.target_dpi,
                    image=img,
                    np_image=np_img,
                    grayscale=gray,
                    binary=binary,
                    pdf_text=pdf_text,
                    pdf_words=scaled_words,
                    width=img.width,
                    height=img.height,
                    skew_angle=skew_angle,
                )
            )

        doc.close()
        return rendered_pages

    @staticmethod
    def _rotate_bbox(
        bbox: Tuple[float, float, float, float],
        angle_degrees: float,
        center: Tuple[float, float],
    ) -> Tuple[float, float, float, float]:
        """Rotate every bbox corner around the PIL ``expand=False`` centre."""
        x0, y0, x1, y1 = bbox
        cx, cy = center
        radians = math.radians(angle_degrees)
        cosine, sine = math.cos(radians), math.sin(radians)
        points = []
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            dx, dy = x - cx, y - cy
            points.append((cx + dx * cosine - dy * sine, cy + dx * sine + dy * cosine))
        xs, ys = zip(*points, strict=True)
        return min(xs), min(ys), max(xs), max(ys)

    @staticmethod
    def _compute_otsu_threshold(gray: np.ndarray) -> int:
        """Computes optimal global binarization threshold via Otsu's method."""
        hist, _ = np.histogram(gray.ravel(), bins=256, range=(0, 256))
        total = gray.size
        current_max, threshold = 0.0, 128
        sum_total = np.dot(np.arange(256), hist)
        sum_back, weight_back = 0.0, 0

        for i in range(256):
            weight_back += hist[i]
            if weight_back == 0:
                continue
            weight_fore = total - weight_back
            if weight_fore == 0:
                break
            sum_back += i * hist[i]
            mean_back = sum_back / weight_back
            mean_fore = (sum_total - sum_back) / weight_fore
            var_between = weight_back * weight_fore * ((mean_back - mean_fore) ** 2)
            if var_between > current_max:
                current_max = var_between
                threshold = i

        return threshold

    @staticmethod
    def _estimate_skew_angle(binary: np.ndarray) -> float:
        """Estimates rotation skew angle using projection profile variance on downsampled thumbnail."""
        h, w = binary.shape
        # Downsample to small thumbnail (height 400) for instant variance calculation
        scale = min(1.0, 400.0 / max(h, w))
        small_w, small_h = max(10, int(w * scale)), max(10, int(h * scale))
        small_img = Image.fromarray(binary).resize((small_w, small_h), Image.Resampling.NEAREST)

        best_angle = 0.0
        max_variance = 0.0
        # Test angles between -2.0 and +2.0 degrees
        angles = [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]

        for angle in angles:
            if abs(angle) < 1e-4:
                rot_img = small_img
            else:
                rot_img = small_img.rotate(
                    angle, resample=Image.Resampling.NEAREST, expand=False, fillcolor=0
                )

            rot_arr = np.array(rot_img)
            hpp = np.sum(rot_arr, axis=1, dtype=np.float64)
            var = float(np.var(hpp))
            if var > max_variance:
                max_variance = var
                best_angle = float(angle)

        return best_angle
