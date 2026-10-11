import pytest

from timetable.application.dto.solve import SolveOptions, SolveResult, SolveStatus
from timetable.domain.entities import (
    ClassGroup,
    Course,
    LessonUnit,
    Problem,
    Room,
    Slot,
    Teacher,
    TimeGrid,
    Timetable,
)
from timetable.infrastructure.solver.builder import build_model, default_hard_encoders
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver

ONE_SLOT = TimeGrid(days=1, periods=1, allowed_periods=(0,), period_times=())
TWO_SLOTS = TimeGrid(days=1, periods=2, allowed_periods=(0, 1), period_times=())
OPTIONS = SolveOptions(time_limit_s=30, num_workers=1)

STANDARD_ROOMS = (Room("R1", "R1", 30), Room("R2", "R2", 30))


def unit(uid: str, cls: str, teacher: str, room_type: str = "standard") -> LessonUnit:
    return LessonUnit(
        id=uid, course_id=f"M-{uid}", class_id=cls, teacher_id=teacher, required_room_type=room_type
    )


def make_problem(
    units: list[LessonUnit],
    rooms: tuple[Room, ...] = STANDARD_ROOMS,
    grid: TimeGrid = ONE_SLOT,
    class_size: int = 20,
) -> Problem:
    class_ids = sorted({u.class_id for u in units})
    teacher_ids = sorted({u.teacher_id for u in units})
    return Problem(
        rooms=rooms,
        teachers=tuple(Teacher(t, t) for t in teacher_ids),
        class_groups=tuple(ClassGroup(c, c, class_size) for c in class_ids),
        courses=tuple(Course(f"M-{u.id}", u.id, u.class_id, u.teacher_id, 1) for u in units),
        lesson_units=tuple(units),
        grid=grid,
    )


def solve(problem: Problem) -> SolveResult:
    return CpSatSolver().solve(problem, OPTIONS)


def check_valid(problem: Problem, timetable: Timetable) -> None:
    """Kiểm tra độc lập (không dùng mô hình) rằng lịch thỏa các ràng buộc cứng."""
    units = {u.id: u for u in problem.lesson_units}
    rooms = {r.id: r for r in problem.rooms}
    classes = {c.id: c for c in problem.class_groups}
    assert {a.unit_id for a in timetable.assignments} == set(units)
    assert len(timetable.assignments) == len(units)

    used_room: set[tuple[str, int, int]] = set()
    used_teacher: set[tuple[str, int, int]] = set()
    used_class: set[tuple[str, int, int]] = set()
    for a in timetable.assignments:
        u = units[a.unit_id]
        room = rooms[a.room_id]
        assert problem.grid.contains(Slot(a.day, a.period))
        assert room.can_host(u.required_room_type)
        assert room.capacity >= classes[u.class_id].size
        for used, owner in (
            (used_room, a.room_id),
            (used_teacher, u.teacher_id),
            (used_class, u.class_id),
        ):
            key = (owner, a.day, a.period)
            assert key not in used, f"trùng {key}"
            used.add(key)


def test_default_encoder_names() -> None:
    names = [e.name for e in default_hard_encoders()]
    assert names == ["each_unit_once", "room_no_overlap", "teacher_no_overlap", "class_no_overlap"]


def test_variables_only_for_allowed_rooms_and_periods(sample_problem: Problem) -> None:
    ctx = build_model(sample_problem)
    assert ctx.x
    rooms_of_unit: dict[str, set[str]] = {}
    for unit_id, day, period, room_id in ctx.x:
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
