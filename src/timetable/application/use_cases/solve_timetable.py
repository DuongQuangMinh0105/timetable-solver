from collections.abc import Callable
from dataclasses import dataclass

from timetable.application.dto.diagnosis_report import DiagnosisReport
from timetable.application.dto.solve import SolveOptions, SolveResult, SolveStatus
from timetable.application.ports.solver import SolverPort
from timetable.application.ports.timetable_checker import TimetableChecker
from timetable.application.use_cases.describe_conflicts import describe_conflict_groups
from timetable.domain.entities import Problem
from timetable.domain.services.precheck import Issue
from timetable.domain.violation import Violation

ProblemPrecheck = Callable[[Problem], list[Issue]]


@dataclass(frozen=True, slots=True)
class SolveOutcome:
    """Kết quả của use case: kết quả giải kèm các vi phạm do bộ kiểm tra tìm thấy."""

    result: SolveResult
    violations: tuple[Violation, ...] = ()
    # Chỉ có khi vô nghiệm: lý do (từ kiểm tra nhanh hoặc từ lõi vô nghiệm của solver).
    diagnosis: DiagnosisReport | None = None

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

    def __init__(
        self,
        solver: SolverPort,
        checker: TimetableChecker,
        precheck: ProblemPrecheck | None = None,
    ) -> None:
        self._solver = solver
        self._checker = checker
        self._precheck = precheck

    def execute(self, problem: Problem, options: SolveOptions | None = None) -> SolveOutcome:
        if self._precheck is not None:
            issues = self._precheck(problem)
            if issues:
                # Điều kiện cần không thỏa nên chắc chắn vô nghiệm: khỏi gọi solver.
                return SolveOutcome(
                    result=SolveResult(status=SolveStatus.INFEASIBLE),
                    diagnosis=DiagnosisReport(issues=tuple(issues), source="precheck"),
                )
        result = self._solver.solve(problem, options or SolveOptions())
        if result.timetable is None:
            diagnosis = None
            if result.status == SolveStatus.INFEASIBLE and result.conflict_groups:
                diagnosis = describe_conflict_groups(result.conflict_groups)
            return SolveOutcome(result=result, diagnosis=diagnosis)
        violations = self._checker(problem, result.timetable)
        return SolveOutcome(result=result, violations=tuple(violations))
