from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from timetable.application.use_cases.submit_solve_job import (
    SubmitSolveJobResult,
)
from timetable.domain.entities.job import JobStatus
from timetable.interfaces.api.dependencies import get_submit_solve_job
from timetable.interfaces.api.main import app

TEST_API_KEY = "test-api-key"


class FakeSubmitSolveJob:
    """Fake use case so API tests need no database or worker."""

    def __init__(self) -> None:
        self.called = False

    def execute(
        self,
        payload: dict[str, object],
    ) -> SubmitSolveJobResult:
        self.called = True
        return SubmitSolveJobResult(
            job_id=uuid4(),
            status=JobStatus.QUEUED,
        )


def valid_solve_request() -> dict[str, object]:
    """Return a valid request payload for API tests."""
    return {
        "schema_version": "1.0",
        "grid": {
            "days": 5,
            "periods": 6,
            "allowed_periods": [0, 1, 2, 3, 4, 5],
        },
        "rooms": [
            {
                "id": "room-1",
                "name": "Room 1",
                "capacity": 30,
            }
        ],
        "teachers": [{"id": "teacher-1", "name": "Teacher 1"}],
        "class_groups": [{"id": "class-1", "name": "Class 1", "size": 25}],
        "courses": [
            {
                "id": "course-1",
                "name": "Math",
                "class_id": "class-1",
                "teacher_id": "teacher-1",
                "periods_per_week": 2,
            }
        ],
    }


def test_post_solve_returns_202_and_job_id(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    fake = FakeSubmitSolveJob()
    app.dependency_overrides[get_submit_solve_job] = lambda: fake

    try:
        with TestClient(app) as client:
            response = client.post(
                "/solve",
                json=valid_solve_request(),
                headers={"X-API-Key": TEST_API_KEY},
            )

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "queued"
        assert body["job_id"]
        assert fake.called is True
    finally:
        app.dependency_overrides.pop(get_submit_solve_job, None)


def test_post_solve_rejects_invalid_request(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    fake = FakeSubmitSolveJob()
    app.dependency_overrides[get_submit_solve_job] = lambda: fake

    try:
        with TestClient(app) as client:
            response = client.post(
                "/solve",
                json={"schema_version": "1.0"},
                headers={"X-API-Key": TEST_API_KEY},
            )

        assert response.status_code == 422
        assert fake.called is False
    finally:
        app.dependency_overrides.pop(get_submit_solve_job, None)


@pytest.mark.parametrize(
    "case",
    [
        "duplicate-room-id",
        "duplicate-teacher-id",
        "duplicate-class-id",
        "duplicate-course-id",
        "duplicate-unit-id",
        "course-unknown-class",
        "course-unknown-teacher",
        "unit-unknown-course",
        "unit-unknown-class",
        "unit-unknown-teacher",
        "unit-class-mismatch",
        "unit-teacher-mismatch",
        "unit-room-type-mismatch",
        "unit-total-mismatch",
        "unit-invalid-duration",
        "weight-negative",
        "weight-fractional",
        "weight-string",
        "weight-boolean",
        "weight-unsupported-key",
        "weight-not-object",
    ],
)
def test_post_solve_rejects_invalid_semantics_before_creating_job(
    monkeypatch: MonkeyPatch,
    case: str,
) -> None:
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    payload = valid_solve_request()
    payload["lesson_units"] = [
        {
            "id": "unit-1",
            "course_id": "course-1",
            "class_id": "class-1",
            "teacher_id": "teacher-1",
            "duration": 2,
        }
    ]
    payload["class_groups"].append({"id": "class-2", "name": "Class 2", "size": 20})
    payload["teachers"].append({"id": "teacher-2", "name": "Teacher 2"})

    if case == "duplicate-room-id":
        payload["rooms"].append(payload["rooms"][0].copy())
    elif case == "duplicate-teacher-id":
        payload["teachers"].append(payload["teachers"][0].copy())
    elif case == "duplicate-class-id":
        payload["class_groups"].append(payload["class_groups"][0].copy())
    elif case == "duplicate-course-id":
        payload["courses"].append(payload["courses"][0].copy())
    elif case == "duplicate-unit-id":
        payload["lesson_units"].append(payload["lesson_units"][0].copy())
    elif case == "course-unknown-class":
        payload["courses"][0]["class_id"] = "missing-class"
    elif case == "course-unknown-teacher":
        payload["courses"][0]["teacher_id"] = "missing-teacher"
    elif case == "unit-unknown-course":
        payload["lesson_units"][0]["course_id"] = "missing-course"
    elif case == "unit-unknown-class":
        payload["lesson_units"][0]["class_id"] = "missing-class"
    elif case == "unit-unknown-teacher":
        payload["lesson_units"][0]["teacher_id"] = "missing-teacher"
    elif case == "unit-class-mismatch":
        payload["lesson_units"][0]["class_id"] = "class-2"
    elif case == "unit-teacher-mismatch":
        payload["lesson_units"][0]["teacher_id"] = "teacher-2"
    elif case == "unit-room-type-mismatch":
        payload["lesson_units"][0]["required_room_type"] = "mba"
    elif case == "unit-total-mismatch":
        payload["lesson_units"][0]["duration"] = 1
    elif case == "unit-invalid-duration":
        payload["lesson_units"][0]["duration"] = 3
    elif case == "weight-negative":
        payload["soft_weights"] = {"avoid_saturday": -1}
    elif case == "weight-fractional":
        payload["soft_weights"] = {"avoid_saturday": 1.5}
    elif case == "weight-string":
        payload["soft_weights"] = {"avoid_saturday": "1"}
    elif case == "weight-boolean":
        payload["soft_weights"] = {"avoid_saturday": True}
    elif case == "weight-unsupported-key":
        payload["soft_weights"] = {"unknown": 1}
    elif case == "weight-not-object":
        payload["soft_weights"] = []

    fake = FakeSubmitSolveJob()
    app.dependency_overrides[get_submit_solve_job] = lambda: fake

    try:
        with TestClient(app) as client:
            response = client.post(
                "/solve",
                json=payload,
                headers={"X-API-Key": TEST_API_KEY},
            )

        assert response.status_code == 422, f"{case}: {response.text}"
        assert fake.called is False
    finally:
        app.dependency_overrides.pop(get_submit_solve_job, None)
