from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Assignment:
    """Kết quả xếp một đơn vị học vào (ngày, tiết, phòng)."""

    unit_id: str
    day: int
    period: int
    room_id: str


@dataclass(frozen=True, slots=True)
class Timetable:
    assignments: tuple[Assignment, ...] = ()

    def for_unit(self, unit_id: str) -> Assignment | None:
        for assignment in self.assignments:
            if assignment.unit_id == unit_id:
                return assignment
        return None
