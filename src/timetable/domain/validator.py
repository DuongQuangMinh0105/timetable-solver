from collections.abc import Sequence

from timetable.domain.entities import Assignment, Problem, Timetable
from timetable.domain.services.timetable_checker import check_timetable
from timetable.domain.violation import Violation

__all__ = ["Validator", "Violation"]


class Validator:
    """Kiểm tra tính hợp lệ của một thời khóa biểu.

    Luôn báo lỗi khi lịch rỗng. Khi có `problem`, kiểm tra thêm toàn bộ ràng buộc cứng bằng
    `check_timetable` (trùng phòng/giáo viên/lớp, ô không hợp lệ, quá 2 tiết liên tiếp...).
    """

    def validate(
        self,
        timetable: Timetable | Sequence[Assignment],
        problem: Problem | None = None,
    ) -> list[Violation]:
        assignments = (
            timetable.assignments if isinstance(timetable, Timetable) else tuple(timetable)
        )
        if not assignments:
            return [
                Violation(
                    rule_id="TIMETABLE_EMPTY",
                    description="Thời khóa biểu không được để trống.",
                )
            ]
        if problem is None:
            return []
        return check_timetable(problem, Timetable(assignments))
