from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Room:
    """Phòng học.

    room_type là loại chính của phòng (standard, mba, art). also_supports là các loại
    khác phòng vẫn có thể dùng (ví dụ phòng MBA vẫn cho lớp thường học).
    """

    id: str
    name: str
    capacity: int
    room_type: str = "standard"
    also_supports: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity phải lớn hơn 0")

    def can_host(self, required_type: str) -> bool:
        """Phòng có được phép dùng cho đơn vị học yêu cầu loại phòng này không."""
        return required_type == self.room_type or required_type in self.also_supports

    def is_primary_for(self, required_type: str) -> bool:
        """Đúng loại chính của phòng (dùng cho luật ưu tiên, ví dụ ưu tiên lớp MBA vào G316)."""
        return required_type == self.room_type
