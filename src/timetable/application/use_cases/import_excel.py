from pathlib import Path

from timetable.application.ports.excel_importer import ExcelImporter
from timetable.domain.entities import Problem


class ImportExcel:
    def __init__(self, importer: ExcelImporter) -> None:
        self._importer = importer

    def execute(self, path: Path) -> Problem:
        return self._importer.load(path)
