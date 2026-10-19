"""Đo thời gian giải của mô hình với các cấu hình tối ưu khác nhau.

Chạy từ thư mục gốc repo:
    uv run python scripts/bench_model.py --per-class 18 21 24 --workers 2 --time-limit 60

Mỗi dòng kết quả: cấu hình, trạng thái, thời gian, giá trị mục tiêu (nếu có).
Dữ liệu là bài toán nhân tạo: 10 lớp (2 MBA, 2 Design); mỗi lớp thường có
per-class tiết/tuần (lớp MBA và Design tối đa 16 vì mỗi loại dùng chung một
phòng), chia thành các môn 2 đến 4 tiết.
Giáo viên gán ngẫu nhiên nhưng cố định theo seed.
"""

import argparse
import random
import time
from typing import Any

from timetable.application.dto.solve import SolveOptions
from timetable.domain.entities import Problem
from timetable.domain.services.timetable_checker import check_timetable
from timetable.infrastructure.generator import generate_v1
from timetable.infrastructure.problem_loader import problem_from_dict
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.infrastructure.solver.default_solver import build_default_solver
from timetable.infrastructure.solver.optimization import (
    ClassDayCapacityEncoder,
    IdenticalUnitOrderEncoder,
    RoomValuePrecedenceEncoder,
)

CONFIGS: dict[str, list[Any]] = {
    "baseline": [],
    "+ca_giong_nhau": [IdenticalUnitOrderEncoder()],
    "+phong_giong_nhau": [RoomValuePrecedenceEncoder()],
    "+suc_chua_ngay": [ClassDayCapacityEncoder()],
    "+tat_ca": [
        IdenticalUnitOrderEncoder(),
        RoomValuePrecedenceEncoder(),
        ClassDayCapacityEncoder(),
    ],
}


def make_problem(
    per_class: int,
    teachers: int = 12,
    seed: int = 0,
) -> tuple[Problem, dict[str, Any]]:
    rng = random.Random(seed)
    data = generate_v1(
        10,
        teachers,
        seed,
        num_mba_classes=2,
        num_art_classes=2,
    )

    courses: list[dict[str, Any]] = []

    for group in data["class_groups"]:
        room_type = next(
            (
                course["required_room_type"]
                for course in data["courses"]
                if course["class_id"] == group["id"]
            ),
            "standard",
        )

        # Hai lớp MBA dùng chung G316 và hai lớp Design dùng chung G313,
        # mỗi phòng 36 tiết/tuần nên các lớp này bị chặn ở 16 tiết.
        left = per_class if room_type == "standard" else min(per_class, 16)
        index = 0

        while left > 0:
            periods = min(left, rng.choice([2, 3, 3, 4]))
            courses.append(
                {
                    "id": f"{group['id']}-M{index}",
                    "name": f"M{index}",
                    "class_id": group["id"],
                    "teacher_id": f"T{rng.randint(1, teachers):02d}",
                    "periods_per_week": periods,
                    "required_room_type": room_type,
                }
            )
            left -= periods
            index += 1

    data["courses"] = courses
    data["lesson_units"] = []
    data["constraints"]["block_starts"] = [0, 2, 4]

    return problem_from_dict(data), data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--per-class",
        type=int,
        nargs="+",
        default=[18, 21],
    )
    parser.add_argument("--configs", nargs="+", default=list(CONFIGS))
    parser.add_argument(
        "--objective",
        choices=["off", "on", "both"],
        default="off",
    )
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--time-limit", type=float, default=60)
    args = parser.parse_args()

    options = SolveOptions(
        time_limit_s=args.time_limit,
        num_workers=args.workers,
        random_seed=0,
    )

    objective_modes = {
        "off": [False],
        "on": [True],
        "both": [False, True],
    }[args.objective]

    for per_class in args.per_class:
        problem, data = make_problem(per_class)

        for with_objective in objective_modes:
            for name in args.configs:
                if name not in CONFIGS:
                    parser.error(f"Unknown config: {name}")

                encoders = CONFIGS[name]

                if with_objective:
                    solver = build_default_solver(
                        problem,
                        data,
                        optimization_encoders=encoders,
                    )
                else:
                    solver = CpSatSolver(optimization_encoders=encoders)

                started = time.time()
                result = solver.solve(problem, options)
                elapsed = time.time() - started

                violations = (
                    check_timetable(problem, result.timetable) if result.timetable else None
                )

                print(
                    f"per_class={per_class} "
                    f"units={len(problem.lesson_units)} "
                    f"objective={'on' if with_objective else 'off'} "
                    f"{name:<18} "
                    f"{result.status.value:<10} "
                    f"{elapsed:6.1f}s "
                    f"obj={result.objective} "
                    f"violations="
                    f"{None if violations is None else len(violations)}",
                    flush=True,
                )


if __name__ == "__main__":
    main()
