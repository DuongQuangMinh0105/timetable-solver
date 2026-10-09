from collections.abc import Iterator
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class Slot:
    """Một ô thời gian: ngày (0 = Thứ 2 ... 5 = Thứ 7) và tiết (0 = tiết 1 ...)."""

    day: int
    period: int


@dataclass(frozen=True, slots=True)
class TimeGrid:
    """Lưới thời gian của tuần: mặc định 6 ngày x 6 tiết."""

    SATURDAY: ClassVar[int] = 5

    days: int = 6
    periods: int = 6

    def __post_init__(self) -> None:
        if self.days <= 0 or self.periods <= 0:
            raise ValueError("days và periods phải lớn hơn 0")

    @property
    def num_slots(self) -> int:
        return self.days * self.periods

    def slots(self) -> Iterator[Slot]:
        for day in range(self.days):
            for period in range(self.periods):
                yield Slot(day, period)

    def contains(self, slot: Slot) -> bool:
        return 0 <= slot.day < self.days and 0 <= slot.period < self.periods

    def is_saturday(self, day: int) -> bool:
        return day == self.SATURDAY
