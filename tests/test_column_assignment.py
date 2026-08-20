from __future__ import annotations

import pytest

from census_extractor.geometry.column_detector import ColumnSpan
from census_extractor.ocr.client import OCRResult, OCRToken
from census_extractor.ocr.column_assigner import ColumnAssigner


def spans():
    return [
        ColumnSpan(1, "Serial", "sl_no", 100, 200, 0, 0.2),
        ColumnSpan(2, "Name", "town_name", 200, 600, 0.2, 1),
    ]


def test_scale_1000_and_assignment():
    result = OCRResult(
        0,
        1,
        "",
        tokens=[
            OCRToken("1", [0, 0, 190, 900]),
            OCRToken("Agra", [250, 0, 600, 900]),
            OCRToken("(M.C.)", [610, 0, 900, 900]),
        ],
    )
    values = ColumnAssigner().assign_tokens_to_columns(result, spans(), (100, 10, 600, 50))
    assert values == {"sl_no": "1", "town_name": "Agra (M.C.)"}


def test_invalid_coordinate_system_has_no_sequential_fallback():
    result = OCRResult(0, 1, "", tokens=[OCRToken("invented", None)])
    assert ColumnAssigner().assign_tokens_to_columns(result, spans(), (100, 10, 600, 50)) == {
        "sl_no": "",
        "town_name": "",
    }
    with pytest.raises(ValueError, match="Invalid"):
        ColumnAssigner.scale_bbox_1000([0, 0, 1001, 20], (0, 0, 100, 100))
