"""Bộ sinh dữ liệu test phiên bản 1.

- ``generate_v1``: sinh một bài toán đầy đủ, đúng schema ``docs/schema/input.sample.json``.
- ``generate_profile``: các bộ tham số đặt tên sẵn (kích thước và dữ liệu "khó").
"""

from __future__ import annotations

import itertools
import random
from typing import Any, NamedTuple

from timetable.domain.rules.soft_constraints import W_G316, W_ROOM, W_SAT

SCHEMA_VERSION = "0.1"

# Lưới thời gian: 6 ngày (0 = Thứ 2 ... 5 = Thứ 7), 8 tiết, chỉ xếp tiết 0 đến 5.
NUM_DAYS = 6
NUM_PERIODS = 8
ALLOWED_PERIODS = [0, 1, 2, 3, 4, 5]
MAX_CONSECUTIVE_PERIODS = 2

# Sức chứa 30 là giá trị tạm, giống file mẫu. Sĩ số phải luôn <= sức chứa.
ROOM_CAPACITY = 30
MIN_CLASS_SIZE = 20
MAX_CLASS_SIZE = 28

STANDARD_ROOM_IDS = (
    "G314",
    "G317",
    "G318",
    "G319",
    "G502",
    "G503",
    "G504",
    "G508",
    "G509",
    "G510",
)
MBA_ROOM_ID = "G316"
ART_ROOM_ID = "G313"

# (mã môn, tên môn, số tiết/tuần, loại phòng yêu cầu)
_Subject = tuple[str, str, int, str]

_REGULAR_SUBJECTS: tuple[_Subject, ...] = (
    ("ENG", "Tiếng Anh", 3, "standard"),
    ("MATH", "Toán", 3, "standard"),
    ("IT", "Tin học", 2, "standard"),
)
_MBA_SUBJECTS: tuple[_Subject, ...] = (
    ("MGT", "Quản trị", 2, "mba"),
    ("FIN", "Tài chính", 2, "mba"),
)
_ART_SUBJECTS: tuple[_Subject, ...] = (
    ("DRAW", "Vẽ", 3, "art"),
    ("ENG", "Tiếng Anh", 2, "standard"),
)


class _ClassPlan(NamedTuple):
    code: str
    kind: str
    name: str
    subjects: tuple[_Subject, ...]


def generate_v1(
    num_classes: int = 4,
    num_teachers: int = 6,
    seed: int = 0,
    *,
    num_mba_classes: int = 1,
    num_art_classes: int = 1,
) -> dict[str, Any]:
    """Generator v1: sinh một bài toán đầy đủ, đúng schema file mẫu.

    Ba tham số đầu giữ đúng thứ tự ``(num_classes, num_teachers, seed)`` nên có thể
    gọi theo vị trí. Cùng ``seed`` và cùng tham số luôn cho ra đúng cùng một kết quả;
    dùng ``random.Random(seed)`` riêng nên không đụng đến trạng thái ``random`` toàn cục.
    ``num_classes`` là tổng số lớp, trong đó ``num_mba_classes`` là lớp MBA,
    ``num_art_classes`` là lớp Design, phần còn lại là lớp thường.
    """
    _check_params(num_classes, num_teachers, num_mba_classes, num_art_classes)
    rng = random.Random(seed)

    teacher_ids = [f"T{i:02d}" for i in range(1, num_teachers + 1)]
    teachers = [{"id": tid, "name": f"Giáo viên {i}"} for i, tid in enumerate(teacher_ids, start=1)]

    # Xáo thứ tự giáo viên theo seed, rồi gán xoay vòng để tải đều giữa các giáo viên.
    shuffled = teacher_ids[:]
    rng.shuffle(shuffled)
    teacher_cycle = itertools.cycle(shuffled)

    num_regular = num_classes - num_mba_classes - num_art_classes
    class_groups: list[dict[str, Any]] = []
    courses: list[dict[str, Any]] = []
    lesson_units: list[dict[str, Any]] = []

    for plan in _class_plans(num_regular, num_mba_classes, num_art_classes):
        class_id = f"C-{plan.code}"

        # FIX MYPY: Ép kiểu int() để chắc chắn rng.randint trả về int
        class_size = int(rng.randint(MIN_CLASS_SIZE, MAX_CLASS_SIZE))

        class_groups.append(
            {
                "id": class_id,
                "name": plan.name,
                "size": class_size,
                "kind": plan.kind,
            }
        )
        for subject_code, subject_name, periods, room_type in plan.subjects:
            course_id = f"M-{plan.code}-{subject_code}"
            teacher_id = next(teacher_cycle)

            # FIX MYPY: Ép kiểu int() cho periods
            periods_int = int(periods)

            courses.append(
                {
                    "id": course_id,
                    "name": subject_name,
                    "class_id": class_id,
                    "teacher_id": teacher_id,
                    "periods_per_week": periods_int,
                    "required_room_type": room_type,
                }
            )
            lesson_units.extend(
                {
                    "id": f"{course_id}-{index}",
                    "course_id": course_id,
                    "class_id": class_id,
                    "teacher_id": teacher_id,
                    "index": int(index),  # FIX MYPY: Ép kiểu int()
                    "required_room_type": room_type,
                }
                for index in range(periods_int)
            )

    return {
        "schema_version": SCHEMA_VERSION,
        "_comment": f"Dữ liệu sinh tự động bởi generator v1 (seed={seed}).",
        "grid": {
            "days": NUM_DAYS,
            "periods": NUM_PERIODS,
            "allowed_periods": list(ALLOWED_PERIODS),
        },
        "rooms": _rooms(),
        "teachers": teachers,
        "class_groups": class_groups,
        "courses": courses,
        "lesson_units": lesson_units,
        "constraints": {"max_consecutive_periods": MAX_CONSECUTIVE_PERIODS},
        "soft_weights": {
            "avoid_saturday": W_SAT,
            "room_stability": W_ROOM,
            "reserve_mba_room": W_G316,
        },
        "solver": {"time_limit_s": 60, "num_workers": 8, "random_seed": seed},
    }


