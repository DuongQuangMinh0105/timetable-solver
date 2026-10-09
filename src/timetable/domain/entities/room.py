from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Room:
    id: str
    name: str
    capacity: int
    room_type: str = "standard"  # ví dụ: standard, art, lab

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity phải lớn hơn 0")
