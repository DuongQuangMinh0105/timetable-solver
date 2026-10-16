import random
from dataclasses import replace

from solver_helpers import OPTIONS, check_valid, make_problem, unit
from timetable.application.dto.solve import SolveResult, SolveStatus
from timetable.domain.entities import Course, Problem, Room, TimeGrid
from timetable.domain.services.unit_splitter import lesson_units_for_course
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.infrastructure.solver.optimization import (
    ClassDayCapacityEncoder,
    IdenticalUnitOrderEncoder,
    RoomValuePrecedenceEncoder,
    optimization_encoders,
)
from timetable.infrastructure.solver.soft_adapter import SoftObjectiveApplier
from timetable.infrastructure.solver.soft_objective import add_soft_objective

ALIGNED = (0, 2, 4)


def _random_problem(seed: int) -> Problem:
    r = random.Random(seed)
    days = r.choice([2, 3])
    grid = TimeGrid(days=days, periods=8, allowed_periods=(0, 1, 2, 3, 4, 5))
    n_classes = r.randint(1, 3)
    courses = []
    for c in range(n_classes):
        for m in range(r.randint(1, 3)):
            courses.append(
                Course(f"C{c}M{m}", "m", f"C{c}", f"T{r.randint(0, 2)}", r.choice([1, 2, 3, 4]))
            )
    units = [u for course in courses for u in lesson_units_for_course(course)]
    rooms = tuple(Room(f"R{i}", f"R{i}", 30) for i in range(r.randint(2, 3)))
    base = make_problem(units, rooms=rooms, grid=grid, block_starts=ALIGNED)
    return replace(base, courses=tuple(courses))


def _solve(problem: Problem, *, optimized: bool, objective: bool) -> SolveResult:
    applier = (
        SoftObjectiveApplier(add_soft_objective, saturdays=(1,), mba_room_id="R0")
        if objective
        else None
    )
    encoders = optimization_encoders(excluded_room_ids={"R0"}) if optimized else []
    return CpSatSolver(objective=applier, optimization_encoders=encoders).solve(problem, OPTIONS)


def test_optimization_keeps_feasibility_and_optimum() -> None:
    """Có hay không có encoder tối ưu: cùng kết luận có nghiệm và cùng giá trị tối ưu."""
    nonzero = 0
    for seed in range(40):
        problem = _random_problem(seed)
        plain = _solve(problem, optimized=False, objective=True)
        fast = _solve(problem, optimized=True, objective=True)
        assert plain.status == fast.status, seed
        if plain.status is SolveStatus.OPTIMAL:
            assert plain.objective == fast.objective, seed
            assert fast.timetable is not None
            check_valid(problem, fast.timetable)
            nonzero += bool(plain.objective)
    assert nonzero >= 5  # có đủ ca mà tối ưu khác 0, để phép so sánh có ý nghĩa


def test_precedence_needs_penalized_room_to_be_excluded() -> None:
    """Nếu hàm mục tiêu phạt riêng một phòng thì phòng đó phải bị loại khỏi nhóm hoán đổi."""
    wrong = 0
    for seed in range(40):
        problem = _random_problem(seed)
        plain = _solve(problem, optimized=False, objective=True)
        applier = SoftObjectiveApplier(add_soft_objective, saturdays=(1,), mba_room_id="R0")
        naive = CpSatSolver(
            objective=applier, optimization_encoders=[RoomValuePrecedenceEncoder()]
        ).solve(problem, OPTIONS)
        wrong += plain.objective != naive.objective
    assert wrong > 0  # không loại phòng thì mất tối ưu: đây là lý do có `excluded_room_ids`


def test_each_encoder_keeps_feasibility() -> None:
    for encoder in (
        IdenticalUnitOrderEncoder(),
        RoomValuePrecedenceEncoder(),
        ClassDayCapacityEncoder(),
    ):
        for seed in range(15):
            problem = _random_problem(seed)
            plain = CpSatSolver().solve(problem, OPTIONS).status
            one = CpSatSolver(optimization_encoders=[encoder]).solve(problem, OPTIONS).status
            assert plain == one, (type(encoder).__name__, seed)


def test_identical_units_are_ordered_by_start_time() -> None:
    units = [
        replace(unit("a", "C", "T"), course_id="M", id="M-0", index=0),
        replace(unit("b", "C", "T"), course_id="M", id="M-1", index=1),
        replace(unit("c", "C", "T"), course_id="M", id="M-2", index=2),
    ]
    problem = make_problem(units, grid=TimeGrid(days=2, periods=8, allowed_periods=(0, 1, 2, 3)))
    result = CpSatSolver(optimization_encoders=[IdenticalUnitOrderEncoder()]).solve(
        problem, OPTIONS
    )
    assert result.timetable is not None
    order = {a.unit_id: (a.day, a.period) for a in result.timetable.assignments}
    assert order["M-0"] < order["M-1"] < order["M-2"]


def test_room_precedence_uses_lowest_rooms_first() -> None:
    units = [unit(f"u{i}", f"C{i}", f"T{i}") for i in range(2)]
    rooms = tuple(Room(f"R{i}", f"R{i}", 30) for i in range(4))
    grid = TimeGrid(days=1, periods=8, allowed_periods=(0,))
    problem = make_problem(units, rooms=rooms, grid=grid)
    result = CpSatSolver(optimization_encoders=[RoomValuePrecedenceEncoder()]).solve(
        problem, OPTIONS
    )
    assert result.timetable is not None
    # Hai ca cùng một tiết cần hai phòng: luôn là hai phòng đầu danh sách.
    assert {a.room_id for a in result.timetable.assignments} == {"R0", "R1"}


def test_rooms_of_different_type_are_not_merged() -> None:
    rooms = (Room("A", "A", 30), Room("B", "B", 30, "art"), Room("C", "C", 30))
    units = [unit("u1", "C1", "T1", room_type="art"), unit("u2", "C2", "T2")]
    grid = TimeGrid(days=1, periods=8, allowed_periods=(0,))
    problem = make_problem(units, rooms=rooms, grid=grid)
    result = CpSatSolver(optimization_encoders=[RoomValuePrecedenceEncoder()]).solve(
        problem, OPTIONS
    )
    assert result.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)
    assert result.timetable is not None
    check_valid(problem, result.timetable)


def test_class_day_capacity_does_not_cut_a_valid_full_day() -> None:
    """Một ngày kín 4 tiết (1-2 và 5-6) của một lớp vẫn xếp được."""
    units = [unit("a", "C", "T1", duration=2), unit("b", "C", "T2", duration=2)]
    grid = TimeGrid(days=1, periods=8, allowed_periods=(0, 1, 2, 3, 4, 5))
    problem = make_problem(units, grid=grid, block_starts=ALIGNED)
    result = CpSatSolver(optimization_encoders=[ClassDayCapacityEncoder()]).solve(problem, OPTIONS)
    assert result.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)
