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
    data: dict[str, Any] = json.loads(
        SAMPLE_PATH.read_text(encoding="utf-8")
    )
    data["solver"] = {
        "time_limit_s": 30,
        "num_workers": 1,
        "random_seed": 0,
    }
    return data


def _bytes(data: dict[str, Any]) -> bytes:
    return json.dumps(data).encode("utf-8")


def _plain_solver(_problem: Problem, _data: dict[str, Any]) -> SolverPort:
    """Chỉ áp dụng ràng buộc cứng, không có hàm mục tiêu."""
    return CpSatSolver()


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
        mba = {
            course["id"]
            for course in data["courses"]
            if course["required_room_type"] == "mba"
        }

        sessions = [
            (
                assignment["course_id"],
                assignment["day"],
                assignment["start_period"],
                assignment["room_id"],
            )
            for assignment in result["assignments"]
        ]

        weights = soft_weights_from_dict(data)

        assert reference_cost(
            sessions,
            {5},
            mba,
            "G316",
            weights,
        ) == result["cost_terms"]


def test_result_has_agreed_format() -> None:
    handler = make_solve_handler(_plain_solver, check_timetable)

    result = json.loads(handler(_bytes(_sample())))

    assert set(result) == {
        "constraint_config_version",
        "status",
        "objective",
        "cost_terms",
        "assignments",
        "violations",
    }

    assert result["objective"] is None
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
    data["grid"]["allowed_periods"] = [0]

    handler = make_solve_handler(_plain_solver, check_timetable)
    result = json.loads(handler(_bytes(data)))

    assert result["status"] == "INFEASIBLE"
    assert result["assignments"] == []
    assert result["objective"] is None


def test_handler_raises_when_checker_finds_violations() -> None:
    def always_bad(
        problem: Problem,
        timetable: Timetable,
    ) -> list[Violation]:
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
        def solve(
            self,
            problem: Problem,
            options: SolveOptions,
        ) -> SolveResult:
            timetable = Timetable(
                tuple(
                    Assignment(unit.id, 0, 0, problem.rooms[0].id)
                    for unit in problem.lesson_units
                )
            )

            return SolveResult(
                status=SolveStatus.FEASIBLE,
                timetable=timetable,
                objective=15.0,
            )

    def always_valid(
        problem: Problem,
        timetable: Timetable,
    ) -> list[Violation]:
        return []

    handler = make_solve_handler(
        lambda _problem, _data: FakeSolver(),
        always_valid,
    )

    result = json.loads(handler(_bytes(_sample())))

    assert result["status"] == "FEASIBLE"
    assert result["objective"] == 15
    assert isinstance(result["objective"], int)
    assert len(result["assignments"]) == 25


def test_soft_weights_follow_input_order_room_sat_g316() -> None:
    data = {
        "soft_weights": {
            "avoid_saturday": 10,
            "room_stability": 5,
            "reserve_mba_room": 2,
        }
    }

    assert soft_weights_from_dict(data) == (5, 10, 2)


def test_soft_weights_use_defaults_when_missing() -> None:
    assert soft_weights_from_dict({}) == soft_weights_from_dict(
        {"soft_weights": {}}
    )

    assert soft_weights_from_dict(
        {"soft_weights": {"avoid_saturday": 7}}
    )[1] == 7


def test_soft_weights_accept_whole_floats_and_reject_fractions() -> None:
    assert soft_weights_from_dict(
        {"soft_weights": {"avoid_saturday": 10.0}}
    )[1] == 10

    with pytest.raises(ValueError, match="avoid_saturday"):
        soft_weights_from_dict(
            {"soft_weights": {"avoid_saturday": 2.5}}
        )


class _RecordingSolver:
    """Bộ giải giả ghi lại tùy chọn nhận được."""

    def __init__(self) -> None:
        self.options: SolveOptions | None = None

    def solve(
        self,
        problem: Problem,
        options: SolveOptions,
    ) -> SolveResult:
        self.options = options
        return SolveResult(status=SolveStatus.UNKNOWN)


