from timetable.domain.entities import Problem
from timetable.domain.services.precheck import Issue


def check_units_match_courses(problem: Problem) -> list[Issue]:
    """Kiểm tra các `LessonUnit` khớp với `Course` mà chúng được tách ra.

    Với mỗi môn: tổng `duration` của các ca phải bằng `periods_per_week`; lớp và giáo viên của ca
    phải trùng với môn; id ca không được trùng; `duration` của ca chỉ là 1 hoặc 2.
    """
    issues: list[Issue] = []

    entity_groups = (
        ("room", problem.rooms),
        ("teacher", problem.teachers),
        ("class", problem.class_groups),
        ("course", problem.courses),
    )
    for entity_type, entities in entity_groups:
        seen_ids: set[str] = set()
        for entity in entities:
            if entity.id in seen_ids:
                issues.append(
                    Issue(
                        f"{entity_type}_duplicated",
                        f"{entity_type.title()} {entity.id} bị trùng id.",
                        f"Đổi id {entity_type}.",
                    )
                )
            seen_ids.add(entity.id)

    class_ids = {class_group.id for class_group in problem.class_groups}
    teacher_ids = {teacher.id for teacher in problem.teachers}
    courses = {c.id: c for c in problem.courses}
    total: dict[str, int] = dict.fromkeys(courses, 0)
    seen: set[str] = set()

    for course in problem.courses:
        if course.class_id not in class_ids:
            issues.append(
                Issue(
                    "course_unknown_class",
                    f"Môn {course.id} tham chiếu lớp {course.class_id} không tồn tại.",
                    "Sửa class_id hoặc thêm lớp.",
                )
            )
        if course.teacher_id not in teacher_ids:
            issues.append(
                Issue(
                    "course_unknown_teacher",
                    f"Môn {course.id} tham chiếu giáo viên {course.teacher_id} không tồn tại.",
                    "Sửa teacher_id hoặc thêm giáo viên.",
                )
            )

    for u in problem.lesson_units:
        if u.id in seen:
            issues.append(Issue("unit_duplicated", f"Ca học {u.id} bị trùng id.", "Đổi id ca học."))
        seen.add(u.id)
        if u.class_id not in class_ids:
            issues.append(
                Issue(
                    "unit_unknown_class",
                    f"Ca học {u.id} tham chiếu lớp {u.class_id} không tồn tại.",
                    "Sửa class_id hoặc thêm lớp.",
                )
            )
        if u.teacher_id not in teacher_ids:
            issues.append(
                Issue(
                    "unit_unknown_teacher",
                    f"Ca học {u.id} tham chiếu giáo viên {u.teacher_id} không tồn tại.",
                    "Sửa teacher_id hoặc thêm giáo viên.",
                )
            )
        unit_course = courses.get(u.course_id)
        if unit_course is None:
            issues.append(
                Issue(
                    "unit_unknown_course",
                    f"Ca học {u.id} tham chiếu môn {u.course_id} không tồn tại.",
                    "Sửa course_id hoặc thêm môn.",
                )
            )
            continue
        total[unit_course.id] += u.duration
        if (
            u.class_id != unit_course.class_id
            or u.teacher_id != unit_course.teacher_id
            or u.required_room_type != unit_course.required_room_type
        ):
            issues.append(
                Issue(
                    "unit_mismatch",
                    f"Ca học {u.id} không khớp lớp, giáo viên hoặc loại phòng của môn "
                    f"{unit_course.id}.",
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
