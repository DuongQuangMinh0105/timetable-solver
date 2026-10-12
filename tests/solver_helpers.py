from timetable.application.dto.solve import SolveOptions, SolveResult
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
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver

ONE_SLOT = TimeGrid(days=1, periods=1, allowed_periods=(0,), period_times=())
TWO_SLOTS = TimeGrid(days=1, periods=2, allowed_periods=(0, 1), period_times=())
OPTIONS = SolveOptions(time_limit_s=30, num_workers=1)

STANDARD_ROOMS = (Room("R1", "R1", 30), Room("R2", "R2", 30), Room("R3", "R3", 30))


def one_day_grid(*periods: int) -> TimeGrid:
    """Một ngày trong lưới 8 tiết, chỉ cho phép các tiết (đánh số từ 1) được liệt kê."""
    return TimeGrid(days=1, periods=8, allowed_periods=tuple(p - 1 for p in periods))


def unit(
    uid: str, cls: str, teacher: str, room_type: str = "standard", duration: int = 1
) -> LessonUnit:
    return LessonUnit(
        id=uid,
        course_id=f"M-{uid}",
        class_id=cls,
        teacher_id=teacher,
        required_room_type=room_type,
        duration=duration,
    )


def make_problem(
    units: list[LessonUnit],
    rooms: tuple[Room, ...] = STANDARD_ROOMS,
    grid: TimeGrid = ONE_SLOT,
    class_size: int = 20,
    max_consecutive: int = 2,
    block_starts: tuple[int, ...] | None = None,
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
        max_consecutive_periods=max_consecutive,
        block_starts=block_starts,
    )


def solve(problem: Problem) -> SolveResult:
    return CpSatSolver().solve(problem, OPTIONS)


def longest_run(periods: list[int]) -> int:
    """Độ dài chuỗi tiết liền nhau dài nhất trong danh sách chỉ số tiết."""
    best = run = 0
    previous: int | None = None
    for p in sorted(periods):
        run = run + 1 if previous is not None and p == previous + 1 else 1
        best = max(best, run)
        previous = p
    return best


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
    class_periods: dict[tuple[str, int], list[int]] = {}
    for a in timetable.assignments:
        u = units[a.unit_id]
        room = rooms[a.room_id]
        assert problem.grid.contains(Slot(a.day, a.period))
        assert room.can_host(u.required_room_type)
        assert room.capacity >= classes[u.class_id].size
        for q in range(a.period, a.period + u.duration):
            assert q in problem.grid.allowed_periods
            for used, owner in (
                (used_room, a.room_id),
                (used_teacher, u.teacher_id),
                (used_class, u.class_id),
            ):
                key = (owner, a.day, q)
                assert key not in used, f"trùng {key}"
                used.add(key)
            class_periods.setdefault((u.class_id, a.day), []).append(q)

    for (class_id, day), periods in class_periods.items():
        assert longest_run(periods) <= problem.max_consecutive_periods, (class_id, day, periods)
