"""Physical column span record.

Column detection itself lives in :mod:`panel_detector` because production
columns must be grounded by printed column numbers; proportional estimation is
intentionally unsupported.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class ColumnSpan:
    column_no: int
    column_name: str
    variable: str
    x_start: int
    x_end: int
    relative_start: float
    relative_end: float
