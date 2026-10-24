from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from timetable.application.use_cases.get_job import JobNotFoundError
from timetable.domain.entities.job import Job, JobStatus
from timetable.interfaces.api.dependencies import get_get_job
from timetable.interfaces.api.main import app

TEST_API_KEY = "test-api-key"
AUTH_HEADERS = {"X-API-Key": TEST_API_KEY}


class FakeGetJob:
    """Fake use case so API tests need no database or worker."""

    def __init__(self, job: Job | None) -> None:
        self.job = job

    def execute(self, job_id: UUID) -> Job:
        if self.job is None:
            raise JobNotFoundError(str(job_id))
        return self.job


def test_get_job_returns_queued_job(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
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
        with TestClient(app) as client:
            response = client.get(f"/jobs/{job_id}", headers=AUTH_HEADERS)

        assert response.status_code == 200
        assert response.json() == {
            "job_id": str(job_id),
            "status": "QUEUED",
            "result_ref": None,
        }
    finally:
        app.dependency_overrides.pop(get_get_job, None)


def test_get_job_returns_done_for_completed_job(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
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
        with TestClient(app) as client:
            response = client.get(f"/jobs/{job_id}", headers=AUTH_HEADERS)

        assert response.status_code == 200
        assert response.json() == {
            "job_id": str(job_id),
            "status": "DONE",
            "result_ref": "results/example.json",
        }
    finally:
        app.dependency_overrides.pop(get_get_job, None)


def test_get_job_returns_404_when_job_does_not_exist(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    fake = FakeGetJob(None)
    app.dependency_overrides[get_get_job] = lambda: fake

    try:
        with TestClient(app) as client:
            response = client.get(f"/jobs/{uuid4()}", headers=AUTH_HEADERS)

        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"
    finally:
        app.dependency_overrides.pop(get_get_job, None)


def test_get_job_rejects_invalid_uuid(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", TEST_API_KEY)

    with TestClient(app) as client:
        response = client.get(
            "/jobs/not-a-valid-uuid",
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 422
