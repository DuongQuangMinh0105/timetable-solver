
import json
from typing import cast

import pytest
from pydantic import ValidationError

from timetable.application.dto.solve import SolveResult, SolveStatus
from timetable.domain.entities import Assignment, Timetable
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.infrastructure.solver.handler import create_solver_handler

VALID_PAYLOAD = {
    "schema_version": "1.0",
    "grid": {
        "days": 1,
        "periods": 2,
        "allowed_periods": [0, 1],
    },
    "rooms": [
        {
            "id": "R1",
            "name": "Room 1",
            "capacity": 30,
        }
    ],
    "teachers": [{"id": "T1", "name": "Teacher 1"}],
    "class_groups": [{"id": "C1", "name": "Class 1", "size": 20}],
    "courses": [
        {
            "id": "SUB1",
            "name": "Subject 1",
            "class_id": "C1",
            "teacher_id": "T1",
            "periods_per_week": 1,
        }
    ],
    "constraints": {"max_consecutive_periods": 2},
    "solver": {
        "time_limit_s": 1.0,
        "num_workers": 1,
        "random_seed": 0,
    },
}


class FakeSolver:
    def __init__(self, result: SolveResult) -> None:
        self.result = result
        self.received_problem = None
        self.received_options = None

    def solve(self, problem, options) -> SolveResult:
        self.received_problem = problem
        self.received_options = options
        return self.result


def test_handler_serializes_successful_result() -> None:
    result = SolveResult(
        status=SolveStatus.OPTIMAL,
        timetable=Timetable(
            (
                Assignment(
                    unit_id="SUB1-0",
                    day=0,
                    period=0,
                    room_id="R1",
                ),
            )
        ),
        objective=0.0,
        optimal=True,
        objective_bound=0.0,
        cost_terms={"room": 0, "sat": 0, "g316": 0},
    )
    fake_solver = FakeSolver(result)
    handler = create_solver_handler(cast(CpSatSolver, fake_solver))

    output = json.loads(handler(json.dumps(VALID_PAYLOAD).encode("utf-8")))

    assert output["status"] == "OPTIMAL"
    assert output["optimal"] is True
    assert output["timetable"] == [
        {
            "unit_id": "SUB1-0",
            "day": 0,
            "period": 0,
            "room_id": "R1",
        }
    ]
    assert fake_solver.received_problem is not None
    assert fake_solver.received_options.time_limit_s == 1.0


def test_handler_rejects_invalid_json() -> None:
    handler = create_solver_handler()

    with pytest.raises(json.JSONDecodeError):
        handler(b"{invalid json")


def test_handler_rejects_invalid_request_schema() -> None:
    handler = create_solver_handler()
    payload = {**VALID_PAYLOAD, "grid": {"days": 0, "periods": 2, "allowed_periods": [0]}}
    data = json.dumps(payload).encode("utf-8")

    with pytest.raises(ValidationError):
        handler(data)


def test_handler_preserves_infeasible_status() -> None:
    fake_solver = FakeSolver(SolveResult(status=SolveStatus.INFEASIBLE))
    handler = create_solver_handler(cast(CpSatSolver, fake_solver))

    output = json.loads(handler(json.dumps(VALID_PAYLOAD).encode("utf-8")))

    assert output["status"] == "INFEASIBLE"
    assert output["timetable"] is None