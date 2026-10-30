from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Teacher:
    id: str
    name: str
    # Nhóm chuyên môn (ví dụ IT, Business, Design, English). None là không giới hạn.
    department: str | None = None
