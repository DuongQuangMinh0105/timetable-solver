import json
from dataclasses import replace
from pathlib import Path

import pytest

from solver_helpers import OPTIONS
from timetable.application.use_cases.solve_timetable import SolveTimetable
from timetable.domain.entities import ClassGroup, LessonUnit, Problem, Teacher
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
    problem = replace(
        sample_problem,
        teachers=(*sample_problem.teachers, Teacher("T-OTHER", "Other teacher")),
        lesson_units=(bad, *sample_problem.lesson_units[1:]),
    )
    assert _codes(problem) == {"unit_mismatch"}


def test_unit_with_other_existing_class_is_reported(sample_problem: Problem) -> None:
    first = sample_problem.lesson_units[0]
    bad = replace(first, class_id="C-OTHER")
    problem = replace(
        sample_problem,
        class_groups=(*sample_problem.class_groups, ClassGroup("C-OTHER", "Other class", 20)),
        lesson_units=(bad, *sample_problem.lesson_units[1:]),
    )

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


@pytest.mark.parametrize(
    "collection,issue_code",
    [
        pytest.param("rooms", "room_duplicated", id="room-id"),
        pytest.param("teachers", "teacher_duplicated", id="teacher-id"),
        pytest.param("class_groups", "class_duplicated", id="class-id"),
        pytest.param("courses", "course_duplicated", id="course-id"),
    ],
)
def test_duplicate_entity_ids_are_reported(
    sample_problem: Problem,
    collection: str,
    issue_code: str,
) -> None:
    entities = getattr(sample_problem, collection)
    duplicated = replace(sample_problem, **{collection: (*entities, entities[0])})

    assert issue_code in _codes(duplicated)


@pytest.mark.parametrize(
    "field,value,issue_code",
    [
        pytest.param(
            "class_id",
            "MISSING-CLASS",
            "course_unknown_class",
            id="course-class-reference",
        ),
        pytest.param(
            "teacher_id",
            "MISSING-TEACHER",
            "course_unknown_teacher",
            id="course-teacher-reference",
        ),
    ],
)
def test_course_references_must_exist(
    sample_problem: Problem,
    field: str,
    value: str,
    issue_code: str,
) -> None:
    course = replace(sample_problem.courses[0], **{field: value})
    problem = replace(sample_problem, courses=(course, *sample_problem.courses[1:]))

    assert issue_code in _codes(problem)


@pytest.mark.parametrize(
    "field,value,issue_code",
    [
        pytest.param("class_id", "MISSING-CLASS", "unit_unknown_class", id="unit-class-reference"),
        pytest.param(
            "teacher_id",
            "MISSING-TEACHER",
            "unit_unknown_teacher",
            id="unit-teacher-reference",
        ),
        pytest.param("required_room_type", "mba", "unit_mismatch", id="unit-room-type"),
    ],
)
def test_unit_references_and_room_type_must_match_course(
    sample_problem: Problem,
    field: str,
    value: str,
    issue_code: str,
) -> None:
    unit = replace(sample_problem.lesson_units[0], **{field: value})
    problem = replace(
        sample_problem,
        lesson_units=(unit, *sample_problem.lesson_units[1:]),
    )

    assert issue_code in _codes(problem)


def test_loader_rejects_inconsistent_data() -> None:
    data = json.loads((DOCS / "input.sample.json").read_text(encoding="utf-8"))
    data["lesson_units"] = data["lesson_units"][1:]
    with pytest.raises(InvalidProblemError, match="course_periods_mismatch"):
        problem_from_dict(data)


@pytest.mark.parametrize(
    "case",
    [
        "course-unknown-class",
        "course-unknown-teacher",
        "unit-unknown-course",
        "unit-unknown-class",
        "unit-unknown-teacher",
        "unit-room-type-mismatch",
        "duplicate-room-id",
    ],
)
def test_loader_rejects_invalid_entity_references_and_duplicate_ids(case: str) -> None:
    data = json.loads((DOCS / "input.sample.json").read_text(encoding="utf-8"))
    unit = data["lesson_units"][0]
    if case == "course-unknown-class":
        data["courses"][0]["class_id"] = "MISSING-CLASS"
        expected_code = "course_unknown_class"
    elif case == "course-unknown-teacher":
        data["courses"][0]["teacher_id"] = "MISSING-TEACHER"
        expected_code = "course_unknown_teacher"
    elif case == "unit-unknown-course":
        unit["course_id"] = "MISSING-COURSE"
        expected_code = "unit_unknown_course"
    elif case == "unit-unknown-class":
        unit["class_id"] = "MISSING-CLASS"
        expected_code = "unit_unknown_class"
    elif case == "unit-unknown-teacher":
        unit["teacher_id"] = "MISSING-TEACHER"
        expected_code = "unit_unknown_teacher"
    elif case == "unit-room-type-mismatch":
        unit["required_room_type"] = "unavailable"
        expected_code = "unit_mismatch"
    else:
        data["rooms"].append(data["rooms"][0].copy())
        expected_code = "room_duplicated"

    with pytest.raises(InvalidProblemError, match=expected_code):
        problem_from_dict(data)


@pytest.mark.parametrize(
    "case,weights",
    [
        pytest.param("negative", {"avoid_saturday": -1}, id="negative"),
        pytest.param("fractional", {"avoid_saturday": 1.5}, id="fractional"),
        pytest.param("whole-float", {"avoid_saturday": 1.0}, id="whole-float"),
        pytest.param("numeric-string", {"avoid_saturday": "1"}, id="numeric-string"),
        pytest.param("boolean", {"avoid_saturday": True}, id="boolean"),
        pytest.param("unsupported-key", {"unknown": 1}, id="unsupported-key"),
        pytest.param("not-an-object", ["avoid_saturday", 1], id="not-an-object"),
    ],
)
def test_loader_rejects_invalid_soft_weights(case: str, weights: object) -> None:
    data = json.loads((DOCS / "input.sample.json").read_text(encoding="utf-8"))
    data["soft_weights"] = weights

    with pytest.raises(InvalidProblemError, match="soft_weights"):
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
