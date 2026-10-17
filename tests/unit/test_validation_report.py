from timetable.domain.entities import Problem
from timetable.domain.entities.timetable import Assignment, Timetable
from timetable.domain.rules.soft_constraints import W_G316, W_ROOM, W_SAT, reference_cost
from timetable.domain.services.validation_report import (
    build_report,
    soft_violations,
)
from timetable.infrastructure.generator import generate_v1
from timetable.infrastructure.problem_loader import problem_from_dict


def _problem() -> Problem:
    return problem_from_dict(generate_v1())


def _standard_unit(problem: Problem):  # type: ignore[no-untyped-def]
    standard = {c.id for c in problem.courses if c.required_room_type == "standard"}
    return next(u for u in problem.lesson_units if u.course_id in standard)


def test_empty_timetable_has_no_soft_violation() -> None:
    assert soft_violations(_problem(), Timetable()) == []


def test_saturday_and_g316_are_reported() -> None:
    problem = _problem()
    unit = _standard_unit(problem)
    timetable = Timetable((Assignment(unit.id, 5, 0, "G316"),))
    found = {v.rule_id: v.penalty for v in soft_violations(problem, timetable)}
    assert found == {"AVOID_SATURDAY": W_SAT, "RESERVE_MBA_ROOM": W_G316}


def test_changing_room_inside_a_course_is_reported() -> None:
    problem = _problem()
    first = _standard_unit(problem)
    second = next(
        u for u in problem.lesson_units if u.course_id == first.course_id and u.id != first.id
    )
    timetable = Timetable((Assignment(first.id, 0, 0, "G314"), Assignment(second.id, 1, 0, "G317")))
    found = soft_violations(problem, timetable)
    assert [(v.rule_id, v.penalty) for v in found] == [("ROOM_STABILITY", W_ROOM)]


def test_total_penalty_matches_reference_cost() -> None:
    problem = _problem()
    unit = _standard_unit(problem)
    timetable = Timetable((Assignment(unit.id, 5, 0, "G316"),))
    mba = {c.id for c in problem.courses if c.required_room_type == "mba"}
    schedule = [(unit.course_id, 5, 0, "G316")]
    expected = sum(reference_cost(schedule, {5}, mba, "G316").values())
    assert build_report(problem, timetable).summary()["soft_penalty"] == expected


def test_summary_counts_hard_and_soft() -> None:
    problem = _problem()
    unit = _standard_unit(problem)
    report = build_report(problem, Timetable((Assignment(unit.id, 5, 0, "G316"),)))
    summary = report.summary()
    assert summary["hard"] > 0  # các ca học còn lại chưa được xếp (UNIT_UNASSIGNED)
    assert summary["soft"] == 2
    assert summary["total"] == summary["hard"] + summary["soft"]
    assert summary["by_rule"]["UNIT_UNASSIGNED"] == summary["hard"]
