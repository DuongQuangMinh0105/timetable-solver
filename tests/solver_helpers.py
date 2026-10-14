from timetable.application.dto.solve import SolveOptions, SolveResult
from timetable.domain.entities import (
    ClassGroup,
    Course,
    LessonUnit,
    Problem,
    Room,
    Teacher,
    TimeGrid,
    Timetable,
)
from timetable.domain.services.timetable_checker import check_timetable
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


def check_valid(problem: Problem, timetable: Timetable) -> None:
    """Kiểm tra độc lập (không dùng mô hình) rằng lịch thỏa các ràng buộc cứng."""
    violations = check_timetable(problem, timetable)
    assert not violations, [f"{v.rule_id}: {v.description}" for v in violations]
