from pathlib import Path

from timetable.application.ports.excel_exporter import ExcelExporter
from timetable.domain.entities import Problem, Timetable


class ExportExcel:
    def __init__(self, exporter: ExcelExporter) -> None:
        self._exporter = exporter

    def execute(self, problem: Problem, timetable: Timetable, path: Path) -> None:
        self._exporter.export(problem, timetable, path)