def _workers_used(
    monkeypatch: pytest.MonkeyPatch,
    cap: str | None,
    requested: int,
) -> int:
    if cap is None:
        monkeypatch.delenv("SOLVER_MAX_WORKERS", raising=False)
    else:
        monkeypatch.setenv("SOLVER_MAX_WORKERS", cap)

    data = _sample()
    data["solver"] = {
        "time_limit_s": 5,
        "num_workers": requested,
        "random_seed": 0,
    }

    solver = _RecordingSolver()
    make_solve_handler(
        lambda _problem, _data: solver,
        check_timetable,
    )(_bytes(data))

    assert solver.options is not None
    return solver.options.num_workers


def test_max_workers_env_caps_requested_workers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _workers_used(monkeypatch, cap="1", requested=8) == 1


def test_max_workers_env_does_not_raise_requested_workers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _workers_used(monkeypatch, cap="4", requested=2) == 2


def test_workers_unchanged_without_max_workers_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _workers_used(monkeypatch, cap=None, requested=8) == 8


def test_max_workers_env_rejects_invalid_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="SOLVER_MAX_WORKERS"):
        _workers_used(monkeypatch, cap="0", requested=8)


def _time_limit_used(
    monkeypatch: pytest.MonkeyPatch,
    cap: str | None,
    requested: float,
) -> float:
    monkeypatch.delenv("SOLVER_MAX_WORKERS", raising=False)

    if cap is None:
        monkeypatch.delenv("SOLVER_MAX_TIME_S", raising=False)
    else:
        monkeypatch.setenv("SOLVER_MAX_TIME_S", cap)

    data = _sample()
    data["solver"] = {
        "time_limit_s": requested,
        "num_workers": 1,
        "random_seed": 0,
    }

    solver = _RecordingSolver()
    make_solve_handler(
        lambda _problem, _data: solver,
        check_timetable,
    )(_bytes(data))

    assert solver.options is not None
    return solver.options.time_limit_s


def test_max_time_env_caps_requested_time_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _time_limit_used(monkeypatch, cap="30", requested=60) == 30


def test_max_time_env_does_not_raise_requested_time_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _time_limit_used(monkeypatch, cap="30", requested=10) == 10


def test_time_limit_unchanged_without_max_time_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _time_limit_used(monkeypatch, cap=None, requested=60) == 60


@pytest.mark.parametrize("bad", ["0", "abc"])
def test_max_time_env_rejects_invalid_value(
    monkeypatch: pytest.MonkeyPatch,
    bad: str,
) -> None:
    with pytest.raises(ValueError, match="SOLVER_MAX_TIME_S"):
        _time_limit_used(monkeypatch, cap=bad, requested=60)


def test_result_carries_constraint_config_version() -> None:
    from timetable.domain.constraint_config import CONSTRAINT_CONFIG_VERSION

    handler = make_solve_handler(
        lambda _problem, _data: _RecordingSolver(),
        check_timetable,
    )

    result = json.loads(handler(_bytes(_sample())))

    assert result["constraint_config_version"] == CONSTRAINT_CONFIG_VERSION


def test_unsupported_constraint_config_version_is_rejected() -> None:
    from timetable.infrastructure.problem_loader import InvalidProblemError

    data = _sample()
    data["constraint_config_version"] = "99.0"

    with pytest.raises(InvalidProblemError, match="constraint_config_version"):
        make_solve_handler(
            lambda _problem, _data: _RecordingSolver(),
            check_timetable,
        )(_bytes(data))


def test_missing_constraint_config_version_is_accepted() -> None:
    data = _sample()
    data.pop("constraint_config_version", None)

    make_solve_handler(
        lambda _problem, _data: _RecordingSolver(),
        check_timetable,
    )(_bytes(data))