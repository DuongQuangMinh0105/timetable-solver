"""E2E cục bộ thật: Generator -> bộ giải CP-SAT (cùng handler với worker) -> bộ kiểm tra độc lập.

Không cần Postgres hay API. Dùng `--workers` và `--time-limit` để mô phỏng tài nguyên của nơi chạy.
Ví dụ: uv run python scripts/run_local_e2e.py --seed 1 --workers 1 --time-limit 30
"""

import argparse
import json
import time
from pathlib import Path

from timetable.domain.services.timetable_checker import check_timetable
from timetable.infrastructure.generator import generate_hard
from timetable.infrastructure.problem_loader import problem_from_dict
from timetable.infrastructure.solver.default_solver import build_default_solver
from timetable.infrastructure.solver.solve_handler import make_solve_handler


def main() -> None:
    parser = argparse.ArgumentParser(description="E2E cục bộ: Generator -> Solver -> Validator")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--classes", type=int, default=None, help="Ghi đè số lớp của bộ 'khó'")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--time-limit", type=float, default=60.0)
    parser.add_argument("--report", type=Path, default=Path("docs/reports/e2e_local_report.md"))
    args = parser.parse_args()

    overrides = {} if args.classes is None else {"num_classes": args.classes}
    data = generate_hard(seed=args.seed, **overrides)
    data["solver"] = {
        "time_limit_s": args.time_limit,
        "num_workers": args.workers,
        "random_seed": args.seed,
    }
    problem = problem_from_dict(data)
    print(
        f"[1/3] Generator: {len(problem.class_groups)} lớp, {len(problem.teachers)} giáo viên, "
        f"{len(problem.rooms)} phòng, {len(problem.lesson_units)} ca học"
    )

    print(f"[2/3] Giải với {args.workers} luồng, tối đa {args.time_limit:.0f}s ...")
    handler = make_solve_handler(build_default_solver, check_timetable)
    started = time.perf_counter()
    result = json.loads(handler(json.dumps(data).encode("utf-8")))
    elapsed = time.perf_counter() - started

    hard = [v for v in result["violations"] if v["severity"] == "HARD"]
    print(f"[3/3] Trạng thái {result['status']}, objective {result['objective']}, {elapsed:.1f}s")
    print(f"      {len(result['assignments'])} phân công, vi phạm: {len(result['violations'])}")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    terms = ", ".join(f"{k}={v}" for k, v in result["cost_terms"].items()) or "không có"
    args.report.write_text(
        f"""# Báo cáo E2E cục bộ

- **Thời gian chạy**: {time.strftime("%Y-%m-%d %H:%M:%S")}
- **Seed**: {args.seed}
- **Quy mô**: {len(problem.class_groups)} lớp, {len(problem.teachers)} giáo viên, \
{len(problem.rooms)} phòng, {len(problem.lesson_units)} ca học
- **Tài nguyên**: {args.workers} luồng, giới hạn {args.time_limit:.0f}s
- **Trạng thái solver**: {result["status"]}
- **Thời gian giải thực tế**: {elapsed:.1f}s
- **Objective**: {result["objective"]} ({terms})
- **Số phân công**: {len(result["assignments"])}
- **Vi phạm cứng**: {len(hard)}
- **Tổng vi phạm báo cáo**: {len(result["violations"])}
""",
        encoding="utf-8",
    )
    print(f"[+] Đã lưu báo cáo: {args.report}")
    if hard:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
