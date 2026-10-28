"""Ca cố định: người dùng khóa một ca vào ô, bộ giải phải giữ nguyên và xếp phần còn lại."""

import json
from dataclasses import replace

import pytest

from solver_helpers import (
    check_valid,
    make_problem,
    one_day_grid,
    solve,
    unit,
)
from timetable.application.dto.solve import SolveStatus
from timetable.domain.entities import Assignment
from timetable.domain.services.timetable_checker import check_timetable
from timetable.infrastructure.generator import generate_v1
from timetable.infrastructure.problem_loader import InvalidProblemError, problem_from_dict
from timetable.infrastructure.solver.default_solver import build_default_solver
from timetable.infrastructure.solver.solve_handler import make_solve_handler

GRID = one_day_grid(1, 2, 3, 4)


def _problem(*fixed: Assignment):  # type: ignore[no-untyped-def]
    base = make_problem([unit("u1", "C1", "T1"), unit("u2", "C2", "T1")], grid=GRID)
    return replace(base, fixed_assignments=tuple(fixed))


def test_fixed_assignment_is_kept() -> None:
    fixed = Assignment("u1", 0, 3, "R2")
    result = solve(_problem(fixed))
    assert result.status in {SolveStatus.OPTIMAL, SolveStatus.FEASIBLE}
    assert result.timetable is not None
    assert fixed in result.timetable.assignments
    check_valid(_problem(fixed), result.timetable)


def test_rest_is_scheduled_around_the_fixed_assignment() -> None:
    result = solve(_problem(Assignment("u1", 0, 0, "R1")))
    assert result.timetable is not None
    by_unit = {a.unit_id: a for a in result.timetable.assignments}
    assert (by_unit["u2"].day, by_unit["u2"].period) != (0, 0)  # cùng giáo viên T1


def test_fixed_into_forbidden_period_is_diagnosed() -> None:
    result = solve(_problem(Assignment("u1", 0, 6, "R1")))  # tiết 7 bị cấm
    assert result.status == SolveStatus.INFEASIBLE
    assert "fixed_assignments:u1" in result.conflict_groups


def test_two_fixed_units_clashing_are_diagnosed() -> None:
    # Cùng giáo viên T1, cùng ô.
    result = solve(_problem(Assignment("u1", 0, 0, "R1"), Assignment("u2", 0, 0, "R2")))
    assert result.status == SolveStatus.INFEASIBLE
    assert any(g.startswith("fixed_assignments:") for g in result.conflict_groups)


def test_no_fixed_assignments_changes_nothing() -> None:
    result = solve(_problem())
    assert result.status in {SolveStatus.OPTIMAL, SolveStatus.FEASIBLE}


def _data() -> dict:  # type: ignore[type-arg]
    return generate_v1(seed=3)


@pytest.mark.parametrize(
    ("item", "message"),
    [
        ({"unit_id": "nope", "day": 0, "start_period": 0, "room_id": "G314"}, "không tồn tại"),
        ({"unit_id": "{u}", "day": 0, "start_period": 0, "room_id": "X"}, "phòng không tồn tại"),
        ({"unit_id": "{u}", "day": 99, "start_period": 0, "room_id": "G314"}, "ngoài lưới"),
        ({"unit_id": "{u}", "day": 0, "start_period": 7, "room_id": "G314"}, "ngoài lưới"),
    ],
)
def test_loader_rejects_bad_fixed_assignments(item: dict, message: str) -> None:  # type: ignore[type-arg]
    data = _data()
    unit_id = problem_from_dict(data).lesson_units[0].id
    item = {k: (unit_id if v == "{u}" else v) for k, v in item.items()}
    data["fixed_assignments"] = [item]
    with pytest.raises(InvalidProblemError, match=message):
        problem_from_dict(data)


def test_loader_rejects_duplicate_fixed_unit() -> None:
    data = _data()
    unit_id = problem_from_dict(data).lesson_units[0].id
    one = {"unit_id": unit_id, "day": 0, "start_period": 0, "room_id": "G314"}
    data["fixed_assignments"] = [one, one]
    with pytest.raises(InvalidProblemError, match="hai lần"):
        problem_from_dict(data)


def test_handler_keeps_fixed_assignments_end_to_end() -> None:
    data = _data()
    data["solver"] = {"time_limit_s": 20, "num_workers": 1, "random_seed": 0}
    handler = make_solve_handler(build_default_solver, check_timetable)
    first = json.loads(handler(json.dumps(data).encode()))
    pick = first["assignments"][0]
    data["fixed_assignments"] = [
        {
            "unit_id": pick["unit_id"],
            "day": pick["day"],
            "start_period": pick["start_period"],
            "room_id": pick["room_id"],
        }
    ]
    second = json.loads(handler(json.dumps(data).encode()))
    assert second["violations"] == []
    kept = {a["unit_id"]: a for a in second["assignments"]}[pick["unit_id"]]
    assert (kept["day"], kept["start_period"], kept["room_id"]) == (
        pick["day"],
        pick["start_period"],
        pick["room_id"],
    )
