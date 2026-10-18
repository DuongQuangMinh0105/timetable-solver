"""Chạy E2E cục bộ: generator -> load_problem -> solver -> validator.

Cách chạy (từ thư mục gốc repo, PowerShell):

    $env:PYTHONPATH = "src"
    uv run python scripts/run_e2e.py                          # tất cả profile
    uv run python scripts/run_e2e.py --profile spec --seed 1
    uv run python scripts/run_e2e.py --units blocks --out e2e_report.md

Với mỗi profile, script in: trạng thái solver, thời gian giải, giá trị mục tiêu,
ba số hạng phạt (room, sat, g316) so với `reference_cost`, và các vi phạm cứng do
validator tìm được. Dán phần báo cáo này khi báo lỗi cho P1.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from timetable.application.dto.solve import SolveOptions
from timetable.domain.entities import Problem, Timetable
from timetable.domain.rules.soft_constraints import reference_cost
from timetable.domain.services.unit_splitter import lesson_units_for_course
from timetable.domain.validator import Validator
from timetable.infrastructure.generator import INFEASIBLE_PROFILES, PROFILES, generate_profile
from timetable.infrastructure.problem_loader import load_problem
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver

SATURDAY = 5
R_MBA = "G316"
ALIGNED_STARTS = (0, 2, 4)
SOLVED = {"OPTIMAL", "FEASIBLE"}


@dataclass
class RunResult:
    profile: str
    units: int
    status: str
    seconds: float
    objective: float | None
    cost_terms: dict[str, int]
    reference: dict[str, int] | None
    hard: Counter[str]
    messages: list[str] = field(default_factory=list)

    @property
    def expected_infeasible(self) -> bool:
        return self.profile in INFEASIBLE_PROFILES

    @property
    def cost_matches(self) -> bool | None:
        """None nếu không có gì để so sánh."""
        if self.reference is None or not self.cost_terms:
            return None
        return all(self.cost_terms.get(k) == v for k, v in self.reference.items())

    @property
    def verdict(self) -> str:
        if self.expected_infeasible:
            if self.status == "INFEASIBLE":
                return "OK"
            return "CHƯA CHỨNG MINH" if self.status == "UNKNOWN" else "KHÁC DỰ KIẾN"
        if self.status not in SOLVED:
            return "KHÔNG CÓ LỊCH"
        if self.hard or self.cost_matches is False:
            return "LỖI"
        return "OK"


def _load(data: dict[str, Any], units: str) -> Problem:
    """Ghi JSON ra file tạm rồi nạp bằng `load_problem`, đúng đường đi thật."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "input.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        problem = load_problem(path)
    if units == "blocks":
        blocks = tuple(u for c in problem.courses for u in lesson_units_for_course(c))
        problem = replace(problem, lesson_units=blocks, block_starts=ALIGNED_STARTS)
    return problem


def _reference(problem: Problem, timetable: Timetable) -> dict[str, int]:
    unit_course = {u.id: u.course_id for u in problem.lesson_units}
    mba = {c.id for c in problem.courses if c.required_room_type == "mba"}
    schedule = [
        (unit_course[a.unit_id], a.day, a.period, a.room_id)
        for a in timetable.assignments
        if a.unit_id in unit_course
    ]
    return reference_cost(schedule, sat_days={SATURDAY}, mba=mba, r_mba=R_MBA)


def run_profile(name: str, seed: int, units: str, options: SolveOptions) -> RunResult:
    problem = _load(generate_profile(name, seed), units)
    started = time.perf_counter()
    result = CpSatSolver().solve(problem, options)
    seconds = time.perf_counter() - started

    hard: Counter[str] = Counter()
    messages: list[str] = []
    reference: dict[str, int] | None = None
    if result.timetable is not None:
        violations = Validator().validate(problem, result.timetable)
        hard.update(v.rule_id for v in violations)
        messages = [f"{v.rule_id}: {v.description}" for v in violations[:10]]
        reference = _reference(problem, result.timetable)

    return RunResult(
        profile=name,
        units=len(problem.lesson_units),
        status=str(result.status),
        seconds=seconds,
        objective=result.objective,
        cost_terms=dict(result.cost_terms),
        reference=reference,
        hard=hard,
        messages=messages,
    )


def _fmt_terms(terms: dict[str, int] | None) -> str:
    if not terms:
        return "-"
    return ", ".join(f"{k}={terms[k]}" for k in ("room", "sat", "g316") if k in terms)


def _fmt_hard(hard: Counter[str]) -> str:
    return "-" if not hard else ", ".join(f"{rule} x{n}" for rule, n in sorted(hard.items()))


def format_report(results: list[RunResult], seed: int, units: str) -> str:
    lines = [
        f"# Báo cáo E2E (seed={seed}, units={units})",
        "",
        "| Profile | Unit | Trạng thái | Giây | Mục tiêu | Solver (room/sat/g316) "
        "| reference_cost | Vi phạm cứng | Kết luận |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        objective = "-" if r.objective is None else f"{r.objective:g}"
        lines.append(
            f"| {r.profile} | {r.units} | {r.status} | {r.seconds:.1f} | {objective} "
            f"| {_fmt_terms(r.cost_terms)} | {_fmt_terms(r.reference)} "
            f"| {_fmt_hard(r.hard)} | {r.verdict} |"
        )
    problems = [r for r in results if r.verdict != "OK"]
    if problems:
        lines += ["", "## Chi tiết các lần chạy có vấn đề"]
        for r in problems:
            lines += ["", f"### {r.profile}: {r.verdict}"]
            if r.cost_matches is False:
                lines.append(
                    f"- Số hạng phạt của solver ({_fmt_terms(r.cost_terms)}) "
                    f"khác `reference_cost` ({_fmt_terms(r.reference)})."
                )
            lines += [f"- {m}" for m in r.messages]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--profile", choices=[*PROFILES, "all"], default="all")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--units", choices=["json", "blocks"], default="json")
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    options = SolveOptions(
        time_limit_s=args.time_limit, num_workers=args.workers, random_seed=args.seed
    )
    names = list(PROFILES) if args.profile == "all" else [args.profile]
    results = []
    for name in names:
        print(f"Đang chạy {name} ...", file=sys.stderr, flush=True)
        results.append(run_profile(name, args.seed, args.units, options))

    report = format_report(results, args.seed, args.units)
    print(report)
    if args.out is not None:
        args.out.write_text(report, encoding="utf-8")
    return 0 if all(r.verdict == "OK" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
