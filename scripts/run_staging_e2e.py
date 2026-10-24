"""Script chạy E2E đầy đủ (Task 13):
Generator -> Solver/Staging -> Validator -> Lập danh sách lỗi theo mức độ.

Cách dùng:
    uv run python scripts/run_staging_e2e.py --seed 1 --time-limit 60
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
    parser = argparse.ArgumentParser(description="E2E Staging Full: Solver + Error Categorization")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--time-limit", type=float, default=60.0)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("docs/reports/staging_e2e_report.md"),
    )
    args = parser.parse_args()

    data = generate_hard(seed=args.seed)
    data["solver"] = {
        "time_limit_s": args.time_limit,
        "num_workers": args.workers,
        "random_seed": args.seed,
    }
    problem = problem_from_dict(data)
    print(
        f"[1/3] Generator: {len(problem.class_groups)} lớp, "
        f"{len(problem.teachers)} giáo viên, "
        f"{len(problem.rooms)} phòng, {len(problem.lesson_units)} tiết học"
    )

    print(f"[2/3] Đang chạy solver với {args.workers} luồng, tối đa {args.time_limit:.0f}s...")
    handler = make_solve_handler(build_default_solver, check_timetable)
    started = time.perf_counter()
    raw_response = handler(json.dumps(data).encode("utf-8"))
    result = json.loads(raw_response)
    elapsed = time.perf_counter() - started

    violations = result.get("violations", [])
    hard_violations = [v for v in violations if v.get("severity") == "HARD"]
    soft_violations = [v for v in violations if v.get("severity") == "SOFT"]

    print(
        f"[3/3] Trạng thái: {result.get('status')}, "
        f"Objective: {result.get('objective')}, Thời gian: {elapsed:.1f}s"
    )
    print(f"      Tổng số phân công: {len(result.get('assignments', []))}")
    print(f"      - Vi phạm HARD: {len(hard_violations)}")
    print(f"      - Vi phạm SOFT: {len(soft_violations)}")

    args.report.parent.mkdir(parents=True, exist_ok=True)

    total_violations = len(violations)
    num_hard = len(hard_violations)
    num_soft = len(soft_violations)

    report_content = f"""# Báo cáo E2E Staging Full (Task 13)

- **Thời gian thực thi**: {elapsed:.2f} giây
- **Tài nguyên**: {args.workers} luồng, giới hạn {args.time_limit:.0f}s
- **Trạng thái Solver**: `{result.get("status")}`
- **Tổng số phân công**: {len(result.get("assignments", []))}
- **Tổng số vi phạm**: {total_violations} (HARD: {num_hard}, SOFT: {num_soft})

## Chi tiết lỗi vi phạm theo mức độ

### 1. Vi phạm Ràng buộc Cứng (HARD Violations - {num_hard})
"""
    if hard_violations:
        for v in hard_violations:
            rule_id = v.get("rule_id", "UNKNOWN")
            msg = v.get("message", "Không có mô tả")
            report_content += f"- **[{rule_id}]**: {msg}\n"
    else:
        report_content += "*(Không có lỗi vi phạm cứng nào - Đạt yêu cầu)*\n"

    report_content += f"\n### 2. Vi phạm Ràng buộc Mềm (SOFT Violations - {len(soft_violations)})\n"
    if soft_violations:
        for v in soft_violations:
            rule_id = v.get("rule_id", "UNKNOWN")
            msg = v.get("message", "Không có mô tả")
            cost = v.get("cost", 0)
            report_content += f"- **[{rule_id}]**: {msg} (Trọng số/Chi phí: {cost})\n"
    else:
        report_content += "*(Không có lỗi vi phạm mềm)*\n"

    args.report.write_text(report_content, encoding="utf-8")
    print(f"Đã lưu báo cáo chi tiết tại: {args.report}")

    if hard_violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
