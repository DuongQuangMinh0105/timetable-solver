import pytest

from solver_helpers import (
    OPTIONS,
    check_valid,
    make_problem,
    one_day_grid,
    solve,
    unit,
)
from timetable.application.dto.solve import SolveStatus
from timetable.domain.entities import LessonUnit, Problem
from timetable.domain.services.timetable_checker import longest_run
from timetable.infrastructure.solver.builder import build_model, default_hard_encoders
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.infrastructure.solver.encoder import ModelContext


def three_units_one_class() -> list[LessonUnit]:
    return [unit("U1", "C1", "T1"), unit("U2", "C1", "T2"), unit("U3", "C1", "T3")]


def test_longest_run_helper() -> None:
    assert longest_run([0, 1, 4, 5]) == 2
    assert longest_run([1, 2, 3]) == 3
    assert longest_run([2]) == 1
    assert longest_run([]) == 0


@pytest.mark.parametrize("periods", [(1, 2, 3), (2, 3, 4)])
def test_three_consecutive_periods_are_forbidden(periods: tuple[int, ...]) -> None:
    problem = make_problem(three_units_one_class(), grid=one_day_grid(*periods))
    assert solve(problem).status == SolveStatus.INFEASIBLE


def test_lunch_break_does_not_split_a_run() -> None:
    # Tiết 2,3,4 bị cấm dù giữa tiết 3 và 4 có nghỉ trưa
    problem = make_problem(three_units_one_class(), grid=one_day_grid(2, 3, 4))
    assert solve(problem).status == SolveStatus.INFEASIBLE


@pytest.mark.parametrize("periods", [(2, 3), (3, 4), (1, 2)])
def test_two_consecutive_periods_are_valid(periods: tuple[int, ...]) -> None:
    units = [unit("U1", "C1", "T1"), unit("U2", "C1", "T2")]
    problem = make_problem(units, grid=one_day_grid(*periods))
    result = solve(problem)
    assert result.timetable is not None
    check_valid(problem, result.timetable)


def test_two_blocks_with_a_gap_are_valid() -> None:
    # Tiết 1,2 rồi nghỉ, sau đó tiết 5,6
    units = [unit(f"U{i}", "C1", f"T{i}") for i in range(4)]
    problem = make_problem(units, grid=one_day_grid(1, 2, 5, 6))
    result = solve(problem)
    assert result.timetable is not None
    check_valid(problem, result.timetable)
    assert sorted(a.period for a in result.timetable.assignments) == [0, 1, 4, 5]


def test_four_units_in_one_run_of_four_is_forbidden() -> None:
    units = [unit(f"U{i}", "C1", f"T{i}") for i in range(4)]
    assert solve(make_problem(units, grid=one_day_grid(1, 2, 3, 4))).status == (
        SolveStatus.INFEASIBLE
    )


def test_teachers_have_no_consecutive_limit() -> None:
    # Một giáo viên dạy 3 tiết liền ở 3 lớp khác nhau vẫn hợp lệ
    units = [unit("U1", "C1", "T1"), unit("U2", "C2", "T1"), unit("U3", "C3", "T1")]
    problem = make_problem(units, grid=one_day_grid(1, 2, 3))
    result = solve(problem)
    assert result.timetable is not None
    check_valid(problem, result.timetable)
    assert sorted(a.period for a in result.timetable.assignments) == [0, 1, 2]


def test_limit_is_configurable() -> None:
    problem = make_problem(three_units_one_class(), grid=one_day_grid(1, 2, 3), max_consecutive=3)
    result = solve(problem)
    assert result.timetable is not None
    check_valid(problem, result.timetable)


def test_forbidden_period_breaks_the_run() -> None:
    # Tiết 3 bị cấm: các tiết 2 và 4 không liền nhau nên 3 đơn vị ở tiết 1,2,4 hợp lệ
    problem = make_problem(three_units_one_class(), grid=one_day_grid(1, 2, 4))
    result = solve(problem)
    assert result.timetable is not None
    check_valid(problem, result.timetable)


def test_encoder_adds_constraints_to_the_model() -> None:
    problem = make_problem(three_units_one_class(), grid=one_day_grid(1, 2, 3))
    without = build_model(problem, default_hard_encoders()[:-1])
    with_rule = build_model(problem)
    assert len(with_rule.model.proto.constraints) > len(without.model.proto.constraints)


def test_sample_never_exceeds_two_consecutive_periods(sample_problem: Problem) -> None:
    result = solve(sample_problem)
    assert result.timetable is not None
    check_valid(sample_problem, result.timetable)


class SaturdayPenalty:
    """Ví dụ ràng buộc mềm (P2 sẽ viết bản thật): phạt mỗi tiết xếp vào Thứ 7."""

    name = "avoid_saturday_example"

    def encode(self, ctx: ModelContext) -> None:
        for (_u, day, _p, _r), var in ctx.s.items():
            if ctx.problem.grid.is_saturday(day):
                ctx.penalties.append((10, var))


class MinimizePenalties:
    """Ví dụ ObjectiveApplier: tối thiểu hóa tổng trọng số * biến phạt."""

    def apply(self, ctx: ModelContext) -> None:
        ctx.model.minimize(sum(w * v for w, v in ctx.penalties))


def test_soft_encoder_and_objective_hooks(sample_problem: Problem) -> None:
    solver = CpSatSolver(soft_encoders=[SaturdayPenalty()], objective=MinimizePenalties())
    result = solver.solve(sample_problem, OPTIONS)
    assert result.status == SolveStatus.OPTIMAL
    assert result.objective == 0
    assert result.timetable is not None
    assert all(a.day != 5 for a in result.timetable.assignments)
    check_valid(sample_problem, result.timetable)
