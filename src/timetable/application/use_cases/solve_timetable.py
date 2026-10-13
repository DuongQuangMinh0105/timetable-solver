from dataclasses import dataclass

from timetable.application.dto.solve import SolveOptions, SolveResult, SolveStatus
from timetable.application.ports.solver import SolverPort
from timetable.application.ports.timetable_checker import TimetableChecker
from timetable.domain.entities import Problem
from timetable.domain.validator import Violation


@dataclass(frozen=True, slots=True)
class SolveOutcome:
    """Kết quả của use case: kết quả giải kèm các vi phạm do bộ kiểm tra tìm thấy."""

    result: SolveResult
    violations: tuple[Violation, ...] = ()

    @property
    def ok(self) -> bool:
        """Có lịch và lịch đó không vi phạm ràng buộc cứng nào."""
        has_schedule = self.result.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)
        return has_schedule and not self.violations


class SolveTimetable:
    """Giải bài toán xếp lịch rồi kiểm tra lại kết quả bằng bộ kiểm tra độc lập.

    Bộ kiểm tra là lưới an toàn: nếu mô hình có lỗi, lịch sai sẽ bị phát hiện thay vì được
    trả về như hợp lệ.
    """

    def __init__(self, solver: SolverPort, checker: TimetableChecker) -> None:
        self._solver = solver
        self._checker = checker

    def execute(self, problem: Problem, options: SolveOptions | None = None) -> SolveOutcome:
        result = self._solver.solve(problem, options or SolveOptions())
        if result.timetable is None:
            return SolveOutcome(result=result)
        violations = self._checker(problem, result.timetable)
        return SolveOutcome(result=result, violations=tuple(violations))
