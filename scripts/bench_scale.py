"""Đo quy mô: bộ sinh "khó" với số lớp tăng dần, giải một pha hoặc hai pha (khả thi rồi tối ưu).

Chạy từ thư mục gốc repo:
    uv run python scripts/bench_scale.py --classes 30 50 --teachers 20 --seeds 1 2 --time-limit 60

Lưu ý: số giáo viên phải tăng theo số lớp. Mỗi giáo viên có 36 tiết/tuần (6 ngày x 6 tiết), nên
8 giáo viên (mặc định của bộ "khó") chỉ phục vụ tối đa 288 tiết; 50 lớp cần khoảng 358 tiết và
sẽ vô nghiệm hoặc không tìm ra nghiệm.
"""

import argparse
import time
from typing import Any

from ortools.sat.python import cp_model

from timetable.application.dto.solve import SolveOptions
from timetable.domain.entities import Problem
from timetable.infrastructure.generator import generate_hard
from timetable.infrastructure.problem_loader import problem_from_dict
from timetable.infrastructure.solver.builder import build_model
from timetable.infrastructure.solver.default_solver import (
    MBA_ROOM_ID,
    MBA_ROOM_TYPE,
    SATURDAYS,
    build_default_solver,
    soft_weights_from_dict,
)
from timetable.infrastructure.solver.soft_adapter import SoftObjectiveApplier
from timetable.infrastructure.solver.soft_objective import add_soft_objective


def single_phase(problem: Problem, data: dict[str, Any], options: SolveOptions) -> str:
    result = build_default_solver(problem, data).solve(problem, options)
    terms = result.cost_terms or {}
    return (
        f"{result.status.name:<10} obj={result.objective} {terms} {result.stats.wall_time_s:.1f}s"
    )


def two_phase(problem: Problem, data: dict[str, Any], options: SolveOptions) -> str:
    """Pha 1 tìm nghiệm khả thi (không mục tiêu), pha 2 tối ưu với AddHint từ pha 1."""
    started = time.perf_counter()
    first_ctx = build_model(problem)
    first = cp_model.CpSolver()
    first.parameters.max_time_in_seconds = options.time_limit_s / 4
    first.parameters.num_workers = options.num_workers
    first.parameters.random_seed = options.random_seed
    first_status = first.solve(first_ctx.model)
    if first_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return f"pha 1 {first.status_name(first_status)}"

    mba = {c.id for c in problem.courses if c.required_room_type == MBA_ROOM_TYPE}
    objective = SoftObjectiveApplier(
        add_soft_objective,
        saturdays=SATURDAYS,
        mba_course_ids=mba,
        mba_room_id=MBA_ROOM_ID,
        weights=soft_weights_from_dict(data),
    )
    ctx = build_model(problem, objective=objective)
    for key, var in first_ctx.s.items():
        ctx.model.add_hint(ctx.s[key], first.boolean_value(var))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(1.0, options.time_limit_s - first.wall_time)
    solver.parameters.num_workers = options.num_workers
    solver.parameters.random_seed = options.random_seed
    status = solver.solve(ctx.model)
    value = solver.objective_value if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None
    return (
        f"{solver.status_name(status):<10} obj={value} "
        f"pha 1 {first.wall_time:.1f}s, tổng {time.perf_counter() - started:.1f}s"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--classes", type=int, nargs="+", default=[30, 50])
    parser.add_argument("--teachers", type=int, default=20)
    parser.add_argument("--seeds", type=int, nargs="+", default=[1])
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--time-limit", type=float, default=60)
    parser.add_argument("--strategy", choices=["single", "staged"], default="single")
    args = parser.parse_args()

    run = single_phase if args.strategy == "single" else two_phase
    for classes in args.classes:
        for seed in args.seeds:
            data = generate_hard(seed=seed, num_classes=classes, num_teachers=args.teachers)
            problem = problem_from_dict(data)
            options = SolveOptions(
                time_limit_s=args.time_limit, num_workers=args.workers, random_seed=seed
            )
            print(
                f"classes={classes} teachers={args.teachers} seed={seed} "
                f"units={len(problem.lesson_units)} {args.strategy}: "
                f"{run(problem, data, options)}",
                flush=True,
            )


if __name__ == "__main__":
    main()
