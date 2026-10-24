"""`domain/validation_report.py` (điểm phạt mềm) phải khớp với điểm phạt mà bộ giải tính."""

import json
from pathlib import Path

from timetable.application.dto.solve import SolveOptions
from timetable.domain.entities import Assignment, Problem, Timetable
from timetable.domain.services.timetable_checker import check_timetable
from timetable.domain.validation_report import summarize_validation, validate_soft
from timetable.infrastructure.problem_loader import problem_from_dict
from timetable.infrastructure.solver.default_solver import build_default_solver

SAMPLE = Path("docs/schema/input.blocks.sample.json")


def _solved() -> tuple[Problem, Timetable, int]:
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    problem = problem_from_dict(data)
    result = build_default_solver(problem, data).solve(
        problem, SolveOptions(time_limit_s=20, num_workers=1)
    )
    assert result.timetable is not None and result.objective is not None
    return problem, result.timetable, int(result.objective)


def test_total_penalty_matches_the_solver_objective() -> None:
    problem, timetable, objective = _solved()
    hard = check_timetable(problem, timetable)

    summary = summarize_validation(problem, timetable, hard)

    assert summary.hard_count == 0
    assert summary.total_penalty == objective


def test_soft_violation_is_reported_for_a_saturday_session() -> None:
    problem, timetable, _ = _solved()
    first = timetable.assignments[0]
    on_saturday = Timetable((Assignment(first.unit_id, 5, first.period, first.room_id),))

    violations = validate_soft(problem, on_saturday)

    assert [v.rule_id for v in violations] == ["SOFT_SAT"]
    assert all(v.severity == "SOFT" for v in violations)
