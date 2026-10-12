from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LessonUnit:
    """Một ca học cần xếp: một block liên tiếp `duration` tiết (1 hoặc 2).

    Môn nhiều tiết được tách thành nhiều đơn vị (xem `unit_splitter`). Khi xếp lịch, `period`
    của một phân công là tiết **bắt đầu**; đơn vị chiếm các tiết từ `period` đến
    `period + duration - 1`.
    """

    id: str
    course_id: str
    class_id: str
    teacher_id: str
    index: int = 0  # đây là ca thứ mấy của môn trong tuần
    required_room_type: str = "standard"
    duration: int = 1

    def __post_init__(self) -> None:
        if self.duration <= 0:
            raise ValueError("duration phải lớn hơn 0")
