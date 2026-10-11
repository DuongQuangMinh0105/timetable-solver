from timetable.domain.entities import ClassGroup, Course, LessonUnit, Problem, Room, Teacher
from timetable.domain.services.room_policy import allowed_rooms_by_unit


def _ids(rooms: tuple[Room, ...]) -> set[str]:
    return {r.id for r in rooms}


def test_mba_unit_only_in_mba_room(sample_problem: Problem) -> None:
    allowed = allowed_rooms_by_unit(sample_problem)
    mba_units = [u for u in sample_problem.lesson_units if u.required_room_type == "mba"]
    assert mba_units
    for unit in mba_units:
        assert _ids(allowed[unit.id]) == {"G316"}


def test_art_unit_only_in_art_room(sample_problem: Problem) -> None:
    allowed = allowed_rooms_by_unit(sample_problem)
    art_units = [u for u in sample_problem.lesson_units if u.required_room_type == "art"]
    assert art_units
    for unit in art_units:
        assert _ids(allowed[unit.id]) == {"G313"}


def test_standard_unit_can_use_standard_rooms_and_mba_room_but_not_art_room(
    sample_problem: Problem,
) -> None:
    allowed = allowed_rooms_by_unit(sample_problem)
    standard_units = [u for u in sample_problem.lesson_units if u.required_room_type == "standard"]
    for unit in standard_units:
        ids = _ids(allowed[unit.id])
        assert "G316" in ids
        assert "G502" in ids
        assert "G313" not in ids
        assert not ids & {"G311", "G312"}


def test_capacity_filters_rooms() -> None:
    problem = Problem(
        rooms=(Room("A", "A", 20), Room("B", "B", 30)),
        teachers=(Teacher("T1", "T1"),),
        class_groups=(ClassGroup("C1", "C1", 25),),
        courses=(Course("M1", "M1", "C1", "T1", 1),),
        lesson_units=(LessonUnit("U1", "M1", "C1", "T1"),),
    )
    assert _ids(allowed_rooms_by_unit(problem)["U1"]) == {"B"}
