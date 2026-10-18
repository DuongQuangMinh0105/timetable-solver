import json
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import delete

from timetable.application.use_cases.submit_solve_job import SubmitSolveJob
from timetable.infrastructure.persistence.database import SessionFactory
from timetable.infrastructure.persistence.job_repository import JobRepository
from timetable.infrastructure.persistence.models import BlobModel, JobModel
from timetable.infrastructure.storage.postgres import PostgresStorage
from timetable.interfaces.api.dependencies import get_submit_solve_job
from timetable.interfaces.api.main import app
from timetable.interfaces.api.schemas.solve import SolveRequest


class FakeDispatcher:
    """Prevent integration tests from enqueueing real worker jobs."""

    def dispatch(self, job_id: str) -> None:
        pass


def test_concurrent_solve_requests_persist_independent_jobs() -> None:
    storage = PostgresStorage()
    repository = JobRepository()

    def build_use_case() -> SubmitSolveJob:
        return SubmitSolveJob(
            repository=repository,
            storage=storage,
            dispatcher=FakeDispatcher(),
        )

    app.dependency_overrides[get_submit_solve_job] = build_use_case

    payloads = [
        {
            "schema_version": "1.0",
            "grid": {
                "days": 5,
                "periods": 6,
                "allowed_periods": [0, 1, 2, 3, 4, 5],
            },
            "rooms": [{"id": f"room-{i}", "name": f"Room {i}", "capacity": 30}],
            "teachers": [{"id": f"teacher-{i}", "name": f"Teacher {i}"}],
            "class_groups": [{"id": f"class-{i}", "name": f"Class {i}", "size": 25}],
            "courses": [
                {
                    "id": f"course-{i}",
                    "name": f"Course {i}",
                    "class_id": f"class-{i}",
                    "teacher_id": f"teacher-{i}",
                    "periods_per_week": 2,
                }
            ],
        }
        for i in range(5)
    ]

    job_ids: list[UUID] = []

    try:

        def submit(payload: dict[str, object]) -> tuple[int, dict]:
            with TestClient(app) as client:
                response = client.post("/solve", json=payload)
                return response.status_code, response.json()

        with ThreadPoolExecutor(max_workers=5) as executor:
            responses = list(executor.map(submit, payloads))

        assert all(status_code == 202 for status_code, _ in responses)

        job_ids = [UUID(body["job_id"]) for _, body in responses]
        assert len(set(job_ids)) == len(payloads)

        expected_by_job_id = {
            UUID(body["job_id"]): SolveRequest.model_validate(payload).model_dump(mode="json")
            for (_, body), payload in zip(responses, payloads, strict=True)
        }

        for job_id in job_ids:
            job = repository.get_by_id(job_id)
            assert job is not None
            assert job.status.value == "queued"
            assert job.input_ref == f"inputs/{job_id}.json"

            stored_payload = json.loads(storage.get(job.input_ref))
            expected_payload = expected_by_job_id[job_id]

            assert stored_payload == expected_payload

    finally:
        app.dependency_overrides.pop(get_submit_solve_job, None)

        if job_ids:
            input_refs = [f"inputs/{job_id}.json" for job_id in job_ids]

            with SessionFactory() as session:
                session.execute(delete(JobModel).where(JobModel.id.in_(job_ids)))
                session.execute(delete(BlobModel).where(BlobModel.key.in_(input_refs)))
                session.commit()
