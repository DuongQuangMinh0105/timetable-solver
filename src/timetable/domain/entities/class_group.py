from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassGroup:
    id: str
    name: str
    size: int
    kind: str = "regular"  # ví dụ: regular, mba, art

    def __post_init__(self) -> None:
        if self.size <= 0:
            raise ValueError("size phải lớn hơn 0")
