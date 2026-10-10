from typing import Any


def generate_v0(num_rooms: int = 5, num_teachers: int = 5) -> dict[str, list[Any]]:
    """Generator v0: Khởi tạo dữ liệu mẫu ban đầu gồm phòng học và giáo viên."""
    rooms = [f"Room_{i + 1:02d}" for i in range(num_rooms)]
    teachers = [f"Teacher_{i + 1:02d}" for i in range(num_teachers)]

    return {
        "rooms": rooms,
        "teachers": teachers,
    }