from uuid import uuid4

from fastapi.testclient import TestClient

from timetable.application.use_cases.get_job import (
    JobNotFoundError,
)
from timetable.domain.entities.job import Job, JobStatus
from timetable.interfaces.api.dependencies import get_get_job
from timetable.interfaces.api.main import app


class FakeGetJob:
    """Fake use case so API tests need no database or worker."""

    def __init__(self, job: Job | None) -> None:
        self.job = job

    def execute(self, job_id):
        if self.job is None:
            raise JobNotFoundError(str(job_id))
        return self.job


def test_get_job_returns_queued_job() -> None:
    job_id = uuid4()
    fake = FakeGetJob(
        Job(
            id=job_id,
            status=JobStatus.QUEUED,
            input_ref="inputs/example.json",
        )
    )
    app.dependency_overrides[get_get_job] = lambda: fake

    try:
        client = TestClient(app)
        response = client.get(f"/jobs/{job_id}")

        assert response.status_code == 200
        assert response.json() == {
            "job_id": str(job_id),
            "status": "QUEUED",
            "result_ref": None,
        }
    finally:
        app.dependency_overrides.pop(get_get_job, None)


def test_get_job_returns_done_for_completed_job() -> None:
    job_id = uuid4()
    fake = FakeGetJob(
        Job(
            id=job_id,
            status=JobStatus.COMPLETED,
            input_ref="inputs/example.json",
            result_ref="results/example.json",
        )
    )
    app.dependency_overrides[get_get_job] = lambda: fake

    try:
        client = TestClient(app)
        response = client.get(f"/jobs/{job_id}")

        assert response.status_code == 200
        assert response.json() == {
            "job_id": str(job_id),
            "status": "DONE",
            "result_ref": "results/example.json",
        }
    finally:
        app.dependency_overrides.pop(get_get_job, None)


def test_get_job_returns_404_when_job_does_not_exist() -> None:
    fake = FakeGetJob(None)
    app.dependency_overrides[get_get_job] = lambda: fake

    try:
        client = TestClient(app)
        response = client.get(f"/jobs/{uuid4()}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"
    finally:
        app.dependency_overrides.pop(get_get_job, None)


def test_get_job_rejects_invalid_uuid() -> None:
    client = TestClient(app)
    response = client.get("/jobs/not-a-valid-uuid")

    assert response.status_code == 422
