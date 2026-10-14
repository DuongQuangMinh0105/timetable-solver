import json
from dataclasses import replace

from conftest import SAMPLE_PATH
from solver_helpers import OPTIONS, make_problem, one_day_grid, unit
from timetable.application.dto.solve import SolveResult, SolveStatus
from timetable.application.use_cases.solve_timetable import SolveTimetable
from timetable.domain.entities import Assignment, Problem, Timetable
from timetable.domain.services.timetable_checker import check_timetable
from timetable.domain.violation import Violation
from timetable.infrastructure.problem_loader import (
    problem_from_dict,
    solve_options_from_dict,
)
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver

SIX = one_day_grid(1, 2, 3, 4, 5, 6)


def _rules(problem: Problem, assignments: list[Assignment]) -> set[str]:
    return {v.rule_id for v in check_timetable(problem, Timetable(tuple(assignments)))}


def test_use_case_solves_and_checks_sample(sample_problem: Problem) -> None:
    outcome = SolveTimetable(CpSatSolver(), check_timetable).execute(sample_problem, OPTIONS)
    assert outcome.ok
    assert outcome.result.timetable is not None
    assert len(outcome.result.timetable.assignments) == len(sample_problem.lesson_units)


def test_use_case_reports_infeasible_without_checking() -> None:
    units = [unit("a", "C", "T1"), unit("b", "C", "T2")]
    problem = make_problem(units)  # 2 đơn vị cùng lớp, chỉ 1 ô
    outcome = SolveTimetable(CpSatSolver(), check_timetable).execute(problem, OPTIONS)
    assert outcome.result.status is SolveStatus.INFEASIBLE
    assert not outcome.ok
    assert outcome.violations == ()


def test_use_case_surfaces_checker_violations(sample_problem: Problem) -> None:
    def always_bad(_p: Problem, _t: Timetable) -> list[Violation]:
        return [Violation("X", "lỗi giả")]

    outcome = SolveTimetable(CpSatSolver(), always_bad).execute(sample_problem, OPTIONS)
    assert not outcome.ok
    assert [v.rule_id for v in outcome.violations] == ["X"]


def test_use_case_with_fake_solver_without_timetable(sample_problem: Problem) -> None:
    class FakeSolver:
        def solve(self, problem: Problem, options: object) -> SolveResult:
            return SolveResult(status=SolveStatus.UNKNOWN)

    outcome = SolveTimetable(FakeSolver(), check_timetable).execute(sample_problem)
    assert outcome.result.status is SolveStatus.UNKNOWN
    assert not outcome.ok


def test_checker_accepts_valid_blocks() -> None:
    units = [unit("a", "C", "T1", duration=2), unit("b", "C", "T2", duration=2)]
    problem = make_problem(units, grid=SIX, block_starts=(0, 2, 4))
    assert not _rules(problem, [Assignment("a", 0, 0, "R1"), Assignment("b", 0, 4, "R1")])


def test_checker_flags_four_consecutive_periods() -> None:
    units = [unit("a", "C", "T1", duration=2), unit("b", "C", "T2", duration=2)]
    problem = make_problem(units, grid=SIX, block_starts=(0, 2, 4))
    rules = _rules(problem, [Assignment("a", 0, 0, "R1"), Assignment("b", 0, 2, "R2")])
    assert rules == {"MAX_CONSECUTIVE"}


def test_checker_flags_overlap_of_occupied_periods() -> None:
    units = [unit("a", "C1", "T", duration=2), unit("b", "C2", "T", duration=1)]
    problem = make_problem(units, grid=SIX)
    rules = _rules(problem, [Assignment("a", 0, 0, "R1"), Assignment("b", 0, 1, "R2")])
    assert rules == {"TEACHER_OVERLAP"}


def test_checker_flags_misaligned_block_and_missing_unit() -> None:
    units = [unit("a", "C", "T1", duration=2), unit("b", "C", "T2")]
    problem = make_problem(units, grid=SIX, block_starts=(0, 2, 4))
    rules = _rules(problem, [Assignment("a", 0, 1, "R1")])
    assert rules == {"INVALID_SLOT", "UNIT_UNASSIGNED"}


def test_checker_flags_room_capacity_and_unknown_reference() -> None:
    problem = make_problem([unit("a", "C", "T")], grid=SIX, class_size=50)
    rules = _rules(problem, [Assignment("a", 0, 0, "R1"), Assignment("zzz", 0, 1, "R1")])
    assert rules == {"ROOM_CAPACITY", "UNKNOWN_REFERENCE"}


def test_loader_splits_courses_when_no_lesson_units() -> None:
    data = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    data["lesson_units"] = []
    data["constraints"]["block_starts"] = [0, 2, 4]
    problem = problem_from_dict(data)
    assert problem.block_starts == (0, 2, 4)
    by_course: dict[str, list[int]] = {}
    for u in problem.lesson_units:
        by_course.setdefault(u.course_id, []).append(u.duration)
    for course in problem.courses:
        assert sum(by_course[course.id]) == course.periods_per_week
        assert max(by_course[course.id]) <= 2


def test_loader_solves_split_sample() -> None:
    data = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    data["lesson_units"] = []
    data["constraints"]["block_starts"] = [0, 2, 4]
    problem = problem_from_dict(data)
    outcome = SolveTimetable(CpSatSolver(), check_timetable).execute(problem, OPTIONS)
    assert outcome.ok, outcome.violations


def test_solve_options_from_dict() -> None:
    assert solve_options_from_dict({"solver": {"time_limit_s": 5, "random_seed": 7}}) == replace(
        solve_options_from_dict({}), time_limit_s=5, random_seed=7
    )
