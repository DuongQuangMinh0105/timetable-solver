"""Kiểm tra nhanh sức chứa tuần của phòng và giáo viên, không cần solver.

Là điều kiện **cần** kiểu "bồ câu và chuồng": tổng số tiết cần xếp cho một nhóm tài nguyên không
được vượt tổng số tiết mà nhóm đó có trong tuần. Vi phạm thì chắc chắn vô nghiệm. Solver chứng minh
điều này rất chậm (có thể không kịp trong 60 giây) trong khi phép kiểm tra tĩnh gần như tức thì.
"""

from collections import defaultdict

from timetable.domain.entities import Problem
from timetable.domain.services.precheck import Issue
from timetable.domain.services.room_policy import allowed_rooms_by_unit


def weekly_cells(problem: Problem) -> int:
    """Số tiết có thể xếp trong một tuần của một tài nguyên (phòng hoặc giáo viên)."""
    return problem.grid.days * len(problem.grid.allowed_periods)


def teacher_capacity_issues(problem: Problem) -> list[Issue]:
    """Giáo viên được giao nhiều tiết hơn số tiết có thể xếp trong tuần."""
    load: dict[str, int] = defaultdict(int)
    for u in problem.lesson_units:
        load[u.teacher_id] += u.duration
    cap = weekly_cells(problem)
    return [
        Issue(
            "teacher_capacity",
            f"Giáo viên {teacher} được giao {periods} tiết mỗi tuần nhưng tối đa xếp được {cap}.",
            "Giảm số tiết của giáo viên này hoặc phân công thêm giáo viên.",
        )
        for teacher, periods in sorted(load.items())
        if periods > cap
    ]


def room_capacity_issues(problem: Problem) -> list[Issue]:
    """Nhóm ca học chỉ dùng được một tập phòng nhỏ nhưng cần nhiều tiết hơn tập phòng đó có.

    Với mỗi tập phòng A xuất hiện làm "phòng cho phép" của một ca nào đó, các ca có phòng cho phép
    nằm trọn trong A cần tổng số tiết không vượt `|A| x số tiết tuần`.
    """
    allowed = allowed_rooms_by_unit(problem)
    sets = {frozenset(r.id for r in rooms) for rooms in allowed.values()}
    cap = weekly_cells(problem)
    issues: list[Issue] = []
    for room_set in sorted(sets, key=lambda s: (len(s), sorted(s))):
        if not room_set:
            courses = sorted({u.course_id for u in problem.lesson_units if not allowed[u.id]})
            issues.append(
                Issue(
                    "no_valid_room",
                    f"Không có phòng nào phù hợp cho các môn: {', '.join(courses)} "
                    "(thiếu phòng đúng loại yêu cầu hoặc sức chứa phòng không đủ cho lớp).",
                    "Thêm phòng đúng loại (ví dụ phòng đặc biệt cho lớp MBA) hoặc kiểm tra "
                    "loại phòng yêu cầu và sức chứa.",
                )
            )
            continue
        needed = sum(
            u.duration for u in problem.lesson_units if {r.id for r in allowed[u.id]} <= room_set
        )
        if needed > len(room_set) * cap:
            names = ", ".join(sorted(room_set))
            issues.append(
                Issue(
                    "room_capacity",
                    f"Các ca học chỉ dùng được phòng ({names}) cần {needed} tiết mỗi tuần nhưng "
                    f"các phòng này chỉ có {len(room_set) * cap} tiết.",
                    "Giảm số tiết cần các phòng này hoặc cho phép dùng thêm phòng.",
                )
            )
    return issues


def resource_capacity_issues(problem: Problem) -> list[Issue]:
    return [*teacher_capacity_issues(problem), *room_capacity_issues(problem)]
