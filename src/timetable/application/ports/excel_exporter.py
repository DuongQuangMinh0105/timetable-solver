from pathlib import Path
from typing import Protocol

from timetable.domain.entities import Problem, Timetable


class ExcelExportError(ValueError):
    """Không xuất được file Excel (ví dụ lịch tham chiếu đơn vị học không có trong bài toán)."""


class ExcelExporter(Protocol):
    """Ghi thời khóa biểu ra file Excel. Hiện thực: openpyxl."""

    def export(self, problem: Problem, timetable: Timetable, path: Path) -> None: ...
