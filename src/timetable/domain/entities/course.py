from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Course:
    """Một môn của một lớp do một giáo viên dạy, cần periods_per_week tiết mỗi tuần."""

    id: str
    name: str
    class_id: str
    teacher_id: str
    periods_per_week: int
    required_room_type: str = "standard"
    # Nhóm chuyên môn của môn; nếu có thì giáo viên phải cùng nhóm. None là không giới hạn.
    department: str | None = None

    def __post_init__(self) -> None:
        if self.periods_per_week <= 0:
            raise ValueError("periods_per_week phải lớn hơn 0")
