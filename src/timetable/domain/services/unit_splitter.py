from timetable.domain.entities import Course, LessonUnit


def split_into_blocks(periods: int) -> list[int]:
    """Tách số tiết mỗi tuần thành các block: ưu tiên block 2 tiết, phần lẻ là block 1 tiết.

    1 -> [1]; 2 -> [2]; 3 -> [2, 1]; 4 -> [2, 2]; 5 -> [2, 2, 1].
    """
    if periods <= 0:
        raise ValueError("periods phải lớn hơn 0")
    return [2] * (periods // 2) + [1] * (periods % 2)


def lesson_units_for_course(course: Course) -> tuple[LessonUnit, ...]:
    """Tạo các LessonUnit cho một môn theo quy tắc tách block."""
    return tuple(
        LessonUnit(
            id=f"{course.id}-{index}",
            course_id=course.id,
            class_id=course.class_id,
            teacher_id=course.teacher_id,
            index=index,
            required_room_type=course.required_room_type,
            duration=duration,
        )
        for index, duration in enumerate(split_into_blocks(course.periods_per_week))
    )
