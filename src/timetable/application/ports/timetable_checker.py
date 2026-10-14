from typing import Protocol

from timetable.domain.entities import Problem, Timetable
from timetable.domain.violation import Violation


class TimetableChecker(Protocol):
    """Kiểm tra một thời khóa biểu so với bài toán; trả về danh sách vi phạm."""

    def __call__(self, problem: Problem, timetable: Timetable) -> list[Violation]: ...
