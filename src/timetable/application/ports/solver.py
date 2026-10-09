from typing import Protocol

from timetable.application.dto.solve import SolveOptions, SolveResult
from timetable.domain.entities import Problem


class SolverPort(Protocol):
    """Chạy bộ giải xếp lịch. Hiện thực: OR-Tools CP-SAT."""

    def solve(self, problem: Problem, options: SolveOptions) -> SolveResult: ...
