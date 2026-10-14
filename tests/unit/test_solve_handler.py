import json

import pytest

from conftest import SAMPLE_PATH
from timetable.application.dto.solve import SolveOptions, SolveResult, SolveStatus
from timetable.domain.entities import Assignment, Problem, Timetable
from timetable.domain.services.timetable_checker import check_timetable
from timetable.domain.violation import Violation
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.infrastructure.solver.solve_handler import (
    InvalidTimetableError,
    make_solve_handler,
)


def _sample_bytes(time_limit_s: float = 20) -> bytes:
    data = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    data["solver"] = {"time_limit_s": time_limit_s, "num_workers": 1, "random_seed": 0}
    return json.dumps(data).encode("utf-8")


def test_handler_solves_sample_and_returns_json() -> None:
    handler = make_solve_handler(CpSatSolver(), check_timetable)

    result = json.loads(handler(_sample_bytes()))

    assert result["ok"] is True
    assert result["status"] in {"OPTIMAL", "FEASIBLE"}
    assert result["violations"] == []
    assert len(result["assignments"]) == 25  # 25 lesson_units trong dữ liệu mẫu
    assert set(result["assignments"][0]) == {"unit_id", "day", "period", "room_id"}


def test_handler_reports_infeasible_without_raising() -> None:
    data = json.loads(_sample_bytes())
    data["grid"]["allowed_periods"] = [0]  # quá ít ô để xếp hết các ca học
    handler = make_solve_handler(CpSatSolver(), check_timetable)

    result = json.loads(handler(json.dumps(data).encode("utf-8")))

    assert result["status"] == "INFEASIBLE"
    assert result["ok"] is False
    assert result["assignments"] == []


def test_handler_raises_when_checker_finds_violations() -> None:
    def always_bad(_p: Problem, _t: Timetable) -> list[Violation]:
        return [Violation("X", "lỗi giả")]

    handler = make_solve_handler(CpSatSolver(), always_bad)

    with pytest.raises(InvalidTimetableError, match="X"):
        handler(_sample_bytes())


def test_handler_rejects_invalid_json() -> None:
    handler = make_solve_handler(CpSatSolver(), check_timetable)

    with pytest.raises(ValueError):
        handler(b"khong phai json")


def test_handler_works_with_fake_solver() -> None:
    class FakeSolver:
        def solve(self, problem: Problem, options: SolveOptions) -> SolveResult:
            units = problem.lesson_units
            rooms = problem.rooms
            tt = Timetable(tuple(Assignment(u.id, 0, 0, rooms[0].id) for u in units))
            return SolveResult(status=SolveStatus.FEASIBLE, timetable=tt)

    handler = make_solve_handler(FakeSolver(), lambda _p, _t: [])

    result = json.loads(handler(_sample_bytes()))

    assert result["status"] == "FEASIBLE"
    assert len(result["assignments"]) == 25
