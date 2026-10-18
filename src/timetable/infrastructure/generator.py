"""Facade export các hàm sinh dữ liệu test."""

from timetable.infrastructure.generator_v1 import (
    INFEASIBLE_PROFILES,
    MAX_CLASS_SIZE,
    MIN_CLASS_SIZE,
    PROFILES,
    ROOM_CAPACITY,
    generate_profile,
    generate_v1,
)

__all__ = [
    "INFEASIBLE_PROFILES",
    "MAX_CLASS_SIZE",
    "MIN_CLASS_SIZE",
    "PROFILES",
    "ROOM_CAPACITY",
    "generate_profile",
    "generate_v1",
]


def generate_v0(num_rooms: int = 5, num_teachers: int = 5) -> dict[str, list[str]]:
    """Generator v0: Khởi tạo dữ liệu mẫu ban đầu gồm phòng học và giáo viên."""
    rooms = [f"Room_{i + 1:02d}" for i in range(num_rooms)]
    teachers = [f"Teacher_{i + 1:02d}" for i in range(num_teachers)]

    return {
        "rooms": rooms,
        "teachers": teachers,
    }
