from timetable.domain.entities import Problem
from timetable.domain.services.precheck import Issue

MAX_SUGGESTED_TEACHERS = 3


def _key(name: str | None) -> str:
    return (name or "").strip().casefold()


def check_teacher_departments(problem: Problem) -> list[Issue]:
    """Giáo viên chỉ được dạy môn thuộc đúng nhóm chuyên môn của mình.

    Chỉ kiểm tra khi cả môn và giáo viên đều khai nhóm; thiếu một bên thì không giới hạn.
    So sánh không phân biệt hoa thường.
    """
    teachers = {t.id: t for t in problem.teachers}
    by_department: dict[str, list[str]] = {}
    for member in problem.teachers:
        if _key(member.department):
            by_department.setdefault(_key(member.department), []).append(member.id)

    issues: list[Issue] = []
    for course in problem.courses:
        teacher = teachers.get(course.teacher_id)
        if teacher is None or not _key(course.department) or not _key(teacher.department):
            continue
        if _key(course.department) == _key(teacher.department):
            continue
        candidates = by_department.get(_key(course.department), [])[:MAX_SUGGESTED_TEACHERS]
        hint = f" (ví dụ {', '.join(candidates)})" if candidates else ""
        suggestion = f"Gán môn này cho giáo viên nhóm {course.department}{hint}."
        issues.append(
            Issue(
                "teacher_department_mismatch",
                f"Môn {course.name} ({course.id}, lớp {course.class_id}) thuộc nhóm "
                f"{course.department} nhưng giáo viên {teacher.id} thuộc nhóm "
                f"{teacher.department}. {suggestion}",
                suggestion,
            )
        )
    return issues
