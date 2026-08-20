"""Novita DeepSeek OCR 2 integration."""

from .client import DeepSeekOCRClient, NovitaDeepSeekOCRClient, OCRResult, OCRToken
from .column_assigner import ColumnAssigner, ExtractedCell
from .prompts import (
    FREE_OCR_PROMPT,
    GROUNDING_PROMPT,
    build_cell_free_ocr_prompt,
    build_page_grounding_prompt,
    build_row_grounding_prompt,
)

__all__ = [
    "DeepSeekOCRClient",
    "NovitaDeepSeekOCRClient",
    "OCRResult",
    "OCRToken",
    "GROUNDING_PROMPT",
    "FREE_OCR_PROMPT",
    "build_row_grounding_prompt",
    "build_page_grounding_prompt",
    "build_cell_free_ocr_prompt",
    "ColumnAssigner",
    "ExtractedCell",
]
