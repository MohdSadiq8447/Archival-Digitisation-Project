"""
Geometric Analysis: Row Segmentation, Column Boundary Estimation, and Continuation Alignment.
"""

from .aligner import ContinuationAligner, MatchedRowPair
from .column_detector import ColumnSpan
from .panel_detector import PanelDetector, PanelDiscoveryError, PanelGeometry
from .row_segmenter import RowCrop, RowSegmenter

__all__ = [
    "RowSegmenter",
    "RowCrop",
    "ColumnSpan",
    "ContinuationAligner",
    "MatchedRowPair",
    "PanelDetector",
    "PanelDiscoveryError",
    "PanelGeometry",
]
