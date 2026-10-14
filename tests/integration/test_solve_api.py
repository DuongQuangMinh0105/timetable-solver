from uuid import uuid4

from fastapi.testclient import TestClient

from timetable.application.use_cases.submit_solve_job import (
    SubmitSolveJobResult,
)
from timetable.domain.entities.job import JobStatus
from timetable.interfaces.api.dependencies import get_submit_solve_job
from timetable.interfaces.api.main import app


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


def test_post_solve_returns_202_and_job_id() -> None:
    fake = FakeSubmitSolveJob()
    app.dependency_overrides[get_submit_solve_job] = lambda: fake

    try:
        client = TestClient(app)
        response = client.post(
            "/solve",
            json={
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
            },
        )

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "queued"
        assert body["job_id"]
        assert fake.called is True
    finally:
        app.dependency_overrides.pop(get_submit_solve_job, None)


def test_post_solve_rejects_invalid_request() -> None:
    fake = FakeSubmitSolveJob()
    app.dependency_overrides[get_submit_solve_job] = lambda: fake

    try:
        client = TestClient(app)
        response = client.post(
            "/solve",
            json={"schema_version": "1.0"},
        )

        assert response.status_code == 422
        assert fake.called is False
    finally:
        app.dependency_overrides.pop(get_submit_solve_job, None)
