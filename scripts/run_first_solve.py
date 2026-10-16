"""Chạy solver trên dữ liệu khó, chạy validator trên kết quả, ghi báo cáo cho P1.

    python scripts/run_first_solve.py --seed 1 --time-limit 60
"""

import argparse
import time
from collections import Counter
from pathlib import Path

from timetable.application.dto.solve import SolveOptions
from timetable.domain.services.timetable_checker import check_timetable
from timetable.domain.validator import Validator
from timetable.infrastructure.generator import HARD_PARAMS, generate_hard
from timetable.infrastructure.problem_loader import problem_from_dict
from timetable.infrastructure.solver.default_solver import build_default_solver


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--time-limit", type=float, default=60)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--out", type=Path, default=Path("docs/reports/first_solve_run.md"))
    args = parser.parse_args()

    data = generate_hard(seed=args.seed)
    problem = problem_from_dict(data)
    solver = build_default_solver(problem, data)
    options = SolveOptions(
        time_limit_s=args.time_limit, num_workers=args.workers, random_seed=args.seed
    )

    started = time.time()
    result = solver.solve(problem, options)
    elapsed = time.time() - started

    lines = [
        "# Báo cáo lần giải đầu tiên (dữ liệu khó)",
        "",
        f"- Seed: {args.seed}",
        f"- Tham số generator: {HARD_PARAMS}",
        f"- Số ca học: {len(problem.lesson_units)}",
        f"- Trạng thái solver: {result.status.value}",
        f"- Thời gian giải: {elapsed:.1f}s (giới hạn {args.time_limit}s, {args.workers} workers)",
        f"- Lệnh chạy lại: `python scripts/run_first_solve.py --seed {args.seed}"
        f" --time-limit {args.time_limit} --workers {args.workers}`",
        "",
    ]

    if result.timetable is None:
        lines.append("**Solver không trả về thời khóa biểu, không có gì để validate.**")
    else:
        violations = Validator().validate(result.timetable, problem)
        by_rule = Counter(v.rule_id for v in violations)
        checker = check_timetable(problem, result.timetable)
        lines += [
            f"- Validator: {len(violations)} vi phạm",
            f"- timetable_checker: {len(checker)} vi phạm",
            "",
            "| Rule | Số vi phạm |",
            "|---|---|",
            *(f"| {rule} | {count} |" for rule, count in sorted(by_rule.items())),
            "",
            "## Ví dụ",
            *(f"- [{v.severity}] {v.rule_id}: {v.description}" for v in violations[:5]),
        ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
