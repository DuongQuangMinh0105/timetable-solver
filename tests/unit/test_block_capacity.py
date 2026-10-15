import random

from solver_helpers import OPTIONS, make_problem, one_day_grid
from timetable.application.dto.solve import SolveStatus
from timetable.domain.entities import Course, Problem, TimeGrid
from timetable.domain.services.block_capacity import (
    class_capacity_issues,
    class_fits,
    day_patterns,
)
from timetable.domain.services.unit_splitter import lesson_units_for_course
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver

ALIGNED = (0, 2, 4)


def _empty(days: int = 6, block_starts: tuple[int, ...] | None = ALIGNED) -> Problem:
    grid = TimeGrid(days=days, periods=8, allowed_periods=(0, 1, 2, 3, 4, 5))
    return Problem((), (), (), (), (), grid, 2, block_starts)


def test_day_patterns_with_aligned_blocks() -> None:
    # Một ngày tối đa 4 tiết: 2 block 2 tiết; hoặc 1 block 2 tiết + 2 block 1 tiết; hoặc 4 block 1.
    assert day_patterns(_empty()) == {
        (0, 0),
        (0, 1),
        (0, 2),
        (0, 3),
        (0, 4),
        (1, 0),
        (1, 1),
        (1, 2),
        (2, 0),
    }


def test_two_blocks_back_to_back_are_not_a_pattern() -> None:
    assert (2, 1) not in day_patterns(_empty())
    assert (3, 0) not in day_patterns(_empty())


def test_max_three_period_courses_per_class_is_eight() -> None:
    problem = _empty()
    assert class_fits(problem, 8, 8)  # 8 môn 3 tiết = 24 tiết, kín cả tuần
    assert not class_fits(problem, 9, 9)


def test_class_capacity_issue_for_overfull_class() -> None:
    courses = tuple(Course(f"M{i}", "m", "C", f"T{i}", 3) for i in range(9))
    units = tuple(u for c in courses for u in lesson_units_for_course(c))
    problem = _empty()
    problem = Problem((), (), (), courses, units, problem.grid, 2, ALIGNED)
    issues = class_capacity_issues(problem)
    assert [i.code for i in issues] == ["class_capacity"]
    assert "C" in issues[0].message


def test_no_issue_when_class_fits() -> None:
    courses = tuple(Course(f"M{i}", "m", "C", f"T{i}", 3) for i in range(8))
    units = tuple(u for c in courses for u in lesson_units_for_course(c))
    problem = Problem((), (), (), courses, units, _empty().grid, 2, ALIGNED)
    assert class_capacity_issues(problem) == []


def test_single_day_limits() -> None:
    problem = _empty(days=1)
    assert class_fits(problem, 1, 2)  # 2 + 1 + 1 = 4 tiết
    assert not class_fits(problem, 1, 3)
    assert not class_fits(problem, 3, 0)


def test_three_period_course_is_feasible_on_one_day_with_gap() -> None:
    """Môn 3 tiết = block 2 + block 1; cùng ngày được miễn không thành 3 tiết liền."""
    units = list(lesson_units_for_course(Course("M", "m", "C", "T", 3)))
    problem = make_problem(units, grid=one_day_grid(1, 2, 3, 4, 5, 6), block_starts=ALIGNED)
    assert CpSatSolver().solve(problem, OPTIONS).status in (
        SolveStatus.OPTIMAL,
        SolveStatus.FEASIBLE,
    )


def test_formula_matches_solver_for_a_single_class() -> None:
    """Một lớp, mỗi môn một giáo viên, đủ phòng: solver có nghiệm khi và chỉ khi `class_fits`."""
    for seed in range(30):
        r = random.Random(seed)
        days = r.choice([1, 2, 3, 6])
        grid = TimeGrid(days=days, periods=8, allowed_periods=(0, 1, 2, 3, 4, 5))
        courses = [
            Course(f"M{i}", "m", "C", f"T{i}", r.choice([1, 2, 3, 3, 4, 5]))
            for i in range(r.randint(1, 8))
        ]
        units = [u for c in courses for u in lesson_units_for_course(c)]
        problem = make_problem(units, grid=grid, block_starts=ALIGNED)
        twos = sum(u.duration == 2 for u in units)
        predicted = class_fits(problem, twos, len(units) - twos)
        status = CpSatSolver().solve(problem, OPTIONS).status
        solved = status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)
        assert solved == predicted, (seed, days, [c.periods_per_week for c in courses])
