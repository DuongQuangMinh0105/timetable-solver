from dataclasses import dataclass, field

from timetable.domain.entities.class_group import ClassGroup
from timetable.domain.entities.course import Course
from timetable.domain.entities.lesson_unit import LessonUnit
from timetable.domain.entities.room import Room
from timetable.domain.entities.teacher import Teacher
from timetable.domain.entities.time_grid import TimeGrid
from timetable.domain.rules.soft_constraints import W_G316, W_ROOM, W_SAT


@dataclass(frozen=True, slots=True)
class Problem:
    """Toàn bộ dữ liệu đầu vào của một bài toán xếp lịch."""

    rooms: tuple[Room, ...]
    teachers: tuple[Teacher, ...]
    class_groups: tuple[ClassGroup, ...]
    courses: tuple[Course, ...]
    lesson_units: tuple[LessonUnit, ...]
    grid: TimeGrid = field(default_factory=TimeGrid)
    max_consecutive_periods: int = 2
    block_starts: tuple[int, ...] | None = None

    # THÊM DÒNG NÀY: Trọng số cho các ràng buộc mềm (room stability, tránh T7, ưu tiên G316)
    soft_weights: tuple[int, int, int] = (W_ROOM, W_SAT, W_G316)
