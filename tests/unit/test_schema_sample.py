from timetable.domain.entities import Problem


def test_sample_loads_and_references_are_consistent(sample_problem: Problem) -> None:
    problem = sample_problem
    class_ids = {c.id for c in problem.class_groups}
    teacher_ids = {t.id for t in problem.teachers}
    course_ids = {c.id for c in problem.courses}

    assert all(c.class_id in class_ids and c.teacher_id in teacher_ids for c in problem.courses)
    assert all(u.course_id in course_ids for u in problem.lesson_units)
    assert len({u.id for u in problem.lesson_units}) == len(problem.lesson_units)


def test_sample_units_match_periods_per_week(sample_problem: Problem) -> None:
    for course in sample_problem.courses:
        count = sum(1 for u in sample_problem.lesson_units if u.course_id == course.id)
        assert count == course.periods_per_week


def test_sample_every_unit_has_a_valid_room(sample_problem: Problem) -> None:
    size = {c.id: c.size for c in sample_problem.class_groups}
    for unit in sample_problem.lesson_units:
        assert any(
            room.can_host(unit.required_room_type) and room.capacity >= size[unit.class_id]
            for room in sample_problem.rooms
        ), unit.id


def test_sample_uses_real_rooms_and_excludes_non_teaching_rooms(sample_problem: Problem) -> None:
    ids = {r.id for r in sample_problem.rooms}
    assert {"G313", "G316", "G502"} <= ids
    assert not ids & {"G311", "G312", "G315", "G320", "G501", "G505", "G506", "G507"}
    assert sample_problem.max_consecutive_periods == 2
