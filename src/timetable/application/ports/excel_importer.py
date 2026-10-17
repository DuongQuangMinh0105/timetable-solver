from pathlib import Path
from typing import Protocol

from timetable.domain.entities import Problem


class ExcelImportError(ValueError):
    """File Excel không đọc được hoặc dữ liệu sai; thông báo nêu sheet và dòng."""


class ExcelImporter(Protocol):
    """Đọc file Excel và dựng `Problem`. Hiện thực: openpyxl."""

    def load(self, path: Path) -> Problem: ...
