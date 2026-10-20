"""Đo thời gian giải của mô hình với các cấu hình tối ưu khác nhau.

Chạy từ thư mục gốc repo:
    uv run python scripts/bench_model.py --per-class 18 21 24 --workers 2 --time-limit 60
"""

import argparse
import random
import time

from ortools.sat.python import cp_model

from timetable.application.dto.solve import SolveOptions
from timetable.domain.entities import Problem
from timetable.domain.services.timetable_checker import check_timetable
from timetable.infrastructure.generator import generate_v1
from timetable.infrastructure.problem_loader import problem_from_dict
from timetable.infrastructure.solver.builder import build_model
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.infrastructure.solver.default_solver import build_default_solver
from timetable.infrastructure.solver.optimization import (
    ClassDayCapacityEncoder,
    IdenticalUnitOrderEncoder,
    RoomValuePrecedenceEncoder,
)

CONFIGS = {
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


def make_problem(per_class: int, teachers: int = 12, seed: int = 0) -> tuple[Problem, dict]:  # type: ignore[type-arg]
    rng = random.Random(seed)
    data = generate_v1(10, teachers, seed, num_mba_classes=2, num_art_classes=2)
    courses = []
    for group in data["class_groups"]:
        room_type = next(
            (c["required_room_type"] for c in data["courses"] if c["class_id"] == group["id"]),
            "standard",
        )
        left, i = (per_class if room_type == "standard" else min(per_class, 16)), 0
        while left > 0:
            periods = min(left, rng.choice([2, 3, 3, 4]))
            courses.append(
                {
                    "id": f"{group['id']}-M{i}",
                    "name": f"M{i}",
                    "class_id": group["id"],
                    "teacher_id": f"T{rng.randint(1, teachers):02d}",
                    "periods_per_week": periods,
                    "required_room_type": room_type,
                }
            )
            left -= periods
            i += 1
    data["courses"], data["lesson_units"] = courses, []
    data["constraints"]["block_starts"] = [0, 2, 4]
    return problem_from_dict(data), data


def create_naive_hints(problem: Problem, ctx) -> dict:
    """Tạo hint ngây thơ: gợi ý phòng cho từng unit dựa trên required_room_type."""
    rooms_by_type = {}
    for room in problem.rooms:
        rooms_by_type.setdefault(room.room_type, []).append(room.id)
        for supported in room.also_supports:
            rooms_by_type.setdefault(supported, []).append(room.id)

    hints = {}
    # Sửa lỗi B007: Đổi tên day, period thành _day, _period
    for (unit_id, _day, _period, room_id), var in ctx.s.items():
        unit = next((u for u in problem.lesson_units if u.id == unit_id), None)
        if not unit:
            hints[var] = 0
            continue

        suitable_rooms = rooms_by_type.get(unit.required_room_type, [])
        if room_id in suitable_rooms:
            hints[var] = 1
        else:
            hints[var] = 0
    return hints


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-class", type=int, nargs="+", default=[18, 21])
    parser.add_argument("--configs", nargs="+", default=list(CONFIGS))
    parser.add_argument("--objective", choices=["off", "on", "both"], default="off")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--time-limit", type=float, default=60)
    parser.add_argument("--use-hint", action="store_true", help="Sử dụng AddHint (gợi ý phòng)")
    args = parser.parse_args()
    options = SolveOptions(time_limit_s=args.time_limit, num_workers=args.workers)

    for per_class in args.per_class:
        problem, data = make_problem(per_class)
        for with_objective in {"off": [False], "on": [True], "both": [False, True]}[args.objective]:
            for name in args.configs:
                if args.use_hint:
                    if with_objective:
                        ctx = build_model(problem, optimization_encoders=CONFIGS[name])
                    else:
                        ctx = build_model(problem, optimization_encoders=CONFIGS[name])

                    hints = create_naive_hints(problem, ctx)
                    for var, value in hints.items():
                        ctx.model.AddHint(var, value)

                    solver = cp_model.CpSolver()
                    solver.parameters.max_time_in_seconds = args.time_limit
                    solver.parameters.num_workers = args.workers

                    started = time.time()
                    status = solver.solve(ctx.model)
                    elapsed = time.time() - started
                    obj_val = solver.objective_value if ctx.model.has_objective() else None
                    print(
                        f"per_class={per_class} units={len(problem.lesson_units)} "
                        f"objective={'on' if with_objective else 'off'} {name:<18} "
                        f"{solver.status_name(status):<10} {elapsed:6.1f}s obj={obj_val} "
                        f"[HINT ENABLED]",
                        flush=True,
                    )
                    continue

                if with_objective:
                    solver = build_default_solver(problem, data, CONFIGS[name])
                else:
                    solver = CpSatSolver(optimization_encoders=CONFIGS[name])
                started = time.time()
                result = solver.solve(problem, options)
                elapsed = time.time() - started
                bad = check_timetable(problem, result.timetable) if result.timetable else None
                print(
                    f"per_class={per_class} units={len(problem.lesson_units)} "
                    f"objective={'on' if with_objective else 'off'} {name:<18} "
                    f"{result.status.value:<10} {elapsed:6.1f}s obj={result.objective} "
                    f"violations={None if bad is None else len(bad)}",
                    flush=True,
                )


if __name__ == "__main__":
    main()
