import json
from dataclasses import replace
from pathlib import Path

import pytest

from solver_helpers import OPTIONS
from timetable.application.use_cases.solve_timetable import SolveTimetable
from timetable.domain.entities import LessonUnit, Problem
from timetable.domain.services.timetable_checker import check_timetable
from timetable.domain.services.unit_consistency import check_units_match_courses
from timetable.infrastructure.problem_loader import (
    InvalidProblemError,
    load_problem,
    problem_from_dict,
)
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver

DOCS = Path(__file__).resolve().parents[2] / "docs" / "schema"


def _codes(problem: Problem) -> set[str]:
    return {i.code for i in check_units_match_courses(problem)}


def test_original_sample_is_consistent(sample_problem: Problem) -> None:
    assert check_units_match_courses(sample_problem) == []


def test_missing_unit_is_reported(sample_problem: Problem) -> None:
    problem = replace(sample_problem, lesson_units=sample_problem.lesson_units[1:])
    assert _codes(problem) == {"course_periods_mismatch"}


def test_unit_with_other_teacher_is_reported(sample_problem: Problem) -> None:
    first = sample_problem.lesson_units[0]
    bad = replace(first, teacher_id="T-OTHER")
    problem = replace(sample_problem, lesson_units=(bad, *sample_problem.lesson_units[1:]))
    assert _codes(problem) == {"unit_mismatch"}


def test_unknown_course_duplicate_and_bad_duration(sample_problem: Problem) -> None:
    extra = (
        LessonUnit("X1", "NOPE", "C-A1", "T01"),
        replace(sample_problem.lesson_units[0]),
        LessonUnit("BIG", sample_problem.courses[0].id, "C-A1", "T01", duration=3),
    )
    problem = replace(sample_problem, lesson_units=(*sample_problem.lesson_units, *extra))
    codes = _codes(problem)
    assert {"unit_unknown_course", "unit_duplicated", "unit_duration"} <= codes


def test_loader_rejects_inconsistent_data() -> None:
    data = json.loads((DOCS / "input.sample.json").read_text(encoding="utf-8"))
    data["lesson_units"] = data["lesson_units"][1:]
    with pytest.raises(InvalidProblemError, match="course_periods_mismatch"):
        problem_from_dict(data)


def test_block_sample_splits_three_period_courses_into_two_plus_one() -> None:
    problem = load_problem(DOCS / "input.blocks.sample.json")
    assert problem.block_starts == (0, 2, 4)
    by_course: dict[str, list[int]] = {}
    for u in problem.lesson_units:
        by_course.setdefault(u.course_id, []).append(u.duration)
    for course in problem.courses:
        durations = sorted(by_course[course.id], reverse=True)
        assert sum(durations) == course.periods_per_week
        assert durations == {2: [2], 3: [2, 1]}[course.periods_per_week]


def test_block_sample_is_solvable_and_valid() -> None:
    problem = load_problem(DOCS / "input.blocks.sample.json")
    outcome = SolveTimetable(CpSatSolver(), check_timetable).execute(problem, OPTIONS)
    assert outcome.ok, outcome.violations
