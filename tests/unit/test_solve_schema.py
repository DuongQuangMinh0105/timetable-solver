import pytest
from pydantic import ValidationError

from timetable.interfaces.api.schemas.solve import (
    GridInput,
    SolveRequest,
)


def test_grid_rejects_duplicate_allowed_periods() -> None:
    with pytest.raises(ValidationError):
        GridInput(
            days=6,
            periods=8,
            allowed_periods=[0, 1, 1, 2],
        )


def test_grid_rejects_period_outside_grid() -> None:
    with pytest.raises(ValidationError):
        GridInput(
            days=6,
            periods=8,
            allowed_periods=[0, 8],
        )


def test_grid_rejects_empty_allowed_periods() -> None:
    with pytest.raises(ValidationError):
        GridInput(
            days=6,
            periods=8,
            allowed_periods=[],
        )


def test_solve_request_accepts_empty_lesson_units() -> None:
    payload = {
        "schema_version": "0.1",
        "grid": {
            "days": 6,
            "periods": 8,
            "allowed_periods": [0, 1, 2, 3, 4, 5],
        },
        "rooms": [
            {
                "id": "G314",
                "name": "G314",
                "capacity": 30,
            }
        ],
        "teachers": [{"id": "T01", "name": "Teacher 1"}],
        "class_groups": [
            {
                "id": "C-A1",
                "name": "Class A1",
                "size": 28,
            }
        ],
        "courses": [
            {
                "id": "M-A1-ENG",
                "name": "English",
                "class_id": "C-A1",
                "teacher_id": "T01",
                "periods_per_week": 3,
            }
        ],
        "lesson_units": [],
    }

    request = SolveRequest.model_validate(payload)

    assert request.lesson_units == []
    assert request.constraints.max_consecutive_periods == 2
    assert request.solver.time_limit_s == 60
    assert request.solver.num_workers == 8
    assert request.solver.random_seed == 0


def _sample_request(**extra: object) -> dict[str, object]:
    import json
    from pathlib import Path

    data = json.loads(Path("docs/schema/input.sample.json").read_text(encoding="utf-8"))
    data.update(extra)
    return data  # type: ignore[no-any-return]


def test_request_accepts_current_constraint_config_version() -> None:
    request = SolveRequest.model_validate(_sample_request(constraint_config_version="1.0"))
    assert request.constraint_config_version == "1.0"


def test_request_rejects_unknown_constraint_config_version() -> None:
    with pytest.raises(ValidationError, match="constraint_config_version"):
        SolveRequest.model_validate(_sample_request(constraint_config_version="99.0"))
