import random
from typing import Any


def generate_v1(num_classes: int = 3, num_teachers: int = 3, seed: int = 42) -> dict[str, Any]:
    """Generator v1: Sinh dữ liệu mẫu tuân thủ schema đầu vào với seed cố định."""
    random.seed(seed)

    rooms = [f"Room_{i + 1:02d}" for i in range(max(3, num_classes))]
    teachers = [f"Teacher_{i + 1:02d}" for i in range(num_teachers)]
    class_groups = [f"Class_{i + 1:02d}" for i in range(num_classes)]

    return {
        "version": "1.0",
        "seed": seed,
        "rooms": rooms,
        "teachers": teachers,
        "class_groups": class_groups,
    }
