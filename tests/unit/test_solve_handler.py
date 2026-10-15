import json
from typing import Any

import pytest

from conftest import SAMPLE_PATH
from timetable.application.dto.solve import SolveOptions, SolveResult, SolveStatus
from timetable.application.ports.solver import SolverPort
from timetable.domain.entities import Assignment, Problem, Timetable
from timetable.domain.rules.soft_constraints import reference_cost
from timetable.domain.services.timetable_checker import check_timetable
from timetable.domain.violation import Violation
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.infrastructure.solver.default_solver import (
    build_default_solver,
    soft_weights_from_dict,
)
from timetable.infrastructure.solver.solve_handler import (
    InvalidTimetableError,
    make_solve_handler,
)


def _sample() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    data["solver"] = {"time_limit_s": 30, "num_workers": 1, "random_seed": 0}
    return data


def _bytes(data: dict[str, Any]) -> bytes:
    return json.dumps(data).encode("utf-8")


def _plain_solver(_problem: Problem, _data: dict[str, Any]) -> SolverPort:
    return CpSatSolver()  # chỉ ràng buộc cứng, không có hàm mục tiêu


def test_handler_solves_sample_with_soft_objective() -> None:
    data = _sample()
    handler = make_solve_handler(build_default_solver, check_timetable)

    result = json.loads(handler(_bytes(data)))

    assert result["status"] in {"OPTIMAL", "FEASIBLE"}
    assert result["violations"] == []
    assert len(result["assignments"]) == len(data["lesson_units"])
    assert set(result["cost_terms"]) == {"room", "sat", "g316"}
    assert result["objective"] is not None
    if result["status"] == "OPTIMAL":
        # Kiểm tra chéo điểm phạt bằng hàm tính độc lập, không dùng bộ giải.
        mba = {c["id"] for c in data["courses"] if c["required_room_type"] == "mba"}
        sessions = [
            (a["course_id"], a["day"], a["start_period"], a["room_id"])
            for a in result["assignments"]
        ]
        weights = soft_weights_from_dict(data)
        assert reference_cost(sessions, {5}, mba, "G316", weights) == result["cost_terms"]


def test_result_has_agreed_format() -> None:
    handler = make_solve_handler(_plain_solver, check_timetable)

    result = json.loads(handler(_bytes(_sample())))

    assert set(result) == {"status", "objective", "cost_terms", "assignments", "violations"}
    assert result["objective"] is None  # không có hàm mục tiêu
    assert result["cost_terms"] == {}
    assert set(result["assignments"][0]) == {
        "unit_id",
        "course_id",
        "class_id",
        "teacher_id",
        "day",
        "start_period",
        "duration",
        "room_id",
    }


def test_handler_reports_infeasible_without_raising() -> None:
    data = _sample()
    data["grid"]["allowed_periods"] = [0]  # quá ít ô để xếp hết các ca học
    handler = make_solve_handler(_plain_solver, check_timetable)

    result = json.loads(handler(_bytes(data)))

    assert result["status"] == "INFEASIBLE"
    assert result["assignments"] == []
    assert result["objective"] is None


def test_handler_raises_when_checker_finds_violations() -> None:
    def always_bad(_p: Problem, _t: Timetable) -> list[Violation]:
        return [Violation("X", "lỗi giả")]

    handler = make_solve_handler(_plain_solver, always_bad)

    with pytest.raises(InvalidTimetableError, match="X"):
        handler(_bytes(_sample()))


def test_handler_rejects_invalid_json() -> None:
    handler = make_solve_handler(_plain_solver, check_timetable)

    with pytest.raises(ValueError):
        handler(b"khong phai json")


def test_handler_works_with_fake_solver() -> None:
    class FakeSolver:
        def solve(self, problem: Problem, options: SolveOptions) -> SolveResult:
            tt = Timetable(
                tuple(Assignment(u.id, 0, 0, problem.rooms[0].id) for u in problem.lesson_units)
            )
            return SolveResult(status=SolveStatus.FEASIBLE, timetable=tt, objective=15.0)

    handler = make_solve_handler(lambda _p, _d: FakeSolver(), lambda _p, _t: [])

    result = json.loads(handler(_bytes(_sample())))

    assert result["status"] == "FEASIBLE"
    assert result["objective"] == 15
    assert isinstance(result["objective"], int)  # 15, không phải 15.0
    assert len(result["assignments"]) == 25


def test_soft_weights_follow_input_order_room_sat_g316() -> None:
    data = {"soft_weights": {"avoid_saturday": 10, "room_stability": 5, "reserve_mba_room": 2}}
    assert soft_weights_from_dict(data) == (5, 10, 2)


def test_soft_weights_use_defaults_when_missing() -> None:
    assert soft_weights_from_dict({}) == soft_weights_from_dict({"soft_weights": {}})
    assert soft_weights_from_dict({"soft_weights": {"avoid_saturday": 7}})[1] == 7


def test_soft_weights_accept_whole_floats_and_reject_fractions() -> None:
    assert soft_weights_from_dict({"soft_weights": {"avoid_saturday": 10.0}})[1] == 10
    with pytest.raises(ValueError, match="avoid_saturday"):
        soft_weights_from_dict({"soft_weights": {"avoid_saturday": 2.5}})
