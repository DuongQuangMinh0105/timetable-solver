from timetable.domain.entities import Problem
from timetable.domain.services.precheck import Issue


def check_units_match_courses(problem: Problem) -> list[Issue]:
    """Kiểm tra các `LessonUnit` khớp với `Course` mà chúng được tách ra.

    Với mỗi môn: tổng `duration` của các ca phải bằng `periods_per_week`; lớp và giáo viên của ca
    phải trùng với môn; id ca không được trùng; `duration` của ca chỉ là 1 hoặc 2.
    """
    issues: list[Issue] = []
    courses = {c.id: c for c in problem.courses}
    total: dict[str, int] = dict.fromkeys(courses, 0)
    seen: set[str] = set()

    for u in problem.lesson_units:
        if u.id in seen:
            issues.append(Issue("unit_duplicated", f"Ca học {u.id} bị trùng id.", "Đổi id ca học."))
        seen.add(u.id)
        course = courses.get(u.course_id)
        if course is None:
            issues.append(
                Issue(
                    "unit_unknown_course",
                    f"Ca học {u.id} tham chiếu môn {u.course_id} không tồn tại.",
                    "Sửa course_id hoặc thêm môn.",
                )
            )
            continue
        total[course.id] += u.duration
        if u.class_id != course.class_id or u.teacher_id != course.teacher_id:
            issues.append(
                Issue(
                    "unit_mismatch",
                    f"Ca học {u.id} có lớp hoặc giáo viên khác với môn {course.id}.",
                    "Đồng bộ class_id và teacher_id của ca học với môn.",
                )
            )
        if u.duration not in (1, 2):
            issues.append(
                Issue(
                    "unit_duration",
                    f"Ca học {u.id} có duration {u.duration}; chỉ hỗ trợ 1 hoặc 2 tiết.",
                    "Tách ca học thành các block 1 hoặc 2 tiết.",
                )
            )

    for course in problem.courses:
        if total[course.id] != course.periods_per_week:
            issues.append(
                Issue(
                    "course_periods_mismatch",
                    f"Môn {course.id} cần {course.periods_per_week} tiết/tuần "
                    f"nhưng các ca học cộng lại được {total[course.id]} tiết.",
                    "Tách lại môn thành các ca học (block 2+1) cho đủ số tiết.",
                )
            )
    return issues
