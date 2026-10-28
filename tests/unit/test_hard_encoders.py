import pytest

from solver_helpers import (
    ONE_SLOT,
    STANDARD_ROOMS,
    TWO_SLOTS,
    check_valid,
    make_problem,
    solve,
    unit,
)
from timetable.application.dto.solve import SolveOptions, SolveStatus
from timetable.domain.entities import Problem, Room
from timetable.infrastructure.solver.builder import build_model, default_hard_encoders
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver


def test_default_encoder_names() -> None:
    names = [e.name for e in default_hard_encoders()]
    assert names == [
        "each_unit_once",
        "room_no_overlap",
        "teacher_no_overlap",
        "class_no_overlap",
        "max_consecutive_periods",
        "fixed_assignments",
    ]


def test_variables_only_for_allowed_rooms_and_periods(sample_problem: Problem) -> None:
    ctx = build_model(sample_problem)
    assert ctx.s
    rooms_of_unit: dict[str, set[str]] = {}
    for unit_id, day, period, room_id in ctx.s:
        assert 0 <= day <= 5
        assert 0 <= period <= 5  # tiết 7, 8 không có biến
        rooms_of_unit.setdefault(unit_id, set()).add(room_id)
    for u in sample_problem.lesson_units:
        if u.required_room_type == "mba":
            assert rooms_of_unit[u.id] == {"G316"}
        if u.required_room_type == "art":
            assert rooms_of_unit[u.id] == {"G313"}
        assert "G311" not in rooms_of_unit[u.id]


def test_sample_with_four_classes_is_feasible_and_valid(sample_problem: Problem) -> None:
    result = solve(sample_problem)
    assert result.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)
    assert result.timetable is not None
    check_valid(sample_problem, result.timetable)

    by_unit = {a.unit_id: a for a in result.timetable.assignments}
    for u in sample_problem.lesson_units:
        room = by_unit[u.id].room_id
        if u.required_room_type == "mba":
            assert room == "G316"
        elif u.required_room_type == "art":
            assert room == "G313"
        else:
            assert room != "G313"  # môn thường (kể cả của lớp Design) không vào phòng vẽ


def test_teacher_cannot_teach_two_units_in_same_slot() -> None:
    units = [unit("U1", "C1", "T1"), unit("U2", "C2", "T1")]
    assert solve(make_problem(units, grid=ONE_SLOT)).status == SolveStatus.INFEASIBLE

    feasible = make_problem(units, grid=TWO_SLOTS)
    result = solve(feasible)
    assert result.timetable is not None
    check_valid(feasible, result.timetable)


def test_class_cannot_have_two_units_in_same_slot() -> None:
    units = [unit("U1", "C1", "T1"), unit("U2", "C1", "T2")]
    assert solve(make_problem(units, grid=ONE_SLOT)).status == SolveStatus.INFEASIBLE

    feasible = make_problem(units, grid=TWO_SLOTS)
    result = solve(feasible)
    assert result.timetable is not None
    check_valid(feasible, result.timetable)


def test_room_cannot_host_two_units_in_same_slot() -> None:
    units = [unit("U1", "C1", "T1"), unit("U2", "C2", "T2")]
    one_room = make_problem(units, rooms=(Room("R1", "R1", 30),), grid=ONE_SLOT)
    assert solve(one_room).status == SolveStatus.INFEASIBLE
    assert solve(make_problem(units, grid=ONE_SLOT)).status in (
        SolveStatus.OPTIMAL,
        SolveStatus.FEASIBLE,
    )


def test_mba_units_share_only_the_mba_room() -> None:
    rooms = (*STANDARD_ROOMS, Room("G316", "G316", 30, "mba", ("standard",)))
    units = [unit("U1", "MBA1", "T1", "mba"), unit("U2", "MBA2", "T2", "mba")]
    assert solve(make_problem(units, rooms=rooms, grid=ONE_SLOT)).status == SolveStatus.INFEASIBLE

    problem = make_problem(units, rooms=rooms, grid=TWO_SLOTS)
    result = solve(problem)
    assert result.timetable is not None
    assert {a.room_id for a in result.timetable.assignments} == {"G316"}
    check_valid(problem, result.timetable)


def test_unit_without_valid_room_is_infeasible() -> None:
    mba_unit = [unit("U1", "MBA1", "T1", "mba")]
    assert solve(make_problem(mba_unit, rooms=STANDARD_ROOMS, grid=TWO_SLOTS)).status == (
        SolveStatus.INFEASIBLE
    )

    too_big = [unit("U1", "C1", "T1")]
    assert solve(make_problem(too_big, grid=TWO_SLOTS, class_size=40)).status == (
        SolveStatus.INFEASIBLE
    )


def test_standard_classes_may_use_the_mba_room() -> None:
    rooms = (Room("G316", "G316", 30, "mba", ("standard",)),)
    units = [unit("U1", "C1", "T1"), unit("U2", "C2", "T2")]
    problem = make_problem(units, rooms=rooms, grid=TWO_SLOTS)
    result = solve(problem)
    assert result.timetable is not None
    assert {a.room_id for a in result.timetable.assignments} == {"G316"}
    check_valid(problem, result.timetable)


@pytest.mark.parametrize("workers", [1, 4])
def test_solver_respects_options(sample_problem: Problem, workers: int) -> None:
    result = CpSatSolver().solve(sample_problem, SolveOptions(time_limit_s=30, num_workers=workers))
    assert result.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)
