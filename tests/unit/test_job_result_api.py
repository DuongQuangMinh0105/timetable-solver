from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from timetable.application.use_cases.get_job import JobNotFoundError
from timetable.application.use_cases.get_job_result import ResultNotReadyError
from timetable.interfaces.api.dependencies import get_get_job_result
from timetable.interfaces.api.main import app


class _UseCase:
    def __init__(self, outcome: Any) -> None:
        self._outcome = outcome

    def execute(self, job_id: UUID) -> Any:
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


@pytest.fixture(autouse=True)
def _api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "k")


def _call(outcome: Any, key: str | None = "k") -> Any:
    app.dependency_overrides[get_get_job_result] = lambda: _UseCase(outcome)
    try:
        headers = {} if key is None else {"X-API-Key": key}
        return TestClient(app).get(f"/jobs/{uuid4()}/result", headers=headers)
    finally:
        app.dependency_overrides.clear()


def test_returns_result() -> None:
    response = _call({"status": "OPTIMAL", "assignments": []})
    assert response.status_code == 200
    assert response.json()["status"] == "OPTIMAL"


def test_unknown_job_is_404() -> None:
    assert _call(JobNotFoundError("x")).status_code == 404


def test_not_ready_is_409() -> None:
    assert _call(ResultNotReadyError("x")).status_code == 409


def test_missing_api_key_is_401() -> None:
    assert _call({}, key=None).status_code == 401
