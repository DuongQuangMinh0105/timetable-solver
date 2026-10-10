import json
from pathlib import Path

from timetable.domain.entities import (
    ClassGroup,
    Course,
    LessonUnit,
    Problem,
    Room,
    Teacher,
    TimeGrid,
)

SAMPLE = Path(__file__).resolve().parents[2] / "docs" / "schema" / "input.sample.json"


def load_problem(path: Path) -> Problem:
    data = json.loads(path.read_text(encoding="utf-8"))
    grid = data["grid"]
    return Problem(
        rooms=tuple(
            Room(
                id=r["id"],
                name=r["name"],
                capacity=r["capacity"],
                room_type=r["room_type"],
                also_supports=tuple(r["also_supports"]),
            )
            for r in data["rooms"]
        ),
        teachers=tuple(Teacher(**t) for t in data["teachers"]),
        class_groups=tuple(ClassGroup(**c) for c in data["class_groups"]),
        courses=tuple(Course(**c) for c in data["courses"]),
        lesson_units=tuple(LessonUnit(**u) for u in data["lesson_units"]),
        grid=TimeGrid(
            days=grid["days"],
            periods=grid["periods"],
            allowed_periods=tuple(grid["allowed_periods"]),
        ),
        max_consecutive_periods=data["constraints"]["max_consecutive_periods"],
    )


def test_sample_loads_and_references_are_consistent() -> None:
    problem = load_problem(SAMPLE)
    class_ids = {c.id for c in problem.class_groups}
    teacher_ids = {t.id for t in problem.teachers}
    course_ids = {c.id for c in problem.courses}

    assert all(c.class_id in class_ids and c.teacher_id in teacher_ids for c in problem.courses)
    assert all(u.course_id in course_ids for u in problem.lesson_units)
    assert len({u.id for u in problem.lesson_units}) == len(problem.lesson_units)


def test_sample_units_match_periods_per_week() -> None:
    problem = load_problem(SAMPLE)
    for course in problem.courses:
        count = sum(1 for u in problem.lesson_units if u.course_id == course.id)
        assert count == course.periods_per_week


def test_sample_every_unit_has_a_valid_room() -> None:
    problem = load_problem(SAMPLE)
    size = {c.id: c.size for c in problem.class_groups}
    for unit in problem.lesson_units:
        assert any(
            room.can_host(unit.required_room_type) and room.capacity >= size[unit.class_id]
            for room in problem.rooms
        ), unit.id


def test_sample_uses_real_rooms_and_excludes_non_teaching_rooms() -> None:
    problem = load_problem(SAMPLE)
    ids = {r.id for r in problem.rooms}
    assert {"G313", "G316", "G502"} <= ids
    assert not ids & {"G311", "G312", "G315", "G320", "G501", "G505", "G506", "G507"}
    assert problem.max_consecutive_periods == 2
