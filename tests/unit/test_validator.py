from solver_helpers import make_problem, one_day_grid, unit
from timetable.domain.entities import Assignment, Timetable
from timetable.domain.validator import Validator

SIX = one_day_grid(1, 2, 3, 4, 5, 6)


def test_empty_timetable_object_is_reported() -> None:
    violations = Validator().validate(Timetable())
    assert [v.rule_id for v in violations] == ["TIMETABLE_EMPTY"]


def test_without_problem_only_emptiness_is_checked() -> None:
    assert Validator().validate([Assignment("a", 0, 0, "R1")]) == []


def test_with_problem_runs_hard_constraint_checks() -> None:
    units = [unit("a", "C", "T1", duration=2), unit("b", "C", "T2", duration=2)]
    problem = make_problem(units, grid=SIX, block_starts=(0, 2, 4))
    good = Timetable((Assignment("a", 0, 0, "R1"), Assignment("b", 0, 4, "R1")))
    bad = Timetable((Assignment("a", 0, 0, "R1"), Assignment("b", 0, 2, "R1")))
    assert Validator().validate(good, problem) == []
    assert [v.rule_id for v in Validator().validate(bad, problem)] == ["MAX_CONSECUTIVE"]


def test_violation_is_hashable_and_defaults_to_hard() -> None:
    violations = Validator().validate(Timetable())
    assert violations[0].severity == "HARD"
    assert len(set(violations)) == 1