# Bộ tham số đặt tên sẵn. Số tiết mỗi lớp: thường 8, MBA 4, Design 5. Phòng G316 và G313
# mỗi phòng chỉ có 6 ngày x 6 tiết = 36 tiết/tuần.
PROFILES: dict[str, dict[str, int]] = {
    # Quy mô file mẫu.
    "small": {"num_classes": 4, "num_teachers": 6, "num_mba_classes": 1, "num_art_classes": 1},
    # Quy mô theo docs/test-data-spec.md.
    "spec": {"num_classes": 10, "num_teachers": 8, "num_mba_classes": 2, "num_art_classes": 2},
    # 8 lớp MBA = 32/36 tiết của G316 (khoảng 89%).
    "many_mba": {
        "num_classes": 12,
        "num_teachers": 8,
        "num_mba_classes": 8,
        "num_art_classes": 1,
    },
    # 10 lớp Design cần 30/36 tiết của G313 (khoảng 83%).
    "many_art": {
        "num_classes": 12,
        "num_teachers": 8,
        "num_mba_classes": 1,
        "num_art_classes": 10,
    },
    # Ít giáo viên nên nhiều ràng buộc trùng giáo viên.
    "tight_teachers": {
        "num_classes": 10,
        "num_teachers": 4,
        "num_mba_classes": 2,
        "num_art_classes": 2,
    },
    # Cố ý vô nghiệm: 10 lớp MBA cần 40 tiết trong G316, vượt 36 tiết/tuần.
    "overload_mba": {
        "num_classes": 10,
        "num_teachers": 8,
        "num_mba_classes": 10,
        "num_art_classes": 0,
    },
}

INFEASIBLE_PROFILES = frozenset({"overload_mba"})


def generate_profile(name: str, seed: int = 0) -> dict[str, Any]:
    """Sinh dữ liệu theo một bộ tham số đặt tên sẵn trong ``PROFILES``."""
    if name not in PROFILES:
        raise ValueError(f"profile không tồn tại: {name} (có: {', '.join(PROFILES)})")
    return generate_v1(seed=seed, **PROFILES[name])


def _check_params(
    num_classes: int,
    num_teachers: int,
    num_mba_classes: int,
    num_art_classes: int,
) -> None:
    if num_classes < 1:
        raise ValueError("num_classes phải >= 1")
    if num_teachers < 1:
        raise ValueError("num_teachers phải >= 1")
    if num_mba_classes < 0 or num_art_classes < 0:
        raise ValueError("num_mba_classes và num_art_classes không được âm")
    if num_mba_classes + num_art_classes > num_classes:
        raise ValueError("num_mba_classes + num_art_classes không được vượt num_classes")


def _class_plans(num_regular: int, num_mba: int, num_art: int) -> list[_ClassPlan]:
    plans = [
        _ClassPlan(f"A{i}", "regular", f"Lớp thường A{i}", _REGULAR_SUBJECTS)
        for i in range(1, num_regular + 1)
    ]
    plans += [
        _ClassPlan(f"MBA{i}", "mba", f"Lớp MBA {i}", _MBA_SUBJECTS) for i in range(1, num_mba + 1)
    ]
    plans += [
        _ClassPlan(f"DES{i}", "art", f"Lớp Design {i}", _ART_SUBJECTS)
        for i in range(1, num_art + 1)
    ]
    return plans


def _rooms() -> list[dict[str, Any]]:
    rooms: list[dict[str, Any]] = [
        {
            "id": room_id,
            "name": room_id,
            "capacity": ROOM_CAPACITY,
            "room_type": "standard",
            "also_supports": [],
        }
        for room_id in STANDARD_ROOM_IDS
    ]
    rooms.append(
        {
            "id": MBA_ROOM_ID,
            "name": MBA_ROOM_ID,
            "capacity": ROOM_CAPACITY,
            "room_type": "mba",
            "also_supports": ["standard"],
        }
    )
    rooms.append(
        {
            "id": ART_ROOM_ID,
            "name": ART_ROOM_ID,
            "capacity": ROOM_CAPACITY,
            "room_type": "art",
            "also_supports": [],
        }
    )
    return rooms
