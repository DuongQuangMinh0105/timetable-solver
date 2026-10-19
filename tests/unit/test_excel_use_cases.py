from pathlib import Path

from timetable.application.use_cases.export_excel import ExportExcel
from timetable.application.use_cases.import_excel import ImportExcel
from timetable.domain.entities import Assignment, Problem, TimeGrid, Timetable


def _problem() -> Problem:
    return Problem((), (), (), (), (), TimeGrid(days=6, periods=8, allowed_periods=(0, 1)))


class _FakeImporter:
    def __init__(self, problem: Problem) -> None:
        self.problem = problem
        self.paths: list[Path] = []

    def load(self, path: Path) -> Problem:
        self.paths.append(path)
        return self.problem


class _FakeExporter:
    def __init__(self) -> None:
        self.calls: list[tuple[Problem, Timetable, Path]] = []

    def export(self, problem: Problem, timetable: Timetable, path: Path) -> None:
        self.calls.append((problem, timetable, path))


def test_import_excel_returns_what_the_importer_loads() -> None:
    problem = _problem()
    importer = _FakeImporter(problem)

    assert ImportExcel(importer).execute(Path("in.xlsx")) is problem
    assert importer.paths == [Path("in.xlsx")]


def test_export_excel_passes_everything_to_the_exporter() -> None:
    problem = _problem()
    timetable = Timetable((Assignment("u1", 0, 0, "R1"),))
    exporter = _FakeExporter()

    ExportExcel(exporter).execute(problem, timetable, Path("out.xlsx"))

    assert exporter.calls == [(problem, timetable, Path("out.xlsx"))]
