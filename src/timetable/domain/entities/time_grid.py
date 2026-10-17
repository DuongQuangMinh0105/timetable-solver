from collections.abc import Iterator
from dataclasses import dataclass
from typing import ClassVar

# Giờ từng tiết (chỉ số 0 = tiết 1). Dùng để hiển thị, solver chỉ cần chỉ số tiết.
DEFAULT_PERIOD_TIMES: tuple[tuple[str, str], ...] = (
    ("07:30", "09:00"),
    ("09:10", "10:40"),
    ("10:50", "12:20"),
    ("12:50", "14:20"),
    ("14:30", "16:00"),
    ("16:10", "17:40"),
    ("17:50", "19:20"),
    ("19:30", "21:00"),
)


@dataclass(frozen=True, slots=True)
class Slot:
    """Một ô thời gian: ngày (0 = Thứ 2 ... 5 = Thứ 7) và tiết (0 = tiết 1 ...)."""

    day: int
    period: int


@dataclass(frozen=True, slots=True)
class TimeGrid:
    """Lưới thời gian của tuần: 6 ngày x 8 tiết, nhưng chỉ được xếp vào các tiết cho phép.

    Mặc định chỉ xếp tiết 1 đến 6 (chỉ số 0 đến 5); tiết 7 và 8 (chỉ số 6, 7) bị cấm.
    """

    SATURDAY: ClassVar[int] = 5

    days: int = 6
    periods: int = 8
    allowed_periods: tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    period_times: tuple[tuple[str, str], ...] = DEFAULT_PERIOD_TIMES

    def __post_init__(self) -> None:
        if self.days <= 0 or self.periods <= 0:
            raise ValueError("days và periods phải lớn hơn 0")
        if not self.allowed_periods:
            raise ValueError("allowed_periods không được rỗng")
        if any(not 0 <= p < self.periods for p in self.allowed_periods):
            raise ValueError("allowed_periods có tiết nằm ngoài lưới")
        if list(self.allowed_periods) != sorted(set(self.allowed_periods)):
            raise ValueError("allowed_periods phải tăng dần và không trùng")
        if self.period_times and len(self.period_times) != self.periods:
            raise ValueError("period_times phải rỗng hoặc có đúng 'periods' phần tử")

    @property
    def num_slots(self) -> int:
        """Số ô thực sự được phép xếp lịch trong tuần."""
        return self.days * len(self.allowed_periods)

    def slots(self) -> Iterator[Slot]:
        """Duyệt các ô được phép xếp lịch."""
        for day in range(self.days):
            for period in self.allowed_periods:
                yield Slot(day, period)

    def contains(self, slot: Slot) -> bool:
        return 0 <= slot.day < self.days and slot.period in self.allowed_periods

    def is_saturday(self, day: int) -> bool:
        return day == self.SATURDAY