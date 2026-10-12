from dataclasses import dataclass, field

from timetable.domain.entities.class_group import ClassGroup
from timetable.domain.entities.course import Course
from timetable.domain.entities.lesson_unit import LessonUnit
from timetable.domain.entities.room import Room
from timetable.domain.entities.teacher import Teacher
from timetable.domain.entities.time_grid import TimeGrid


@dataclass(frozen=True, slots=True)
class Problem:
    """Toàn bộ dữ liệu đầu vào của một bài toán xếp lịch."""

    rooms: tuple[Room, ...]
    teachers: tuple[Teacher, ...]
    class_groups: tuple[ClassGroup, ...]
    courses: tuple[Course, ...]
    lesson_units: tuple[LessonUnit, ...]
    grid: TimeGrid = field(default_factory=TimeGrid)
    # Một lớp không học liên tiếp quá số tiết này (tính theo số thứ tự tiết, không xét nghỉ trưa).
    max_consecutive_periods: int = 2
    # Tiết bắt đầu cho phép của block từ 2 tiết trở lên (đánh số từ 0).
    # None: bắt đầu ở tiết nào cũng được miễn mọi tiết bị chiếm đều hợp lệ.
    # Ví dụ (0, 2, 4): chỉ block căn cặp 1-2, 3-4, 5-6.
    block_starts: tuple[int, ...] | None = None
