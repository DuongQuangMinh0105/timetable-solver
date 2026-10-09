from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LessonUnit:
    """Một tiết học cần xếp (đơn vị nhỏ nhất). Môn nhiều tiết được tách thành nhiều đơn vị."""

    id: str
    course_id: str
    class_id: str
    teacher_id: str
    index: int = 0  # đây là tiết thứ mấy của môn trong tuần
    required_room_type: str = "standard"
