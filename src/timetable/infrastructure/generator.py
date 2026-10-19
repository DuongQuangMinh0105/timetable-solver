"""Facade export các hàm sinh dữ liệu test."""

from timetable.infrastructure.generator_v1 import (
    ALLOWED_PERIODS,
    ART_ROOM_ID,
    HARD_PARAMS,
    INFEASIBLE_PROFILES,
    MAX_CLASS_SIZE,
    MAX_CONSECUTIVE_PERIODS,  # <-- Đã thêm
    MBA_ROOM_ID,
    MIN_CLASS_SIZE,
    NUM_DAYS,
    NUM_PERIODS,
    PROFILES,
    ROOM_CAPACITY,
    SCHEMA_VERSION,
    STANDARD_ROOM_IDS,
    generate_hard,
    generate_profile,
    generate_v0,
    generate_v1,
)

__all__ = [
    "ALLOWED_PERIODS",
    "ART_ROOM_ID",
    "HARD_PARAMS",
    "INFEASIBLE_PROFILES",
    "MAX_CLASS_SIZE",
    "MAX_CONSECUTIVE_PERIODS",
    "MBA_ROOM_ID",
    "MIN_CLASS_SIZE",
    "NUM_DAYS",
    "NUM_PERIODS",
    "PROFILES",
    "ROOM_CAPACITY",
    "SCHEMA_VERSION",
    "STANDARD_ROOM_IDS",
    "generate_hard",
    "generate_profile",
    "generate_v0",
    "generate_v1",
]
